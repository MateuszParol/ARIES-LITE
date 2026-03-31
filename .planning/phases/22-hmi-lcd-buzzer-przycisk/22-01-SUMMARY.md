---
phase: 22-hmi-lcd-buzzer-przycisk
plan: 01
subsystem: firmware
tags: [arduino, lcd, liquidcrystal, hmi, avr, dtostrf]

# Dependency graph
requires:
  - phase: 20-firmware-arduino-pid-servo
    provides: istniejacy firmware aries_controller.ino z PID, serwa, maszyna stanow
provides:
  - LCD 1602 4-bit inicjalizacja w firmware Arduino (piny 2,3,4,5,6,11)
  - Bootscreen "ARIES-LITE v2.0" przez 2s przy starcie
  - lcd_tick() odswiezanie co 200ms — Row 0: tryb+katy, Row 1: bledy X/Y
  - Wzorzec setCursor+overwrite bez LCD.clear() — brak migotania
affects:
  - 22-02-PLAN (buzzer, przycisk — nastepny plan tej fazy)
  - 23 (weryfikacja empiryczna HMI na hardware)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LCD bez migotania: setCursor(0,0) + print() z nadpisaniem zamiast lcd.clear() w lcd_tick()"
    - "Float na AVR: dtostrf() zamiast sprintf('%f') — avr-libc, sprintf float nieobslugiwany"
    - "HMI poza PID: lcd_tick() w loop() POZA pid_tick() — nie wplywa na 100Hz timing"

key-files:
  created: []
  modified:
    - src/arduino/aries_controller/aries_controller.ino

key-decisions:
  - "setCursor+overwrite zamiast lcd.clear() w lcd_tick() — brak migotania, 1.52ms zaoszczedzone"
  - "dtostrf(kat_pan, 4, 0, buf) dla katow bez miejsc po przecinku — wystarczajaca precyzja na LCD"
  - "Bootscreen przed serwo attach — uzytkownik widzi status podczas inicjalizacji serw"

patterns-established:
  - "Pattern LCD bez migotania: setCursor(row, col) + snprintf do 16-znakowego bufora + lcd.print()"
  - "Pattern dtostrf: dtostrf(wartosc, szerokosc, precyzja, bufor) dla kazdego float na AVR"
  - "Pattern HMI timer: millis() throttle z osobna zmienna czas_ostatniego_lcd — niezalezny od PID"

requirements-completed: [HMI-01, HMI-04]

# Metrics
duration: 3min
completed: 2026-03-31
---

# Phase 22 Plan 01: LCD HMI Summary

**LCD 1602 4-bit zainicjalizowany w firmware Arduino z bootscreen "ARIES-LITE v2.0" (2s) i lcd_tick() odswiezaniem co 200ms — tryb/katy/bledy na fizycznym wyswietlaczu bez migotania**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-31T13:46:38Z
- **Completed:** 2026-03-31T13:49:29Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments

- LCD 1602 skonfigurowany na pinach D2/D3/D4/D5/D6/D11 w trybie 4-bit parallel
- Bootscreen "ARIES-LITE v2.0" + "Inicjalizacja..." widoczny przez 2 sekundy po resecie Arduino
- lcd_tick() co 200ms (5 Hz): Row 0 = tryb systemu (SLEDZ/SKAN/IDLE) + katy serw pan/tilt, Row 1 = blady X/Y z ostatniej ramki
- Brak migotania — setCursor+overwrite zamiast lcd.clear() per Pitfall 3 z RESEARCH.md
- dtostrf() zamiast sprintf("%f") per Pitfall 1 — AVR float-safe
- Kompilacja: 15470B flash (53%), 532B RAM (20%), exit 0

## Task Commits

1. **Task 1: LCD defines, globals, lcd_tick() i bootscreen w setup()** - `65ca09d` (feat)

**Plan metadata:** (docs commit — nastepuje po tej sekcji)

## Files Created/Modified

- `src/arduino/aries_controller/aries_controller.ino` - Dodano LCD #define (LCD_RS/EN/D4-D7_PIN/INTERVAL), globalny LiquidCrystal lcd, lcd_tick(), bootscreen w setup(), wywolanie lcd_tick() w loop()

## Decisions Made

- Katy serw bez miejsc po przecinku (`dtostrf(kat, 4, 0, buf)`) — bardziej czytelne na malym LCD
- Bootscreen przed `serwo_pan.attach()` — uzytkownik widzi status podczas 2s inicjalizacji serw
- setCursor+overwrite zamiast lcd.clear() w lcd_tick() — potwierdzone Pitfall 3 z RESEARCH.md

## Deviations from Plan

Brak — plan wykonany dokladnie zgodnie ze specyfikacja.

## Issues Encountered

Brak.

## Known Stubs

Brak — lcd_tick() odczytuje rzeczywiste zmienne firmware (stan_systemu, kat_pan, kat_tilt, ostatni_blad_x, ostatni_blad_y).

## User Setup Required

Brak konfiguracji zewnetrznych uslug. Upload firmware wymaga polaczenia Arduino Leonardo przez USB: `arduino-cli upload --fqbn arduino:avr:leonardo -p /dev/ttyACM0 src/arduino/aries_controller/`

## Next Phase Readiness

- Plan 22-01 kompletny — LCD HMI gotowy
- Plan 22-02 gotowy do wykonania: buzzer (D8, tone() przy TRACK) + przycisk akcji (D7, INPUT_PULLUP, abort TRACK→SCAN)
- Firmware kompiluje sie czysto — baza dla planu 22-02

---
*Phase: 22-hmi-lcd-buzzer-przycisk*
*Completed: 2026-03-31*
