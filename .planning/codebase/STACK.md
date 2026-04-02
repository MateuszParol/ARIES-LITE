# Technology Stack

**Analysis Date:** 2026-03-30

## Languages

**Primary:**
- Python 3.13.5 - All application code, configuration, entry points

**Secondary:**
- HTML/CSS/JavaScript - Single-page web UI (`web/templates/index.html`) with inline CSS and vanilla JS (no framework)

## Runtime

**Environment:**
- CPython 3.13.5 on Raspberry Pi 4 (Linux aarch64, kernel 6.12.75+rpt-rpi-v8)
- Requires `--system-site-packages` venv for `picamera2` access

**Package Manager:**
- pip (via requirements.txt)
- Lockfile: missing (no pip-tools, no poetry.lock)

## Frameworks

**Core:**
- Flask 3.0.0 - Web server for MJPEG stream + REST API (`web/server.py`)
- Werkzeug 3.0.0 - WSGI server (bundled with Flask, also used for `secure_filename`)

**Vision/ML:**
- OpenCV 4.8.1.78 (`opencv-python-headless` + `opencv-contrib-python-headless`) - HAAR cascade, CSRT tracker, DNN face detection, image encoding
- face_recognition 1.3.0 - dlib-backed face encoding/comparison (main app only)
- dlib 19.24.2 - Underlying HOG + CNN face models (pulled in by face_recognition)

**Control:**
- simple-pid >=2.0.1 - PID controller for pan/tilt servo loop (`src/tracker.py`, `src/modes/test_tracker.py`)

**Hardware:**
- gpiozero 2.0 - `AngularServo` abstraction for PWM servo control (`src/hardware.py`)
- pigpio 1.78 - Hardware-level PWM backend via `PiGPIOFactory` (requires `sudo pigpiod` daemon)

**Testing:**
- No test framework configured (no pytest, no unittest runner)

**Build/Dev:**
- No build tooling (no Makefile, no tox, no pre-commit)

## Key Dependencies

**Critical (core functionality breaks without these):**
- `opencv-contrib-python-headless` 4.8.1.78 - The `contrib` variant is required for `cv2.TrackerCSRT_create()` (CSRT tracker not in base opencv)
- `face_recognition` 1.3.0 - Identity verification in main app; wraps dlib. Compiling dlib from source on RPi4 takes 30+ minutes
- `numpy` 1.26.0 - Array operations for all vision code
- `simple-pid` >=2.0.1 - Both entry points depend on this for servo PID control
- `gpiozero` 2.0 + `pigpio` 1.78 - Servo control (graceful mock fallback when unavailable)

**System packages (not in requirements.txt, must be apt-installed):**
- `python3-picamera2` - Camera backend for test tracker (`src/modes/test_tracker.py`); imported via system-site-packages
- `pigpiod` daemon - Must run before application start (`sudo pigpiod`)
- `libcamera` stack - Required by picamera2 on RPi

**DNN Model Files (not pip-installable):**
- `models/deploy.prototxt` - Caffe model architecture for res10_300x300 SSD face detector
- `models/res10_300x300_ssd_iter_140000.caffemodel` - Pretrained weights (~10MB)

## Configuration

**Environment:**
- No `.env` files present
- No environment variables used; all configuration is in `src/config.py` (Python constants)
- Face recognition tolerance (0.55) is hardcoded in `src/vision.py` line 116, not in config

**Build:**
- No build config files
- No Dockerfile or container configuration
- Application version tracked in `VERSION` file (current: 1.4.0)

**Key Config Constants (`src/config.py`):**
- PID gains: `PID_PAN_P=0.05`, `PID_PAN_I=0.001`, `PID_PAN_D=0.005` (same for tilt)
- Servo limits: pan +/-60 degrees, tilt +/-30 degrees
- Camera: index 0, 640x480 @ 30 FPS (main app); 320x240 YUV420 (test tracker, hardcoded in `src/modes/test_tracker.py`)
- GPIO pins: pan=12, tilt=13 (hardcoded in `src/hardware.py` line 16)

## Platform Requirements

**Development (non-RPi):**
- Python 3.11+ (uses modern typing features)
- `pip install -r requirements.txt` (dlib compilation requires cmake + C++ compiler)
- Main app (`main.py`) runs in mock servo mode; test tracker (`run_test_tracker.py`) exits without picamera2

**Production (Raspberry Pi 4):**
- Raspberry Pi OS (64-bit recommended for dlib performance)
- `sudo apt install python3-picamera2` (for test tracker)
- `sudo pigpiod` running before launch
- Separate 5V/6V power supply for MG-90S servos (USB power causes brownouts)
- Camera module connected (IMX219 or compatible CSI camera)

## Two Distinct Runtime Profiles

**Main App (`main.py`):**
- Flask + OpenCV VideoCapture + HAAR + CSRT + dlib (async) + gpiozero
- Full web UI at `http://0.0.0.0:5000`
- 4 threads: main (Flask), logic, camera, vision

**Test Tracker (`run_test_tracker.py`):**
- Picamera2 + OpenCV DNN (res10_300x300 Caffe) + simple-pid + gpiozero
- No Flask, no dlib, no web UI
- cv2.imshow HUD (headless fallback available)
- 2 threads: main (loop), camera daemon

---

*Stack analysis: 2026-03-30*
