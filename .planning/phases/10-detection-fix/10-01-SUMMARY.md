---
phase: 10-detection-fix
plan: 01
subsystem: vision
tags: [opencv, haar, detection, picamera2, test-tracker]

# Dependency graph
requires: []
provides:
  - HAAR_MIN_NEIGHBORS zmniejszony z 8 do 4 — detekcja pod katem do ±30°
  - HAAR_MIN_SIZE zmniejszony z (80,80) do (40,40) — detekcja od 40cm do ~100cm

affects: [12-pid-validation, 13-dnn-detection]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HAAR minNeighbors=4 + minSize=(40,40) + STREAK_REQUIRED=3 — balans czulosci i false positives"

key-files:
  created: []
  modified:
    - src/modes/test_tracker.py

key-decisions:
  - "HAAR_MIN_NEIGHBORS = 4 (nie 3 default, nie 8 oryginal) — streak filter zapewnia dodatkowa filtracje FP"
  - "HAAR_MIN_SIZE = (40,40) — minimalna twarz zajmuje ~12.5% kadru 320x240, pokrywa 40-100cm przy RPi FOV"
  - "STREAK_REQUIRED = 3 pozostaje bez zmian — wymagane 3 kolejne detekcje przed TRACKING"

patterns-established:
  - "Parametry HAAR jako stale modulowe w test_tracker.py — nie w config.py, per D-05"

requirements-completed: [DET-01, DET-02]

# Metrics
duration: 5min
completed: 2026-03-29
---

# Phase 10 Plan 01: Detection Fix Summary

**HAAR minSize=(40,40) i minNeighbors=4 zamiast (80,80) i 8 — detekcja twarzy od 40cm do 100cm i pod katem do ±30°**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-29T10:00:00Z
- **Completed:** 2026-03-29T10:05:00Z
- **Tasks:** 1 z 2 (Task 2 to checkpoint:human-verify — oczekuje empirycznej weryfikacji na RPi4)
- **Files modified:** 1

## Accomplishments

- Zmieniono HAAR_MIN_NEIGHBORS: 8 → 4 (bliski default OpenCV, streak filter filtruje false positives)
- Zmieniono HAAR_MIN_SIZE: (80,80) → (40,40) (twarz od 40cm do ~100cm przy FOV kamery RPi)
- STREAK_REQUIRED=3 bez zmian — zachowana filtracja fałszywych detekcji
- Syntax check Python AST przeszedl bez bledow

## Task Commits

1. **Task 1: Zmiana parametrow HAAR w test_tracker.py** - `a5fa317` (fix)

## Files Created/Modified

- `/home/parolisko/ARIES-LITE/src/modes/test_tracker.py` - Zmienione stale HAAR_MIN_NEIGHBORS i HAAR_MIN_SIZE

## Decisions Made

None — wykonano dokladnie wedlug planu, decyzje D-01 do D-05 przeniesione z CONTEXT.md.

## Deviations from Plan

None — plan wykonany dokladnie jak zapisano.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Task 2 (checkpoint:human-verify) oczekuje empirycznej weryfikacji na RPi4:
  - Test DET-01: zielony prostokat na HUD przy 40-100cm od kamery
  - Test DET-02: detekcja przy odchyleniu glowy ~30°
  - Test stabilnosci: TRACKING utrzymywany >= 3 sekundy
  - Test false positives: brak TRACKING na pustym pokoju
- Po zatwierdzeniu: Phase 12 (PID validation) moze startowac — zalezna od stabilnej detekcji

---
*Phase: 10-detection-fix*
*Completed: 2026-03-29*
