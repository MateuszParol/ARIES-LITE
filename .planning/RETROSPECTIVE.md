# Retrospective

## Milestone: v1.5.0 — Stabilization & Hardening

**Shipped:** 2026-03-18
**Phases:** 3 | **Plans:** 3 | **Tasks:** 8

### What Was Built
- Fixed CENTER command crash (missing logger)
- HAAR face detection sorted by area (largest face selected)
- Thread-safe frame access in VideoStream
- Graceful shutdown with SIGINT/SIGTERM signal handlers
- Non-blocking CENTER command (background thread)
- Startup race condition guard (init_event + 503 response)
- Cleaned dependencies (removed imutils, added __all__)
- Removed orphaned adapters/ and .gsd/ directories

### What Worked
- Single-wave execution per phase kept things simple
- All three phases were independent enough to execute sequentially in one session
- GSD tracking caught the Phase 1 SUMMARY gap before milestone completion

### What Was Inefficient
- Phase 1 was executed before GSD tracking was set up, requiring manual SUMMARY backfill
- REQUIREMENTS.md wasn't updated during Phase 1 and Phase 2 execution (only Phase 3 executor updated REQ-17)

### Patterns Established
- `web/server.py` is the central modification point for robustness fixes
- `require_init()` pattern for Flask route guards
- Signal handler + try/finally belt-and-suspenders for shutdown

### Key Lessons
- Start GSD tracking before Phase 1 execution to avoid artifact gaps
- Requirements should be marked Validated as part of each phase execution, not batched at milestone completion

## Cross-Milestone Trends

| Metric | v1.5.0 |
|--------|--------|
| Phases | 3 |
| Plans | 3 |
| Tasks | 8 |
| Python LOC | 652 |
| Timeline | 1 day |
