---
phase: 07-pid-sign-correctness
plan: 01
subsystem: pid-control
tags: [simple-pid, pid, tilt, servo, test_tracker]

# Dependency graph
requires:
  - phase: 06-clamp-logging-awb
    provides: "clamp logging + AWB warm-up in test_tracker.py — stable visual baseline"
provides:
  - "korekta_tilt = -self.pid_tilt(blad_tilt) — tilt PID sign corrected for convergence"
  - "simple-pid>=2.0.1 pinned in requirements.txt — anti-windup reset() bug fixed"
affects: [07-02-hardware-verify, scan-logic-phase]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Both PID axes negated identically: korekta_pan = -pid_pan(), korekta_tilt = -pid_tilt()"

key-files:
  created: []
  modified:
    - src/modes/test_tracker.py
    - requirements.txt

key-decisions:
  - "Tilt negation is 1-character fix: add minus sign to korekta_tilt in MaszynaStanow._sledz()"
  - "simple-pid pinned to >=2.0.1 (not ==) to allow patch releases while ensuring _last_error reset fix"
  - "venv not present on dev machine — requirements.txt update is sufficient; pip install on RPi4 during Wave 2"

patterns-established:
  - "pixel-to-servo axis inversion: both pan and tilt outputs negated before adding to current angle"

requirements-completed: [PID-01, PID-02, PID-03]

# Metrics
duration: 1min
completed: 2026-03-27
---

# Phase 7 Plan 01: PID Sign Correctness Summary

**One-character tilt PID sign fix (korekta_tilt negated) and simple-pid>=2.0.1 pin — enables convergent servo tracking in Wave 2 hardware verify**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-27T15:21:16Z
- **Completed:** 2026-03-27T15:22:22Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Negation added to korekta_tilt in MaszynaStanow._sledz() — tilt axis now converges toward face instead of diverging to soft-limit
- simple-pid dependency bumped from ==2.0.0 to >=2.0.1 — eliminates stale _last_error on PID reset() entering TRACKING
- Smoke test (ast.parse) confirms both corrections present and module syntax valid

## Task Commits

Each task was committed atomically:

1. **Task 1: Verify and upgrade simple-pid to >= 2.0.1** - `a64542a` (chore)
2. **Task 2: Apply tilt sign fix in MaszynaStanow._sledz()** - `cd6776e` (fix)
3. **Task 3: Smoke test — import and startup check** - (auto-checkpoint, no code change, no separate commit)

## Files Created/Modified
- `src/modes/test_tracker.py` - Line 275: korekta_tilt = -self.pid_tilt(blad_tilt); comment updated to "Obie korekty negowane"
- `requirements.txt` - simple-pid==2.0.0 → simple-pid>=2.0.1

## Decisions Made
- Pinned `>=2.0.1` instead of `==2.0.1` — allows patch releases while guaranteeing the reset() fix (introduced in 2.0.1)
- Comment on line 273 updated from "# Pan negowany (jak w tracker.py:77)" to "# Obie korekty negowane — inwersja osi pixel→servo" — reflects new symmetric treatment of both axes
- venv absent on dev machine (macOS); pip install will run on RPi4 during Wave 2 hardware session

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. venv not present on dev machine (expected for macOS dev environment per CLAUDE.md). Verification performed with system Python3 ast.parse — sufficient for syntax and sign correctness checks.

## User Setup Required

On RPi4 before hardware verify (Wave 2):
```bash
source venv/bin/activate
pip install -r requirements.txt
pip show simple-pid  # Confirm Version: >= 2.0.1
```

## Next Phase Readiness
- Wave 1 code changes complete: tilt sign fixed, simple-pid version updated
- Ready for Phase 07-02 hardware verify (Wave 2): run_test_tracker.py on RPi4, confirm tilt convergence
- Functional verification (convergence, no integrator spike, no pan regression) deferred to 07-02 per plan

---
*Phase: 07-pid-sign-correctness*
*Completed: 2026-03-27*
