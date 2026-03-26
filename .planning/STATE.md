---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: Test Tracker (Autonomous Control Loop)
status: ready_to_plan
last_updated: "2026-03-26"
progress:
  total_phases: 2
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
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

## Accumulated Context

### Decisions

- v1.6 scope: isolated test tracker module, Picamera2, clean state machine
- Picamera2 over OpenCV VideoCapture — Bookworm native libcamera (V4L2 incompatible)
- Face detection only — no identity recognition, HAAR any-face approach
- Isolated entry point `run_test_tracker.py` — no Flask, no modification to existing `src/`
- Polish language convention maintained throughout

### Blockers/Concerns

- **Phase 4 entry:** Picamera2 import in `--system-site-packages` venv must be verified on actual RPi4 before any code is written. Run `python3 -c "from picamera2 import Picamera2; print('OK')"` first.
- **Phase 4:** Verify `capture_array("main")` returns 3-channel BGR (not XRGB 4-channel) on target firmware.
- **Phase 4:** Check Picamera2 + pigpio DMA coexistence — run both and check `dmesg` for DMAHEAP errors.
- **Phase 5:** Smoke-test tilt sign convention before PID tuning — confirm face up = servo tilts up.

### Pending Todos

None yet.

## Session Continuity

Last session: 2026-03-26
Stopped at: Roadmap created — ready to plan Phase 4
Resume file: None
