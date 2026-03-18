# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ARIES-LITE (Autonomous Real-time Intelligent Eye System) is a research platform for autonomous real-time face tracking on Raspberry Pi 4. It combines IoT, machine learning (dlib face recognition), and PID control theory with a mobile-first Flask web interface. The codebase uses Polish-language comments and variable names.

## Commands

```bash
# Run the application (starts Flask + camera logic thread)
python3 main.py

# Prerequisites on Raspberry Pi
sudo pigpiod                    # Start pigpio daemon (required for servo PWM)

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Validation scripts
scripts/validate-all.sh         # Master validation
scripts/validate-workflows.sh   # GSD workflow validation
```

There are no unit tests or linting tools configured. Verification is empirical (HTTP responses, screenshots, command output).

## Architecture

### Threading Model (4 threads)
- **Main thread**: Flask server (`web/server.py`) — blocks on `app.run()`, serves UI at `http://0.0.0.0:5000`
- **Logic thread**: Real-time camera processing loop (daemon, 30 FPS)
- **Camera thread**: Async frame capture via `src/camera.py` VideoStream (daemon)
- **Vision thread**: Heavy dlib face recognition operations (daemon, async)

### Data Flow
```
Camera → VideoStream (async) → HybridVision.process_frame()
  ├→ HAAR cascade (fast detection, 30 FPS)
  ├→ CSRT/KCF tracker (smooth following)
  └→ Async dlib verification (200-500ms, non-blocking)
      ↓
TrackerMachine.logic_tick() [state machine]
  SAFE_START → SCANNING → TRACKING → IDLE
      ↓
PanTiltSystem.set_angles() → pigpio hardware PWM
      ↓
Flask /video_feed (MJPEG stream)
```

### Key Design Decisions
- **Hybrid vision**: Full dlib on every frame = 2-3 FPS on RPi4, so HAAR cascade handles detection while dlib runs async for verification only
- **PID over Kalman**: Simpler tuning for servo hardware, sufficient for this use case
- **Flask over FastAPI**: Lighter weight for RPi4, built-in werkzeug MJPEG streaming
- **pigpio over RPi.GPIO**: Hardware-level PWM for smoother servo control (requires `sudo pigpiod`)

### Core Modules
- `src/config.py` — All tuning constants: PID gains (Kp=0.05, Ki=0.001, Kd=0.005), servo limits (pan ±60°, tilt ±30°), camera 640x480@30fps
- `src/vision.py` — HybridVision: HAAR + CSRT/KCF tracker + async dlib, uses `_async_lock` for thread safety
- `src/tracker.py` — TrackerMachine state machine with PID controllers, 2-second timeout before scanning
- `src/hardware.py` — PanTiltSystem servo abstraction, graceful mock mode when pigpio unavailable (`PIGPIO_AVAILABLE` flag)
- `web/server.py` — Flask routes, MJPEG streaming, target image upload

### Critical Hardware Constraints
- `smooth_move_to()` must be used at startup — direct servo jumps cause brownout/reboot from current spikes
- Servo angle limits protect camera ribbon cable (pan ±60°, tilt ±30°)
- Shared frame resources guarded by locks (`shared_frame_lock`, `_async_lock`)
- GPIO pins: pan=12, tilt=13; separate 5V/6V power supply required

## Development Methodology (GSD)

The project follows GSD (Get Shit Done) methodology defined in `PROJECT_RULES.md`:
- **Flow**: SPEC → PLAN → EXECUTE → VERIFY → COMMIT
- **Planning lock**: No implementation until `SPEC.md` status is FINALIZED
- **Commits**: `type(scope): description` — one task = one commit
- **Verification**: Every change needs empirical proof (command output, screenshot)
- **State**: `.gsd/STATE.md` maintains session memory across context windows
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
