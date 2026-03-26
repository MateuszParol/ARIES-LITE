---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: Test Tracker
status: planning
stopped_at: Completed 05-state-machine-vision-pid-integration/05-01-PLAN.md
last_updated: "2026-03-26T14:24:31.522Z"
last_activity: 2026-03-26 — Roadmap created for v1.6
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 2
  completed_plans: 2
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-26)

**Core value:** Izolowany moduł testowy udowadniający płynne działanie hardware (pigpio + PID) z Picamera2 na RPi OS Bookworm
**Current focus:** Phase 4 — Hardware Foundation & Camera Integration

## Current Position

Phase: 4 of 5 (Hardware Foundation & Camera Integration)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-03-26 — Roadmap created for v1.6

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (v1.6)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 4. Hardware Foundation | TBD | — | — |
| 5. State Machine + Vision | TBD | — | — |

*Updated after each plan completion*
| Phase 04 P01 | 18 | 3 tasks | 1 files |
| Phase 05-state-machine-vision-pid-integration P01 | 2 | 1 tasks | 1 files |
| Phase 05 P01 | 12 | 2 tasks | 1 files |

## Accumulated Context

### Decisions

- v1.6 scope: isolated test tracker module, Picamera2, clean state machine
- Picamera2 over OpenCV VideoCapture — Bookworm native libcamera (V4L2 incompatible)
- Face detection only — no identity recognition, HAAR any-face approach
- Isolated entry point `run_test_tracker.py` — no Flask, no modification to existing `src/`
- Polish language convention maintained throughout
- [Phase 04]: No mock camera mode — Picamera2 unavailable = sys.exit(1) with actionable install instructions
- [Phase 04]: Camera retry limited to 3 attempts (CAMERA_MAX_RETRIES) with 1s delay before clean shutdown
- [Phase 04]: Display upscaled 2x (320x240 to 640x480) using cv2.INTER_NEAREST; headless mode auto-detected via cv2.error
- [Phase 04]: No mock camera mode — Picamera2 unavailable = sys.exit(1) with actionable install instructions
- [Phase 04]: Camera retry limited to 3 attempts (CAMERA_MAX_RETRIES) with 1s delay before clean shutdown
- [Phase 04]: Display upscaled 2x (320x240 to 640x480) using cv2.INTER_NEAREST; headless mode auto-detected via cv2.error
- [Phase 05]: HAAR_MIN_SIZE=(80,80): 50px too small for stable PID centroid tracking at 320x240
- [Phase 05]: sample_time=0.033 on both PID instances prevents D-term spikes from variable HAAR frame timing
- [Phase 05]: TARGET_LOST two-tick pattern: visible in HUD for one frame before SCANNING resumes
- [Phase 05]: resetuj_streak() wired at TestTracker level (not MaszynaStanow) to avoid circular reference
- [Phase 05]: Tilt sign convention verified correct on RPi4 hardware — no sign inversion needed in _sledz()
- [Phase 05]: Tilt sign convention verified correct on RPi4 hardware — no sign inversion needed in _sledz()

### Blockers/Concerns

- **Phase 4 entry:** Picamera2 import in `--system-site-packages` venv must be verified on actual RPi4 before any code is written. Run `python3 -c "from picamera2 import Picamera2; print('OK')"` first.
- **Phase 4:** Verify `capture_array("main")` returns 3-channel BGR (not XRGB 4-channel) on target firmware.
- **Phase 4:** Check Picamera2 + pigpio DMA coexistence — run both and check `dmesg` for DMAHEAP errors.
- **Phase 5:** Tilt sign convention verified correct on RPi4 — no inversion needed. Resolved.

### Pending Todos

None yet.

## Session Continuity

Last session: 2026-03-26T14:20:39.319Z
Stopped at: Completed 05-state-machine-vision-pid-integration/05-01-PLAN.md
Resume file: None
