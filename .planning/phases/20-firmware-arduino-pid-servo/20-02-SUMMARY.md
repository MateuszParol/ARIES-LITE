---
phase: 20-firmware-arduino-pid-servo
plan: "02"
subsystem: arduino-firmware
tags: [arduino, pid, servo, firmware, state-machine, lissajous, watchdog]
dependency_graph:
  requires: [20-01]
  provides: [arduino-firmware-complete]
  affects: [21-rpi-serial-driver]
tech_stack:
  added: []
  patterns: [dispatch-ramke, przejdz_do-state-transition, pid-tick-100Hz, lissajous-scan, millis-watchdog]
key_files:
  created: []
  modified:
    - src/arduino/aries_controller/aries_controller.ino
decisions:
  - "Watchdog odpala sie tylko dla TRACK (nie IDLE/SCAN) — IDLE to stan startowy, SCAN juz dziala autonomicznie"
  - "dispatch_ramke() resetuje watchdog po poprawnej checksumie — nie w przetwarzaj_bajt() (Pitfall 5)"
  - "przejdz_do() resetuje PID przy kazdej zmianie stanu (SCAN i TRACK) — zapobiega ucieczce serw z narosnieta wartoscia integratora"
metrics:
  duration_minutes: 10
  completed_date: "2026-03-31"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 1
---

# Phase 20 Plan 02: Logika sterowania — dispatch, PID tick, Lissajous, watchdog

**One-liner:** Kompletna logika sterowania Arduino: dispatch ramek z maszyna stanow IDLE/SCAN/TRACK, petla PID 100 Hz z normalizacja bledu i INVERT, skan Lissajous 2D (f_pan=0.05 Hz, f_tilt=0.073 Hz, AMP 70/25 deg), watchdog millis() 500ms, pelna integracja loop().

## What Was Built

Plik `src/arduino/aries_controller/aries_controller.ino` rozszerzony o kompletna logike sterowania — firmware gotowy do uploadu i testow empirycznych.

### Nowe funkcje

- **`przejdz_do(StanSystemu nowy_stan)`** — zmiana stanu z resetem PID i scan timer przy wejsciu w SCAN lub TRACK
- **`dispatch_ramke()`** — ekstrakcja pol ramki (tryb, blad_x/y LE int16), reset watchdog, bezposredni dispatch do maszyny stanow (D-08); walidacja `tryb <= 2`
- **`skan_tick(unsigned long teraz)`** — skan Lissajous 2D: `kat = AMP * sin(2*pi*freq*t)`, irracjonalny stosunek f_tilt/f_pan=1.46, clamp defense-in-depth
- **`pid_tick()`** — petla 100 Hz z millis() throttle; normalizacja: `pan_wej = blad_x / 160.0f`; QuickPID Compute(); korekta przez PAN/TILT_INVERT; wywoluje skan_tick() gdy SCAN

### Zmodyfikowane funkcje

- **`przetwarzaj_bajt()`** — zamiana `Serial.write(echo)` na `dispatch_ramke()` po poprawnej checksumie; komentarz naglowkowy zaktualizowany
- **`loop()`** — rozbudowa: parser serial (zachowany) + watchdog `WATCHDOG_TIMEOUT_MS` sprawdzany tylko dla TRACK + `pid_tick()`

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Funkcje dispatch_ramke(), przejdz_do(), pid_tick(), skan_tick() | 4e0088f | src/arduino/aries_controller/aries_controller.ino |
| 2 | Modyfikacja przetwarzaj_bajt() i loop() — pelna integracja | f715cf0 | src/arduino/aries_controller/aries_controller.ino |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Komentarz naglowkowy przetwarzaj_bajt() zawierajacy "Serial.write"**
- **Found during:** Task 2, weryfikacja grep -c "Serial.write" (kryterium: 0)
- **Issue:** Komentarz naglowka funkcji z Phase 19 zawierl "echo identycznej ramki (Serial.write)" — grep liczy zarowno kod jak i komentarze, wiec kryterium zwracalo 1 zamiast 0
- **Fix:** Zaktualizowano komentarz na "dispatch do maszyny stanow (dispatch_ramke)"
- **Files modified:** src/arduino/aries_controller/aries_controller.ino
- **Commit:** f715cf0

## Known Stubs

None — firmware w pelni zaimplementowany i kompiluje sie.

## Verification Results

- Kompilacja Task 1: `arduino-cli compile --fqbn arduino:avr:leonardo` — exit 0, 26% flash, 15% RAM
- Kompilacja Task 2: `arduino-cli compile --fqbn arduino:avr:leonardo` — exit 0, 38% flash, 16% RAM
- Serial.write: 0 (echo usuniety)
- dispatch_ramke() wywolan: 2 (definicja + wywolanie w przetwarzaj_bajt)
- pid_tick() wywolan: 2 (definicja + wywolanie w loop)
- WATCHDOG_TIMEOUT_MS: 2 (define + uzycie w loop)
- przejdz_do(SCAN): 1 (watchdog w loop)
- pidPan.Reset: 2 (SCAN + TRACK w przejdz_do)
- SCAN_FREQ_PAN+sin: 1 (w skan_tick)

## Self-Check: PASSED

- File exists: src/arduino/aries_controller/aries_controller.ino — FOUND
- Commit 4e0088f — FOUND
- Commit f715cf0 — FOUND
