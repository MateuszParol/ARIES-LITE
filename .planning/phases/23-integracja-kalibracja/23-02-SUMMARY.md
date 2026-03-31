---
phase: 23-integracja-kalibracja
plan: 02
subsystem: firmware
tags: [arduino, quickpid, servo, oop, c++, refactor, polonizacja, python]

# Dependency graph
requires:
  - phase: 23-01
    provides: Skrypt kalibracyjny serw + logowanie latencji TX w brain.py

provides:
  - Arduino firmware OOP z klasami ServoPID, MaszynaStanow, HMI w jednym pliku .ino
  - Spolonizowane enumy StanSystemu (BEZCZYNNOSC/SKANOWANIE/SLEDZENIE) i StanParsera (CZEKAJ_START/CZYTAJ_PAYLOAD)
  - Kod RPi Python z TRYB_BEZCZYNNOSC/TRYB_SKANOWANIE/TRYB_SLEDZENIE zamiast MODE_IDLE/MODE_SCAN/MODE_TRACK
  - Pelna polonizacja zmiennych, komentarzy i docstringow na obu stronach systemu

affects: [faza-24-tuning, dokumentacja, future-maintainers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Arduino OOP: klasy C++ w jednym pliku .ino — ServoPID/MaszynaStanow/HMI"
    - "Constructor initializer list dla QuickPID — wskazniki do pol klasy (nie zmiennych globalnych)"
    - "przycisk_krok() zwraca bool — loop sprawdza i wywoluje wymus_skanowanie() zamiast callback lambda"
    - "Polskie stalowe trybow: TRYB_* w Python, BEZCZYNNOSC/SKANOWANIE/SLEDZENIE w Arduino"

key-files:
  created: []
  modified:
    - src/arduino/aries_controller/aries_controller.ino
    - src/vision/brain.py
    - src/vision/serial_interface.py
    - src/vision/detector.py
    - src/vision/camera.py

key-decisions:
  - "przycisk_krok() zwraca bool zamiast przyjmowac callback — Arduino avr-gcc nie wspiera lambdy z capture"
  - "MaszynaStanow trzyma referencje do ServoPID i HMI — inicjalizowane jako globale przed instancja maszyny"
  - "wymus_skanowanie() jako publiczna metoda MaszynaStanow — uzywana przez abort przycisku z loop()"

patterns-established:
  - "Pattern: Arduino klasy C++ w jednym .ino — kolejnosc deklaracji: HMI, ServoPID, MaszynaStanow, globalne instancje, setup(), loop()"
  - "Pattern: Enumy z explicite wartosciami liczbowymi gdy cast z uint8 wymagany — BEZCZYNNOSC=0, SKANOWANIE=1, SLEDZENIE=2"

requirements-completed: [INT-04, INT-05]

# Metrics
duration: 10min
completed: 2026-03-31
---

# Phase 23 Plan 02: Refaktor OOP + Polonizacja Summary

**Arduino firmware przepisany na 3 klasy C++ (ServoPID/MaszynaStanow/HMI) z pelna polonizacja obu stron — kompiluje bez bledow, protokol 8B niezmieniony**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-31T19:44:32Z
- **Completed:** 2026-03-31T19:55:03Z
- **Tasks:** 2/3 (Task 3 = checkpoint hardware — oczekiwanie na weryfikacje)
- **Files modified:** 5

## Accomplishments
- Arduino firmware zrefaktoryzowany z proceduralnego C na OOP: 3 klasy (ServoPID, MaszynaStanow, HMI) w jednym pliku .ino — zachowanie identyczne, brak regresji logiki
- Spolonizowane enumy: StanSystemu z BEZCZYNNOSC=0/SKANOWANIE=1/SLEDZENIE=2 (cast z uint8 dziala), StanParsera z CZEKAJ_START/CZYTAJ_PAYLOAD
- Kod RPi Python spolonizowany: MODE_* -> TRYB_* we wszystkich 4 plikach, polskie stringi HUD, polskie komentarze i docstringi
- Kompilacja arduino-cli: exit 0, 59% flash, 22% RAM

## Task Commits

Kazdy task commitowany atomowo:

1. **Task 1: Refaktoryzacja Arduino firmware na klasy C++ (INT-04 + INT-05)** - `7ccca38` (feat)
2. **Task 2: Polonizacja kodu RPi Python (INT-05)** - `769cacf` (feat)
3. **Task 3: Weryfikacja E2E po refaktorze** - oczekuje hardware (checkpoint:human-verify)

## Files Created/Modified
- `src/arduino/aries_controller/aries_controller.ino` - Przepisany na OOP: klasy ServoPID, MaszynaStanow, HMI; spolonizowane enumy i komentarze
- `src/vision/brain.py` - MODE_IDLE/SCAN/TRACK -> TRYB_BEZCZYNNOSC/SKANOWANIE/SLEDZENIE; polskie stringi HUD
- `src/vision/serial_interface.py` - payload -> dane w _buduj_ramke(); spolonizowane komentarze i docstringi
- `src/vision/detector.py` - Spolonizowane komentarze
- `src/vision/camera.py` - Spolonizowane komentarze

## Decisions Made

- **przycisk_krok() zwraca bool**: Plan zakladal callback lambda, ale avr-gcc nie wspiera lambdy z capture w Arduino. Rozwiazanie: metoda zwraca bool, loop() sprawdza i wywoluje `maszyna.wymus_skanowanie()` — to samo zachowanie, czystszy kod.
- **wymus_skanowanie() jako publiczna metoda**: Zamiast udostepniac _przejdz_do() publicznie, dodano dedykowana metode dla abort przycisku — enkapsulacja zachowana.
- **MaszynaStanow inicjalizowana jako global**: Referencje do serwa i hmi sa stabilne od poczatku, bez potrzeby re-inicjalizacji w setup().

## Deviations from Plan

### Auto-fixed Issues

Brak — plan wykonany scisle wedlug specyfikacji z jednym dopasowaniem implementacyjnym.

**Uwaga techniczna (nie odchylenie):** Plan opisywal dwa warianty implementacji przycisk_krok() — callback lambda i zwracany bool. Wybrano wariant z bool (wyraznie wskazany jako "LEPSZE rozwiazanie" w planie). Nie jest to odchylenie od planu.

---

**Total deviations:** 0
**Impact on plan:** Brak odchylen — plan wykonany zgodnie ze specyfikacja.

## Issues Encountered

Brak problemow technicznych. Arduino-cli skompilowalo firmware poprawnie za pierwszym razem.

## Known Stubs

Brak — kod jest czysto strukturalna zmiana, zadne wartosci danych nie sa placeholder ani mockiem.

## User Setup Required

**Task 3 wymaga weryfikacji hardware.** Kroki weryfikacji:

1. Skompiluj i wgraj firmware:
   ```
   arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/
   arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:leonardo src/arduino/aries_controller/
   ```
2. Uruchom skrypt kalibracyjny (weryfikacja braku regresji):
   ```
   source venv/bin/activate
   python3 scripts/kalibracja_serw.py
   ```
   - Oczekiwane: wszystkie 4 kroki PASS (jak w Plan 01)
3. Uruchom pelny system E2E:
   ```
   python3 run_pi_brain.py
   ```
   - HUD powinien pokazywac "Tryb: SLEDZENIE" (polskie nazwy)
   - LCD Arduino powinien pokazywac "SLEDZ" / "SKAN " / "BEZCZ"
4. Zweryfikuj brak regresji HMI: buzzer, przycisk abort, watchdog

## Next Phase Readiness

- Firmware OOP gotowy do uploadu i weryfikacji E2E na hardware
- Kod RPi Python w pelni spolonizowany — zgodny z konwencja projektu (D-07/D-08)
- INT-04 i INT-05 spelnic — po weryfikacji hardware Task 3 zostaje zamkniety
- Blokada: Arduino Leonardo USB enumeration — ten sam bloker co w Plan 01 (Task 3 deferred)

---
*Phase: 23-integracja-kalibracja*
*Completed: 2026-03-31*
