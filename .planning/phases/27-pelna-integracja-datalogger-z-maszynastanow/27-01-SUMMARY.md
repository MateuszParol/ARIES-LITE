---
phase: 27-pelna-integracja-datalogger-z-maszynastanow
plan: 01
subsystem: firmware
tags: [arduino, datalogger, maszynastanow, csv, rtc, serial, pid]

# Dependency graph
requires:
  - phase: 26-sd-card-datalogger-csv
    provides: "DataLogger z krok(), rotacja dobowa, ring buffer, RTC timestamps"
  - phase: 25-rtc-ds1307-izolowana-integracja
    provides: "ZegarRTC adapter, Wire+RTC inicjalizacja"
provides:
  - "DataLogger zintegrowany z MaszynaStanow — logowanie zmian stanow z RTC timestamp"
  - "face_size z bajtu 6 ramki 8B zapisywany w CSV"
  - "latency_ms obliczany z millis() delta od ostatniej ramki RPi"
  - "Komenda serialowa 'D' do zrzutu 10 ostatnich wpisow bufora"
  - "Bufor krazacy _bufor_diagnostyczny[10][64] w DataLogger"
  - "Guard w _przejdz_do() zapobiegajacy wielokrotnemu logowaniu tego samego stanu"
affects:
  - phase: 28-flash-firmware-uno-r4-wifi
  - e2e-testing

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Kolejnosc klas w pliku .ino: HMI -> ServoPID -> ZegarRTC -> DataLogger -> MaszynaStanow (dependency order)"
    - "Forward reference rozwiazane przez reorder klas, nie przez forward declaration"
    - "Guard pattern: if(nowy == _stan_systemu) return przed logowaniem i akcjami stanu"
    - "Intercept bajtu ASCII przed binarnym parserem ramki — jesli bajt == 'D' to zrzut, inaczej przetwarzaj_bajt()"

key-files:
  created: []
  modified:
    - src/arduino/aries_controller/aries_controller.ino

key-decisions:
  - "Reorder klas w .ino zamiast forward declaration — forward decl nie pozwala na wywolania metod niekompletnego typu"
  - "loguj_zmiane_stanu() uzywa tego samego formatu CSV co _zapisz_csv() — D-05, prosty parsing pandas"
  - "Natychmiastowy flush w loguj_zmiane_stanu() — zdarzenie krytyczne rzadkie, nie degraduje PID"
  - "latency_ms = millis() - maszyna.czas_ostatniej_ramki() w loop() — swiezosc danych z RPi"
  - "(void)stary w loguj_zmiane_stanu() — usuwanie warning unused parametru"

patterns-established:
  - "Kolejnosc globalnych instancji wazna: ZegarRTC -> ServoPID -> HMI -> DataLogger -> MaszynaStanow"
  - "MaszynaStanow przyjmuje DataLogger& przez konstruktor — dependency injection bez singletona"

requirements-completed:
  - INT-06
  - INT-08

# Metrics
duration: 25min
completed: 2026-04-04
---

# Phase 27 Plan 01: Pelna Integracja DataLogger z MaszynaStanow Summary

**DataLogger zintegrowany z MaszynaStanow: logowanie zmian stanow SCAN/TRACK z RTC timestamp, face_size z bajtu 6 ramki 8B, latency_ms z millis() delta, komenda 'D' do zrzutu 10 wpisow diagnostycznych — firmware kompiluje sie na Uno R4 WiFi bez bledow**

## Performance

- **Duration:** 25 min
- **Started:** 2026-04-04T07:50:00Z
- **Completed:** 2026-04-04T08:15:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Pelna integracja DataLogger z MaszynaStanow przez referencje DataLogger& w konstruktorze
- Logowanie WSZYSTKICH zmian stanow (BEZCZYNNOSC/SKANOWANIE/SLEDZENIE) z RTC timestamp i natychmiastowym flush
- Eliminacja placeholderow — face_size z bajtu 6 ramki 8B, latency_ms z millis() delta petli loop()
- Komenda serialowa 'D' — zrzut ostatnich 10 wpisow bufora krazacego na Serial bez wyjmowania karty SD
- Guard w _przejdz_do() zapobiega wielokrotnemu logowaniu tego samego stanu (Pitfall 2)
- Firmware kompiluje sie na arduino:renesas_uno:unor4wifi: Flash 83596B (31%), RAM 11268B (34%)

## Task Commits

1. **Task 1: Integracja DataLogger z MaszynaStanow** - `4154edc` (feat)

**Plan metadata:** (w tym samym commicie co SUMMARY.md)

## Files Created/Modified
- `src/arduino/aries_controller/aries_controller.ino` - Pelna integracja DataLogger z MaszynaStanow: nowe metody loguj_zmiane_stanu() i zrzuc_ostatnie(), bufor krazacy, reorder klas, modyfikacja loop()

## Decisions Made
- Reorder klas w .ino (ZegarRTC i DataLogger PRZED MaszynaStanow) zamiast forward declaration — forward decl pozwala jedynie na wskazniki/referencje w sygnaturach, nie na wywolania metod w ciele klasy. Reorder jest jedynym poprawnym rozwiazaniem dla C++.
- loguj_zmiane_stanu() uzywa formatu `timestamp,stan,pan,tilt,0,0,0,0` — ten sam format CSV co _zapisz_csv() dla prostego parsingu pandas (D-05)
- latency_ms liczony jako `millis() - maszyna.czas_ostatniej_ramki()` w momencie logger.krok() — mierzy swizosc danych z RPi, nie czas petli loop()

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Reorder klas zamiast forward declaration**
- **Found during:** Task 1 (kompilacja po pierwszej wersji zmian)
- **Issue:** Forward declaration `class DataLogger;` pozwala na referencje w sygnaturach, ale blad kompilatora: "invalid use of incomplete type" przy wywolaniu `_logger.loguj_zmiane_stanu()` w ciele metody _przejdz_do() — cialo klasy DataLogger musi byc widoczne w miejscu wywolania
- **Fix:** Przesunieto klasy ZegarRTC i DataLogger PRZED MaszynaStanow w pliku .ino. Usunieto forward declaration.
- **Files modified:** src/arduino/aries_controller/aries_controller.ino
- **Verification:** arduino-cli compile bez bledow
- **Committed in:** 4154edc (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix konieczny — C++ wymaga pelnej definicji klasy przed wywolaniami jej metod. Reorder klas jest standardowym rozwiazaniem w single-file Arduino .ino.

## Issues Encountered
- Kompilacja failowala po pierwszym podejsciu z forward declaration — rozwiazano reorderem klas (patrz Deviations)

## Known Stubs

Brak — wszystkie placeholdery (face_size=0, latency_ms=0) zastapione rzeczywistymi wartosciami.

## Next Phase Readiness
- Firmware gotowy do wgrania na Uno R4 WiFi (Phase 28: flash + weryfikacja sprzetowa E2E)
- DataLogger zapisuje kompletna telemetrie: timestamp RTC, stan systemu, katy serw, bledy PID, face_size, latency_ms
- Komenda 'D' umozliwia weryfikacje bez wyjmowania karty SD

## Self-Check: PASSED
- FOUND: src/arduino/aries_controller/aries_controller.ino
- FOUND: .planning/phases/27-pelna-integracja-datalogger-z-maszynastanow/27-01-SUMMARY.md
- FOUND: commit 4154edc

---
*Phase: 27-pelna-integracja-datalogger-z-maszynastanow*
*Completed: 2026-04-04*
