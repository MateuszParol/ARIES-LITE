# PROJECT.md — ARIES-LITE

> **Full Name**: Autonomous Real-time Intelligent Eye System — Lightweight Edition
> **Status**: Active (v1.7 in progress)
> **Current Version**: v1.7.0-dev
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

**v1.6.0** delivered isolated test tracker module:
- `src/modes/test_tracker.py` — standalone pętla sterowania bez Flaska
- Picamera2 backend (YUV420→BGR, 320x240) z Bookworm 64-bit
- State machine: SCANNING → TRACKING → TARGET_LOST → SCANNING
- HAAR detekcja z streak filter, PID dual-axis, sinusoidal scan
- Safe startup, graceful shutdown, headless fallback

## Current Milestone: v1.7 Debugging & Optimization

**Goal:** Naprawić krytyczne bugi w test_tracker.py wykryte podczas testów na hardware RPi4 — brak ruchu tilt, runaway camera (błąd znaku PID), blue tint AWB, logika przejść stanów.

**Target fixes:**
- Naprawa osi TILT — analiza znaku PID, weryfikacja czy korekta dociera do serwa GPIO 13
- Runaway Camera — analiza matematyczna pętli sprzężenia zwrotnego, naprawa znaku regulatora
- Blue tint (AWB) — konfiguracja Picamera2 AWB/color gains dla sensora IMX219
- Logika skanowania — płynne przejście TRACKING→SCANNING z resetem I-term (anti-windup)

**Kontekst hardware:**
- **Montaż**: Standardowy — pan+ = prawo, tilt+ = dół
- **Obserwacja**: TRACKING stabilny (nie flickeruje), tilt się nie rusza
- **Hardware**: MG-90S serwa, GPIO 12 (pan) / GPIO 13 (tilt), zasilanie 6V (4xAA)
- **Software**: pigpio + gpiozero, Picamera2, RPi OS Bookworm 64-bit

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
| Picamera2 over OpenCV VideoCapture | Good — native libcamera on Bookworm | v1.6 |
| Isolated test module over rewrite | Good — preserves stable v1.5 code | v1.6 |
| Montaż standardowy: pan+=prawo, tilt+=dół | Potwierdzone empirycznie | v1.7 |

## Team & Context

- Solo developer project (research/IoT focus)
- Development on Windows, deployment on Raspberry Pi 4
- No CI/CD pipeline, empirical verification
- GSD methodology for project management

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-27 after v1.7 milestone start*
