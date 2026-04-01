---
phase: 24-migracja-pinow-i-kompilacja-bazowa
plan: 01
subsystem: firmware
tags: [arduino, aries_controller, uno-r4-wifi, renesas, serial, pid, servo, lcd]

# Dependency graph
requires:
  - phase: 23-integracja-kalibracja
    provides: Firmware OOP v2.0 (ServoPID, MaszynaStanow, HMI) — baza do migracji
provides:
  - Firmware v2.1 skompilowany zero bledow na arduino:renesas_uno:unor4wifi
  - Nowa mapa pinow: PAN=D6, TILT=D9, LCD(A0,A1,D2-D5), Buzzer=D8, Przycisk=D7
  - pinMode(A0, OUTPUT) i pinMode(A1, OUTPUT) w setup() per D-11
  - dtostrf zastapione snprintf z int cast (ARM Renesas kompatybilny)
  - Serial CDC wait skrocony do 500ms (z 3000ms)
  - Soft Start delay(500) przed inicjalizacja serw (MIG-08)
  - serial_interface.py bez Leonardo DTR workaround
affects: [25-rtc-ds1307, 26-sd-datalogger, 27-integracja-datalogger]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - snprintf z int cast zamiast dtostrf dla float-to-string na ARM
    - Jawne pinMode(A0, OUTPUT) dla pinow analogowych uzytych jako GPIO

key-files:
  created: []
  modified:
    - src/arduino/aries_controller/aries_controller.ino
    - src/vision/serial_interface.py

key-decisions:
  - "PAN=D6, TILT=D9 — nowa mapa serw dla Uno R4 WiFi (D-02)"
  - "LCD RS=A0, EN=A1, D4-D7=D2-D5 — mapa LCD dla DataLogger Shield (D-01)"
  - "snprintf('%4d', (int)kat) zamiast dtostrf — ARM Renesas nie ma dtostrf (D-07)"
  - "delay(500) Soft Start przed serwa.inicjalizuj() — stabilizacja zasilacza 6V (D-05)"
  - "Serial CDC wait 500ms zamiast 3000ms — R4 uzywa ESP32-S3 bridge (D-06)"
  - "pinMode(A0, OUTPUT) i pinMode(A1, OUTPUT) w setup() przed hmi.inicjalizuj() (D-11)"

patterns-established:
  - "snprintf z int cast: snprintf(buf, sizeof(buf), \"%4d\", (int)float_val)"
  - "Jawny pinMode dla pinow analogowych uzytych jako LCD GPIO"

requirements-completed: [MIG-03, MIG-04, MIG-05, MIG-06, MIG-07, MIG-08, MIG-09]

# Metrics
duration: 4min
completed: 2026-04-01
---

# Phase 24 Plan 01: Migracja firmware na Uno R4 WiFi — kompilacja bazowa

**Port firmware ARIES-LITE v2.0→v2.1: 7 zmian #define pinow, snprintf zamiast dtostrf, Soft Start 500ms, CDC wait 500ms — kompilacja zero bledow na arduino:renesas_uno:unor4wifi (64KB/262KB, 22% RAM)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-01T16:50:08Z
- **Completed:** 2026-04-01T16:54:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Firmware v2.1 kompiluje sie zero bledow na Arduino Uno R4 WiFi (64172 bajtow = 24% flash, 7432 bajtow = 22% RAM)
- Nowa mapa pinow zaimplementowana: PAN=D6, TILT=D9, LCD(A0,A1,D2-D5), Buzzer=D8 i Przycisk=D7 bez zmian
- dtostrf() calkowicie usuniete, zastapione snprintf z int cast (ARM Renesas RA4M1 kompatybilny)
- Jawne pinMode(A0, OUTPUT) i pinMode(A1, OUTPUT) w setup() przed inicjalizacja LCD (per D-11)
- Soft Start delay(500) dodany miedzy hmi.inicjalizuj() a serwa.inicjalizuj() — stabilizacja napiecia 6V
- Serial CDC wait skrocony z 3000ms do 500ms — R4 WiFi uzywa ESP32-S3 bridge, nie natywne USB CDC
- serial_interface.py oczyszczone z Leonardo-specific DTR=False workaround
- Komentarz naglowkowy i bootscreen LCD zaktualizowane do v2.1

## Task Commits

1. **Task 1: Migracja firmware na Uno R4 WiFi** - `ad4e5ca` (feat)
2. **Task 2: Usuniecie Leonardo DTR workaround** - `4f928b1` (fix)

**Plan metadata:** (docs commit — nastepny)

## Files Created/Modified

- `/home/parolisko/ARIES-LITE/src/arduino/aries_controller/aries_controller.ino` — Firmware v2.1: nowa mapa pinow, snprintf, pinMode A0/A1, Soft Start, CDC 500ms, wersja v2.1
- `/home/parolisko/ARIES-LITE/src/vision/serial_interface.py` — Usunieto ser.dtr=False, zaktualizowano docstring do Uno R4 WiFi

## Decisions Made

- snprintf z `"%4d"` i `(int)kat` zamiast dtostrf — precision=0 w oryginale upraszcza zamiane, int cast wystarczy
- delay(500) Soft Start umieszczony PO hmi.inicjalizuj() (bootscreen widoczny od razu) ale PRZED serwa.inicjalizuj() (zasilacz stabilny przed ruchem)
- Jawne pinMode(A0, OUTPUT) przed hmi.inicjalizuj() — gwarantuje OUTPUT zanim LiquidCrystal przejmie piny
- CDC wait skrocony do 500ms — R4 uzywa ESP32-S3 bridge zamiast natywnego USB CDC, 500ms wystarczy

## Deviations from Plan

None — plan wykonany dokladnie zgodnie ze specyfikacja.

## Issues Encountered

- Weryfikacja importu `from src.vision.serial_interface import SerialInterface` nie dziala przez `src/vision/__init__.py` importujacy mediapipe (brak na dev machine). Zweryfikowano przez bezposredni import modulu — SerialInterface importuje poprawnie. Issue pre-existing, niezwiazany ze zmianami w tym planie.

## User Setup Required

None — nie wymagana konfiguracja zewnetrzna. Flashowanie firmware na Uno R4 WiFi nastapi w Planie 02.

## Next Phase Readiness

- Firmware v2.1 gotowy do flashowania na Uno R4 WiFi (`arduino-cli upload`)
- Plan 02 (weryfikacja sprzetowa): flash + test serw + test LCD + test przycisk + test buzzer
- Brak blokow — kompilacja zweryfikowana, zmiany atomowe i sprawdzone

---
*Phase: 24-migracja-pinow-i-kompilacja-bazowa*
*Completed: 2026-04-01*
