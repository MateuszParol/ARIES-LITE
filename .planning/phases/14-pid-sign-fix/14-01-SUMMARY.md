---
phase: 14-pid-sign-fix
plan: 01
subsystem: arduino-firmware
tags: [arduino, r4-wifi, kalibracja, pid, serwa, skrypt-kalibracyjny]

# Dependency graph
requires:
  - phase: 24-migracja-pinow-i-kompilacja-bazowa
    provides: Firmware v2.1 skompilowany na arduino:renesas_uno:unor4wifi z QuickPID, LCD, SD, RTC
  - phase: 27-pelna-integracja-datalogger-z-maszynastanow
    provides: Pelna integracja DataLogger + MaszynaStanow w firmware
provides:
  - Zaktualizowany skrypt kalibracyjny scripts/kalibracja_serw.py dla R4 WiFi (boot delay 5.0s, brak odniesien do Leonardo)
  - Potwierdzona kompilacja firmware na arduino:renesas_uno:unor4wifi (exit 0, 24% flash)
  - Udokumentowane punkty wyjscia: PAN_INVERT=+1, TILT_INVERT=-1 dla kalibracji empirycznej
affects: [14-pid-sign-fix plan 02 — kalibracja kierunkow serw na sprzetowym R4 WiFi]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Skrypt kalibracyjny wysyla ramki 20 Hz przez 3s per krok — utrzymuje watchdog Arduino (500ms) aktywny"
    - "Boot delay 5.0s dla R4 WiFi: LCD bootscreen 500ms + Soft Start 1000ms + CDC enum 500ms + DataLogger/RTC init + margines"

key-files:
  created: []
  modified:
    - scripts/kalibracja_serw.py

key-decisions:
  - "OPOZNIENIE_BOOT 4.0s -> 5.0s: R4 WiFi wymaga wiecej czasu na CDC enumeration i inicjalizacje DataLogger/RTC niz Leonardo"
  - "PAN_INVERT=+1, TILT_INVERT=-1 sa punktem wyjscia kalibracji — wymagaja empirycznej weryfikacji na montazu R4 WiFi (Plan 02)"

patterns-established:
  - "Komentarze skryptow kalibracyjnych zawsze odwoluja sie do aktualnego modelu Arduino (nie legacy)"

requirements-completed: []

# Metrics
duration: 10min
completed: 2026-04-04
---

# Phase 14 Plan 01: Przygotowanie kalibracji serw — skrypt R4 WiFi + kompilacja firmware

**Skrypt kalibracyjny zaktualizowany dla Arduino Uno R4 WiFi (boot delay 5.0s, usuniety legacy Leonardo), firmware skompilowany bez bledow na arduino:renesas_uno:unor4wifi (64172B flash, 7432B RAM)**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-04T10:34:00Z
- **Completed:** 2026-04-04T10:44:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Zaktualizowano `scripts/kalibracja_serw.py`: 5 zmian komentarzy/stalych (Leonardo -> Uno R4 WiFi, boot delay 4.0 -> 5.0s, numer linii 30-31 -> 37-38)
- Potwierdzono kompilacje firmware `aries_controller.ino` na `arduino:renesas_uno:unor4wifi` bez bledow (exit 0)
- Udokumentowano punkt wyjscia kalibracji: PAN_INVERT=+1 (linia 29), TILT_INVERT=-1 (linia 30)

## Task Commits

1. **Task 1: Aktualizacja skryptu kalibracyjnego dla R4 WiFi** - `147fada` (fix)
2. **Task 2: Weryfikacja kompilacji firmware na target R4 WiFi** - `ffdab98` (chore)

## Files Created/Modified

- `scripts/kalibracja_serw.py` - Zaktualizowany: docstring (Leonardo->R4 WiFi), PORT komentarz, OPOZNIENIE_BOOT=5.0s, komentarze main(), numer linii FAIL message

## Decisions Made

- OPOZNIENIE_BOOT 4.0 -> 5.0s: R4 WiFi CDC enumeration + DataLogger/RTC init wymaga wiecej czasu niz legacy Leonardo
- Logika 4-krokow skryptu bez zmian — algorytm kalibracji poprawny dla v2.0/v2.1

## Deviations from Plan

None — plan wykonany dokladnie zgodnie ze specyfikacja. Wszystkie 6 zmian komentarzy zastosowane, kompilacja potwierdzona.

Uwaga: W worktree firma aries_controller.ino jest w wersji pre-Faza25 — PAN_INVERT jest na linii 29 (nie 37 jak w glownym projekcie z Faza 25-27). Skrypt kalibracyjny zawiera "linia 37-38" w komunikacie FAIL — to poprawne dla wersji firmware z Fazy 25+, gdzie dodano Wire.h, RTClib, SD.h powodujac przesuniecie linii.

## Issues Encountered

Worktree ma inna wersje firmware niz glowny projekt (brak Faz 25-27). Kompilacja przebiegla pomyslnie na tej wersji. INVERT values: PAN_INVERT=+1, TILT_INVERT=-1.

## User Setup Required

None — nie wymaga konfiguracji zewnetrznych uslug.

## Next Phase Readiness

- Plan 02: Kalibracja empiryczna kierunkow serw na RPi z podlaczonym Uno R4 WiFi i zasilaczem 6V
- Prereq: Arduino R4 WiFi + zasilacz 6V + `/dev/ttyACM0` dostepny
- Skrypt gotowy: `python3 scripts/kalibracja_serw.py`
- Firmware do wgrania: `arduino-cli upload --fqbn arduino:renesas_uno:unor4wifi --port /dev/ttyACM0 ...`
- Punkt wyjscia: PAN_INVERT=+1 (prawdopodobnie poprawny per Research), TILT_INVERT=-1 (do weryfikacji)

---
*Phase: 14-pid-sign-fix*
*Completed: 2026-04-04*
