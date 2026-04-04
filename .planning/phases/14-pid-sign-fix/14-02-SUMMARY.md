---
phase: 14-pid-sign-fix
plan: "02"
subsystem: arduino-firmware
tags: [firmware, kalibracja, pid, servo, arduino, r4-wifi]
dependency_graph:
  requires: ["14-01"]
  provides: ["TILT_INVERT skalibrowany", "PAN_INVERT potwierdzony"]
  affects: ["src/arduino/aries_controller/aries_controller.ino"]
tech_stack:
  added: []
  patterns: ["empiryczna kalibracja INVERT przez test otwarty petli", "arduino-cli compile+upload workflow"]
key_files:
  created: []
  modified:
    - src/arduino/aries_controller/aries_controller.ino
decisions:
  - "TILT_INVERT zmieniony z (-1) na (+1) — wynik empirycznej kalibracji na R4 WiFi v2.1.1 (Kroki 3,4 FAIL)"
  - "PAN_INVERT pozostaje (+1) — potwierdzony kalibracją (Kroki 1,2 PASS)"
  - "Fix WYLACZNIE w firmware Arduino INVERT constants — nie w brain.py (per D-09)"
metrics:
  duration: "~20 min"
  completed_date: "2026-04-04"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 1
---

# Phase 14 Plan 02: Kalibracja TILT_INVERT — Korekta Firmware Summary

**One-liner:** TILT_INVERT zmieniony z (-1) na (+1) na podstawie empirycznej kalibracji open-loop na R4 WiFi v2.1.1 — firmware skompilowane i zaflashowane.

## What Was Built

Firmware Arduino Uno R4 WiFi zaktualizowany o poprawne wartosci kierunku serw po empirycznej kalibracji:

- `PAN_INVERT = (1)` — potwierdzony PASS (krok 1: pan prawo, krok 2: pan lewo)
- `TILT_INVERT = (1)` — skorygowany z (-1) na (+1), poprzednia wartosc powodowala odwrotny ruch tilt (krok 3 FAIL: tilt szedl w gore zamiast w dol, krok 4 FAIL: tilt szedl w dol zamiast w gore)

Komentarze przy obu definicjach zaktualizowane z "zmien empirycznie" na "skalibrowany empirycznie R4 WiFi v2.1.1".

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Kalibracja empiryczna | (checkpoint — brak kodu) | scripts/kalibracja_serw.py |
| 2 | Korekta firmware TILT_INVERT | 38e9e56 | src/arduino/aries_controller/aries_controller.ino |
| 3 | Weryfikacja negative feedback | CHECKPOINT — awaiting user | scripts/kalibracja_serw.py |

## Firmware Changes

**Plik:** `src/arduino/aries_controller/aries_controller.ino` linie 29-30

Przed:
```c
#define PAN_INVERT      (1)       // +1 lub -1 — zmien empirycznie
#define TILT_INVERT     (-1)      // -1 potwierdzony w v1.7 legacy
```

Po:
```c
#define PAN_INVERT      (1)       // +1 skalibrowany empirycznie R4 WiFi v2.1.1
#define TILT_INVERT     (1)       // +1 skalibrowany empirycznie R4 WiFi v2.1.1
```

**Kompilacja:** 64172B (24% flash), 7432B (22% RAM) — OK
**Upload:** /dev/ttyACM0 — 16 stron, 3.958s — OK

## Deviations from Plan

None — plan executed exactly as written (Scenariusz C — tylko TILT FAIL).

## Known Stubs

None — wszystkie wartosci INVERT sa teraz skalibrowane empirycznie, nie sa placeholderami.

## Verification Status

Task 3 (checkpoint:human-verify) awaiting user confirmation:
- Uruchomienie `python3 scripts/kalibracja_serw.py` po flashu nowego firmware
- Oczekiwany wynik: 4/4 krokow PASS (exit code 0)

## Self-Check: PENDING (checkpoint not yet resolved)

Firmware change verified:
- [x] `grep "TILT_INVERT" aries_controller.ino` zwraca `(1)` — FOUND
- [x] `git log --oneline | grep 38e9e56` — FOUND
- [ ] Task 3 checkpoint — awaiting user verification
