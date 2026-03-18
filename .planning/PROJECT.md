# PROJECT.md — ARIES-LITE

> **Full Name**: Autonomous Real-time Intelligent Eye System — Lightweight Edition
> **Status**: Stable (v1.5.0 shipped)
> **Current Version**: v1.5.0
> **Target Platform**: Raspberry Pi 4 Model B

## Vision

An autonomous real-time face tracking system that combines IoT hardware (pan/tilt servos), hybrid computer vision (HAAR + dlib), and PID control theory to keep a target person centered in frame — controlled entirely via a mobile-first web interface over WiFi.

## Problem Statement

Traditional face tracking on Raspberry Pi either sacrifices accuracy (pure HAAR cascade) or frame rate (full dlib on every frame at 2-3 FPS). ARIES-LITE solves this with a hybrid approach: fast HAAR detection for 30fps responsiveness, CSRT tracker for smooth PID input, and async dlib verification for identity confirmation — all orchestrated through a 4-thread architecture.

## Current State

**v1.5.0** stabilized the existing codebase:
- All runtime bugs fixed (logger, face sorting, frame locking)
- Graceful shutdown with signal handlers (servo detach, camera release)
- Non-blocking CENTER command, startup race condition guard
- Clean dependency tree (removed imutils), proper package exports

**652 lines** of Python across 6 core modules + Flask server.

## What Could Come Next

Potential areas for future milestones:
1. **Security**: Basic auth for API endpoints (network-accessible system)
2. **Operations**: Systemd service, startup scripts, monitoring
3. **Testing**: Automated unit/integration tests
4. **Features**: Multi-face tracking priority, recording, face database

## Technical Decisions (Locked)

These architectural choices are validated and should not change:
- Python 3 + Flask (not FastAPI) — lighter for RPi4
- pigpio H-PWM via gpiozero (not RPi.GPIO) — smoother servo control
- Hybrid HAAR+dlib (not pure deep learning) — FPS vs accuracy tradeoff
- PID control (not Kalman filter) — simpler tuning for servo hardware
- Single-page vanilla HTML/CSS/JS — no build toolchain needed
- Polish-language comments and UI text

## Key Decisions

| Decision | Outcome | Milestone |
|----------|---------|-----------|
| Hybrid vision (HAAR fast + dlib async) | Good — 30 FPS maintained | Pre-v1.5 |
| PID over Kalman for servos | Good — sufficient for hardware | Pre-v1.5 |
| Flask over FastAPI | Good — lighter on RPi4 | Pre-v1.5 |
| Signal handlers + try/finally for shutdown | Good — belt-and-suspenders | v1.5 |
| threading.Event for init gate | Good — clean 503 during startup | v1.5 |
| Background thread for CENTER smooth_move | Good — unblocks Flask thread | v1.5 |

## Team & Context

- Solo developer project (research/IoT focus)
- Development on Windows, deployment on Raspberry Pi 4
- No CI/CD pipeline, empirical verification
- GSD methodology for project management

---
*Last updated: 2026-03-18 after v1.5.0 milestone*
