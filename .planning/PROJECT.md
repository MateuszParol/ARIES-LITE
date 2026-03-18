# PROJECT.md — ARIES-LITE

> **Full Name**: Autonomous Real-time Intelligent Eye System — Lightweight Edition
> **Status**: Brownfield (~85% complete)
> **Current Version**: v1.4.0
> **Target Platform**: Raspberry Pi 4 Model B

## Vision

An autonomous real-time face tracking system that combines IoT hardware (pan/tilt servos), hybrid computer vision (HAAR + dlib), and PID control theory to keep a target person centered in frame — controlled entirely via a mobile-first web interface over WiFi.

## Problem Statement

Traditional face tracking on Raspberry Pi either sacrifices accuracy (pure HAAR cascade) or frame rate (full dlib on every frame at 2-3 FPS). ARIES-LITE solves this with a hybrid approach: fast HAAR detection for 30fps responsiveness, CSRT tracker for smooth PID input, and async dlib verification for identity confirmation — all orchestrated through a 4-thread architecture.

## What Exists (Brownfield)

The core system is implemented and functional:
- **Camera pipeline**: Async VideoStream with daemon thread capture
- **Hybrid vision**: HAAR cascade + CSRT tracker + async dlib verification
- **State machine**: SAFE_START → SCANNING → TRACKING → IDLE with PID control
- **Hardware abstraction**: PanTiltSystem with pigpio H-PWM and mock mode
- **Web interface**: Flask server with MJPEG streaming, target upload, command API
- **Mobile-first UI**: Responsive dark-theme Polish interface

## What Remains (~15%)

Based on codebase analysis (see `.planning/codebase/CONCERNS.md`):

1. **Bug fixes**: Missing logger in server.py, face sorting by area
2. **Robustness**: Graceful shutdown, camera lock safety, startup race condition
3. **Quality**: Automated tests, code cleanup, unused dependencies
4. **Security**: Basic auth for API endpoints (network-accessible system)
5. **Operations**: Systemd service, startup scripts, monitoring

## Technical Decisions (Locked)

These architectural choices are validated and should not change:
- Python 3 + Flask (not FastAPI) — lighter for RPi4
- pigpio H-PWM via gpiozero (not RPi.GPIO) — smoother servo control
- Hybrid HAAR+dlib (not pure deep learning) — FPS vs accuracy tradeoff
- PID control (not Kalman filter) — simpler tuning for servo hardware
- Single-page vanilla HTML/CSS/JS — no build toolchain needed
- Polish-language comments and UI text

## Team & Context

- Solo developer project (research/IoT focus)
- Development on Windows, deployment on Raspberry Pi 4
- No CI/CD pipeline, empirical verification
- GSD methodology for project management
