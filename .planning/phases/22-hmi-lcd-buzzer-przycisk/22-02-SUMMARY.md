---
phase: 22-hmi-lcd-buzzer-przycisk
plan: 02
subsystem: firmware
tags: [arduino, tone, buzzer, przycisk, debounce, hmi, avr]

# Dependency graph
requires:
  - phase: 22-01
    provides: LCD 1602 w firmware — lcd_tick(), lcd.begin(), LiquidCrystal, bootscreen
provides:
  - tone(BUZZER_PIN, 1000, 100) w przejdz_do() — dzwiekowe potwierdzenie TRACK
  - przycisk_tick() z millis() debounce 20ms — abort TRACK→SCAN bez komputera
  - BUZZER_PIN=D8, PRZYCISK_PIN=D7 zdefiniowane i obsluzone w firmware
affects: [22-verify, phase-23-kalibracja-serw]

# Tech tracking
tech-stack:
  added: [tone() (built-in AVR), digitalRead() INPUT_PULLUP pattern]
  patterns: [millis() debounce bez zewnetrznych bibliotek, tone() nieblokujace w przejdz_do()]

key-files:
  created: []
  modified:
    - src/arduino/aries_controller/aries_controller.ino

key-decisions:
  - "tone(BUZZER_PIN, 1000, 100) wywolywane wylacznie w przejdz_do() gdy nowy_stan == TRACK — nie w pid_tick() ani loop()"
  - "przycisk_tick() aktualizuje przycisk_ostatni_stan NA KONCU funkcji (edge detect HIGH→LOW z debounce, nie level detect)"
  - "millis() debounce 20ms bez zewnetrznej biblioteki — zero zaleznosci, deterministyczny timing"

patterns-established:
  - "Pattern: millis() debounce — sprawdz zbocze, zapisz timestamp, po DEBOUNCE_MS i stan LOW → akcja, aktualizuj last_state na koncu"
  - "Pattern: tone() nieblokujace — wywolanie z czasem trwania w ms, Timer3 niezalezny od Servo Timer1 na Leonardo"

requirements-completed: [HMI-02, HMI-03]

# Metrics
duration: 3min
completed: 2026-03-31
---

# Phase 22 Plan 02: HMI Buzzer + Przycisk Abort Summary

**Nieblokujace tone() 1kHz/100ms przy TRACK + millis() debounce 20ms na D7 abort TRACK→SCAN — HMI kompletne bez wplywu na PID 100Hz**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-31T13:52:48Z
- **Completed:** 2026-03-31T13:55:13Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Buzzer D8: tone(BUZZER_PIN, 1000, 100) w przejdz_do() — dzwiekowe potwierdzenie "Target Lock" przy kazdy przejsciu do TRACK
- Przycisk D7: przycisk_tick() z millis() debounce 20ms — abort sledzenia do SCAN bez komputera, ignorowany w SCAN/IDLE
- Kompilacja arduino-cli bez bledow: 16506 B flash (57%), 565 B RAM (22%)

## Task Commits

1. **Task 1: Buzzer tone() + przycisk_tick() z debounce** - `657df8f` (feat)

**Plan metadata:** (commits docs separately)

## Files Created/Modified

- `src/arduino/aries_controller/aries_controller.ino` — dodano BUZZER_PIN/PRZYCISK_PIN/DEBOUNCE_MS defines, zmienne debounce, tone() w przejdz_do(), przycisk_tick(), pinMode w setup(), przycisk_tick() w loop()

## Decisions Made

- `tone()` wywolywane wylacznie w `przejdz_do()` przy nowy_stan == TRACK — nie w `pid_tick()` ani `loop()`. Gwarantuje jeden dzwiek na przejscie, brak interferecji z PID 100Hz.
- `przycisk_tick()` aktualizuje `przycisk_ostatni_stan` NA KONCU funkcji (po sprawdzeniu warunku debounce). Plan explicite zaznaczal to jako kluczowe — edge detect HIGH→LOW z debounce zamiast level detect z natychmiastowym update (jak Pattern 2 w RESEARCH.md).
- `millis()` debounce 20ms bez zewnetrznych bibliotek per decyzja D-08.

## Deviations from Plan

Brak — plan wykonany dokladnie wedlug specyfikacji.

## Issues Encountered

Brak.

## User Setup Required

None — zmiany firmware tylko. Upload do Arduino przez `arduino-cli upload --fqbn arduino:avr:leonardo -p /dev/ttyACM0 src/arduino/aries_controller/` wymagany przy fizycznym dostepie do sprzetowego stanowiska.

## Next Phase Readiness

- Firmware Arduino kompletny: LCD 1602 + buzzer + przycisk — caly HMI z planu 22 zrealizowany
- Weryfikacja empiryczna wymagana na sprzetowym stanowisku: slyszalnosc buzzera z 1m, reakcja przycisku < 50ms, brak wplywu na plynnosc serw
- Phase 22 zakonczona — system gotowy do kalibracji kierunkow serw (Phase 23)

---
*Phase: 22-hmi-lcd-buzzer-przycisk*
*Completed: 2026-03-31*
