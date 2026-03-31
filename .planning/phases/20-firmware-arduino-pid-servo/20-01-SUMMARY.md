---
phase: 20-firmware-arduino-pid-servo
plan: "01"
subsystem: arduino-firmware
tags: [arduino, pid, servo, firmware, safe-startup]
dependency_graph:
  requires: []
  provides: [arduino-firmware-foundation]
  affects: [20-02]
tech_stack:
  added: []
  patterns: [QuickPID dual-axis, safe-startup ramp, millis-watchdog, state-machine]
key_files:
  created: []
  modified:
    - src/arduino/aries_controller/aries_controller.ino
decisions:
  - "QuickPID enum kwalifikacja: QuickPID::iAwMode::iAwCondition / QuickPID::pMode::pOnError / QuickPID::dMode::dOnMeas (nie krotka forma)"
  - "Obie zmiany Task 1 i Task 2 zaaplikowane razem w jednym commicie — plik rozbudowany w jednej iteracji"
metrics:
  duration_minutes: 15
  completed_date: "2026-03-31"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 1
---

# Phase 20 Plan 01: Fundament firmware — stale, PID, servo, setup()

**One-liner:** Rozbudowa aries_controller.ino o #define konfiguracyjne, QuickPID dual-axis z anti-windup/dOnMeas/100Hz, safe_startup() ramp writeMicroseconds 500→1500us, ustaw_serwa(), i setup() z poprawna kolejnoscia: attach → safe_startup → init_pid.

## What Was Built

Plik `src/arduino/aries_controller/aries_controller.ino` rozbudowany z parsera echo (Phase 19) o kompletny fundament sterowania:

### Stale konfiguracyjne (#define)
- Konfiguracja PID: `KP=2.0f`, `KI=0.1f`, `KD=0.5f`, `OUTPUT_LIMIT=5.0f`, `PID_INTERVAL_MS=10`
- Konfiguracja serw: `PAN_PIN=9`, `TILT_PIN=10`, limity katowe +/-60 / +/-30 stopni
- Kierunek serw: `PAN_INVERT=1`, `TILT_INVERT=-1` (empiryczna kalibracja przez zmiane #define)
- Normalizacja bledu: `HALF_FRAME_W=160.0f`
- Watchdog: `WATCHDOG_TIMEOUT_MS=500`
- Skan Lissajous: `SCAN_FREQ_PAN=0.05f`, `SCAN_FREQ_TILT=0.073f` (irracjonalny stosunek), `SCAN_AMP_PAN=70.0f`, `SCAN_AMP_TILT=25.0f`

### Typy danych
- `enum StanSystemu { IDLE, SCAN, TRACK }` — maszyna stanow systemu

### Zmienne globalne
- `Servo serwo_pan`, `Servo serwo_tilt`
- `QuickPID pidPan`, `QuickPID pidTilt` z float* API
- Zmienne stanu: `stan_systemu`, `kat_pan`, `kat_tilt`, `ostatni_blad_x/y`
- Timery: `czas_ostatniej_ramki`, `czas_ostatniego_pid`, `czas_startowy_skanu`

### Nowe funkcje
- `safe_startup()` — rampa writeMicroseconds 500→1500us w 50 krokach (1000ms), brak skoku pradu
- `init_pid()` — konfiguracja QuickPID: 100Hz, OUTPUT_LIMIT +/-5.0, iAwCondition, pOnError, dOnMeas
- `ustaw_serwa()` — constrain do limitow katowych + Servo.write(kat+90)

### Zmodyfikowany setup()
Kolejnosc: `Serial.begin` → `attach(PAN_PIN/TILT_PIN)` → `safe_startup()` → `init_pid()` → inicjalizacja timerow → `stan_systemu = IDLE`

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Stale konfiguracyjne i zmienne globalne | f4d37be | src/arduino/aries_controller/aries_controller.ino |
| 2 | Funkcje safe_startup(), init_pid(), ustaw_serwa() i nowy setup() | f4d37be | src/arduino/aries_controller/aries_controller.ino |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Nieprawidlowe nazwy enum QuickPID API**
- **Found during:** Task 2, kompilacja
- **Issue:** Plan specyfikowal `QuickPID::iAwCondition`, `QuickPID::pOnError`, `QuickPID::dOnMeas` — ale QuickPID 3.1.9 uzywa klas enum z kwalifikacja `QuickPID::iAwMode::iAwCondition`, `QuickPID::pMode::pOnError`, `QuickPID::dMode::dOnMeas`
- **Fix:** Sprawdzono naglowki biblioteki w `/home/parolisko/Arduino/libraries/QuickPID/` i zastosowano poprawne kwalifikatory klas enum
- **Files modified:** src/arduino/aries_controller/aries_controller.ino
- **Commit:** f4d37be

## Known Stubs

None — wszystkie zmienne i funkcje sa w pelni zaimplementowane. Parser z Phase 19 zachowany bez zmian.

## Verification Results

- Kompilacja: `arduino-cli compile --fqbn arduino:avr:leonardo` — exit 0, 26% flash, 15% RAM
- Wszystkie grep kryteria akceptacji potwierdzone (≥1 dla kazdego kryterium)
- Parser `przetwarzaj_bajt()` niezmieniony (echo Serial.write nadal obecne)

## Self-Check: PASSED

- File exists: src/arduino/aries_controller/aries_controller.ino — FOUND
- Commit f4d37be — FOUND
