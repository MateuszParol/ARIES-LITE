# Milestones

## v1.7 Debugging & Optimization (Shipped: 2026-03-29)

**Phases completed:** 5 phases, 6 plans, 12 tasks

**Key accomplishments:**

- Picamera2Stream with fail-fast import, 3-retry mid-run recovery, 2x upscale display, and smooth servo shutdown — closes 4 gaps in test_tracker.py for RPi4 hardware verification
- HAAR detection (80px minSize) + dual-axis PID (sample_time=0.033) + TARGET_LOST transient state + FPS HUD counter patched into test_tracker.py — 5 gaps, 28 lines changed, complete SCANNING->TRACKING->TARGET_LOST->SCANNING loop, verified on RPi4 hardware
- One-character tilt PID sign fix (korekta_tilt negated) and simple-pid>=2.0.1 pin — enables convergent servo tracking in Wave 2 hardware verify
- Empirical RPi4 confirmation that tilt negation fix and simple-pid>=2.0.1 pin (07-01) resolve all three PID failure modes: convergent tilt tracking, unchanged pan direction, and clean integrator on TRACKING re-entry
- Sinusoidal scan phase offset (math.asin clamp) + streak reset moved to TARGET_LOST entry to eliminate servo jump and premature TRACKING

---

## v1.5 Stabilization & Hardening (Shipped: 2026-03-18)

**Phases completed:** 3 phases, 3 plans, 8 tasks
**Lines of code:** 652 Python

**Key accomplishments:**

- Fixed CENTER command crash (missing logger in server.py)
- Added HAAR face detection sort by area — largest face selected
- Thread-safe frame access with lock protection in VideoStream
- Graceful shutdown with SIGINT/SIGTERM handlers — servo detach, camera release
- Non-blocking CENTER command via background thread
- Startup race condition fix with init_event gate on all API routes (503 during boot)
- Removed unused imutils dependency, added proper `__all__` exports
- Cleaned up orphaned adapters/ and .gsd/ directories

---
