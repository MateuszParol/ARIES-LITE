# External Integrations

**Analysis Date:** 2026-03-30

## APIs & External Services

No external cloud APIs or SaaS services are used. The system is fully self-contained and runs offline on Raspberry Pi 4.

## Hardware Interfaces

**Servo Motors (MG-90S):**
- Interface: Hardware PWM via `gpiozero.AngularServo` + `PiGPIOFactory`
- Implementation: `src/hardware.py` (`PanTiltSystem` class)
- GPIO pins: pan=12 (BCM), tilt=13 (BCM) -- hardcoded in constructor defaults (line 16)
- Range: -90 to +90 degrees (hardware); clamped to pan +/-60, tilt +/-30 (software safety in `set_angles()`)
- Daemon dependency: `pigpiod` must be running (`sudo pigpiod`)
- Mock mode: When `gpiozero`/`pigpio` import fails, `PanTiltSystem` silently becomes a no-op (lines 9-11)
- Power: Requires separate 5V/6V supply; USB power causes brownout on servo startup

**Camera -- Main App (`src/camera.py`):**
- Backend: OpenCV `cv2.VideoCapture` (V4L2 on Linux)
- Resolution: 640x480 @ 30 FPS (configurable via `src/config.py`)
- Threading: Dedicated daemon thread for async frame capture (`VideoStream.update()`)
- Compatible with any V4L2 camera (USB webcam, CSI via v4l2 driver)

**Camera -- Test Tracker (`src/modes/test_tracker.py`):**
- Backend: `picamera2.Picamera2` (libcamera-based, RPi-only)
- Resolution: 320x240 YUV420 lores stream (hardcoded in `Picamera2Stream`, lines 58-59)
- Color pipeline: YUV420p -> BGR via `cv2.cvtColor(klatka_yuv, cv2.COLOR_YUV420p2BGR)` (line 103)
- AWB: Continuous auto white balance (no gain locking); warmup 1.0s after start (line 83)
- Error recovery: Auto-reinitializes camera on failure, up to 3 retries (lines 110-134)
- System package: `python3-picamera2` (apt, not pip)

## ML Models

**HAAR Cascade (Main App):**
- Model: `haarcascade_frontalface_default.xml` (bundled with OpenCV)
- Location: loaded via `cv2.data.haarcascades` path (no local file)
- Used in: `src/vision.py` line 22-23
- Parameters: `scaleFactor=1.1, minNeighbors=5, minSize=(60,60)` (line 85)

**DNN Face Detector (Test Tracker):**
- Model: OpenCV DNN with Caffe backend (res10_300x300 SSD)
- Files: `models/deploy.prototxt`, `models/res10_300x300_ssd_iter_140000.caffemodel`
- Used in: `src/modes/test_tracker.py` (`DetekcjaTwarzy` class, line 172)
- Confidence threshold: 0.5 (line 28)
- Forward pass frequency: every 5th frame (`DNN_SKIP_EVERY=5`, line 29)
- Warmup: dummy forward pass on init to avoid cold-start latency (lines 179-183)

**dlib Face Recognition (Main App only):**
- Library: `face_recognition` (wraps dlib HOG/CNN)
- Used in: `src/vision.py` (`HybridVision` class)
- Tolerance: 0.55 (hardcoded at line 116, NOT in `src/config.py`)
- Execution: Async in daemon thread to avoid blocking 30 FPS loop (lines 100-129)
- Reference encoding: loaded from uploaded image via `/api/upload_target` endpoint

**CSRT Tracker (Main App only):**
- Library: `opencv-contrib-python-headless` (contrib required, not available in base opencv)
- Used in: `src/vision.py` line 57 (`cv2.TrackerCSRT_create()`)
- Purpose: Smooth bbox tracking between HAAR detections (avoids per-frame HAAR cost)

## Data Storage

**Databases:**
- None. No database of any kind.

**File Storage:**
- `tmp_faces/` directory - Uploaded target face images (created at runtime, `web/server.py` line 20)
- `models/` directory - DNN model files (committed to repo)
- Default target image: `tmp_faces/target.jpg` (loaded on startup if exists, `web/server.py` line 128)

**Caching:**
- None. All state is in-memory Python objects.

## Authentication & Identity

**Auth Provider:**
- None. No authentication on any endpoint. Flask server binds to `0.0.0.0:5000` without auth.
- File upload endpoint (`/api/upload_target`) accepts any POST with multipart file.

## Web Interface

**Server:**
- Flask 3.0.0 development server (Werkzeug)
- Host: `0.0.0.0`, Port: `5000` (hardcoded in `web/server.py` line 191)
- No production WSGI server (no gunicorn, no uwsgi)
- `debug=False, use_reloader=False` (line 191)

**Frontend (`web/templates/index.html`):**
- Single HTML file with inline CSS + inline JavaScript
- No build step, no npm, no frontend framework
- Mobile-first responsive design (max-width: 600px container)
- Vanilla `fetch()` API for REST calls
- MJPEG stream via `<img src="/video_feed">`
- State polling: `setInterval` every 1000ms to `/api/state`

**REST Endpoints (`web/server.py`):**
- `GET /` -- Serves `index.html` (line 58-61)
- `GET /video_feed` -- MJPEG multipart stream (line 63-66)
- `GET /api/state` -- JSON `{"state": "SCANNING"}` (line 91-97)
- `POST /api/command` -- JSON body `{"cmd": "START"|"STOP"|"CENTER"}` (line 99-115)
- `POST /api/upload_target` -- Multipart file upload (line 68-89)
- All API endpoints return 503 until `init_event` is set (startup guard, line 30-33)

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, no error reporting service.

**Logs:**
- Python `logging` module throughout all modules
- Format: `[%(levelname)s] %(message)s` (main app), `%(asctime)s [%(levelname)s] %(name)s: %(message)s` (test tracker)
- Debug-level PID diagnostics available via `--debug` flag in test tracker (per-tick P/I/D components)
- No log persistence (stdout only)

## CI/CD & Deployment

**Hosting:**
- Bare metal Raspberry Pi 4 (no containers, no orchestration)

**CI Pipeline:**
- None. No GitHub Actions, no CI configuration files.

**Deployment:**
- Manual: `python3 main.py` or `python3 run_test_tracker.py`
- No systemd service file, no supervisor config
- Utility scripts in `scripts/` directory (search/validation helpers, not deployment)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Network Requirements

- WiFi/Ethernet on RPi for web UI access (Flask on port 5000)
- No outbound internet required (fully offline operation)
- Mobile devices connect via local network to `http://<rpi-ip>:5000`

## System Dependencies Summary

| Dependency | Install Method | Required By | Notes |
|---|---|---|---|
| `pigpiod` daemon | `sudo pigpiod` | Both entry points | Must run before app start |
| `python3-picamera2` | `sudo apt install` | Test tracker only | Needs `--system-site-packages` venv |
| `libcamera` | System package | Test tracker (via picamera2) | Pre-installed on RPi OS |
| CMake + C++ compiler | `sudo apt install cmake g++` | pip install dlib | One-time build dependency |
| V4L2 camera driver | Kernel module | Main app (OpenCV VideoCapture) | Usually pre-loaded |

---

*Integration audit: 2026-03-30*
