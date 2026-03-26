# Phase 5: State Machine, Vision & PID Integration - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete the autonomous control loop: HAAR detects any face, PID drives servos to center it, sinusoidal scan resumes when face is lost, HUD makes every state transition empirically observable. The skeleton code already implements all 4 classes — this phase is targeted patches and RPi4 empirical verification, not from-scratch development.

</domain>

<decisions>
## Implementation Decisions

### PID tuning baseline
- Set `sample_time=0.033` on both PID instances — stabilizes derivative term against variable loop timing (~30 FPS target)
- **Keep existing gains** (Kp=0.05, Ki=0.001, Kd=0.005) from config.py — validated at 640x480 in v1.5, output_limits=±10 already caps correction. Tune empirically on RPi4 if needed, don't pre-optimize.
- Tilt sign convention: Claude's discretion on verification approach. Current code uses `+pid_tilt(error_tilt)` — may need sign flip after RPi4 testing.

### Streak filter wiring
- **Call `detekcja.resetuj_streak()` on TRACKING→SCANNING transition** — prevents stale count from previous detection carrying over. Wire it in `MaszynaStanow._przejdz_do()` or in `TestTracker` main loop when state changes to SCANNING.

### HUD completeness
- **Add FPS counter** to HUD — critical for proving ~30 FPS on RPi4. Use `time.time()` delta between frames.
- **Placement:** Bottom-right corner, gray text — subtle, not competing with state label (top-left) or servo angles (bottom-left).

### Detection parameters
- **Increase HAAR_MIN_SIZE from (50,50) to (80,80)** — at 320x240, a 50px face is too small for reliable PID tracking. 80px is more stable.
- **Keep HAAR_MIN_NEIGHBORS=8** — stricter detection compensates for no dlib verification. Fewer false positives.

### Claude's Discretion
- Tilt sign convention verification approach (comment + checkpoint flip, or pre-check)
- FPS calculation method (rolling average vs instantaneous)
- Where exactly to wire resetuj_streak() call (MaszynaStanow or TestTracker level)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Current implementation (MODIFY)
- `src/modes/test_tracker.py` — All 4 classes already implemented. Phase 5 patches this file.

### Hardware abstraction (reuse, read-only)
- `src/hardware.py` — PanTiltSystem: smooth_move_to, set_angles, detach_servos
- `src/config.py` — PID gains, servo limits, TIME_TO_LOST_SEC=2.0, state name constants

### Existing tracker (reference pattern)
- `src/tracker.py` — TrackerMachine: PID sign convention (line 77: `-pid_pan`, line 78: `+pid_tilt`), state transitions, timeout logic

### Research
- `.planning/research/SUMMARY.md` — PID tuning guidance, HAAR parameters, sinusoidal scan rationale
- `.planning/research/FEATURES.md` — Table stakes vs differentiators, PID windup notes
- `.planning/research/PITFALLS.md` — Integral windup, sign convention, false detection pitfalls

### Phase 4 context (carried forward)
- `.planning/phases/04-hardware-foundation-camera-integration/04-CONTEXT.md` — Camera mock mode, headless fallback, retry logic decisions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DetekcjaTwarzy` (test_tracker.py:143): HAAR + streak filter already implemented. Needs: minSize change (50→80), resetuj_streak() wiring.
- `MaszynaStanow` (test_tracker.py:184): State machine + PID already implemented. Needs: sample_time on PIDs, streak reset call.
- `TestTracker._rysuj_hud` (test_tracker.py:330): HUD overlay exists. Needs: FPS counter addition.
- `TestTracker.uruchom` (test_tracker.py:287): Main loop already wired: capture→detect→tick→HUD→display. Needs: FPS tracking variable.

### Established Patterns
- Polish-language method names and comments
- Module-level constants at top of file (HAAR_MIN_SIZE, STREAK_REQUIRED, etc.)
- State transitions logged via `logger.info` in `_przejdz_do()`
- PID sign convention: pan negated (`-pid_pan`), tilt positive (`+pid_tilt`)

### Integration Points
- `config.py` provides PID gains — test_tracker reads but doesn't modify
- `PanTiltSystem` handles angle clamping — PID output goes through `set_angles()`
- `run_test_tracker.py` entry point — unchanged by Phase 5

</code_context>

<specifics>
## Specific Ideas

- FPS counter in bottom-right, gray text — user explicitly chose subtle placement
- minSize=(80,80) for 320x240 resolution — user accepted research recommendation
- sample_time=0.033 for derivative stability — user accepted research recommendation
- Streak reset on TRACKING→SCANNING — user chose explicit reset over implicit

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-state-machine-vision-pid-integration*
*Context gathered: 2026-03-26*
