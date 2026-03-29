---
phase: 13-dnn-detector
plan: 01
subsystem: detection
tags: [opencv-dnn, res10, caffe, face-detection, test-tracker]

requires:
  - phase: 10-detection-fix
    provides: HAAR parametry (40,40) minSize — teraz zastapione przez DNN
  - phase: 12-pid-validation
    provides: PID software path zwalidowany — DNN zmienia tylko detekcje, nie PID
provides:
  - "DNN res10_300x300 jako glowny detektor twarzy w test_tracker.py"
  - "Detekcja pod katem >30 stopni (gdzie HAAR zawiodl)"
  - "FPS >= 10 na RPi4 z DNN_SKIP_EVERY=5"
affects: [pid-tuning, main-app-dnn]

tech-stack:
  added: [opencv-dnn, res10_300x300-caffe]
  patterns: [DNN skip_every dla FPS, blob creation z BGR mean subtraction, warm-up forward pass]

key-files:
  created: [models/deploy.prototxt, models/res10_300x300_ssd_iter_140000.caffemodel]
  modified: [src/modes/test_tracker.py]

key-decisions:
  - "DNN_SKIP_EVERY=5 zamiast co-klatke — research zmierzyl 2.4 FPS co klatke, skip_every=5 daje ~12.5 FPS"
  - "Warm-up forward pass w __init__() — eliminuje ~1200ms cold start penalty"
  - "swapRB=False — model trenowany na BGR, OpenCV dostarcza BGR"

patterns-established:
  - "DNN skip_every: forward pass co N klatek, cached bbox miedzy nimi"
  - "Model files w models/ — commitowane do repo"

requirements-completed: [DET-03]

duration: 12min
completed: 2026-03-29
---

# Phase 13: DNN Detector Summary

**OpenCV DNN res10_300x300 zastepuje HAAR cascade w DetekcjaTwarzy — detekcja pod katem >30°, FPS >= 10 na RPi4 z skip_every=5**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-29
- **Completed:** 2026-03-29
- **Tasks:** 2 (1 auto + 1 human-verify)
- **Files modified:** 1 + 2 model files

## Accomplishments
- DNN res10_300x300 zaladowany przez cv2.dnn.readNetFromCaffe — pelna zamiana HAAR
- DNN_SKIP_EVERY=5 daje >10 FPS na RPi4 (research zmierzyl ~12.5 FPS)
- Detekcja twarzy pod katem >30 stopni — potwierdzone empirycznie na RPi4
- Interfejs wykryj() zachowany — MaszynaStanow i TestTracker bez zmian
- Streak filter zachowany — zapobiega migotaniu detekcji
- Warm-up forward pass eliminuje cold start penalty
- RuntimeError przy braku plikow modelu

## Task Commits

1. **Task 1: Zamiana HAAR na DNN** - `23da7d1` (feat)
2. **Task 2: Weryfikacja empiryczna DNN na RPi4** - human-verify checkpoint, approved

## Files Created/Modified
- `src/modes/test_tracker.py` - DetekcjaTwarzy z DNN zamiast HAAR, nowe stale DNN_*
- `models/deploy.prototxt` - Architektura SSD res10 (28KB)
- `models/res10_300x300_ssd_iter_140000.caffemodel` - Wagi modelu (10.6MB)

## Decisions Made
- DNN_SKIP_EVERY=5 zamiast co klatke — konieczne dla >10 FPS (D-07 vs D-08 conflict resolved)
- swapRB=False — model BGR, OpenCV BGR
- Warm-up forward pass na dummy image w __init__()

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
None - model files committed to repo.

## Next Phase Readiness
- DNN detektor dziala na RPi4 z >10 FPS
- Tilt freeze (serwo nie reaguje fizycznie) to nadal osobny bug
- DNN w main app (vision.py) — potencjalna przyszla faza

---
*Phase: 13-dnn-detector*
*Completed: 2026-03-29*
