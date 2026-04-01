---
phase: 24-migracja-pinow-i-kompilacja-bazowa
plan: 02
subsystem: firmware
tags: [arduino, aries_controller, uno-r4-wifi, renesas, serial, hardware-verify]

# Dependency graph
requires:
  - phase: 24-migracja-pinow-i-kompilacja-bazowa
    provides: Firmware v2.1 skompilowany zero bledow na arduino:renesas_uno:unor4wifi
provides:
  - CHECKPOINT: Oczekuje na fizyczne Arduino Uno R4 WiFi podlaczone do RPi
affects: [24-completion, 25-rtc-ds1307]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions: []

patterns-established: []

requirements-completed: []  # Oczekuje na weryfikacje sprzetowa

# Metrics
duration: 1min (partial — hardware gate)
completed: 2026-04-01
---

# Phase 24 Plan 02: Weryfikacja sprzetowa firmware v2.1 — PARTIAL (hardware gate)

**ZATRZYMANO: Podlaczone urzadzenie to Arduino Uno R3 (AVR, ID 2a03:0043), nie Arduino Uno R4 WiFi (Renesas RA4M1) — flash niemozliwy**

## Performance

- **Duration:** 1 min (partial)
- **Started:** 2026-04-01T16:58:19Z
- **Completed:** PENDING (hardware gate)
- **Tasks:** 0/2 (Task 1 zablokowany — bledne urzadzenie)
- **Files modified:** 0

## Accomplishments

- Brak — wykryto hardware gate przed mozliwoscia flashowania

## Task Commits

Brak — zaden task nie zostal ukonczony

## Files Created/Modified

Brak

## Decisions Made

Brak

## Deviations from Plan

### Hardware Gate (nie jest dewiacja — gate blokujacy)

**Hardware gate: Bledne Arduino podlaczone do RPi**
- **Wykryto podczas:** Task 1 (Flash firmware na Uno R4 WiFi)
- **Problem:** `arduino-cli board list` wykrywa `Arduino UNO Rev3` (AVR ATmega328P, USB ID 2a03:0043) zamiast Arduino Uno R4 WiFi (Renesas RA4M1, USB ID 2341:1002 lub podobny)
- **Komenda ktora zawodzi:** `arduino-cli upload --fqbn arduino:renesas_uno:unor4wifi --port /dev/ttyACM0`
- **Blad:** `No device found on ttyACM0` (po 1200-bps touch reset bossac nie znajduje bootloadera DFU R4)
- **Wymagane dzialanie:** Podlaczenie Arduino Uno R4 WiFi do RPi przez USB

## Issues Encountered

- Podlaczone urzadzenie to Arduino Uno R3 (klasyczny AVR), nie Arduino Uno R4 WiFi.
  `lsusb` potwierdza: `ID 2a03:0043 dog hunter AG Arduino Uno Rev3`
  Flashowanie firmware z FQBN `arduino:renesas_uno:unor4wifi` wymaga fizycznie podlaczonego Uno R4 WiFi.

## User Setup Required

**Wymagane fizyczne dzialanie uzytkownika — podlaczenie Arduino Uno R4 WiFi:**

1. Podlacz Arduino Uno R4 WiFi do RPi4 przez kabel USB
2. Zweryfikuj ze zostalo rozpoznane: `arduino-cli board list --discovery-timeout 5s`
   - Oczekiwany wynik: FQBN `arduino:renesas_uno:unor4wifi` lub Board Name "Arduino UNO R4 WiFi"
3. Po potwierdzeniu uruchom ponownie plan 24-02 (Task 1 wykona flash automatycznie)

**Weryfikacja komendy:**
```bash
arduino-cli board list --discovery-timeout 5s
```
Oczekiwany wynik z R4 WiFi podlaczonym:
```
Port         Protocol Type              Board Name           FQBN                           Core
/dev/ttyACM0 serial   Serial Port (USB) Arduino UNO R4 WiFi  arduino:renesas_uno:unor4wifi  arduino:renesas_uno
```

## Next Phase Readiness

- BLOCKED: Wymaga fizycznego Arduino Uno R4 WiFi podlaczonego do RPi
- Po podlaczeniu R4 WiFi: Task 1 flash + Task 2 weryfikacja sprzetowa (checkpoint:human-verify)
- Firmware v2.1 skompilowany (Plan 01) i gotowy do flashowania — brak problemu z kodem

---
*Phase: 24-migracja-pinow-i-kompilacja-bazowa*
*Status: PARTIAL — hardware gate*
*Completed: 2026-04-01*
