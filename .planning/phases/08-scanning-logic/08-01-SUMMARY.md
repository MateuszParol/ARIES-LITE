---
phase: 08-scanning-logic
plan: 01
subsystem: tracking
tags: [pid, scanning, sinusoid, state-machine, picamera2, haar]

# Dependency graph
requires:
  - phase: 07-pid-sign-correctness
    provides: tilt negation fix and verified PID convergence on RPi4
provides:
  - Phase offset calculation eliminating servo jump on TRACKING→SCANNING transition
  - Streak reset moved to TARGET_LOST entry preventing premature TRACKING during lost-target window
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Phase offset via math.asin(clamp(pan/amplitude)) computed once on SCANNING entry, applied every tick"
    - "Streak guard reset at state entry (TARGET_LOST) rather than exit (SCANNING) for correct semantics"

key-files:
  created: []
  modified:
    - src/modes/test_tracker.py

key-decisions:
  - "SCAN-01: compute _scan_phase_offset = asin(clamp(pan/SCAN_AMPLITUDE)) at SCANNING entry — clamp prevents ValueError when pan > SCAN_AMPLITUDE"
  - "SCAN-02: resetuj_streak() moved to TARGET_LOST entry (not SCANNING entry) so that streak=0 before face appears during the lost-target window, enforcing 3-consecutive-frame requirement"

patterns-established:
  - "State transition side effects (streak reset, phase offset) belong in _przejdz_do() or at state entry detection, not state exit detection"

requirements-completed:
  - SCAN-01
  - SCAN-02

# Metrics
duration: 8min
completed: 2026-03-27
---

# Phase 8 Plan 01: Scanning Logic Summary

**Sinusoidal scan phase offset (math.asin clamp) + streak reset moved to TARGET_LOST entry to eliminate servo jump and premature TRACKING**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-27T16:00:18Z
- **Completed:** 2026-03-27T16:08:00Z
- **Tasks:** 1/1 auto tasks complete (checkpoint:human-verify pending RPi4 approval)
- **Files modified:** 1

## Accomplishments

- Added `_scan_phase_offset: float = 0.0` to `MaszynaStanow.__init__` — eliminates AttributeError on startup
- Phase offset computed in `_przejdz_do()` at STATE_SCANNING entry: `math.asin(max(-1.0, min(1.0, pan/SCAN_AMPLITUDE)))` — clamp guards against ValueError when pan angle exceeds SCAN_AMPLITUDE
- Offset applied in `_skanuj()` as additional argument to sin, so sinusoid continues from current position rather than jumping to sin(2πft)=0
- `resetuj_streak()` trigger moved from STATE_SCANNING entry to STATE_TARGET_LOST entry — streak now resets the moment a face is lost, enforcing the full 3-frame requirement before re-entering TRACKING

## Task Commits

Each task was committed atomically:

1. **Task 1: SCAN-01 phase offset + SCAN-02 streak reset** - `4d623cb` (fix)

**Plan metadata:** (pending — added after hardware checkpoint)

## Files Created/Modified

- `src/modes/test_tracker.py` — 4 surgical changes: `_scan_phase_offset` field, offset computation in `_przejdz_do()`, offset application in `_skanuj()`, streak reset trigger moved to TARGET_LOST entry

## Decisions Made

- Clamp `pan/SCAN_AMPLITUDE` to `[-1.0, 1.0]` before `math.asin` — necessary because pan can reach 55° while SCAN_AMPLITUDE=45°, giving ratio >1.0 which raises ValueError
- Streak reset at TARGET_LOST entry (not SCANNING entry) — semantically correct: we want the counter to be 0 *before* a face can be seen during the lost-target window, not after SCANNING has already started

## Deviations from Plan

None — plan executed exactly as written. All four changes match the plan specification precisely.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Task 1 complete and committed (4d623cb)
- Awaiting hardware verification checkpoint on RPi4:
  - SCAN-01: verify pan servo resumes sinusoid without visible jump after TRACKING exit
  - SCAN-02: verify 1-2 frame face flash during TARGET_LOST window does not trigger TRACKING
- Once checkpoint approved: Phase 8 closes (all plans complete)

## Self-Check

- [x] `src/modes/test_tracker.py` modified — verified via AST/grep script from plan
- [x] Commit `4d623cb` exists — `fix(08-01): SCAN-01 phase offset + SCAN-02 streak reset at TARGET_LOST`
- [x] All 4 assertion checks passed: `_scan_phase_offset` present, `math.asin` present, `+ self._scan_phase_offset` in `_skanuj()`, old SCANNING-entry streak reset absent

## Self-Check: PASSED

---
*Phase: 08-scanning-logic*
*Completed: 2026-03-27*
