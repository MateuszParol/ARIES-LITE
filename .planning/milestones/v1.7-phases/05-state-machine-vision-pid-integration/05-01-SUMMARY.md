---
phase: 05-state-machine-vision-pid-integration
plan: 01
subsystem: vision
tags: [haar, pid, simple_pid, opencv, state-machine, test-tracker, rpi4]

# Dependency graph
requires:
  - phase: 04-hardware-foundation-camera-integration
    provides: Picamera2Stream, PanTiltSystem, run_test_tracker.py entry point, full module skeleton
provides:
  - Complete autonomous control loop in src/modes/test_tracker.py
  - HAAR face detection with minSize=(80,80) and 3-frame streak filter
  - Dual-axis PID tracking with sample_time=0.033 on both controllers
  - TARGET_LOST as observable transient state (visible in HUD for one frame)
  - FPS counter in bottom-right HUD corner (gray text, instantaneous)
  - Streak reset wired at TestTracker level on SCANNING re-entry
affects: [phase-06, empirical-rpi4-verification, pid-tuning]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sample_time=0.033 on simple_pid stabilizes D-term against variable RPi4 frame timing"
    - "TARGET_LOST as two-tick transient: TRACKING sets it, next tick transitions to SCANNING"
    - "Streak reset wired at TestTracker orchestrator level (not MaszynaStanow) to avoid circular ref"
    - "Instantaneous FPS (1/dt) preferred over rolling average for diagnostics on RPi4"

key-files:
  created: []
  modified:
    - src/modes/test_tracker.py

key-decisions:
  - "HAAR_MIN_SIZE=(80,80): at 320x240 a 50px face is too small for stable PID centroid tracking"
  - "sample_time=0.033 on both PID instances: prevents D-term spikes on variable HAAR timing (30-80ms)"
  - "TARGET_LOST two-tick pattern: visible in red HUD for one frame before SCANNING resumes"
  - "Option B for resetuj_streak: TestTracker.uruchom() watches state transitions, avoids MaszynaStanow<->DetekcjaTwarzy coupling"
  - "Instantaneous FPS display: shows real-time variance on RPi4, diagnostic over cosmetic"
  - "Tilt sign convention confirmed correct on hardware — no inversion needed"

patterns-established:
  - "State transition reset pattern: check (current_state == X and previous_state != X) after tick() call"
  - "FPS counter: compute before detection/tick, render in _rysuj_hud() with cv2.getTextSize for right-alignment"

requirements-completed: [VIS-01, VIS-02, VIS-03, CTL-01, CTL-02, CTL-03, CTL-04]

# Metrics
duration: 12min
completed: 2026-03-26
---

# Phase 5 Plan 01: State Machine, Vision & PID Integration Summary

**HAAR detection (80px minSize) + dual-axis PID (sample_time=0.033) + TARGET_LOST transient state + FPS HUD counter patched into test_tracker.py — 5 gaps, 28 lines changed, complete SCANNING->TRACKING->TARGET_LOST->SCANNING loop, verified on RPi4 hardware**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-26T14:01:51Z
- **Completed:** 2026-03-26T14:13:00Z
- **Tasks:** 2 of 2 complete (Task 1 automated, Task 2 hardware-verified)
- **Files modified:** 1

## Accomplishments

- Patched all 5 gaps in `src/modes/test_tracker.py` in a single wave with no side effects
- Fixed TARGET_LOST from dead code to real two-tick transient state visible in HUD
- Wired streak reset at TestTracker orchestrator level — prevents stale streak count carrying over on SCANNING re-entry
- Added FPS counter with right-aligned gray text in bottom-right corner using cv2.getTextSize
- Verified complete SCANNING -> TRACKING -> TARGET_LOST -> SCANNING loop on physical RPi4 hardware
- Confirmed tilt sign convention is correct — no sign inversion needed

## Task Commits

Each task was committed atomically:

1. **Task 1: Patch all 5 gaps in test_tracker.py** - `28ae2cf` (feat)
2. **Task 2: RPi4 hardware verification** - Approved by user (no code change)

## Files Created/Modified

- `src/modes/test_tracker.py` — 5 targeted patches: HAAR_MIN_SIZE, PID sample_time, TARGET_LOST two-tick pattern, streak reset wiring, FPS counter HUD

## Decisions Made

- HAAR_MIN_SIZE changed from (50,50) to (80,80): plan-specified, confirmed by research that 50px is too small for stable PID centroid on 320x240
- sample_time=0.033 on both PID instances: locked decision from CONTEXT.md, prevents D-term spikes
- TARGET_LOST two-tick pattern: set TARGET_LOST in TRACKING branch, transition to SCANNING happens on next tick via elif STATE_TARGET_LOST branch — makes state visible in HUD for one frame
- resetuj_streak() placed in TestTracker.uruchom() not MaszynaStanow: avoids circular reference, TestTracker already owns both objects
- Tilt sign convention verified correct on RPi4 hardware — no inversion required

## Hardware Verification Results (Task 2)

All 7 requirements verified on physical RPi4 with camera and servos connected:

- **VIS-01:** HAAR detects faces at minSize=(80,80) on 320x240 frames — confirmed
- **VIS-02:** Streak filter (3 frames) prevents false TRACKING transitions; resetuj_streak() fires on SCANNING re-entry — confirmed
- **VIS-03:** HUD shows green bounding box, state label, crosshair, servo angles, FPS counter — confirmed
- **CTL-01:** State machine cycles SCANNING -> TRACKING -> TARGET_LOST -> SCANNING — confirmed
- **CTL-02:** Dual-axis PID tracks correctly with no sign inversion; sample_time=0.033 stabilizes D-term — confirmed
- **CTL-03:** Sinusoidal scan sweeps pan ±45 degrees at 0.1 Hz during SCANNING — confirmed
- **CTL-04:** TARGET_LOST triggers after 2 seconds, visible in HUD (one frame), returns to SCANNING — confirmed

## Deviations from Plan

None - plan executed exactly as written. All 5 gaps were precisely specified in the plan with exact code snippets. No auto-fixes required. No other files modified. Tilt sign convention was confirmed correct (no flip needed, as the plan anticipated).

## Issues Encountered

None. The skeleton was well-structured; all 5 patches were localized single-class changes.

## Self-Check

- [x] `src/modes/test_tracker.py` modified: FOUND
- [x] Commit `28ae2cf` exists in git log
- [x] All 7 grep-based acceptance criteria pass
- [x] Syntax check: `python3 -c "import ast; ast.parse(...)"` returns OK
- [x] No changes to src/config.py, src/hardware.py, run_test_tracker.py
- [x] Task 2 hardware checkpoint: APPROVED by user

## Self-Check: PASSED

---
*Phase: 05-state-machine-vision-pid-integration*
*Completed: 2026-03-26 — all tasks done, hardware verified*
