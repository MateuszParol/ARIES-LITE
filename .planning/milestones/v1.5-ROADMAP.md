# ROADMAP.md — ARIES-LITE v1.5.0 Stabilization

> **Milestone**: v1.5.0 — Stabilization & Hardening
> **Generated**: 2026-03-18
> **Phases**: 3

---

## Phase 1: Critical Bug Fixes & Code Correctness
**Status**: Complete (2026-03-18)
**Objective**: Fix runtime bugs and correctness issues that affect basic operation.
**Requirements**: REQ-11, REQ-12, REQ-14

### Tasks
1. Add `logger = logging.getLogger(__name__)` to `web/server.py` module level
2. Sort HAAR cascade detections by bounding box area (w*h), select largest
3. Add threading.Lock to VideoStream for frame read/write synchronization

### Success Criteria
- CENTER command executes without crash
- Largest face selected when multiple faces in frame
- No frame tearing under concurrent access

### Dependencies
- None (can start immediately)

---

## Phase 2: Robustness & Reliability
**Status**: Complete (2026-03-18)
**Objective**: Add graceful shutdown, fix race conditions, prevent Flask blocking.
**Requirements**: REQ-13, REQ-15, REQ-16

### Tasks
1. Implement signal handler (SIGINT/SIGTERM) for clean shutdown:
   - Detach servos via `hardware.detach_servos()`
   - Release camera via `stream.stop()`
   - Set `tracker.is_running = False`
2. Move `smooth_move_to()` in CENTER command to background thread
3. Add initialization gate (threading.Event) to prevent Flask routes from executing before logic thread starts

### Success Criteria
- Ctrl+C cleanly shuts down all threads and releases hardware
- CENTER command returns HTTP 200 immediately, servo moves in background
- /api/state returns meaningful response even during startup

### Dependencies
- Phase 1 (logger fix required for CENTER command path)

---

## Phase 3: Cleanup & Quality
**Status**: Complete (2026-03-18)
**Objective**: Remove dead code, clean up dependencies, prepare for future development.
**Requirements**: REQ-17

### Tasks
1. Remove `imutils` from requirements.txt
2. Remove empty `adapters/` directory (or document its purpose)
3. Add `__all__` exports to `src/__init__.py`
4. Migrate or archive old `.gsd/` artifacts

### Success Criteria
- `pip install -r requirements.txt` installs only used packages
- Project structure is clean with no orphaned directories
- Old GSD state migrated to `.planning/`

### Dependencies
- Phase 2 (complete core fixes before cleanup)

---

## Phase Map

```
Phase 1 (Bug Fixes)     →  Phase 2 (Robustness)  →  Phase 3 (Cleanup)
  REQ-11: logger fix          REQ-13: shutdown          REQ-17: deps
  REQ-12: face sort            REQ-15: non-blocking      cleanup
  REQ-14: frame lock           REQ-16: race condition    archive
```
