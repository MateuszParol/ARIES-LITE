# Technology Stack

**Analysis Date:** 2026-03-29

## Languages

**Primary:**
- Python 3.13.5 - All backend logic, vision pipeline, hardware control, web server

**Secondary:**
- JavaScript (ES6+, vanilla) - Frontend UI in `web/templates/index.html`, Fetch API for REST calls
- HTML5/CSS3 - Single-page mobile-first UI with CSS custom properties

## Runtime

**Environment:**
- CPython 3.13.5 on Raspberry Pi 4 (ARM64, Raspberry Pi OS / Debian-based, kernel 6.12)
- pigpio daemon required at OS level (`sudo pigpiod`) for hardware PWM

**Package Manager:**
- pip (standard)
- Lockfile: Not present (only `requirements.txt` with pinned versions)

**Virtual Environment:**
- Standard venv: `python3 -m venv venv --system-site-packages`
- `--system-site-packages` required for Picamera2 access in test tracker mode

## Frameworks

**Core:**
- Flask 3.0.0 - Web server, REST API, MJPEG streaming (`web/server.py`)
- Werkzeug 3.0.0 - WSGI layer under Flask, `secure_filename` for uploads

**Vision/ML:**
- OpenCV 4.8.1.78 (`opencv-python-headless`, `opencv-contrib-python-headless`) - HAAR cascade detection, CSRT tracking, frame encoding, HUD rendering
- face_recognition 1.3.0 - dlib-based face encoding and comparison for target verification (`src/vision.py`)
- dlib 19.24.2 - Underlying ML library powering face_recognition (HOG-based face encoding)

**Control:**
- simple-pid >=2.0.1 - PID controller for dual-axis servo tracking (`src/tracker.py`, `src/modes/test_tracker.py`)

**Hardware:**
- gpiozero 2.0 - High-level servo abstraction via `AngularServo` (`src/hardware.py`)
- pigpio 1.78 - Hardware PWM interface via `PiGPIOFactory` (`src/hardware.py`)
- Picamera2 (system package, not in requirements.txt) - Native RPi camera backend used in test tracker mode (`src/modes/test_tracker.py`)

**Build/Dev:**
- No build tools, no linters, no formatters configured
- No test framework
- Git for version control

## Key Dependencies

**Critical (requirements.txt - 10 packages):**

| Package | Version | Role |
|---------|---------|------|
| `flask` | 3.0.0 | Web server, MJPEG streaming, REST API |
| `werkzeug` | 3.0.0 | WSGI utilities (explicit pin, Flask dependency) |
| `opencv-python-headless` | 4.8.1.78 | Core image processing, HAAR cascade, frame encoding |
| `opencv-contrib-python-headless` | 4.8.1.78 | CSRT/KCF tracker algorithms (contrib module) |
| `face_recognition` | 1.3.0 | dlib face encoding and comparison |
| `dlib` | 19.24.2 | ML backbone for face_recognition |
| `gpiozero` | 2.0 | Servo control abstraction |
| `pigpio` | 1.78 | Hardware PWM daemon client |
| `numpy` | 1.26.0 | Array operations for CV pipeline |
| `simple-pid` | >=2.0.1 | PID controller implementation |

**System-level (not in requirements.txt):**
- `picamera2` - Installed via `sudo apt install python3-picamera2`, accessed through `--system-site-packages` venv

**Infrastructure (stdlib):**
- `threading` - Multi-threaded architecture (4 daemon threads in main mode)
- `signal` - Graceful shutdown via SIGINT/SIGTERM handlers
- `logging` - All logging via Python logging module

## Configuration

**Environment:**
- No `.env` files; no environment variable configuration
- All configuration is hardcoded constants in `src/config.py`
- Key constants: PID gains (Kp=0.05, Ki=0.001, Kd=0.005), servo limits (pan +/-60, tilt +/-30), camera 640x480@30fps
- Face recognition tolerance (0.55) is hardcoded in `src/vision.py` line 116, NOT in `src/config.py`

**Build:**
- No build configuration files (no pyproject.toml, setup.py, setup.cfg)
- Direct `pip install -r requirements.txt` for dependency installation

## Platform Requirements

**Development (non-RPi):**
- Python 3.13+
- Hardware module falls back to mock mode when pigpio/gpiozero unavailable (`PIGPIO_AVAILABLE` flag in `src/hardware.py`)
- Camera module uses OpenCV VideoCapture (works with USB webcams on desktop)
- Only `main.py` works on desktop; `run_test_tracker.py` requires Picamera2 (RPi-only, exits with `sys.exit(1)` on import failure)

**Production (Raspberry Pi 4):**
- Raspberry Pi 4 Model B (4GB RAM recommended)
- Raspberry Pi OS (Debian-based, ARM64)
- pigpio daemon: `sudo pigpiod`
- Camera: Pi Camera HD v2 or compatible CSI camera
- Servos: 2x MG-90S on GPIO pins 12 (pan) and 13 (tilt)
- Separate 5V/6V servo power supply (prevents RPi brownout)
- Flask development server (werkzeug) used as production server - no gunicorn/nginx
- No containerization (no Docker), no CI/CD pipeline

## Two Entry Points and Their Stack Differences

| Aspect | `main.py` (Full System) | `run_test_tracker.py` (Test Mode) |
|--------|------------------------|-----------------------------------|
| Camera | OpenCV `VideoCapture` (`src/camera.py`) | Picamera2 YUV420 lores stream (`src/modes/test_tracker.py`) |
| Detection | HAAR + CSRT tracker + async dlib (`src/vision.py`) | HAAR + streak filter (3 consecutive), no dlib (`src/modes/test_tracker.py`) |
| Scanning | Linear raster sweep left-right (`src/tracker.py`) | Sinusoidal oscillation at 0.1 Hz (`src/modes/test_tracker.py`) |
| UI | Flask web UI at port 5000 (`web/server.py`) | Local `cv2.imshow` window or headless fallback |
| Resolution | 640x480 (`src/config.py`) | 320x240 (module constant in `src/modes/test_tracker.py`) |
| Threading | 4 threads (main/Flask, logic, camera, vision) | 2 threads (main loop, camera daemon) |
| States | SAFE_START -> SCANNING -> TRACKING -> IDLE | SCANNING -> TRACKING -> TARGET_LOST -> SCANNING |

---

*Stack analysis: 2026-03-29*
