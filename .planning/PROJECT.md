# PROJECT.md — ARIES-LITE

> **Full Name**: Autonomous Real-time Intelligent Eye System — Lightweight Edition
> **Status**: Active (v2.0 in progress)
> **Current Version**: v2.0.0-dev
> **Target Platform**: Raspberry Pi 4 Model B + Arduino Leonardo

## Vision

An autonomous real-time face tracking system built on a distributed architecture: Raspberry Pi 4 ("Mózg") handles computer vision (MediaPipe Face Detection) and high-level logic, while Arduino Leonardo ("Układ Wykonawczy") runs PID control at 100+ Hz for ultra-smooth servo motion, manages LCD/buzzer HMI, and provides hardware watchdog safety.

## Problem Statement

Running both vision and PID control on a single RPi4 limits servo update rate to ~30 Hz (Python loop) and makes the system fragile (single point of failure). By offloading PID + servo control to Arduino Leonardo via USB Serial, the RPi4 is freed to run heavier vision models (MediaPipe instead of HAAR/DNN) while Arduino delivers hardware-rate PID updates. The distributed architecture also adds physical HMI (LCD, buzzer, action button) and autonomous safety (watchdog returns to SCAN if Pi stops communicating).

## Current State

**v1.8** complete — all 13 phases delivered (DNN detector, PID validation, AWB fix, detection fix, diagnostics).

**v1.9** partially started — AWB/Color Fix phase 14 in progress (continuous AWB approach).

**v2.0** Phase 21 complete — wizja RPi MediaPipe: KameraRPi (Picamera2 + dwuetapowy AWB fix), WykrywaczTwarzy (MediaPipe FaceDetector + sticky tracking 20% histereza), MozgRPi (pętla sterowania + error calc + serial TX + heartbeat 200ms + HUD), run_pi_brain.py. Pętla RPi→Arduino zamknięta end-to-end. Phase 20: firmware Arduino PID + serwa. Phase 19: serial link. Phase 18: środowisko + protokół 8B LOCKED + legacy/.

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

## Current Milestone: v2.0 Architektura Rozproszona

**Goal:** Calkowita przebudowa systemu na architekture rozproszona — Mozg (RPi4) + Uklad Wykonawczy (Arduino Leonardo) polaczone przez USB Serial.

**Target features:**
- Firmware Arduino (`src/arduino/aries_controller.ino`): Serial parser, PID dual-axis (100+ Hz), LCD 1602 status, buzzer feedback, safe startup, watchdog (powrot do SCAN gdy Pi milczy)
- Brain script Pi (`src/vision/pi_brain.py`): MediaPipe Face Detection, sticky tracking (najwieksza twarz), AWB fix dla IMX219, obliczanie bledu + wysylanie do Arduino
- Protokol szeregowy: Pelna ramka — tryb (SCAN/TRACK/IDLE), blad X/Y, rozmiar twarzy, heartbeat
- Przycisk akcji (D7): "Abort Track" — przywraca tryb SCAN gdy kamera sledzi niepozadany cel
- Orientacja serw: Konfigurowalny kierunek (empiryczna kalibracja na hardware)

**Hardware:**
- Arduino Leonardo: LCD 1602 (RS=12,E=11,D4=5,D5=4,D6=3,D7=2), Serwa MG-90S (PAN=D9,TILT=D10), Buzzer=D8, Przycisk=D7 (INPUT_PULLUP), zasilanie serw z zewnetrznego 6V
- RPi4B: Kamera RPi v2 (IMX219), polaczenie USB Serial (/dev/ttyACM0, 115200 baud)

**Kontekst:**
- Stary monolit zachowany w `legacy/` jako referencja
- PID przeniesiony na Arduino dla plynnosci 100+ Hz
- MediaPipe zamiast DNN — RPi odciazone przez Arduino, stac na ciezszy model wizji
- Orientacja serw wymaga empirycznej weryfikacji na nowym montazu

## What Could Come Next

Potential areas for future milestones:
1. **Security**: Basic auth for API endpoints (network-accessible system)
2. **Operations**: Systemd service, startup scripts, monitoring
3. **Testing**: Expand automated test coverage beyond Nyquist validation
4. **Features**: Multi-face tracking priority, recording, face database
5. **Performance**: PID tuning optimization, FPS improvements

## Technical Decisions (Locked)

These architectural choices are validated and should not change:
- Distributed architecture: RPi4 (vision) + Arduino Leonardo (PID + HMI)
- USB Serial communication at 115200 baud (/dev/ttyACM0)
- MediaPipe Face Detection on RPi4 (replaces HAAR/DNN)
- PID control on Arduino (100+ Hz hardware-rate updates)
- Arduino Servo library for MG-90S (PAN=D9, TILT=D10)
- LCD 1602 4-bit mode for status display
- Watchdog na Arduino — autonomiczny powrot do SCAN przy utracie komunikacji
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
*Last updated: 2026-03-29 after milestone v1.9 start — Stabilizacja Ruchu i Obrazu*
