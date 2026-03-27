# External Integrations

**Analysis Date:** 2026-03-27

## Hardware Interfaces

**Servo Control (Pan/Tilt):**
- Interface: `gpiozero.AngularServo` with `PiGPIOFactory` backend
- Implementation: `src/hardware.py` — `PanTiltSystem` class
- GPIO Pins: 12 (pan), 13 (tilt)
- Range: AngularServo configured -90 to +90, software-limited to pan +/-60, tilt +/-30 (`src/config.py`)
- Prerequisite: `sudo pigpiod` daemon must be running before application start
- Fallback: Automatic mock mode when pigpio unavailable (`PIGPIO_AVAILABLE` flag)
- Safety: `smooth_move_to()` provides incremental movement at startup to prevent current-spike brownout

**Camera (Main Mode - OpenCV V4L2):**
- Interface: `cv2.VideoCapture(0)` via Video4Linux2
- Implementation: `src/camera.py` — `VideoStream` class
- Resolution: 640x480 @ 30fps (configured in `src/config.py`)
- Threading: Dedicated daemon thread for async frame capture
- Backend: OpenCV default (comment notes optional `cv2.CAP_V4L2` for lower latency)

**Camera (Test Tracker Mode - Picamera2):**
- Interface: `picamera2.Picamera2` native RPi camera API
- Implementation: `src/modes/test_tracker.py` — `Picamera2Stream` class
- Resolution: 320x240 (lores stream), YUV420 format, converted to BGR via OpenCV
- Threading: Dedicated daemon thread with automatic retry (up to 3 attempts) on camera failure
- Display: Upscaled 2x to 640x480 for cv2.imshow, with headless fallback

## APIs & Services

**Flask HTTP Server (Self-Hosted):**
- Bind: `0.0.0.0:5000` (all interfaces, accessible over WiFi)
- Implementation: `web/server.py`
- No TLS (plain HTTP)
- No authentication on any endpoint

**REST Endpoints:**

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| GET | `/` | Main UI page | - | HTML (`web/templates/index.html`) |
| GET | `/video_feed` | MJPEG stream | - | `multipart/x-mixed-replace` |
| GET | `/api/state` | Current system state | - | `{"state": "SCANNING"}` |
| POST | `/api/command` | Control commands | `{"cmd": "START\|STOP\|CENTER"}` | `{"status": "OK"}` |
| POST | `/api/upload_target` | Upload target face image | multipart form (`file` field) | `{"status": "OK", "msg": "..."}` |

**Readiness Guard:**
- All `/api/*` endpoints return HTTP 503 with `{"error": "System uruchamia sie..."}` until `init_event` is set (after camera and tracker initialization)

## Data Storage

**Databases:**
- None. No database of any kind.

**File Storage:**
- `tmp_faces/` directory - Runtime storage for uploaded target face images
- Created automatically on startup: `os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)` in `web/server.py`
- Default target loaded from `tmp_faces/target.jpg` on startup if present
- Filenames sanitized via `werkzeug.utils.secure_filename`

**Caching:**
- None. All state held in-memory across module-level globals and class instances.

## Authentication & Identity

**Auth Provider:**
- None. No authentication or authorization on any endpoint.
- Server is accessible to anyone on the network.

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, no external error reporting)

**Logs:**
- Python stdlib `logging` module throughout all modules
- Format: `[%(levelname)s] %(message)s` (main mode) or `%(asctime)s [%(levelname)s] %(name)s: %(message)s` (test tracker)
- Polish-language log messages throughout
- Key loggers: `MAIN`, `src.hardware`, `src.camera`, `src.vision`, `src.tracker`, `web.server`

## CI/CD & Deployment

**Hosting:**
- Runs directly on Raspberry Pi 4 hardware
- No containerization, no Docker
- Flask development server (werkzeug) used as production server

**CI Pipeline:**
- None. No automated testing or deployment pipeline.

**Deployment:**
- Manual: SSH into RPi, `git pull`, `pip install -r requirements.txt`, `python3 main.py`

## Environment Configuration

**Required env vars:**
- None. All configuration is hardcoded in `src/config.py`.

**Secrets location:**
- No secrets. No API keys, no tokens, no credentials anywhere.
- No `.env` files detected.

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Integration Patterns

**Hardware Abstraction:**
- `src/hardware.py` wraps gpiozero/pigpio behind `PanTiltSystem` class with transparent mock fallback
- Pattern: try-import with `PIGPIO_AVAILABLE` boolean flag, checked at init time
- All servo operations go through `set_angles()` (direct) or `smooth_move_to()` (incremental) methods

**Camera Abstraction:**
- Two separate implementations, not sharing an interface:
  - `src/camera.py` — `VideoStream` class using OpenCV `VideoCapture` (main Flask mode)
  - `src/modes/test_tracker.py` — `Picamera2Stream` class using Picamera2 (standalone test mode)
- Both use dedicated daemon threads for async frame capture with thread-safe `.read()`/`.odczytaj()` methods

**Vision Pipeline:**
- `src/vision.py` — `HybridVision` class combines three detection strategies in a single `process_frame()` call:
  1. CSRT tracker update (fast, when active)
  2. HAAR cascade detection (fallback when tracker lost)
  3. Async dlib verification (heavy, non-blocking daemon thread with `_async_lock`)

**Thread Safety:**
- `shared_frame_lock` in `web/server.py` guards the encoded MJPEG frame shared between logic thread and Flask response generator
- `_frame_lock` in `src/camera.py` guards raw frame between camera thread and logic thread
- `_async_lock` in `src/vision.py` guards target encoding and verification state between vision thread and main logic

**No External Network Calls:**
- Fully self-contained on-device system
- No cloud services, no telemetry, no external API consumption

---

*Integration audit: 2026-03-27*
