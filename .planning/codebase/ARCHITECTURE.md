# Architecture

**Analysis Date:** 2026-03-29

## Pattern Overview

**Overall:** Multi-threaded real-time control system with embedded web server

**Key Characteristics:**
- Two independent entry points: full system (`main.py`) and standalone test mode (`run_test_tracker.py`)
- State machine drives servo control logic; PID controllers close the feedback loop
- Hybrid vision pipeline: fast HAAR cascade + async dlib verification to maintain FPS on RPi4
- Daemon threads for camera capture and heavy vision work; main thread blocks on Flask HTTP server
- Graceful hardware mock mode when pigpio/gpiozero unavailable (development on non-RPi machines)

## Two System Modes

### Mode 1: Full System (Flask + dlib verification)

**Entry point:** `main.py` -> `web/server.py:start_server_and_logic()`

Components used:
- `src/camera.py` VideoStream (OpenCV VideoCapture, daemon thread)
- `src/vision.py` HybridVision (HAAR + CSRT tracker + async dlib)
- `src/tracker.py` TrackerMachine (state machine + PID)
- `src/hardware.py` PanTiltSystem (servo control)
- `web/server.py` Flask app (MJPEG stream, REST API, HTML UI)

### Mode 2: Test Tracker (standalone, no Flask, no dlib)

**Entry point:** `run_test_tracker.py` -> `src/modes/test_tracker.py:TestTracker`

Components used:
- `src/modes/test_tracker.py` Picamera2Stream (Picamera2 native, daemon thread)
- `src/modes/test_tracker.py` DetekcjaTwarzy (HAAR only, streak filter)
- `src/modes/test_tracker.py` MaszynaStanow (simplified state machine + PID)
- `src/hardware.py` PanTiltSystem (shared with full system)
- OpenCV imshow for local display (with headless fallback)

**Key difference:** Test tracker uses Picamera2 (native RPi camera API) at 320x240, no dlib, no Flask, no CSRT tracker. It is a self-contained module for validating hardware and PID tuning.

## Layers

**Configuration Layer:**
- Purpose: Central constants for the entire system
- Location: `src/config.py`
- Contains: PID gains, servo limits, camera resolution, state name constants, timing thresholds, file paths
- Depends on: Nothing
- Used by: Every other module

**Hardware Abstraction Layer:**
- Purpose: Servo control with safety limits and mock mode
- Location: `src/hardware.py`
- Contains: `PanTiltSystem` class -- `set_angles()`, `smooth_move_to()`, `detach_servos()`
- Depends on: `src/config.py`, `gpiozero` + `pigpio` (optional)
- Used by: `src/tracker.py`, `src/modes/test_tracker.py`

**Camera Layer:**
- Purpose: Async frame capture from camera hardware
- Location: `src/camera.py` (full system, OpenCV VideoCapture), `src/modes/test_tracker.py:Picamera2Stream` (test mode, Picamera2)
- Contains: Threaded capture loops with frame locks
- Depends on: `src/config.py`, OpenCV / Picamera2
- Used by: `web/server.py:main_loop()`, `src/modes/test_tracker.py:TestTracker`

**Vision Layer:**
- Purpose: Face detection, tracking, and identity verification
- Location: `src/vision.py` (full system), `src/modes/test_tracker.py:DetekcjaTwarzy` (test mode)
- Contains: HAAR cascade detection, CSRT tracker management, async dlib face encoding comparison
- Depends on: OpenCV, face_recognition/dlib, threading
- Used by: `web/server.py:main_loop()`

**Control Layer (State Machine + PID):**
- Purpose: Decides what the servos do based on vision output
- Location: `src/tracker.py:TrackerMachine` (full system), `src/modes/test_tracker.py:MaszynaStanow` (test mode)
- Contains: State machine logic, PID error calculation, scanning patterns
- Depends on: `src/hardware.py`, `src/config.py`, `simple_pid`
- Used by: `web/server.py:main_loop()`, `src/modes/test_tracker.py:TestTracker`

**Web/API Layer:**
- Purpose: HTTP interface -- MJPEG video stream, state polling, command API, target upload
- Location: `web/server.py`, `web/templates/index.html`
- Contains: Flask routes, MJPEG generator, main_loop orchestration, signal handlers
- Depends on: All other layers
- Used by: Browser clients over HTTP

## Data Flow

### Full System (main.py):

```
1. start_server_and_logic() creates: VideoStream, HybridVision, TrackerMachine
2. Logic thread (daemon) starts -> main_loop()
3. Main thread blocks on Flask app.run(host='0.0.0.0', port=5000)

Per-frame in main_loop():
  VideoStream.read()                    -> raw frame (640x480 BGR)
  HybridVision.process_frame(frame)     -> (bbox, is_target)
    |-- If tracker active: CSRT update  -> bbox from tracker
    |-- If no tracker: HAAR detection   -> largest face bbox
    +-- trigger_async_verification()    -> daemon thread runs dlib (200-500ms)
  TrackerMachine.logic_tick(bbox, w, h, is_target)
    |-- SCANNING: sweep pan/tilt via do_scan()
    |-- TRACKING: PID correction via do_tracking()
    +-- IDLE: no-op
  HUD overlay drawn on display_frame
  cv2.imencode('.jpg') -> shared_encoded_frame (protected by shared_frame_lock)

MJPEG stream:
  Browser GET /video_feed -> generate_frames() reads shared_encoded_frame in loop
```

### Test Tracker (run_test_tracker.py):

```
1. TestTracker() creates: Picamera2Stream, DetekcjaTwarzy, MaszynaStanow
2. uruchom() -> kamera.start() -> maszyna.inicjalizuj() (safe start) -> main loop

Per-frame:
  Picamera2Stream.odczytaj()            -> raw frame (320x240 BGR)
  DetekcjaTwarzy.wykryj(frame)          -> bbox (with streak filter) or None
  MaszynaStanow.tick(bbox, w, h)        -> state string
    |-- SCANNING: sinusoidal pan sweep  (math.sin based)
    |-- TRACKING: PID correction
    +-- TARGET_LOST: transition state (1 frame) -> SCANNING
  HUD overlay drawn
  cv2.imshow() or headless mode
```

### State Management

**Full system state machine (`src/tracker.py:TrackerMachine`):**
```
SAFE_START -> (smooth_move_to completes) -> SCANNING
SCANNING -> (bbox + is_target=True) -> TRACKING
TRACKING -> (no bbox for TIME_TO_LOST_SEC) -> SCANNING
Any state -> (API cmd STOP) -> IDLE
IDLE -> (API cmd START) -> SCANNING
IDLE -> (API cmd CENTER) -> smooth_move_to(0,0) on daemon thread
```

**Test tracker state machine (`src/modes/test_tracker.py:MaszynaStanow`):**
```
SCANNING -> (bbox detected, streak >= 3) -> TRACKING
TRACKING -> (no bbox for TIME_TO_LOST_SEC) -> TARGET_LOST
TARGET_LOST -> (next tick) -> SCANNING
```

**Shared state between threads (full system):**
- `shared_encoded_frame` + `shared_frame_lock` -- JPEG bytes shared between logic thread and Flask MJPEG generator
- `init_event` (threading.Event) -- gates API requests until initialization completes
- `HybridVision._async_lock` -- protects target_encoding and target_verified between main loop and dlib verification thread
- `VideoStream._frame_lock` -- protects frame between camera thread and logic thread
- `TrackerMachine.state` -- read by Flask `/api/state`, written by logic thread and `/api/command`

## Threading Model

### Full System Threads (4):

| Thread | Type | Started In | Purpose |
|--------|------|-----------|---------|
| Main | blocking | `main.py` | Flask `app.run()` -- HTTP server |
| Logic | daemon | `web/server.py:start_server_and_logic()` | `main_loop()` -- camera read, vision, PID, HUD encode |
| Camera | daemon | `src/camera.py:VideoStream.start()` | Continuous `stream.read()` into `self.frame` |
| Vision (ephemeral) | daemon | `src/vision.py:trigger_async_verification()` | One-shot dlib face encoding comparison |

### Test Tracker Threads (2):

| Thread | Type | Started In | Purpose |
|--------|------|-----------|---------|
| Main | blocking | `run_test_tracker.py` | TestTracker.uruchom() -- main loop |
| Camera | daemon | `src/modes/test_tracker.py:Picamera2Stream.start()` | Frame capture loop |

### Synchronization:

| Lock | Location | Protects |
|------|----------|----------|
| `shared_frame_lock` | `web/server.py` (module-level) | `shared_encoded_frame` JPEG buffer |
| `_frame_lock` | `src/camera.py:VideoStream` | `self.frame` raw camera frame |
| `_async_lock` | `src/vision.py:HybridVision` | `target_encoding`, `target_verified`, `_verifying_task_active` |
| `_lock` | `src/modes/test_tracker.py:Picamera2Stream` | `self._frame` |
| `init_event` | `web/server.py` (module-level) | Gates API until logic thread finishes init |

### Race Condition Note:

`TrackerMachine.state` in `src/tracker.py` is read/written from multiple threads (logic thread writes in `logic_tick()`, Flask thread reads in `/api/state` and writes in `/api/command`) without a lock. This works in CPython due to GIL for simple attribute access but is not formally thread-safe.

## Key Abstractions

**PanTiltSystem (Hardware Adapter):**
- Purpose: Abstract servo hardware; mock when unavailable
- Location: `src/hardware.py`
- Pattern: Adapter with runtime mock fallback (`PIGPIO_AVAILABLE` flag, try/except on init)
- Critical: `smooth_move_to()` prevents current-spike brownout at startup

**HybridVision (Strategy/Pipeline):**
- Purpose: Combine fast detection with slow identity verification
- Location: `src/vision.py`
- Pattern: Pipeline with async offloading -- HAAR (sync, every frame) + CSRT tracker (sync) + dlib (async, on-demand)
- Key method: `process_frame()` returns (bbox, is_target) tuple consumed by state machine

**TrackerMachine / MaszynaStanow (State Machine):**
- Purpose: Map vision output to servo commands
- Location: `src/tracker.py` (full), `src/modes/test_tracker.py` (test)
- Pattern: Finite state machine with per-state tick handlers
- States defined as string constants in `src/config.py`

**PID Controllers:**
- Purpose: Smooth servo correction to center face in frame
- Location: Both state machine classes instantiate `simple_pid.PID`
- Config: Kp=0.05, Ki=0.001, Kd=0.005, output limits [-10, +10] degrees/tick
- Pan error is negated (line 77 of `src/tracker.py`, line 275 of `src/modes/test_tracker.py`) to invert correction direction

## Entry Points

**`main.py` (Full System):**
- Location: `main.py`
- Triggers: `python3 main.py` (requires `sudo pigpiod` on RPi)
- Calls: `web/server.py:start_server_and_logic()`
- Initialization sequence:
  1. Create VideoStream, HybridVision, TrackerMachine (module globals in `web/server.py`)
  2. Start logic daemon thread running `main_loop()`
  3. Register SIGINT/SIGTERM handlers for graceful shutdown
  4. Block on `app.run(host='0.0.0.0', port=5000)`
  5. Inside logic thread: `stream.start()` -> `tracker.start_pipeline()` (safe start) -> `init_event.set()` -> frame loop

**`run_test_tracker.py` (Standalone Test):**
- Location: `run_test_tracker.py`
- Triggers: `python3 run_test_tracker.py`
- Calls: `src/modes/test_tracker.py:TestTracker.uruchom()`
- Initialization sequence:
  1. Register SIGINT/SIGTERM handlers
  2. Create TestTracker (creates Picamera2Stream, DetekcjaTwarzy, MaszynaStanow)
  3. `kamera.start()` -> `maszyna.inicjalizuj()` (safe start) -> blocking main loop
  4. On exit: `zatrzymaj()` -- stop camera, smooth return to (0,0), detach servos

## Error Handling

**Strategy:** Defensive fallbacks with logging; no exceptions propagated to user

**Patterns:**
- **Hardware mock fallback:** `src/hardware.py` catches ImportError for gpiozero/pigpio and sets `_mock_mode = True`. Also catches runtime exceptions during PiGPIOFactory init.
- **Camera retry:** `src/modes/test_tracker.py:Picamera2Stream` retries camera init up to `CAMERA_MAX_RETRIES` (3) with stop/close/reinit cycle
- **API guard:** `web/server.py:require_init()` returns 503 JSON if `init_event` not yet set
- **Vision error swallowing:** `src/vision.py:heavy_task()` catches all exceptions in dlib thread, logs, resets `_verifying_task_active`
- **Headless fallback:** Test tracker catches `cv2.error` on `imshow()` and switches to headless mode
- **Signal handlers:** Both entry points register SIGINT/SIGTERM for cleanup (servo detach, camera release)

## Cross-Cutting Concerns

**Logging:**
- Standard `logging` module throughout
- Format configured in entry points: `main.py` uses `[%(levelname)s] %(message)s`, `run_test_tracker.py` uses timestamped format
- Every module creates its own logger via `logging.getLogger(__name__)`

**Validation:**
- No input validation on servo angles beyond soft limits (clamping in `set_angles()`)
- File upload validated via werkzeug `secure_filename` and face_recognition encoding check
- No request body validation on `/api/command` (trusts `cmd` field)

**Configuration:**
- All tuning constants centralized in `src/config.py`
- Exception: face recognition tolerance hardcoded as `0.55` in `src/vision.py:116`
- Exception: test tracker module-level constants in `src/modes/test_tracker.py:24-36` (LORES_WIDTH, HAAR_MIN_NEIGHBORS, STREAK_REQUIRED, SCAN_AMPLITUDE, SCAN_FREQUENCY, etc.)
- No environment variables, no `.env` files, no runtime config
- Flask upload folder created at import time: `os.makedirs(config.TEMP_FACES_DIR, exist_ok=True)`

**Cleanup/Shutdown:**
- Full system: Signal handlers call `shutdown()` in `web/server.py` -- sets `tracker.is_running = False`, stops stream, detaches servos
- Test tracker: `zatrzymaj()` -- stops camera, smooth return to (0,0) via `smooth_move_to()`, detaches servos, destroys CV windows

---

*Architecture analysis: 2026-03-29*
