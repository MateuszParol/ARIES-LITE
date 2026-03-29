---
phase: 11-awb-fix
plan: 01
subsystem: camera
tags: [picamera2, awb, colour-gains, isp, raspberry-pi]

# Dependency graph
requires:
  - phase: 09-diagnostics
    provides: AWB re-read verification block (linie 89-101 test_tracker.py)
provides:
  - AWB configure-time ColourGains lock via create_video_configuration() controls dict
  - Fallback guard dla None i (0.0, 0.0) gains z capture_metadata()
  - Explicit float() cast w set_controls() — zapobiega TypeError na niektorych wersjach Picamera2
affects:
  - phase-12-pid-validation
  - phase-13-dnn-optional

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Configure-time ISP lock: przekazac controls= do create_video_configuration() zamiast tylko post-start set_controls()"
    - "Defensive gains guard: sprawdzac None i (0.0, 0.0) — oba oznaczaja ze AWB jeszcze dziala"
    - "Explicit float cast: float(gains[0]), float(gains[1]) w set_controls() — defensive typing"

key-files:
  created: []
  modified:
    - src/modes/test_tracker.py

key-decisions:
  - "Configure-time ColourGains=(1.0,1.0) w create_video_configuration() — neutralne kolory od frame 0, zanim ISP zdazy narzucic AWB"
  - "Fallback guard rozszerzony o (0.0, 0.0) check — Picamera2 zwraca (0.0,0.0) gdy AWB nadal liczy, nie tylko None"
  - "AWB_FALLBACK_GAINS=(1.0,1.0) jako stala — odkomentowane, referencja w fallback zamiast hardcoded (2.5,1.9)"

patterns-established:
  - "Picamera2 ISP lock pattern: controls w create_video_configuration() + post-start set_controls() z fallback guard"

requirements-completed:
  - AWB-01
  - AWB-02

# Metrics
duration: ~15min
completed: 2026-03-29
---

# Phase 11 Plan 01: AWB Fix Summary

**Picamera2 configure-time ColourGains lock (1.0, 1.0) + fallback guard dla None/(0.0,0.0) eliminuje blue tint od pierwszej klatki**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-29T10:40:21Z
- **Completed:** 2026-03-29T10:55:00Z
- **Tasks:** 2 (1 auto + 1 human-verify)
- **Files modified:** 1

## Accomplishments

- AWB_FALLBACK_GAINS = (1.0, 1.0) odkomentowane jako aktywna stala
- configure-time ColourGains lock w create_video_configuration(controls=...) — neutralne kolory juz w konfiguracji ISP, przed pierwsza klatka
- Fallback guard rozszerzony: obsluguje None i (0.0, 0.0) — oba sa oznakami ze AWB jeszcze sie liczy
- Explicit float() cast w set_controls() — zapobiega TypeError na niektorych wersjach Picamera2
- Wizualna weryfikacja na RPi4 zatwierdzona: log zawiera "ColourGains zablokowane" z niezerowymi wartosciami, brak blue tint od frame 1

## Task Commits

Kazde zadanie zatwierdzone atomicznie:

1. **Task 1: AWB configure-time lock + fallback guard** - `628b1c6` (feat)
2. **Task 2: Weryfikacja wizualna AWB na RPi4** - weryfikacja zaakceptowana przez uzytkownika (brak commita — checkpoint tylko)

## Files Created/Modified

- `src/modes/test_tracker.py` - AWB_FALLBACK_GAINS odkomentowane, configure-time lock, fallback guard rozszerzony, explicit float cast

## Decisions Made

- Uzyta wartosc (1.0, 1.0) jako fallback — neutralne, bez wzmocnienia, universalna dla kazdego srodowiska oswietleniowego
- configure-time controls= jest pewniejszy niz wylacznie post-start set_controls() — ISP laduuje gains juz przy konfiguracji strumienia
- Fallback guard na (0.0, 0.0) dodany na podstawie zachowania Picamera2: zwraca (0.0,0.0) gdy AWB jeszcze liczy, nie tylko None

## Deviations from Plan

None - plan wykonany dokladnie zgodnie z zapisem.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- AWB-01 i AWB-02 spelnione — kolory neutralne od frame 1, brak crashes przy None/(0.0,0.0)
- Phase 12 (PID validation) moze startowac — detekcja stabilna (Phase 10) + AWB poprawne (Phase 11)
- Uwaga: Phase 13 (DNN) prawdopodobnie zbedna — HAAR z streak filter=3 wystarczajacy po Phase 10

---
*Phase: 11-awb-fix*
*Completed: 2026-03-29*
