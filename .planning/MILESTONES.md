# Milestones

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

