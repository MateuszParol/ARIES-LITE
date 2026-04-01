# PROJECT.md — ARIES-LITE

> **Full Name**: Autonomous Real-time Intelligent Eye System — Lightweight Edition
> **Status**: Active (v2.1 in progress)
> **Current Version**: v2.1.0-dev
> **Target Platform**: Raspberry Pi 4 Model B + Arduino Uno R4 WiFi

## Vision

An autonomous real-time face tracking system built on a distributed architecture: Raspberry Pi 4 ("Mózg") handles computer vision (MediaPipe Face Detection) and high-level logic, while Arduino Uno R4 WiFi ("Układ Wykonawczy") runs PID control at 100+ Hz for ultra-smooth servo motion, manages LCD/buzzer HMI, logs telemetry to SD card with RTC timestamps, and provides hardware watchdog safety.

## Problem Statement

Running both vision and PID control on a single RPi4 limits servo update rate to ~30 Hz (Python loop) and makes the system fragile (single point of failure). By offloading PID + servo control to Arduino Uno R4 WiFi via USB Serial, the RPi4 is freed to run heavier vision models (MediaPipe instead of HAAR/DNN) while Arduino delivers hardware-rate PID updates. The distributed architecture also adds physical HMI (LCD, buzzer, action button), telemetry logging (SD card + RTC), and autonomous safety (watchdog returns to SCAN if Pi stops communicating).

## Current State

**v1.8** complete — all 13 phases delivered (DNN detector, PID validation, AWB fix, detection fix, diagnostics).

**v1.9** partially started — AWB/Color Fix phase 14 in progress (continuous AWB approach).

**v2.0** complete (code) — Architektura rozproszona zaimplementowana: firmware Arduino OOP (ServoPID, MaszynaStanow, HMI), brain RPi (MediaPipe + serial TX), protokół 8B, kalibracja serw, polonizacja. Hardware UAT odłożone — Arduino Leonardo USB blocker rozwiązany przez migrację na Uno R4 WiFi w v2.1.

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

## Current Milestone: v2.1 Migracja na Uno R4 + DataLogger

**Goal:** Port firmware na Arduino Uno R4 WiFi z nowa mapa pinow, integracja DataLogger Shield (RTC DS1307 + SD card logging CSV) i Soft Start — pelna kompatybilnosc z istniejacym protokolem binarnym 8B z RPi.

**Target features:**
- Port klas OOP (ServoPID, MaszynaStanow, HMI) na nowa mape pinow (LCD->A0/A1, serwa->D6/D9, buzzer->D8, przycisk->D7)
- Usuniecie specyfik Leonardo (Caterina DTR=False, USB CDC) — Uno R4 uzywa standardowego UART
- Soft Start 500ms w setup() przed ruchem serw
- RTC DS1307 — odczyt czasu, wyswietlanie na LCD row 1
- SD card logging CSV: timestamp, stan, pan, tilt, error_x, error_y, face_size, latency_ms
- Rotacja plikow dziennych (log_YYYYMMDD.csv), logowanie co zmiane stanu + co 10-ta ramke TRACK
- Rezerwacja pinow SPI (D10-D13) i I2C (A4/A5) dla shielda

**Hardware:**
- Arduino Uno R4 WiFi + DataLogger Shield V1.0 (RTC DS1307 + czytnik SD)
- LCD 1602: RS=A0, E=A1, D4=D2, D5=D3, D6=D4, D7=D5
- Serwa MG-90S: PAN=D6, TILT=D9, zasilanie z zewnetrznego 6V
- Buzzer=D8, Przycisk=D7 (INPUT_PULLUP)
- SD Card: D10 (CS), D11 (MOSI), D12 (MISO), D13 (SCK)
- RTC DS1307 + ToF (przyszlosc): A4 (SDA), A5 (SCL)
- RPi4B: Kamera RPi v2 (IMX219), USB Serial 115200 baud

**Kontekst:**
- Protokol binarny 8B bez zmian — RPi nie wymaga modyfikacji
- Arduino Leonardo USB blocker rozwiazany przez zmiane plytki
- M5Stack Atom S3R i czujnik ToF zarezerwowane na przyszle milestone'y
- Testy na Uno R3 (8-bit) przed przejsciem na R4 (32-bit)

## What Could Come Next

Potential areas for future milestones:
1. **M5Stack Atom S3R**: Asystent glosowy — integracja z systemem sledzenia
2. **Czujnik ToF**: Pomiar odleglosci do obiektu (I2C, A4/A5 zarezerwowane)
3. **Web UI**: Flask MJPEG stream + panel sterowania (port z legacy/)
4. **Operations**: Systemd service, startup scripts, monitoring
5. **Performance**: Adaptywny PID (gain scheduling wg rozmiaru twarzy), FPS improvements

## Technical Decisions (Locked)

These architectural choices are validated and should not change:
- Distributed architecture: RPi4 (vision) + Arduino Uno R4 WiFi (PID + HMI + DataLogger)
- USB Serial communication at 115200 baud
- MediaPipe Face Detection on RPi4 (replaces HAAR/DNN)
- PID control on Arduino (100+ Hz hardware-rate updates)
- Arduino Servo library for MG-90S (PAN=D6, TILT=D9)
- LCD 1602 4-bit mode (RS=A0, E=A1, D4-D7=D2-D5)
- DataLogger Shield: SD (SPI D10-D13) + RTC DS1307 (I2C A4/A5)
- Protokol binarny 8B (0xAA + mode + error_x/y + face_size + XOR checksum)
- Watchdog millis() na Arduino — autonomiczny powrot do SCAN przy utracie komunikacji
- Polish-language comments and UI text
- Pin map v2.1: LCD(A0,A1,D2-D5), Serwa(D6,D9), Buzzer(D8), Przycisk(D7), SD(D10-D13), I2C(A4,A5)

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
*Last updated: 2026-04-01 after milestone v2.1 start — Migracja na Uno R4 + DataLogger*
