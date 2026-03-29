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

## Milestone: v1.7 — Debugging & Optimization

**Shipped:** 2026-03-29
**Phases:** 5 (04-08) | **Plans:** 6 | **Tasks:** 12

### What Was Built
- Per-axis clamp WARNING logging in set_angles() for hardware observability
- AWB warm-up (2s sleep + ColourGains lock) eliminates blue tint on Picamera2/IMX219
- Tilt PID sign negation fix — one-character change resolving convergence failure
- simple-pid>=2.0.1 pin for reliable anti-windup reset()
- Phase offset via math.asin(clamp(pan/amplitude)) — smooth scan resume without servo jump
- Streak reset moved to TARGET_LOST entry — correct 3-frame enforcement
- 12 automated Nyquist validation tests (first tests in project history)

### What Worked
- Diagnostic-first approach (Phase 6 before Phase 7) — clamp logging immediately revealed the sign bug pattern
- Hardware verification checkpoints — caught real convergence behavior that code inspection alone missed
- Surgical scope: 3 files changed total (test_tracker.py, hardware.py, requirements.txt)
- Phase 8 research correctly identified both scan bugs before planning

### What Was Inefficient
- Phase 08 was missing VERIFICATION.md — caught only at milestone audit, not during execution
- STATE.md got out of sync (still said "Awaiting plan-phase 6" when Phase 8 was done)
- v1.6 requirements (Phases 4-5) and v1.7 requirements (Phases 6-8) shared a single ROADMAP — milestone boundaries were not clean in phase numbering

### Patterns Established
- `_przejdz_do()` is the correct place for state-transition side effects (PID reset, phase offset, streak reset)
- AWB lock pattern: `start()` → `sleep(2.0)` → `capture_metadata()` → `set_controls({"ColourGains": gains})`
- Phase offset pattern: `math.asin(max(-1.0, min(1.0, value/amplitude)))` for sinusoidal continuity

### Key Lessons
- Always generate VERIFICATION.md during phase execution, not retroactively
- Hardware checkpoint tasks should be separate plans (as done in Phase 7) for cleaner tracking
- Nyquist validation tests work even without pytest — standalone scripts with mock imports are sufficient for RPi4 projects

### Cost Observations
- Model mix: ~70% sonnet (agents), ~30% opus (orchestration)
- Sessions: 4 (across 4 days)
- Notable: Phase 7 was split into code fix + hardware verify — good pattern for hardware projects

## Cross-Milestone Trends

| Metric | v1.5.0 | v1.7 |
|--------|--------|------|
| Phases | 3 | 5 |
| Plans | 3 | 6 |
| Tasks | 8 | 12 |
| Python LOC | 652 | 1,587 |
| Timeline | 1 day | 4 days |
| Tests | 0 | 12 |
