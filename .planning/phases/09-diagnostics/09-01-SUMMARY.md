---
phase: 09-diagnostics
plan: 01
subsystem: diagnostics
tags: [hardware, pid, awb, hud, mock-mode, picamera2, opencv]

# Dependency graph
requires:
  - phase: 07-test-tracker
    provides: test_tracker.py MaszynaStanow i Picamera2Stream jako baza do rozbudowy
provides:
  - mock_mode property w PanTiltSystem (src/hardware.py)
  - "[MOCK] czerwony overlay w HUD test_tracker (prawy gorny rog)"
  - PID components DEBUG logging per-tick w _sledz() (PAN i TILT)
  - AWB gains re-read po set_controls z detekcja silent failure
affects: [10-detection-tuning, 12-pid-validation, 13-dnn-detector]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "property pattern: _prywatny atrybut eksponowany jako read-only property dla enkapsulacji"
    - "logger.debug dla per-tick diagnostyki (nie zasmiecanie INFO streamu)"
    - "tolerancja 0.1 do porownania gains zmiennoprzecinkowych po AWB"

key-files:
  created: []
  modified:
    - src/hardware.py
    - src/modes/test_tracker.py

key-decisions:
  - "logger.debug dla PID per-tick — INFO byloby za glosne w normalnym uzyciu, DEBUG wymaga jawnego ustawienia poziomu"
  - "Tolerancja 0.1 dla diff gains AWB — ponizej to szum pomiaru, powyzej sugeruje silent failure sensora"
  - "Kolor (0, 0, 255) BGR dla [MOCK] — czysty czerwony, identyczny z TARGET_LOST dla spojnosci ostrzezenia"

patterns-established:
  - "Diagnostyka przez property: hardware.mock_mode zamiast bezposredniego dostepu do _mock_mode"
  - "Re-read po set_controls: zawsze czytaj metadata po ustawieniu i porownaj z zadanymi wartosciami"

requirements-completed: [DIAG-02, DIAG-03, DIAG-04]

# Metrics
duration: 15min
completed: 2026-03-29
---

# Phase 09 Plan 01: Diagnostics Observability Summary

**Trzy addytywne diagnostyki bez zmian logiki: mock_mode property w hardware.py, czerwony [MOCK] overlay na HUD, PID components DEBUG logging per-tick w _sledz(), AWB gains re-read po set_controls z silent failure detection**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-29T08:35:00Z
- **Completed:** 2026-03-29
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Dodano `mock_mode` property do `PanTiltSystem` — eksponuje `_mock_mode` jako publiczny read-only bool (DIAG-02)
- `[MOCK]` czerwony overlay w prawym gornym rogu HUD gdy pigpiod niedostepny (DIAG-02)
- PID components logging (P/I/D/out) per-tick w `_sledz()` na poziomie DEBUG dla obu osi (DIAG-03)
- AWB gains re-read po `set_controls` z porownaniem i logowaniem rozbieznosci (DIAG-04)

## Task Commits

Kazdy task zacommitowany atomicznie:

1. **Task 1: Eksponuj mock_mode jako property w hardware.py** - `4d206ef` (feat)
2. **Task 2: [MOCK] overlay na HUD + PID logging + AWB re-read** - `1a7197d` (feat)

## Files Created/Modified

- `/home/parolisko/ARIES-LITE/src/hardware.py` — dodano `mock_mode` property (5 linii)
- `/home/parolisko/ARIES-LITE/src/modes/test_tracker.py` — [MOCK] overlay, PID logging, AWB re-read (31 linii)

## Decisions Made

- `logger.debug` dla PID per-tick: INFO jest za glosne przy 30 FPS — debug wymaga jawnego `logging.DEBUG`
- Tolerancja 0.1 dla roznic AWB gains: float comparison, ponizej 0.1 to szum pomiaru
- Pozycja [MOCK]: prawy gorny rog (nie dolny) — FPS jest w dolnym prawym, MOCK musi byc widoczny od razu

## Deviations from Plan

Brak — plan wykonany dokladnie jak zapisany.

## Issues Encountered

Brak — wszystkie trzy zmiany addytywne bez regresji. Import test przeszedl, PID logging zweryfikowany przez assert na output loggera.

## Known Stubs

Brak — zaden z dodanych fragmentow nie jest stubem. AWB re-read dziala na realnym sensorze (Picamera2), [MOCK] korzysta z rzeczywistego stanu `_mock_mode`, PID logging czyta z `pid.components` po wywolaniu PID.

## Next Phase Readiness

- Phase 09 kompletna — trzy wymagania DIAG-02/03/04 zrealizowane
- Phase 10 (detection-tuning): HAAR minNeighbors i minSize do zlustrowania (patrz blokery w STATE.md)
- Phase 12 (pid-validation): nie walidowac PID bez stabilnej detekcji z Phase 10

---
*Phase: 09-diagnostics*
*Completed: 2026-03-29*
