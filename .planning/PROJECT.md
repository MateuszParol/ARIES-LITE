# PROJECT.md — ARIES-LITE

> **Full Name**: Autonomous Real-time Intelligent Eye System — Lightweight Edition
> **Status**: Active (v1.8 in progress)
> **Current Version**: v1.8.0-dev
> **Target Platform**: Raspberry Pi 4 Model B

## Vision

An autonomous real-time face tracking system that combines IoT hardware (pan/tilt servos), hybrid computer vision (HAAR + dlib), and PID control theory to keep a target person centered in frame — controlled entirely via a mobile-first web interface over WiFi.

## Problem Statement

Traditional face tracking on Raspberry Pi either sacrifices accuracy (pure HAAR cascade) or frame rate (full dlib on every frame at 2-3 FPS). ARIES-LITE solves this with a hybrid approach: fast HAAR detection for 30fps responsiveness, CSRT tracker for smooth PID input, and async dlib verification for identity confirmation — all orchestrated through a 4-thread architecture.

## Current State

**v1.8** complete — all 13 phases delivered.
- Phase 13 (dnn-detector) complete: OpenCV DNN res10_300x300 zastepuje HAAR, detekcja pod katem >30°, FPS >= 10 na RPi4 z skip_every=5, interfejs wykryj() zachowany
- Phase 12 (pid-validation) complete: --debug flag w run_test_tracker.py, empiryczna walidacja PID na RPi4 — oba kontrolery obliczaja poprawne korekty, brak runaway, konwergencja potwierdzona
- Phase 11 (awb-fix) complete: AWB configure-time lock (1.0, 1.0) w create_video_configuration(), fallback guard na None/(0.0, 0.0), explicit float() cast — neutralne kolory od pierwszej klatki, potwierdzone na RPi4
- Phase 10 (detection-fix) complete: HAAR_MIN_SIZE=(40,40), HAAR_MIN_NEIGHBORS=4 — detekcja dziala 40-100cm, pod katem ±30°, empirycznie potwierdzone na RPi4
- Phase 09 (diagnostics) complete: mock mode [MOCK] HUD indicator, PID component per-tick logging, AWB ColourGains re-read verification after set_controls

**v1.7.0** shipped — all critical hardware bugs fixed in test tracker:
- Dual-axis PID tracking converges correctly (tilt sign fix, pan preserved)
- AWB warm-up + ColourGains lock eliminates blue tint on Picamera2/IMX219
- Per-axis clamp WARNING logging in set_angles() for full observability
- Sinusoidal scan resumes smoothly from current position (phase offset via math.asin)
- Streak filter reset at TARGET_LOST prevents premature TRACKING re-entry
- 12 Nyquist validation tests (SCAN-01, SCAN-02) — first automated tests in project
- simple-pid>=2.0.1 pinned for reliable anti-windup reset()

<details>
<summary>Previous milestones</summary>

**v1.6.0** delivered isolated test tracker module:
- `src/modes/test_tracker.py` — standalone pętla sterowania bez Flaska
- Picamera2 backend (YUV420→BGR, 320x240) z Bookworm 64-bit
- State machine: SCANNING → TRACKING → TARGET_LOST → SCANNING
- HAAR detekcja z streak filter, PID dual-axis, sinusoidal scan
- Safe startup, graceful shutdown, headless fallback

**v1.5.0** stabilized the existing codebase:
- All runtime bugs fixed (logger, face sorting, frame locking)
- Graceful shutdown with signal handlers (servo detach, camera release)
- Non-blocking CENTER command, startup race condition guard
- Clean dependency tree (removed imutils), proper package exports

</details>

## Current Milestone: v1.8 Critical Hardware Fix

**Goal:** System dziala poprawnie na RPi4 — tilt reaguje, PID nie ucieka, obraz bez blue tint, detekcja twarzy jest responsywna.

**Target fixes:**
- Debugowanie TILT (zamrozony na 0.0 w HUD) — sciezka kodu PID → set_angles()
- Naprawa runaway (pozytywne sprzezenie zwrotne na 1 osi, natychmiastowa ucieczka do limitu)
- Naprawa blue tint (AWB warm-up nie wykonuje sie lub gains zle dobrane)
- Zamiana detektora twarzy (HAAR za restrykcyjny → MediaPipe/OpenCV DNN)

**Kontekst hardware:**
- Montaz: kamera prosto na tilt, HUD obraz prawidlowy
- Tilt: HUD zamrozony na 0.0, serwo nie reaguje
- Pan: ucieka natychmiast po TRACKING, bardzo szybki ruch do limitu
- Detekcja: brak zielonych prostokatow, wymaga idealnej pozycji frontalnej

## What Could Come Next

Potential areas for future milestones:
1. **Security**: Basic auth for API endpoints (network-accessible system)
2. **Operations**: Systemd service, startup scripts, monitoring
3. **Testing**: Expand automated test coverage beyond Nyquist validation
4. **Features**: Multi-face tracking priority, recording, face database
5. **Performance**: PID tuning optimization, FPS improvements

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
| Montaz standardowy: pan+=prawo, tilt+=dol | Potwierdzone empirycznie | v1.7 |
| Tilt negation: korekta_tilt = -pid_tilt | Good — convergent tracking | v1.7 |
| AWB lock via set_controls after start()+2s sleep | Good — eliminates blue tint | v1.7 |
| Phase offset via math.asin(clamp) | Good — smooth scan resume | v1.7 |
| Streak reset at TARGET_LOST (not SCANNING) | Good — correct 3-frame enforcement | v1.7 |

## Team & Context

- Solo developer project (research/IoT focus)
- Development on Windows, deployment on Raspberry Pi 4
- No CI/CD pipeline, empirical verification + Nyquist validation tests
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
*Last updated: 2026-03-29 after Phase 13 (dnn-detector) completion — v1.8 milestone complete*
