---
gsd_state_version: 1.0
milestone: v1.9
milestone_name: Stabilizacja Ruchu i Obrazu
status: verifying
stopped_at: Completed 22-02-PLAN.md
last_updated: "2026-03-31T13:56:31.688Z"
last_activity: 2026-03-31
progress:
  total_phases: 14
  completed_phases: 13
  total_plans: 19
  completed_plans: 18
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Rozproszona architektura — RPi4 (wizja) + Arduino Leonardo (PID + HMI) polaczone USB Serial
**Current focus:** Phase 22 — hmi-lcd-buzzer-przycisk

## Current Position

Phase: 22 (hmi-lcd-buzzer-przycisk) — EXECUTING
Plan: 2 of 2
Status: Phase complete — ready for verification
Last activity: 2026-03-31

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 13 (v1.5-v1.8)
- Average duration: brak danych dla v2.0
- Total execution time: brak danych dla v2.0

## Accumulated Context

### Decisions

- [v1.7]: Montaz standardowy: pan+=prawo, tilt+=dol (wymaga re-weryfikacji na nowym montazu Arduino)
- [v1.7]: Tilt negation: korekta_tilt = -pid_tilt (PID przeniesiony na Arduino)
- [v1.8]: PID gains (P=0.05, I=0.001, D=0.005) — punkt startowy dla Arduino, I redukowac 3x (Ki=0.0003) dla 100 Hz
- [v2.0]: Architektura rozproszona — RPi4 + Arduino Leonardo via USB Serial 115200
- [v2.0]: QuickPID zamiast br3ttb PID — iAwCondition anti-windup, dOnMeas derivative mode
- [v2.0]: NIE uzywac AVR hardware WDT — millis() watchdog zamiast wdt_enable() (Caterina bootloader bug)
- [Phase 18-srodowisko-protokol-migracja]: Protokol binarny 8B zamkniety: 0xAA + mode(uint8) + error_x/y(int16 LE) + face_size(uint8) + XOR checksum(1-6 bez start)
- [Phase 18-srodowisko-protokol-migracja]: Stary monolit w legacy/ via git mv — historia plikow zachowana przez git log --follow
- [Phase 18]: Servo i LiquidCrystal wymagaly osobnej instalacji przez arduino-cli lib install — nie sa builtin w arduino:avr 1.8.7
- [Phase 18]: picamera2 nie importuje sie w Python 3.12 venv — rozwiazanie odlozone do Phase 21
- [Phase Phase 18]: Servo i LiquidCrystal wymagaly arduino-cli lib install — nie sa builtin w arduino:avr 1.8.7
- [Phase Phase 18]: picamera2 nie importuje sie w Python 3.12 venv — rozwiazanie odlozone do Phase 21 (systemowy pakiet cp313 niekompatybilny z cp312 venv)
- [Phase 19-serial-link-echo-test]: set_low_latency_mode(True) zamiast subprocess+setserial — pyserial 3.5 wbudowane ioctl bez sudo
- [Phase 19-serial-link-echo-test]: DTR=False przed ser.open() — Caterina bootloader Leonardo no-reset przy polaczeniu USB
- [Phase 20]: QuickPID enum kwalifikacja: QuickPID::iAwMode::iAwCondition / QuickPID::pMode::pOnError / QuickPID::dMode::dOnMeas (nie krotka forma)
- [Phase 20-firmware-arduino-pid-servo]: Watchdog odpala sie tylko dla TRACK — IDLE i SCAN sa stanem stabilnym, nie wymagaja timeoutu
- [Phase 20-firmware-arduino-pid-servo]: dispatch_ramke() resetuje watchdog po poprawnej checksumie — nie w przetwarzaj_bajt() (Pitfall 5)
- [Phase 21-wizja-rpi-mediapipe]: NV12/YUV420p autodetection: cv2.COLOR_YUV2BGR_NV12 probe first, fallback COLOR_YUV420p2BGR — Bookworm compat
- [Phase 21-wizja-rpi-mediapipe]: Sticky tracking umieszczony w WykrywaczTwarzy (nie MozgRPi) — bardziej modularny design
- [Phase 21-wizja-rpi-mediapipe]: Mutowalny ref [float] dla czasu TX miedzy MozgRPi a WatekHeartbeat — prostszy niz Event/Condition, thread-safe pod GIL
- [Phase 21-wizja-rpi-mediapipe]: Heartbeat wysyla MODE_SCAN (nie MODE_IDLE) — per D-07, Arduino skanuje gdy brak twarzy
- [Phase 22-hmi-lcd-buzzer-przycisk]: setCursor+overwrite zamiast lcd.clear() w lcd_tick() — brak migotania LCD (Pitfall 3)
- [Phase 22-hmi-lcd-buzzer-przycisk]: dtostrf() dla float na AVR zamiast sprintf('%f') — avr-libc standard (Pitfall 1)
- [Phase 22-hmi-lcd-buzzer-przycisk]: Bootscreen LCD przed serwo attach — uzytkownik widzi status podczas inicjalizacji serw
- [Phase 22-hmi-lcd-buzzer-przycisk]: tone(BUZZER_PIN, 1000, 100) wywolywane wylacznie w przejdz_do() przy TRACK — nie w pid_tick() ani loop()
- [Phase 22-hmi-lcd-buzzer-przycisk]: przycisk_tick() aktualizuje przycisk_ostatni_stan na koncu funkcji — edge detect HIGH→LOW z debounce 20ms

### Blockers/Concerns

- MediaPipe aarch64 wheel: weryfikacja pip install na konkretnej wersji RPi OS wymagana w Fazie 18 (fail fast)
- Orientacja serw: PAN_DIR / TILT_DIR wymaga empirycznej kalibracji na nowym montazu Arduino w Fazie 20
- setserial low_latency nie persystuje przez USB reconnect — zdecydowac gdzie ustawiac (udev / startup script)

### Pending Todos

None.

## Session Continuity

Last session: 2026-03-31T13:56:31.562Z
Stopped at: Completed 22-02-PLAN.md
Resume file: None
