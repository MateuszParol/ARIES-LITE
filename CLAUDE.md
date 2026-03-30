# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ARIES-LITE (Autonomous Real-time Intelligent Eye System) is a research platform for autonomous real-time face tracking on Raspberry Pi 4. It combines IoT, machine learning (dlib face recognition), and PID control theory with a mobile-first Flask web interface. The codebase uses Polish-language comments, variable names, and method names throughout.

## Commands

```bash
# Run the full application (Flask web UI + camera + vision + servo control)
python3 main.py

# Run standalone test tracker (no Flask, no dlib — HAAR + PID only, uses Picamera2)
python3 run_test_tracker.py

# Prerequisites on Raspberry Pi
sudo pigpiod                    # Start pigpio daemon (required for servo hardware PWM)

# Setup
python3 -m venv venv --system-site-packages   # --system-site-packages needed for picamera2
source venv/bin/activate
pip install -r requirements.txt
```

There are no unit tests or linting tools configured. Verification is empirical (HTTP responses, visual confirmation, command output).

## Architecture

### Two Entry Points
1. **`main.py`** — Full system: Flask web UI + OpenCV VideoCapture + HybridVision (HAAR + dlib) + PID tracking
2. **`run_test_tracker.py`** — Standalone test mode: Picamera2 + HAAR-only detection (streak filter) + PID tracking + sinusoidal scan. No Flask, no dlib. Uses `src/modes/test_tracker.py`.

### Threading Model (main.py — 4 threads)
- **Main thread**: Flask server (`web/server.py`) — blocks on `app.run()`, serves UI at `http://0.0.0.0:5000`
- **Logic thread**: Real-time camera processing loop (`main_loop()` in server.py, daemon)
- **Camera thread**: Async frame capture via `src/camera.py` VideoStream (daemon)
- **Vision thread**: Heavy dlib face recognition operations (daemon, spawned per-verification)

### Data Flow (main.py)
```
Camera → VideoStream (OpenCV) → HybridVision.process_frame()
  ├→ HAAR cascade (fast detection, 30 FPS)
  ├→ CSRT tracker (smooth bbox following between detections)
  └→ Async dlib verification (200-500ms, non-blocking, tolerance=0.55)
      ↓
TrackerMachine.logic_tick() [state machine]
  SAFE_START → SCANNING → TRACKING → IDLE
      ↓
PanTiltSystem.set_angles() → gpiozero AngularServo + PiGPIOFactory (hardware PWM)
      ↓
Flask /video_feed (MJPEG stream)
```

### Data Flow (test tracker)
```
Picamera2Stream (YUV420→BGR, 320x240) → DetekcjaTwarzy.wykryj()
  └→ HAAR with streak filter (3 consecutive detections required)
      ↓
MaszynaStanow.tick() [state machine]
  SCANNING (sinusoidal) → TRACKING → TARGET_LOST → SCANNING
      ↓
PanTiltSystem.set_angles() → same hardware layer
      ↓
cv2.imshow HUD (or headless fallback)
```

### Key Design Decisions
- **Hybrid vision** (main app): Full dlib on every frame = 2-3 FPS on RPi4, so HAAR cascade handles detection while dlib runs async for identity verification only
- **Streak filter** (test tracker): Requires `STREAK_REQUIRED=3` consecutive HAAR detections before accepting a face, reducing false positives without dlib
- **PID over Kalman**: Simpler tuning for servo hardware, sufficient for this use case
- **Flask over FastAPI**: Lighter weight for RPi4, built-in werkzeug MJPEG streaming
- **gpiozero + PiGPIOFactory**: `hardware.py` uses `gpiozero.AngularServo` with `PiGPIOFactory` for hardware-level PWM (requires `sudo pigpiod` daemon)
- **Two camera backends**: OpenCV `VideoCapture` for main app, `Picamera2` (YUV420 lores stream) for test tracker — Picamera2 gives lower latency on RPi but requires system packages

### Core Modules
- `src/config.py` — All tuning constants: PID gains, servo limits, camera resolution, state names. Note: face recognition tolerance (0.55) is hardcoded in `vision.py` (search `tolerance=`), not in config
- `src/vision.py` — HybridVision: HAAR + CSRT tracker + async dlib verification. Thread safety via `_async_lock`
- `src/tracker.py` — TrackerMachine: state machine (SAFE_START→SCANNING→TRACKING→IDLE) with PID controllers
- `src/hardware.py` — PanTiltSystem: servo abstraction with `PIGPIO_AVAILABLE` flag for graceful mock mode on non-RPi systems
- `src/camera.py` — VideoStream: threaded OpenCV capture wrapper (used by main app only)
- `src/modes/test_tracker.py` — Standalone test mode: `Picamera2Stream`, `DetekcjaTwarzy` (HAAR + streak), `MaszynaStanow` (sinusoidal scan), `TestTracker` orchestrator
- `web/server.py` — Flask routes (`/`, `/video_feed`, `/api/state`, `/api/command`, `/api/upload_target`), MJPEG streaming, `init_event` guards endpoints during startup

### Development on Non-RPi Systems
Both entry points run on non-RPi hardware in mock mode — `hardware.py` catches `ImportError` on `gpiozero`/`pigpio` and logs a warning, then all `set_angles()` calls become no-ops. `run_test_tracker.py` will also fail to import `Picamera2` on non-RPi; only `main.py` (OpenCV `VideoCapture`) can run fully on desktop/laptop.

### Critical Hardware Constraints
- `smooth_move_to()` must be used at startup — direct servo jumps cause brownout/reboot from current spikes
- Servo angle limits protect camera ribbon cable (pan ±60°, tilt ±30°)
- Shared frame resources guarded by locks (`shared_frame_lock` in server.py, `_async_lock` in vision.py)
- GPIO pins: pan=12, tilt=13; separate 5V/6V power supply required for servos

### API Endpoints (web/server.py)
- `GET /` — Main UI (renders `web/templates/index.html`)
- `GET /video_feed` — MJPEG stream
- `GET /api/state` — Current tracker state JSON
- `POST /api/command` — Commands: `START` (scanning), `STOP` (idle + detach), `CENTER` (smooth return to 0,0)
- `POST /api/upload_target` — Upload target face image (multipart file)

All API endpoints return 503 until `init_event` is set (system still starting up).

## Development Methodology (GSD)

The project follows GSD (Get Shit Done) methodology defined in `PROJECT_RULES.md`:
- **Flow**: SPEC → PLAN → EXECUTE → VERIFY → COMMIT
- **Planning lock**: No implementation until `SPEC.md` status is FINALIZED
- **Commits**: `type(scope): description` — one task = one commit
- **Verification**: Every change needs empirical proof (command output, screenshot)
- **State**: `.planning/STATE.md` maintains session memory across context windows
- **Phases**: Wave-based execution with dependency grouping

## Commit Conventions

```
feat(phase-N): description    # New feature
fix(scope): description       # Bug fix
docs(scope): description      # Documentation
refactor(scope): description  # No behavior change
test(scope): description      # Tests
chore: description            # Maintenance
```

<!-- GSD:project-start source:PROJECT.md -->
## Project

**PROJECT.md — ARIES-LITE**
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.13.5 - All application code, configuration, entry points
- HTML/CSS/JavaScript - Single-page web UI (`web/templates/index.html`) with inline CSS and vanilla JS (no framework)
## Runtime
- CPython 3.13.5 on Raspberry Pi 4 (Linux aarch64, kernel 6.12.75+rpt-rpi-v8)
- Requires `--system-site-packages` venv for `picamera2` access
- pip (via requirements.txt)
- Lockfile: missing (no pip-tools, no poetry.lock)
## Frameworks
- Flask 3.0.0 - Web server for MJPEG stream + REST API (`web/server.py`)
- Werkzeug 3.0.0 - WSGI server (bundled with Flask, also used for `secure_filename`)
- OpenCV 4.8.1.78 (`opencv-python-headless` + `opencv-contrib-python-headless`) - HAAR cascade, CSRT tracker, DNN face detection, image encoding
- face_recognition 1.3.0 - dlib-backed face encoding/comparison (main app only)
- dlib 19.24.2 - Underlying HOG + CNN face models (pulled in by face_recognition)
- simple-pid >=2.0.1 - PID controller for pan/tilt servo loop (`src/tracker.py`, `src/modes/test_tracker.py`)
- gpiozero 2.0 - `AngularServo` abstraction for PWM servo control (`src/hardware.py`)
- pigpio 1.78 - Hardware-level PWM backend via `PiGPIOFactory` (requires `sudo pigpiod` daemon)
- No test framework configured (no pytest, no unittest runner)
- No build tooling (no Makefile, no tox, no pre-commit)
## Key Dependencies
- `opencv-contrib-python-headless` 4.8.1.78 - The `contrib` variant is required for `cv2.TrackerCSRT_create()` (CSRT tracker not in base opencv)
- `face_recognition` 1.3.0 - Identity verification in main app; wraps dlib. Compiling dlib from source on RPi4 takes 30+ minutes
- `numpy` 1.26.0 - Array operations for all vision code
- `simple-pid` >=2.0.1 - Both entry points depend on this for servo PID control
- `gpiozero` 2.0 + `pigpio` 1.78 - Servo control (graceful mock fallback when unavailable)
- `python3-picamera2` - Camera backend for test tracker (`src/modes/test_tracker.py`); imported via system-site-packages
- `pigpiod` daemon - Must run before application start (`sudo pigpiod`)
- `libcamera` stack - Required by picamera2 on RPi
- `models/deploy.prototxt` - Caffe model architecture for res10_300x300 SSD face detector
- `models/res10_300x300_ssd_iter_140000.caffemodel` - Pretrained weights (~10MB)
## Configuration
- No `.env` files present
- No environment variables used; all configuration is in `src/config.py` (Python constants)
- Face recognition tolerance (0.55) is hardcoded in `src/vision.py` line 116, not in config
- No build config files
- No Dockerfile or container configuration
- Application version tracked in `VERSION` file (current: 1.4.0)
- PID gains: `PID_PAN_P=0.05`, `PID_PAN_I=0.001`, `PID_PAN_D=0.005` (same for tilt)
- Servo limits: pan +/-60 degrees, tilt +/-30 degrees
- Camera: index 0, 640x480 @ 30 FPS (main app); 320x240 YUV420 (test tracker, hardcoded in `src/modes/test_tracker.py`)
- GPIO pins: pan=12, tilt=13 (hardcoded in `src/hardware.py` line 16)
## Platform Requirements
- Python 3.11+ (uses modern typing features)
- `pip install -r requirements.txt` (dlib compilation requires cmake + C++ compiler)
- Main app (`main.py`) runs in mock servo mode; test tracker (`run_test_tracker.py`) exits without picamera2
- Raspberry Pi OS (64-bit recommended for dlib performance)
- `sudo apt install python3-picamera2` (for test tracker)
- `sudo pigpiod` running before launch
- Separate 5V/6V power supply for MG-90S servos (USB power causes brownouts)
- Camera module connected (IMX219 or compatible CSI camera)
## Two Distinct Runtime Profiles
- Flask + OpenCV VideoCapture + HAAR + CSRT + dlib (async) + gpiozero
- Full web UI at `http://0.0.0.0:5000`
- 4 threads: main (Flask), logic, camera, vision
- Picamera2 + OpenCV DNN (res10_300x300 Caffe) + simple-pid + gpiozero
- No Flask, no dlib, no web UI
- cv2.imshow HUD (headless fallback available)
- 2 threads: main (loop), camera daemon
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- snake_case for all Python modules: `video_stream.py`, `test_tracker.py`
- Underscored prefixes for private methods within classes: `_async_lock`, `_mock_mode`, `_petla_przechwytywania`
- snake_case for all functions and methods: `process_frame()`, `load_target_image()`, `smooth_move_to()`
- Polish-language function names in newer code (`src/modes/test_tracker.py`): `wykryj()`, `odczytaj()`, `zatrzymaj()`, `uruchom()`, `resetuj_streak()`, `_rysuj_hud()`, `_skanuj()`, `_sledz()`, `_przejdz_do()`
- English function names in older core modules (`src/vision.py`, `src/tracker.py`, `src/hardware.py`): `process_frame()`, `do_scan()`, `do_tracking()`, `logic_tick()`
- Private methods prefixed with underscore: `_petla_przechwytywania()`, `_rysuj_hud()`
- Polish variable names in newer code: `klatka`, `szara`, `twarze`, `najw`, `srodek_x`, `blad_pan`, `korekta_pan`, `nowy_pan`, `ramka_cx`
- English variable names in older code: `frame`, `bbox`, `gray`, `faces`, `error_pan`, `pan_correction`
- Module-level constants in UPPER_SNAKE_CASE: `PID_PAN_P`, `CAMERA_WIDTH`, `STATE_SCANNING`, `LORES_WIDTH`, `STREAK_REQUIRED`
- Boolean flags use descriptive names: `is_tracking`, `target_verified`, `_verifying_task_active`, `_mock_mode`
- PascalCase: `HybridVision`, `TrackerMachine`, `PanTiltSystem`, `VideoStream`
- Polish class names in newer code: `Picamera2Stream`, `DetekcjaTwarzy`, `MaszynaStanow`, `TestTracker`
## Code Style
- No automated formatter (no black, autopep8, yapf configured)
- 4-space indentation throughout
- No trailing whitespace enforcement
- Line length varies (no enforced limit), typically under 120 characters
- Blank lines between methods within classes (single blank line)
- Two blank lines between top-level definitions
- No linter configured (no flake8, pylint, ruff, mypy)
- No `pyproject.toml`, `setup.cfg`, or `.flake8` files exist
- No pre-commit hooks
- Used in `src/vision.py`: `def process_frame(self, frame: np.ndarray) -> Tuple[Optional[Tuple[int, int, int, int]], bool]:`
- Used in `src/tracker.py`: `def logic_tick(self, bbox: Optional[Tuple[int, int, int, int]], w: int, h: int, is_target: bool):`
- Used in `src/hardware.py`: `def set_angles(self, pan: float, tilt: float) -> None:`
- More thorough in `src/modes/test_tracker.py`: every method has return type annotations
- Convention: Use type hints from `typing` module (`Tuple`, `Optional`, `Generator`) for all new code
## Import Organization
- Relative imports within `src/` package: `from . import config`, `from .hardware import PanTiltSystem`
- Absolute imports from entry points: `from src.camera import VideoStream`, `from src.modes.test_tracker import TestTracker`
- No path aliases configured
## Error Handling
- try/except with `logging.error()` — never re-raise, always log and continue gracefully
- Pattern in `src/vision.py` line 50-53:
- Hardware initialization falls back to mock mode on failure (`src/hardware.py` lines 28-39):
- Camera retry with counter in `src/modes/test_tracker.py` lines 95-131: retries up to `CAMERA_MAX_RETRIES` (3) with `CAMERA_RETRY_DELAY` (1s), then stops system
- `src/hardware.py`: `PIGPIO_AVAILABLE` flag + `_mock_mode` attribute
- `src/modes/test_tracker.py`: `_headless` flag for display fallback
## Logging
- `logger.info("Faza Safe-Start: Wyrownywanie polozenia")`
- `logger.error(f"Verify thread exception: {e}")`
- `logger.info("Hardware servos with PiGPIO initialized successfully.")`
- `logger.info()` — state transitions, initialization events, operational milestones
- `logger.warning()` — clamp limits hit, fallback modes activated, missing optional resources
- `logger.error()` — camera failures, face recognition failures, hardware init failures
- `logger.debug()` — not used anywhere (add for PID tuning data if needed)
## Comments
## Function Design
- Tuples for multi-value returns: `Tuple[Optional[Tuple[int, int, int, int]], bool]`
- `bool` for success/failure: `load_target_image() -> bool`
- `Optional` for nullable returns: `odczytaj() -> Optional[np.ndarray]`
- `str` for state returns: `tick() -> str`
- `None` implicit return for void operations
## Module Design
## Common Patterns
- All tuning parameters live in `src/config.py`
- No environment variables, no `.env` files
- Import as `from . import config` then reference as `config.PID_PAN_P`
- Module-specific constants at module top-level (e.g., `STREAK_REQUIRED` in `src/modes/test_tracker.py`)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Two independent entry points: full system (`main.py`) and standalone test mode (`run_test_tracker.py`)
- State machine drives servo control logic; PID controllers close the feedback loop
- Hybrid vision pipeline: fast HAAR cascade + async dlib verification to maintain FPS on RPi4
- Daemon threads for camera capture and heavy vision work; main thread blocks on Flask HTTP server
- Graceful hardware mock mode when pigpio/gpiozero unavailable (development on non-RPi machines)
## Two System Modes
### Mode 1: Full System (Flask + dlib verification)
- `src/camera.py` VideoStream (OpenCV VideoCapture, daemon thread)
- `src/vision.py` HybridVision (HAAR + CSRT tracker + async dlib)
- `src/tracker.py` TrackerMachine (state machine + PID)
- `src/hardware.py` PanTiltSystem (servo control)
- `web/server.py` Flask app (MJPEG stream, REST API, HTML UI)
### Mode 2: Test Tracker (standalone, no Flask, no dlib)
- `src/modes/test_tracker.py` Picamera2Stream (Picamera2 native, daemon thread)
- `src/modes/test_tracker.py` DetekcjaTwarzy (HAAR only, streak filter)
- `src/modes/test_tracker.py` MaszynaStanow (simplified state machine + PID)
- `src/hardware.py` PanTiltSystem (shared with full system)
- OpenCV imshow for local display (with headless fallback)
## Layers
- Purpose: Central constants for the entire system
- Location: `src/config.py`
- Contains: PID gains, servo limits, camera resolution, state name constants, timing thresholds, file paths
- Depends on: Nothing
- Used by: Every other module
- Purpose: Servo control with safety limits and mock mode
- Location: `src/hardware.py`
- Contains: `PanTiltSystem` class -- `set_angles()`, `smooth_move_to()`, `detach_servos()`
- Depends on: `src/config.py`, `gpiozero` + `pigpio` (optional)
- Used by: `src/tracker.py`, `src/modes/test_tracker.py`
- Purpose: Async frame capture from camera hardware
- Location: `src/camera.py` (full system, OpenCV VideoCapture), `src/modes/test_tracker.py:Picamera2Stream` (test mode, Picamera2)
- Contains: Threaded capture loops with frame locks
- Depends on: `src/config.py`, OpenCV / Picamera2
- Used by: `web/server.py:main_loop()`, `src/modes/test_tracker.py:TestTracker`
- Purpose: Face detection, tracking, and identity verification
- Location: `src/vision.py` (full system), `src/modes/test_tracker.py:DetekcjaTwarzy` (test mode)
- Contains: HAAR cascade detection, CSRT tracker management, async dlib face encoding comparison
- Depends on: OpenCV, face_recognition/dlib, threading
- Used by: `web/server.py:main_loop()`
- Purpose: Decides what the servos do based on vision output
- Location: `src/tracker.py:TrackerMachine` (full system), `src/modes/test_tracker.py:MaszynaStanow` (test mode)
- Contains: State machine logic, PID error calculation, scanning patterns
- Depends on: `src/hardware.py`, `src/config.py`, `simple_pid`
- Used by: `web/server.py:main_loop()`, `src/modes/test_tracker.py:TestTracker`
- Purpose: HTTP interface -- MJPEG video stream, state polling, command API, target upload
- Location: `web/server.py`, `web/templates/index.html`
- Contains: Flask routes, MJPEG generator, main_loop orchestration, signal handlers
- Depends on: All other layers
- Used by: Browser clients over HTTP
## Data Flow
### Full System (main.py):
```
```
### Test Tracker (run_test_tracker.py):
```
```
### State Management
```
```
```
```
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
## Key Abstractions
- Purpose: Abstract servo hardware; mock when unavailable
- Location: `src/hardware.py`
- Pattern: Adapter with runtime mock fallback (`PIGPIO_AVAILABLE` flag, try/except on init)
- Critical: `smooth_move_to()` prevents current-spike brownout at startup
- Purpose: Combine fast detection with slow identity verification
- Location: `src/vision.py`
- Pattern: Pipeline with async offloading -- HAAR (sync, every frame) + CSRT tracker (sync) + dlib (async, on-demand)
- Key method: `process_frame()` returns (bbox, is_target) tuple consumed by state machine
- Purpose: Map vision output to servo commands
- Location: `src/tracker.py` (full), `src/modes/test_tracker.py` (test)
- Pattern: Finite state machine with per-state tick handlers
- States defined as string constants in `src/config.py`
- Purpose: Smooth servo correction to center face in frame
- Location: Both state machine classes instantiate `simple_pid.PID`
- Config: Kp=0.05, Ki=0.001, Kd=0.005, output limits [-10, +10] degrees/tick
- Pan error is negated (line 77 of `src/tracker.py`, line 275 of `src/modes/test_tracker.py`) to invert correction direction
## Entry Points
- Location: `main.py`
- Triggers: `python3 main.py` (requires `sudo pigpiod` on RPi)
- Calls: `web/server.py:start_server_and_logic()`
- Initialization sequence:
- Location: `run_test_tracker.py`
- Triggers: `python3 run_test_tracker.py`
- Calls: `src/modes/test_tracker.py:TestTracker.uruchom()`
- Initialization sequence:
## Error Handling
- **Hardware mock fallback:** `src/hardware.py` catches ImportError for gpiozero/pigpio and sets `_mock_mode = True`. Also catches runtime exceptions during PiGPIOFactory init.
- **Camera retry:** `src/modes/test_tracker.py:Picamera2Stream` retries camera init up to `CAMERA_MAX_RETRIES` (3) with stop/close/reinit cycle
- **API guard:** `web/server.py:require_init()` returns 503 JSON if `init_event` not yet set
- **Vision error swallowing:** `src/vision.py:heavy_task()` catches all exceptions in dlib thread, logs, resets `_verifying_task_active`
- **Headless fallback:** Test tracker catches `cv2.error` on `imshow()` and switches to headless mode
- **Signal handlers:** Both entry points register SIGINT/SIGTERM for cleanup (servo detach, camera release)
## Cross-Cutting Concerns
- Standard `logging` module throughout
- Format configured in entry points: `main.py` uses `[%(levelname)s] %(message)s`, `run_test_tracker.py` uses timestamped format
- Every module creates its own logger via `logging.getLogger(__name__)`
- No input validation on servo angles beyond soft limits (clamping in `set_angles()`)
- File upload validated via werkzeug `secure_filename` and face_recognition encoding check
- No request body validation on `/api/command` (trusts `cmd` field)
- All tuning constants centralized in `src/config.py`
- Exception: face recognition tolerance hardcoded as `0.55` in `src/vision.py:116`
- Exception: test tracker module-level constants in `src/modes/test_tracker.py:24-36` (LORES_WIDTH, HAAR_MIN_NEIGHBORS, STREAK_REQUIRED, SCAN_AMPLITUDE, SCAN_FREQUENCY, etc.)
- No environment variables, no `.env` files, no runtime config
- Flask upload folder created at import time: `os.makedirs(config.TEMP_FACES_DIR, exist_ok=True)`
- Full system: Signal handlers call `shutdown()` in `web/server.py` -- sets `tracker.is_running = False`, stops stream, detaches servos
- Test tracker: `zatrzymaj()` -- stops camera, smooth return to (0,0) via `smooth_move_to()`, detaches servos, destroys CV windows
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
