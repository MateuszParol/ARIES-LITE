---
phase: 04-hardware-foundation-camera-integration
plan: 01
subsystem: hardware
tags: [picamera2, opencv, pigpio, servos, pid, threading]

# Dependency graph
requires: []
provides:
  - Picamera2Stream with fail-fast sys.exit(1) on missing picamera2
  - Camera retry logic (up to 3 retries on mid-run failure)
  - First-frame format verification with 4-channel trim
  - 2x upscale display (320x240 → 640x480) with cv2.error headless fallback
  - smooth_move_to(0, 0) before detach_servos on shutdown
affects: [05-state-machine-vision]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fail-fast imports: missing hardware dependency causes sys.exit(1) not silent mock mode"
    - "Camera retry: up to CAMERA_MAX_RETRIES re-initializations on capture failure before clean shutdown"
    - "Headless fallback: cv2.error on imshow activates headless mode, state transitions logged instead"
    - "Safe shutdown: smooth_move_to(0, 0) before detach_servos prevents servo current spike"

key-files:
  created: []
  modified:
    - src/modes/test_tracker.py

key-decisions:
  - "No mock camera mode — Picamera2 unavailable = sys.exit(1) with actionable install instructions"
  - "Camera retry limited to 3 attempts with 1s delay before clean shutdown"
  - "Display upscaled 2x (320x240 to 640x480) using INTER_NEAREST to avoid blur"
  - "Headless mode auto-detected via cv2.error, state transitions provide terminal output"

patterns-established:
  - "Fail-fast over silent fallback for hardware dependencies"
  - "Retry with re-initialization for transient camera failures"

requirements-completed: [HW-01, HW-02, HW-03, HW-04]

# Metrics
duration: 18min
completed: 2026-03-26
---

# Phase 4 Plan 01: Hardware Foundation — Test Tracker Gaps Summary

**Picamera2Stream with fail-fast import, 3-retry mid-run recovery, 2x upscale display, and smooth servo shutdown — closes 4 gaps in test_tracker.py for RPi4 hardware verification**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-03-26T12:04:11Z
- **Completed:** 2026-03-26T12:22:00Z (Tasks 1-2 complete; Task 3 awaits human verify on RPi4)
- **Tasks:** 2/3 automated tasks complete (1 checkpoint pending human verify)
- **Files modified:** 1

## Accomplishments
- Replaced Picamera2 mock fallback with fail-fast sys.exit(1) — no silent empty frames on missing library
- Added camera retry logic (up to 3 re-initializations on mid-run exception) with clean shutdown after exhausting retries
- Added first-frame format verification with automatic 4-channel → 3-channel BGR trim
- Added 2x upscale (320x240 → 640x480) for display with automatic headless fallback on cv2.error
- Added smooth_move_to(0, 0) before detach_servos in zatrzymaj() — HW-01 safe shutdown requirement

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix Picamera2 fail-fast import and shutdown safety** - `f91b184` (feat)
2. **Task 2: Add camera retry logic and 2x upscale display with headless fallback** - `59b354e` (feat)
3. **Task 3: Verify all HW requirements on RPi4** - AWAITING human verification

## Files Created/Modified
- `src/modes/test_tracker.py` - Picamera2Stream and TestTracker patched with all 4 gap fixes

## Decisions Made
- No mock camera mode — plan specified sys.exit(1) as the correct behavior for a hardware-only module
- CAMERA_MAX_RETRIES=3 and CAMERA_RETRY_DELAY=1.0 placed as module-level constants (not hardcoded)
- Headless mode uses existing MaszynaStanow._przejdz_do() state-change logs — no additional periodic logging needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**Task 3 requires physical RPi4 hardware verification.** Pre-flight checks on RPi4:

```bash
# 1. Verify Picamera2 is available (venv with --system-site-packages)
python3 -c "from picamera2 import Picamera2; print('OK')"

# 2. Verify OpenCV
python3 -c "import cv2; print(cv2.__version__)"

# 3. Start pigpio daemon
sudo pigpiod

# 4. Run the test tracker
python3 run_test_tracker.py
```

Expected observations:
- HW-01: Servos move incrementally to neutral at startup — no reboot, no dmesg under-voltage
- HW-02: cv2.imshow window at 640x480 showing live feed; log shows "Picamera2 uruchomiona: 320x240 BGR888"
- HW-03: Ctrl+C produces "Powrot do pozycji neutralnej..." then "TestTracker zatrzymany"; no leftover libcamera process
- HW-04: `git diff src/hardware.py src/config.py src/camera.py src/tracker.py src/vision.py` shows no changes

## Next Phase Readiness
- Code-side changes complete — ready for RPi4 hardware verification
- Once Task 3 passes, HW-01 through HW-04 requirements are formally verified
- Phase 5 (State Machine + Vision) can begin after checkpoint pass

---
*Phase: 04-hardware-foundation-camera-integration*
*Completed: 2026-03-26 (Tasks 1-2; Task 3 checkpoint pending)*
