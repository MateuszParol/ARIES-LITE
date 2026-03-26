# PROJECT.md — ARIES-LITE

> **Full Name**: Autonomous Real-time Intelligent Eye System — Lightweight Edition
> **Status**: Active (v1.6 in progress)
> **Current Version**: v1.6.0-dev
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

## Current Milestone: v1.6 Test Tracker (Autonomous Control Loop)

**Goal:** Zbudować izolowany moduł testowy z czystą pętlą sterowania (Scan → Detect → PID Track → Target Lost), udowadniający płynne działanie hardware (pigpio + PID) z Picamera2 na RPi OS Bookworm.

**Target features:**
- Izolowany test tracker (`src/modes/test_tracker.py`) — nie modyfikuje istniejącego kodu
- Picamera2 backend (natywne libcamera na Bookworm 64-bit)
- State machine: Safe Startup → Scanning (sinusoida ±45°) → Tracking (PID) → Target Lost (2s timeout)
- Detekcja dowolnej twarzy (HAAR/DNN, bez rozpoznawania tożsamości)
- PID regulator (osobny X/Y) z płynnym ruchem serw MG-90S
- Safe startup: inkrementalne smooth_move do pozycji neutralnej (0,0)

**Constraints:**
- **Hardware**: MG-90S serwa, GPIO 12 (pan) / GPIO 13 (tilt), zasilanie 6V (4xAA), wspólna masa
- **Software**: pigpio (wyłącznie), Picamera2, RPi OS Bookworm 64-bit
- **Isolation**: Nowy moduł — istniejący kod nie może zostać uszkodzony

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
| Picamera2 over OpenCV VideoCapture | — Pending — native libcamera on Bookworm | v1.6 |
| Isolated test module over rewrite | — Pending — preserves stable v1.5 code | v1.6 |

## Team & Context

- Solo developer project (research/IoT focus)
- Development on Windows, deployment on Raspberry Pi 4
- No CI/CD pipeline, empirical verification
- GSD methodology for project management

---
*Last updated: 2026-03-26 after v1.6 milestone start*
