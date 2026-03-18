# STACK.md — Technology Stack Analysis

> Generated: 2026-03-18 | Source: requirements.txt, src/, web/

## Runtime
- **Python 3.x** (CPython, Raspberry Pi 4 ARM64)
- **OS**: Raspberry Pi OS (Debian-based), headless operation

## Core Dependencies (requirements.txt — 11 pinned)

| Package | Version | Purpose |
|---------|---------|---------|
| flask | 3.0.0 | Web server, MJPEG streaming, REST API |
| werkzeug | 3.0.0 | WSGI utilities (implicit via Flask) |
| opencv-python-headless | 4.8.1.78 | Image processing, HAAR cascade, frame encoding |
| opencv-contrib-python-headless | 4.8.1.78 | CSRT/KCF tracker algorithms |
| face_recognition | 1.3.0 | dlib-based face encoding & comparison |
| dlib | 19.24.2 | Underlying ML library for face_recognition |
| gpiozero | 2.0 | High-level GPIO servo control |
| pigpio | 1.78 | Hardware PWM daemon interface |
| numpy | 1.26.0 | Array operations for CV pipeline |
| simple-pid | 2.0.0 | PID controller implementation |
| imutils | 0.5.4 | OpenCV convenience utilities |

## Hardware Stack
- **SBC**: Raspberry Pi 4 Model B (4GB RAM)
- **Camera**: Pi Camera HD v2 (640x480 @ 30fps via OpenCV V4L2)
- **Servos**: 2x MG-90S on GPIO pins 12 (pan) and 13 (tilt)
- **PWM**: Hardware PWM via pigpio daemon (`sudo pigpiod`)
- **Power**: Separate 5V/6V supply for servos (prevents brownout)

## Frontend
- Vanilla HTML/CSS/JS (single `index.html`)
- No build tools, no npm, no framework
- CSS custom properties for theming
- Fetch API for REST communication

## Infrastructure
- No database
- No container/Docker setup
- No CI/CD pipeline
- No test framework configured
- Git for version control
