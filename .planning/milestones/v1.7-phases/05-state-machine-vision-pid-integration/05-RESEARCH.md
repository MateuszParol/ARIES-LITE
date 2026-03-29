# Phase 5: State Machine, Vision & PID Integration - Research

**Researched:** 2026-03-26
**Domain:** HAAR face detection + simple_pid PID control + OpenCV HUD, running inside an existing Python skeleton
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `sample_time=0.033` on both PID instances — stabilizes derivative term against variable loop timing (~30 FPS target)
- Keep existing gains (Kp=0.05, Ki=0.001, Kd=0.005) from config.py — validated at 640x480 in v1.5, output_limits=±10 already caps correction. Tune empirically on RPi4 if needed, don't pre-optimize.
- Call `detekcja.resetuj_streak()` on TRACKING→SCANNING transition — prevents stale count from previous detection carrying over.
- Add FPS counter to HUD — critical for proving ~30 FPS on RPi4. Placement: bottom-right corner, gray text.
- Increase HAAR_MIN_SIZE from (50,50) to (80,80) — at 320x240, a 50px face is too small for reliable PID tracking. 80px is more stable.
- Keep HAAR_MIN_NEIGHBORS=8 — stricter detection compensates for no dlib verification. Fewer false positives.

### Claude's Discretion
- Tilt sign convention verification approach (comment + checkpoint flip, or pre-check)
- FPS calculation method (rolling average vs instantaneous)
- Where exactly to wire resetuj_streak() call (MaszynaStanow or TestTracker level)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIS-01 | HAAR cascade detects any face in grayscale frame (no identity recognition) | Skeleton already loads haarcascade_frontalface_default.xml and calls detectMultiScale. Gap: minSize must change from (50,50) to (80,80). |
| VIS-02 | Detection streak filter requires 3 consecutive frames before triggering TRACKING transition | Skeleton implements streak counter in DetekcjaTwarzy. Gap: resetuj_streak() not wired on TRACKING→SCANNING transition. |
| VIS-03 | HUD overlay shows face bounding box (green), state label, center crosshair, and servo angles | Skeleton has bbox rect, state label, crosshair, and servo angles. Gap: FPS counter missing. |
| CTL-01 | State machine cycles: SCANNING → TRACKING → TARGET_LOST → SCANNING | Skeleton implements full cycle. Minor logic issue in tick() STATE_TARGET_LOST branch — see Code Analysis below. |
| CTL-02 | Dual-axis PID (pan + tilt) drives servos from face centroid error, with reset on SCANNING entry | Skeleton has pid_pan.reset() + pid_tilt.reset() in _przejdz_do(). Gap: sample_time=0.033 not set on either PID instance. |
| CTL-03 | SCANNING state sweeps sinusoidally (±45° pan, 0.1 Hz) | Skeleton implements time-based sinusoidal scan: pan = SCAN_AMPLITUDE * sin(2π * SCAN_FREQUENCY * t). Fully correct as-is. |
| CTL-04 | TARGET_LOST triggers after 2 seconds without face detection, returns to SCANNING | Skeleton uses config.TIME_TO_LOST_SEC=2.0 timeout. Correct. See logic note in Code Analysis. |
</phase_requirements>

## Summary

Phase 5 is a targeted patch phase, not a from-scratch build. The skeleton in `src/modes/test_tracker.py` already implements all four required classes — `Picamera2Stream`, `DetekcjaTwarzy`, `MaszynaStanow`, and `TestTracker` — with the correct architecture, Polish naming convention, and wiring. The gap between the skeleton and a passing implementation is exactly four concrete changes, all small and localized.

The four changes are: (1) change `HAAR_MIN_SIZE = (50, 50)` to `(80, 80)` in the module-level constants block; (2) set `sample_time=0.033` on both `pid_pan` and `pid_tilt` at construction time in `MaszynaStanow.__init__`; (3) call `detekcja.resetuj_streak()` on TRACKING→SCANNING transition; (4) add an FPS counter variable to `TestTracker.uruchom()` and render it in `_rysuj_hud()`. There is also one minor logic issue in `MaszynaStanow.tick()` worth addressing.

All architectural decisions are locked. The sign convention (`-pid_pan`, `+pid_tilt`) is already present and correctly matches `tracker.py:77-78`. The sinusoidal scan is already time-based and immune to stale state. PID reset on SCANNING entry is already wired in `_przejdz_do()`. The only work is filling the four gaps.

**Primary recommendation:** Implement all four gaps in a single wave. Verify tilt sign convention empirically on RPi4 with a smoke test before any numerical PID tuning.

---

## Code Analysis: Current State vs Required State

This section is the primary value of this research. It maps each requirement gap directly to the skeleton code location.

### Gap 1: HAAR_MIN_SIZE (50,50) → (80,80)

**File:** `src/modes/test_tracker.py`, line 28
**Current:**
```python
HAAR_MIN_SIZE = (50, 50)
```
**Required:**
```python
HAAR_MIN_SIZE = (80, 80)
```
**Rationale:** At 320x240 resolution, a 50px face detection is unreliable for PID control — the centroid bounces frame to frame. 80px requires a larger, closer, more stable face region. This is a single-line change in the module constants block.

**Requirement:** VIS-01

---

### Gap 2: sample_time missing on PID instances

**File:** `src/modes/test_tracker.py`, `MaszynaStanow.__init__()`, lines 192-195
**Current:**
```python
self.pid_pan = PID(config.PID_PAN_P, config.PID_PAN_I, config.PID_PAN_D, setpoint=0)
self.pid_pan.output_limits = (-PID_OUTPUT_LIMIT, PID_OUTPUT_LIMIT)

self.pid_tilt = PID(config.PID_TILT_P, config.PID_TILT_I, config.PID_TILT_D, setpoint=0)
self.pid_tilt.output_limits = (-PID_OUTPUT_LIMIT, PID_OUTPUT_LIMIT)
```
**Required (add sample_time to both):**
```python
self.pid_pan = PID(config.PID_PAN_P, config.PID_PAN_I, config.PID_PAN_D,
                   setpoint=0, sample_time=0.033)
self.pid_pan.output_limits = (-PID_OUTPUT_LIMIT, PID_OUTPUT_LIMIT)

self.pid_tilt = PID(config.PID_TILT_P, config.PID_TILT_I, config.PID_TILT_D,
                    setpoint=0, sample_time=0.033)
self.pid_tilt.output_limits = (-PID_OUTPUT_LIMIT, PID_OUTPUT_LIMIT)
```
**Rationale:** Without `sample_time`, `simple_pid` recalculates on every call. HAAR detection on RPi4 varies from ~30ms to ~80ms per frame depending on scene complexity. A frame that takes 80ms produces a derivative spike 2.4x larger than expected, causing servo jitter. With `sample_time=0.033`, the library ignores calls arriving faster than 33ms and caps the effective dt, stabilizing the D-term.

**Requirement:** CTL-02

---

### Gap 3: resetuj_streak() not wired on TRACKING→SCANNING

**File:** `src/modes/test_tracker.py`, `MaszynaStanow._przejdz_do()`, lines 267-274
**Current:** `_przejdz_do()` resets PIDs on SCANNING entry but does not touch the streak counter.
```python
def _przejdz_do(self, nowy_stan: str) -> None:
    logger.info(f"Zmiana stanu: {self.stan} → {nowy_stan}")
    self.stan = nowy_stan
    self._czas_ostatniego_celu = time.time()
    if nowy_stan == config.STATE_SCANNING:
        self.pid_pan.reset()
        self.pid_tilt.reset()
        # MISSING: detekcja.resetuj_streak()
```

**Problem:** `DetekcjaTwarzy._streak` persists across state transitions. If TRACKING was active for 10 frames and then the face is lost, the streak counter stays at 10. When SCANNING resumes and a face briefly appears for 1 frame, `_streak` is already at 10 (above threshold), triggering an immediate SCANNING→TRACKING transition from what may be a single-frame false positive.

**Two valid wiring locations:**

Option A — wire in `MaszynaStanow._przejdz_do()` (requires passing `detekcja` reference into `MaszynaStanow`):
```python
# In _przejdz_do, inside: if nowy_stan == config.STATE_SCANNING:
self.detekcja.resetuj_streak()
```

Option B — wire in `TestTracker.uruchom()` main loop by watching for state change to SCANNING:
```python
# After: stan = self.maszyna.tick(bbox, w, h)
if stan == config.STATE_SCANNING and poprzedni_stan != config.STATE_SCANNING:
    self.detekcja.resetuj_streak()
poprzedni_stan = stan
```

**Recommendation:** Option B (TestTracker level) — avoids creating a circular reference between `MaszynaStanow` and `DetekcjaTwarzy`. `TestTracker` already owns both objects and is the natural coordinator.

**Requirement:** VIS-02

---

### Gap 4: FPS counter missing from HUD

**File:** `src/modes/test_tracker.py`, `TestTracker.uruchom()` (lines 287-328) and `_rysuj_hud()` (lines 330-359)

**Required additions:**

In `TestTracker.__init__()`, add tracking variables:
```python
self._czas_klatki_poprzedniej = time.time()
self._fps_aktualny = 0.0
```

In `uruchom()`, compute FPS before calling `_rysuj_hud()`:
```python
teraz = time.time()
dt = teraz - self._czas_klatki_poprzedniej
self._czas_klatki_poprzedniej = teraz
# Rolling average or instantaneous — both acceptable
self._fps_aktualny = 1.0 / dt if dt > 0 else 0.0
```

In `_rysuj_hud()`, add FPS text at bottom-right:
```python
fps_tekst = f"FPS:{self._fps_aktualny:.1f}"
(tw, th), _ = cv2.getTextSize(fps_tekst, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
cv2.putText(klatka, fps_tekst, (w - tw - 5, h - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
```

**Note on FPS calculation method (Claude's discretion):** Instantaneous FPS (`1/dt`) is simpler to implement and shows real-time variance, which is diagnostically useful on RPi4 (you want to see when HAAR detection causes a dip). A rolling average over 10 frames is smoother for readability. Given the diagnostic purpose (prove ~30 FPS), instantaneous with 1 decimal place is recommended — spikes are visible rather than averaged away.

**Requirement:** VIS-03

---

### Minor Issue: STATE_TARGET_LOST branch in tick() is redundant

**File:** `src/modes/test_tracker.py`, `MaszynaStanow.tick()`, lines 234-236
**Current:**
```python
elif self.stan == STATE_TARGET_LOST:
    # Natychmiastowe przejście do SCANNING (obsłużone powyżej)
    self._przejdz_do(config.STATE_SCANNING)
```
**Problem:** The TRACKING branch (lines 222-232) already sets `self.stan = STATE_TARGET_LOST` and then calls `self._przejdz_do(config.STATE_SCANNING)` in the same tick. By the time the `elif self.stan == STATE_TARGET_LOST` branch is reached, `self.stan` is already `STATE_SCANNING`. The `elif` branch is therefore never executed. This is dead code, not a runtime error.

**Options:**
- Remove the redundant `elif STATE_TARGET_LOST` branch entirely (simplest)
- OR restructure: set `self.stan = STATE_TARGET_LOST`, then handle the transition on the *next* tick (preserves the state being visible in HUD for one frame)

**Recommendation:** Keep the two-step approach (set TARGET_LOST, transition on next tick) because it allows the HUD to render `STATE_TARGET_LOST` in red for at least one visible frame — confirming the state is reachable. Fix the logic so the `elif` branch actually handles the transition:

```python
elif self.stan == config.STATE_TRACKING:
    if bbox is not None:
        self._czas_ostatniego_celu = time.time()
        self._sledz(bbox, w, h)
    else:
        if time.time() - self._czas_ostatniego_celu >= config.TIME_TO_LOST_SEC:
            self._przejdz_do(STATE_TARGET_LOST)  # only set TARGET_LOST, don't chain
            # do NOT call _przejdz_do(SCANNING) here

elif self.stan == STATE_TARGET_LOST:
    self._przejdz_do(config.STATE_SCANNING)  # next tick: transition to SCANNING
```

This makes TARGET_LOST a real transient state visible in the HUD for one frame, satisfying CTL-04's observability.

**Requirement:** CTL-01, CTL-04

---

## Standard Stack

### Core (all already in requirements.txt — no new dependencies)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| `simple_pid` | 2.0+ | PID controller with `sample_time`, `output_limits`, `reset()` | Already installed |
| `opencv-python-headless` | 4.8+ | HAAR cascade, BGR grayscale, HUD rendering, cv2.imshow | Already installed |
| `picamera2` | 0.3.x | Camera capture (via Picamera2Stream) — already working from Phase 4 | Already installed |
| `src.config` | — | PID gains, servo limits, state constants, TIME_TO_LOST_SEC | Imported in skeleton |
| `src.hardware.PanTiltSystem` | — | set_angles(), smooth_move_to(), detach_servos() | Imported in skeleton |

No new `pip install` commands needed. All dependencies were satisfied in Phase 4.

### simple_pid API Reference (verified from library)

```python
from simple_pid import PID

pid = PID(Kp, Ki, Kd, setpoint=0, sample_time=0.033)
pid.output_limits = (-10.0, 10.0)

# Call per tick (returns correction value):
correction = pid(error)

# Reset integral + derivative state:
pid.reset()
```

`sample_time` (float, seconds): if time since last call < sample_time, the previous output is returned unchanged. This prevents derivative spikes on fast or slow frames. Setting to `None` (default) disables rate limiting — do not leave as default.

---

## Architecture Patterns

### Existing Structure (Phase 5 modifies only test_tracker.py)

```
src/modes/
└── test_tracker.py     # All 4 classes — this is the ONLY file modified in Phase 5
run_test_tracker.py     # Entry point — unchanged
src/hardware.py         # PanTiltSystem — read-only
src/config.py           # Constants — read-only
```

### Change Locality

All 4 gaps are contained within `test_tracker.py`. No other file is touched.

| Change | Location | Scope |
|--------|----------|-------|
| HAAR_MIN_SIZE (50→80) | Module constants, line 28 | 1 line |
| sample_time=0.033 | MaszynaStanow.__init__, 2 PID constructors | 2 lines |
| resetuj_streak() wiring | TestTracker.uruchom() + new variable | ~4 lines |
| FPS counter | TestTracker.__init__ + uruchom() + _rysuj_hud() | ~6 lines |
| TARGET_LOST logic fix | MaszynaStanow.tick() | ~3 lines |

Total effective change: ~16 lines in one file.

### PID Sign Convention (locked — do not change)

From `tracker.py` lines 77-78, confirmed identical in skeleton lines 259-260:
```python
korekta_pan = -self.pid_pan(blad_pan)    # negated — camera geometry
korekta_tilt = self.pid_tilt(blad_tilt)  # positive — camera geometry
```
This is correct and must not be changed without empirical verification on the physical hardware.

### Sinusoidal Scan Pattern (already correct in skeleton)

```python
def _skanuj(self) -> None:
    t = time.time()
    pan = SCAN_AMPLITUDE * math.sin(2.0 * math.pi * SCAN_FREQUENCY * t)
    self.hardware.set_angles(pan, 0.0)
```
This is the time-based pattern that is immune to stale state on TRACKING→SCANNING transitions (Pitfall 9 from project research). Tilt is held at 0.0 during scan — correct for a simple proof.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PID sample rate limiting | Custom dt tracking + conditional update | `PID(sample_time=0.033)` | simple_pid does this internally and correctly |
| PID integral reset | Setting `pid._integral = 0` directly | `pid.reset()` | `reset()` also clears last_error and last_time — private attribute access is fragile |
| HAAR cascade loading | Custom file path logic | `cv2.data.haarcascades + "haarcascade_frontalface_default.xml"` | Already in skeleton, already correct |
| Text width for right-align | Manual character counting | `cv2.getTextSize()` | Returns pixel width for right-edge alignment of FPS counter |
| FPS rolling average | Deque + mean | Instantaneous `1/dt` with 1 decimal | Diagnostic, not display — instantaneous shows real-time variance |

---

## Common Pitfalls

### Pitfall A: Calling pid.reset() vs pid._integral = 0

`pid.reset()` resets three internal values: `_proportional`, `_integral`, `_last_error`. Setting `_integral` directly leaves `_last_error` stale, which causes a derivative spike on the next call. Always use `pid.reset()`.

### Pitfall B: sample_time set too low vs too high

`sample_time=0.033` (33ms = 30 FPS) is correct. Setting it lower (e.g., `0.010`) defeats the protection — 33ms frames will still recalculate every call. Setting it higher (e.g., `0.100`) makes PID sluggish — it will ignore fast frames and update only 10 times/second. 33ms matches the target loop rate.

### Pitfall C: FPS calculation divides by zero

If `dt = time.time() - previous_time` is exactly 0 (two calls in same millisecond), `1.0 / dt` raises ZeroDivisionError. Guard: `fps = 1.0 / dt if dt > 0 else 0.0`.

### Pitfall D: resetuj_streak() placement — wrong tick order

If `resetuj_streak()` is called before `detekcja.wykryj()` in the same tick, the streak counter is cleared and then immediately incremented by the next detection. Wire the reset to the state transition event (after state changes to SCANNING), not before detection. The recommended Option B (TestTracker level, checking previous state) ensures this ordering.

### Pitfall E: Tilt sign convention — verify before tuning

Before any numerical PID tuning on RPi4, run the smoke test: move a face up in the frame — servo should tilt up. If tilt correction is backwards, the servo diverges. The current `+pid_tilt` sign is identical to `tracker.py:78`. Until empirically confirmed on the physical hardware, log the sign as a checkpoint.

### Pitfall F: HAAR minSize larger than actual face at 320x240

At 320x240, a face at arm's length (~40cm) subtends roughly 50-70px. Changing minSize to (80,80) requires the subject to be closer (~25-30cm) to be detected. If RPi4 testing shows detection fails at normal sitting distance, consider (70,70) as a fallback. The 80px value is the user's accepted recommendation — test first, adjust empirically.

---

## Code Examples

### FPS counter — complete pattern

```python
# In TestTracker.__init__:
self._czas_klatki_poprzedniej = time.time()
self._fps_aktualny = 0.0

# In uruchom() main loop, after klatka is confirmed not None:
teraz = time.time()
dt = teraz - self._czas_klatki_poprzedniej
self._czas_klatki_poprzedniej = teraz
self._fps_aktualny = 1.0 / dt if dt > 0 else 0.0

# In _rysuj_hud():
fps_tekst = f"FPS:{self._fps_aktualny:.1f}"
(tw, th), _ = cv2.getTextSize(fps_tekst, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
cv2.putText(klatka, fps_tekst, (w - tw - 5, h - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
```

### resetuj_streak() wiring — Option B (TestTracker level)

```python
# In TestTracker.uruchom(), before main loop:
poprzedni_stan = config.STATE_SCANNING

# In main loop, after stan = self.maszyna.tick(bbox, w, h):
if stan == config.STATE_SCANNING and poprzedni_stan != config.STATE_SCANNING:
    self.detekcja.resetuj_streak()
poprzedni_stan = stan
```

### TARGET_LOST as observable transient state

```python
elif self.stan == config.STATE_TRACKING:
    if bbox is not None:
        self._czas_ostatniego_celu = time.time()
        self._sledz(bbox, w, h)
    else:
        if time.time() - self._czas_ostatniego_celu >= config.TIME_TO_LOST_SEC:
            self._przejdz_do(STATE_TARGET_LOST)  # visible for one frame

elif self.stan == STATE_TARGET_LOST:
    self._przejdz_do(config.STATE_SCANNING)  # next tick: transition completes
```

---

## Verification Checkpoints

These are the empirical checks the planner should include as task verification steps:

| Check | Command / Method | Pass Condition |
|-------|-----------------|----------------|
| HAAR loads | Run test_tracker — no RuntimeError at startup | "Klasyfikator HAAR załadowany." in log |
| Streak filter | Hold face for 1 frame, remove — no tracking | No TRACKING entry on single-frame detection |
| Streak filter (positive) | Hold face steady for 3+ frames | TRACKING entry logged after 3rd frame |
| PID sample_time | Check attribute after init | `maszyna.pid_pan.sample_time == 0.033` |
| FPS counter visible | Run with display | FPS label appears in bottom-right corner |
| FPS ~30 | Observe FPS counter on RPi4 | Value consistently 25-33 FPS |
| TARGET_LOST visible | Cover camera for 2s | "TARGET_LOST" state briefly visible in red |
| SCANNING resumes | After TARGET_LOST | Sinusoidal sweep resumes from current time phase |
| Tilt sign (smoke test) | Move face up | Servo tilts up — not down |
| Pan sign (smoke test) | Move face left | Servo pans left — not right |
| Streak reset | Track → lose → immediately show face | Streak restarts from 0, requires 3 new frames |

---

## Open Questions

1. **Tilt sign convention on this specific hardware unit**
   - What we know: `tracker.py` uses `+pid_tilt` and was calibrated in v1.5. Skeleton copies this.
   - What's unclear: Camera ribbon orientation on the specific v1.6 test hardware may differ.
   - Recommendation: Smoke-test empirically before any numerical tuning. If tilt diverges, flip sign and document.

2. **HAAR detection rate at (80,80) on 320x240**
   - What we know: At normal sitting distance (~60cm), a face is roughly 60-90px at this resolution.
   - What's unclear: Whether 80px threshold causes detection gaps at the outer edge of usable range.
   - Recommendation: Start with (80,80) per CONTEXT.md decision. If testing shows detection fails at expected distances, lower to (70,70) as empirical fallback.

---

## Sources

### Primary (HIGH confidence)
- `src/modes/test_tracker.py` — direct code analysis, gap identification against CONTEXT.md decisions
- `src/tracker.py` — PID sign convention reference (lines 77-78), state machine pattern
- `src/config.py` — PID gains (Kp=0.05, Ki=0.001, Kd=0.005), TIME_TO_LOST_SEC=2.0, state constants
- `.planning/phases/05-state-machine-vision-pid-integration/05-CONTEXT.md` — locked decisions
- `.planning/research/PITFALLS.md` — PID windup, sample_time, streak filter, sign convention pitfalls

### Secondary (MEDIUM confidence)
- `simple_pid` library behavior: `sample_time`, `reset()`, `output_limits` — well-documented, stable API
- OpenCV `cv2.getTextSize()` for right-aligned text placement — standard OpenCV pattern

---

## Metadata

**Confidence breakdown:**
- Gap identification: HIGH — direct code comparison of skeleton vs CONTEXT.md decisions
- simple_pid API: HIGH — stable library, behavior well-established
- FPS calculation: HIGH — standard time.time() pattern
- Tilt sign convention: MEDIUM — correct in skeleton, but empirical verification on hardware is mandatory
- HAAR detection at (80,80) on 320x240: MEDIUM — theoretically sound, needs RPi4 verification

**Research date:** 2026-03-26
**Valid until:** 2026-04-25 (30 days — stable domain, no fast-moving dependencies)
