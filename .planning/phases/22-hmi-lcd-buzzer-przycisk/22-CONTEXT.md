# Phase 22: HMI LCD + Buzzer + Przycisk - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Rozbudowa firmware Arduino (`aries_controller.ino`) o fizyczny interfejs uzytkownika: LCD 1602 wyswietla tryb i katy serw, buzzer potwierdza dzwiekowo przejscie do TRACK, przycisk D7 pozwala recznie przerwac sledzenie (abort TRACK→SCAN). Bootscreen z nazwa systemu przy starcie.

Faza NIE obejmuje: zmian w pi_brain.py (RPi), kalibracji kierunkow serw (Phase 23), zmian w protokole 8B, zmian w PID.

</domain>

<decisions>
## Implementation Decisions

### LCD layout
- **D-01:** LCD 2x16. Row 0: tryb (SKAN/SLEDZ/IDLE) + FPS. Row 1: katy serw P:+12.3 T:-5.7. Diagnostyczne podejscie — uzytkownik widzi katy a nie blad pikseli.
- **D-02:** Odswiezanie LCD max 5 Hz (co 200ms) via osobny timer millis(). LCD.print() ~1ms nie blokuje PID tick 10ms. Per HMI-01.
- **D-03:** Bootscreen: nazwa systemu ("ARIES-LITE v2.0") na LCD przez pierwsze 2 sekundy po starcie. Per HMI-04.

### LCD piny
- **D-04:** Piny LCD — Claude's Discretion. Researcher zbada optymalne mapowanie pinow dla Leonardo. Ograniczenia: D7 (przycisk), D8 (buzzer), D9/D10 (serwa) zajete. LiquidCrystal.h juz #include w firmware.

### Buzzer
- **D-05:** Buzzer na pinie D8. Krotki beep (100ms, ~1kHz) TYLKO przy przejsciu do TRACK ("Target Lock"). Brak dzwiekow przy innych przejsciach. Per HMI-02.
- **D-06:** Uzywaj tone() — Arduino Leonardo ma Timer3 (niezalezny od Timer1 serw). tone() nie koliduje z serwami na D9/D10.

### Przycisk
- **D-07:** Przycisk na pinie D7 z INPUT_PULLUP. Aktywny TYLKO w trybie TRACK — przerywa sledzenie i przechodzi do SCAN (abort). W SCAN/IDLE ignorowany. Per HMI-03.
- **D-08:** Debounce przez millis() (20ms). Reakcja w ciagu 50ms od wcisniecia. Bez zewnetrznej biblioteki — prosty wzorzec millis().

### Integracja z petla
- **D-09:** LCD, buzzer i przycisk obslugiwane w loop() POZA pid_tick() — nie wplywaja na deterministyczny timing PID 100Hz.
- **D-10:** Buzzer wywolywany w przejdz_do() — jedyne miejsce zmiany stanu. tone(BUZZER_PIN, 1000, 100) przy nowym stanie == TRACK.

### Claude's Discretion
- Mapowanie pinow LCD (RS, EN, D4-D7 lub I2C) — D-04
- Dokladny format tekstu na LCD (ile znakow, padding, formatowanie katow)
- Kolejnosc inicjalizacji LCD w setup() (po safe_startup czy przed?)
- Czy LCD.clear() przy kazdym odswiezeniu czy tylko przy zmianie trybu

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Firmware
- `src/arduino/aries_controller/aries_controller.ino` — Aktualny firmware z Phase 20: #include LiquidCrystal.h (juz obecne), enum StanSystemu, przejdz_do(), pid_tick(), setup(), loop()
- `.planning/protocol/PROTOCOL_SPEC.md` — Protokol 8B LOCKED (nie zmieniamy)

### Kontekst faz
- `.planning/phases/20-firmware-arduino-pid-servo/20-CONTEXT.md` — Decyzje firmware: PID, serwa, maszyna stanow
- `.planning/phases/20-firmware-arduino-pid-servo/20-01-SUMMARY.md` — Co zbudowano: defines, globals, safe_startup, init_pid, ustaw_serwa
- `.planning/phases/20-firmware-arduino-pid-servo/20-02-SUMMARY.md` — Co zbudowano: dispatch_ramke, pid_tick, skan_tick, loop

### Requirements
- `.planning/REQUIREMENTS.md` §HMI — HMI-01..HMI-04: LCD, buzzer, przycisk, bootscreen

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `#include <LiquidCrystal.h>` juz w firmware — nie trzeba dodawac
- `przejdz_do(StanSystemu nowy_stan)` — jedyne miejsce zmiany stanu, idealny hook dla buzzera
- `millis()` timing pattern — juz uzywany w pid_tick() i watchdog, powielenie dla LCD i debounce

### Established Patterns
- #define na poczatku pliku dla konfiguracji (D-04 z Phase 20)
- Zmienne globalne pod defines
- Funkcje pomiedzy przetwarzaj_bajt() a setup()
- Komentarze po polsku, 4-space indent

### Integration Points
- `loop()`: dodac lcd_tick() i przycisk_tick() obok pid_tick()
- `przejdz_do()`: dodac tone() dla TRACK
- `setup()`: dodac lcd.begin(), bootscreen, pinMode przycisk, pinMode buzzer

</code_context>

<specifics>
## Specific Ideas

- LCD Row 0: tryb + FPS (diagnostyczne), Row 1: katy serw (P:+12.3 T:-5.7)
- Buzzer tylko przy TRACK — minimalne zaklocenie
- Przycisk abort TRACK→SCAN — bezpieczenstwo uzytkowe
- Bootscreen "ARIES-LITE v2.0" przez 2s

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-hmi-lcd-buzzer-przycisk*
*Context gathered: 2026-03-31*
