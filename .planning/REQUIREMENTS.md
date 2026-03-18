# REQUIREMENTS.md — ARIES-LITE v1.4.0

> **Milestone**: v1.5.0 (Stabilization & Hardening)
> **Generated**: 2026-03-18

## Validated Requirements (Existing — Implemented & Working)

### REQ-01: Async Camera Capture
- **Status**: Validated
- **Module**: `src/camera.py`
- **Description**: Asynchronous video stream capture via daemon thread at 640x480@30fps
- **Evidence**: VideoStream class with threaded update loop

### REQ-02: Hybrid Face Detection
- **Status**: Validated
- **Module**: `src/vision.py`
- **Description**: HAAR cascade for fast detection (~30 FPS), CSRT tracker for smooth following, async dlib for identity verification
- **Evidence**: HybridVision.process_frame() pipeline

### REQ-03: PID Servo Tracking
- **Status**: Validated
- **Module**: `src/tracker.py`
- **Description**: Dual-axis PID controller (Kp=0.05, Ki=0.001, Kd=0.005) with state machine (SAFE_START → SCANNING → TRACKING → IDLE)
- **Evidence**: TrackerMachine with simple-pid integration

### REQ-04: Hardware PWM Servo Control
- **Status**: Validated
- **Module**: `src/hardware.py`
- **Description**: PanTiltSystem with pigpio H-PWM, soft limits (pan ±60°, tilt ±30°), safe smooth_move_to(), mock mode fallback
- **Evidence**: PanTiltSystem class with PIGPIO_AVAILABLE flag

### REQ-05: MJPEG Web Streaming
- **Status**: Validated
- **Module**: `web/server.py`
- **Description**: Flask-based MJPEG stream at /video_feed with HUD overlay (bounding boxes, crosshair, state text)
- **Evidence**: generate_frames() generator + multipart response

### REQ-06: Target Upload API
- **Status**: Validated
- **Module**: `web/server.py`
- **Description**: POST /api/upload_target for hot-swapping target face image from mobile browser
- **Evidence**: upload_target() route with secure_filename

### REQ-07: Mobile-First Web UI
- **Status**: Validated
- **Module**: `web/templates/index.html`
- **Description**: Responsive dark-theme Polish interface with live stream, status bar, control buttons, upload form
- **Evidence**: Single-page HTML with CSS custom properties and viewport meta

### REQ-08: Safe Startup Sequence
- **Status**: Validated
- **Module**: `src/tracker.py`, `src/hardware.py`
- **Description**: Incremental smooth_move_to(0,0) at boot to prevent servo current spikes and brownout
- **Evidence**: start_pipeline() → smooth_move_to() with configurable step/delay

### REQ-09: Lost Target Scanning
- **Status**: Validated
- **Module**: `src/tracker.py`
- **Description**: Automatic pan/tilt sweep pattern after 2-second target loss timeout
- **Evidence**: do_scan() with bidirectional sweep and tilt increment

### REQ-10: Remote Command Control
- **Status**: Validated
- **Module**: `web/server.py`
- **Description**: POST /api/command for START/STOP/CENTER commands from web UI
- **Evidence**: handle_command() route

---

## New Requirements (Remaining ~15%)

### REQ-11: Logger Fix in Server
- **Status**: Validated
- **Priority**: Critical
- **Description**: Add missing `logger` definition in `web/server.py` (currently crashes on CENTER command)
- **Evidence**: `logger = logging.getLogger(__name__)` at module level in web/server.py
- **Traces to**: CONCERNS.md #1

### REQ-12: Face Detection Sort by Area
- **Status**: Validated
- **Priority**: Medium
- **Description**: Sort HAAR detections by bounding box area, select largest (not first) face
- **Evidence**: `sorted(faces, key=lambda f: f[2]*f[3], reverse=True)` in src/vision.py
- **Traces to**: CONCERNS.md #6

### REQ-13: Graceful Shutdown
- **Status**: Validated
- **Priority**: High
- **Description**: Signal handler (SIGINT/SIGTERM) to detach servos, release camera, clean up threads
- **Evidence**: `shutdown()` function + signal handlers in web/server.py
- **Traces to**: CONCERNS.md #2

### REQ-14: Frame Read Thread Safety
- **Status**: Validated
- **Priority**: Medium
- **Description**: Add lock protection to VideoStream.read() for frame access between camera and logic threads
- **Evidence**: `_frame_lock = threading.Lock()` in src/camera.py with lock in read()/update()
- **Traces to**: CONCERNS.md #5

### REQ-15: Non-blocking CENTER Command
- **Status**: Validated
- **Priority**: Medium
- **Description**: Move smooth_move_to() call in CENTER handler to background thread to prevent Flask request blocking
- **Evidence**: `threading.Thread(target=..., daemon=True).start()` in web/server.py handle_command()
- **Traces to**: CONCERNS.md #7

### REQ-16: Startup Race Condition Fix
- **Status**: Validated
- **Priority**: Medium
- **Description**: Ensure Flask routes wait for logic thread initialization before serving requests
- **Evidence**: `init_event = threading.Event()` + `require_init()` guard on all API routes
- **Traces to**: CONCERNS.md #4

### REQ-17: Dependency Cleanup
- **Status**: Validated
- **Priority**: Low
- **Description**: Remove unused `imutils` from requirements.txt
- **Traces to**: CONCERNS.md #8

---

## Traceability Matrix

| REQ | Phase | Status |
|-----|-------|--------|
| REQ-01 | — | Validated |
| REQ-02 | — | Validated |
| REQ-03 | — | Validated |
| REQ-04 | — | Validated |
| REQ-05 | — | Validated |
| REQ-06 | — | Validated |
| REQ-07 | — | Validated |
| REQ-08 | — | Validated |
| REQ-09 | — | Validated |
| REQ-10 | — | Validated |
| REQ-11 | Phase 1 | Validated |
| REQ-12 | Phase 1 | Validated |
| REQ-13 | Phase 2 | Validated |
| REQ-14 | Phase 1 | Validated |
| REQ-15 | Phase 2 | Validated |
| REQ-16 | Phase 2 | Validated |
| REQ-17 | Phase 3 | Validated |
