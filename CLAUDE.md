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
