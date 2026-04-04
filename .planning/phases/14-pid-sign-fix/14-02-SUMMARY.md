---
phase: 14-pid-sign-fix
plan: "02"
subsystem: arduino-firmware
tags: [firmware, kalibracja, pid, servo, arduino, r4-wifi]
dependency_graph:
  requires: ["14-01"]
  provides: ["TILT_INVERT skalibrowany", "PAN_INVERT potwierdzony"]
  affects: ["src/arduino/aries_controller/aries_controller.ino", "scripts/kalibracja_serw.py"]
tech_stack:
  added: []
  patterns: ["empiryczna kalibracja INVERT przez test otwarty petli", "arduino-cli compile+upload workflow"]
key_files:
  created: []
  modified:
    - src/arduino/aries_controller/aries_controller.ino
    - scripts/kalibracja_serw.py
decisions:
  - "PAN_INVERT=(+1) potwierdzony kalibracją (Kroki 1,2 PASS)"
  - "TILT_INVERT=(-1) potwierdzony kalibracją (Kroki 3,4 PASS) — oryginalna wartosc poprawna"
  - "Fix WYLACZNIE w firmware Arduino INVERT constants — nie w brain.py (per D-09)"
  - "Pierwsza kalibracja TILT FAIL spowodowana czesciowo rozpietym kablem serwa"
metrics:
  duration: "~40 min"
  completed_date: "2026-04-04"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 2
---

# Phase 14 Plan 02: Kalibracja PAN_INVERT/TILT_INVERT — Summary

**One-liner:** PAN_INVERT=+1 i TILT_INVERT=-1 potwierdzone empirycznie na R4 WiFi v2.1.1 — oryginalne wartosci poprawne, pierwszy FAIL tilt spowodowany rozpietym kablem.

## What Was Built

Firmware Arduino Uno R4 WiFi z potwierdzonymi wartosciami kierunku serw:

- `PAN_INVERT = (1)` — potwierdzony PASS (krok 1: pan prawo, krok 2: pan lewo)
- `TILT_INVERT = (-1)` — potwierdzony PASS (krok 3: tilt dol, krok 4: tilt gora)

Skrypt kalibracyjny zmieniony na tryb nieinteraktywny (input() nie dziala w Claude Code Bash). Dodano opcje --krok N.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Kalibracja empiryczna | (checkpoint — obserwacja) | scripts/kalibracja_serw.py |
| 2 | Korekta firmware | 1204d90 | src/arduino/aries_controller/aries_controller.ino |
| 3 | Weryfikacja negative feedback | (checkpoint — potwierdzone) | scripts/kalibracja_serw.py |

## Firmware State

**Plik:** `src/arduino/aries_controller/aries_controller.ino` linie 37-38

```c
#define PAN_INVERT      (1)       // +1 skalibrowany empirycznie R4 WiFi v2.1.1
#define TILT_INVERT     (-1)      // -1 skalibrowany empirycznie R4 WiFi v2.1.1
```

**Kompilacja:** 83596B (31% flash), 11268B (34% RAM) — OK (pelna wersja z Phase 25-27)
**Upload:** /dev/ttyACM0 — 21 stron, 5.050s — OK

## Deviations from Plan

1. **Kabel tilt czesciowo rozpiety** — pierwsza kalibracja dala FAIL na krokach 3-4, co blednie sugerowalo zmiane TILT_INVERT z -1 na +1. Po naprawie kabla i powrocie do -1, wszystkie kroki PASS.
2. **Worktree regression** — agent flashowal firmware z worktree (503 linii, brak Phase 25-27). Naprawione flash z main (816 linii).
3. **Skrypt zmieniony na nieinteraktywny** — Claude Code Bash nie obsluguje stdin/input().

## Self-Check: PASSED

- [x] PAN_INVERT=+1, krok 1 PASS, krok 2 PASS
- [x] TILT_INVERT=-1, krok 3 PASS, krok 4 PASS
- [x] Firmware zaflashowany z pelna wersja (Phase 25-27, 83596B)
- [x] Kalibracja 4/4 PASS na R4 WiFi z naprawionym kablem
