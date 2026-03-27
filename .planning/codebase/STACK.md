# Technology Stack

**Analysis Date:** 2026-03-27

## Languages

**Primary:**
- Python 3.13.5 - All backend logic, vision pipeline, hardware control, web server

**Secondary:**
- JavaScript (ES6+, vanilla) - Frontend UI in `web/templates/index.html`, Fetch API for REST calls
- HTML5/CSS3 - Single-page mobile-first UI with CSS custom properties

## Runtime

**Environment:**
- CPython 3.13.5 on Raspberry Pi 4 (ARM64, Raspberry Pi OS / Debian-based)
- pigpio daemon required at OS level (`sudo pigpiod`) for hardware PWM

**Package Manager:**
- pip (standard)
- Lockfile: Not present (only `requirements.txt` with pinned versions)

**Virtual Environment:**
- Standard venv: `python3 -m venv venv`
- Test tracker mode requires `--system-site-packages` for Picamera2 access

## Frameworks

**Core:**
- Flask 3.0.0 - Web server, REST API, MJPEG streaming (`web/server.py`)
- Werkzeug 3.0.0 - WSGI layer under Flask, `secure_filename` for uploads

**Vision/ML:**
- OpenCV 4.8.1.78 (`opencv-python-headless`, `opencv-contrib-python-headless`) - HAAR cascade detection, CSRT/KCF tracking, frame encoding, HUD rendering
- face_recognition 1.3.0 - dlib-based face encoding and comparison for target verification (`src/vision.py`)
- dlib 19.24.2 - Underlying ML library powering face_recognition (HOG-based face encoding)

**Control:**
- simple-pid 2.0.0 - PID controller for dual-axis servo tracking (`src/tracker.py`, `src/modes/test_tracker.py`)

**Hardware:**
- gpiozero 2.0 - High-level servo abstraction via `AngularServo` (`src/hardware.py`)
- pigpio 1.78 - Hardware PWM interface via `PiGPIOFactory` (`src/hardware.py`)
- Picamera2 (system package, not in requirements.txt) - Native RPi camera backend used in test tracker mode (`src/modes/test_tracker.py`)

**Build/Dev:**
- No build tools, no linters, no formatters configured
- No test framework
- Git for version control

## Key Dependencies

**Critical (requirements.txt - 10 pinned packages):**

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
| `simple-pid` | 2.0.0 | PID controller implementation |

**System-level (not in requirements.txt):**
- `picamera2` - Installed via `sudo apt install python3-picamera2`, accessed through `--system-site-packages` venv

**Infrastructure:**
- `threading` (stdlib) - Multi-threaded architecture (4 daemon threads)
- `signal` (stdlib) - Graceful shutdown via SIGINT/SIGTERM handlers
- `logging` (stdlib) - All logging via Python logging module

## Configuration

**Environment:**
- No `.env` files detected; no environment variable configuration
- All configuration is hardcoded constants in `src/config.py`
- Key constants: PID gains (Kp=0.05, Ki=0.001, Kd=0.005), servo limits (pan +/-60, tilt +/-30), camera 640x480@30fps

**Build:**
- No build configuration files (no pyproject.toml, setup.py, setup.cfg)
- Direct `pip install -r requirements.txt` for dependency installation

## Platform Requirements

**Development:**
- Python 3.13+ (tested on 3.13.5)
- Raspberry Pi 4 Model B (4GB RAM recommended)
- Raspberry Pi OS (Debian-based, ARM64)
- pigpio daemon: `sudo pigpiod`
- Camera: Pi Camera HD v2 or compatible CSI camera
- Servos: 2x MG-90S on GPIO pins 12 (pan) and 13 (tilt)
- Separate 5V/6V servo power supply (prevents RPi brownout)

**Production:**
- Same as development; runs directly on RPi4 hardware
- No containerization (no Docker)
- No CI/CD pipeline
- Flask development server used in production (no gunicorn/nginx)

**Mock/Desktop Mode:**
- Hardware module falls back to mock mode when pigpio/gpiozero unavailable (`PIGPIO_AVAILABLE` flag in `src/hardware.py`)
- Camera module uses OpenCV VideoCapture (works with USB webcams on desktop)
- Test tracker mode (`run_test_tracker.py`) requires Picamera2 (RPi-only)

---

*Stack analysis: 2026-03-27*
