# INTEGRATIONS.md — External Integrations & Interfaces

> Generated: 2026-03-18

## Hardware Integrations

### pigpio Daemon
- **Protocol**: Local socket to pigpiod process
- **Setup**: `sudo pigpiod` before application start
- **Interface**: `gpiozero.pins.pigpio.PiGPIOFactory` → `AngularServo`
- **Pins**: GPIO 12 (pan), GPIO 13 (tilt)
- **Fallback**: Mock mode when pigpio unavailable

### Camera (V4L2)
- **Interface**: `cv2.VideoCapture(0)` via Video4Linux2
- **Resolution**: 640x480 @ 30fps
- **Backend**: OpenCV default (optionally `cv2.CAP_V4L2`)

## Network Interfaces

### Flask HTTP Server
- **Bind**: `0.0.0.0:5000` (all interfaces — accessible over WiFi)
- **Endpoints**:
  - `GET /` — Main UI page
  - `GET /video_feed` — MJPEG stream (multipart/x-mixed-replace)
  - `GET /api/state` — JSON system state
  - `POST /api/command` — JSON command dispatch (START/STOP/CENTER)
  - `POST /api/upload_target` — Multipart file upload

### No External APIs
- No cloud services
- No authentication/authorization
- No database connections
- No message brokers
- Fully self-contained on-device system

## File System
- `tmp_faces/` — Runtime directory for uploaded target images
- `target.jpg` — Default target image (loaded on startup if exists)

## Security Considerations
- Flask runs without TLS (HTTP only)
- No authentication on any endpoint
- File upload accepts any image/* MIME type
- `secure_filename` sanitizes uploaded filenames
- Server binds to all interfaces (0.0.0.0) — accessible to entire network
