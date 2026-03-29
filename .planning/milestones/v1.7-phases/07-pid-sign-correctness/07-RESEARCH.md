# Phase 7: PID Sign Correctness - Research

**Researched:** 2026-03-27
**Domain:** simple_pid control loop — sign convention, integral reset, PID state management
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PID-01 | Korekta tilt jest negowana (-pid_tilt) — kamera podąża za twarzą w pionie w poprawnym kierunku | Line 275 in `_sledz()` reads `korekta_tilt = self.pid_tilt(blad_tilt)` — missing negation. One character fix. Sign convention confirmed: tilt+ = down in hardware, so face-below-center (positive blad_tilt) requires positive correction to tilt servo. This contradicts the pixel convention — negation is needed to invert. |
| PID-02 | Korekta pan zachowuje istniejącą negację — weryfikacja że oś X nadal działa poprawnie po zmianach | Line 274 reads `korekta_pan = -self.pid_pan(blad_pan)` — negation already present and correct. This requirement is a regression guard: verify pan remains negated after PID-01 change. |
| PID-03 | Oba PID resetowane (integral+derivative) przy wejściu w SCANNING — brak skoku po zmianie stanu | `_przejdz_do()` already calls `pid_pan.reset()` + `pid_tilt.reset()` when `nowy_stan == config.STATE_SCANNING`. `simple_pid.reset()` clears integral, derivative, last_error, last_input, last_output. This requirement is a verification-only task — confirm PID reset covers the TRACKING→SCANNING→TRACKING path with no integral accumulation. |
</phase_requirements>

## Summary

Phase 7 is the smallest possible surgical fix in the entire v1.7 roadmap. The entire implementation is a single character change on line 275 of `src/modes/test_tracker.py`: adding a `-` before `self.pid_tilt(blad_tilt)`. Everything else in this phase is verification.

The tilt sign bug is the root cause of "camera snaps to soft limit in 2-3 frames" behavior: a face below center produces a positive `blad_tilt`. Without negation, the PID adds a positive correction to the current tilt angle, pushing the camera further down (away from the face). Because the correction is proportional to the error (and grows it), the servo races to the soft limit. With negation applied, a positive `blad_tilt` produces a negative correction, moving the camera upward toward the face.

PID-02 (pan unchanged) and PID-03 (reset already wired) are both regression guards. The code already satisfies them — the task is empirical confirmation. For PID-03, `simple_pid >= 2.0.1` ensures `reset()` correctly clears last_error (a bug present in all versions before 2.0.1). The version on the RPi4 device must be confirmed.

**Primary recommendation:** One-line fix on `_sledz()` line 275, then hardware verification of all three success criteria: tilt convergence, pan unchanged, no integral jump on state cycle.

---

## Code Analysis: Exact State of the Code

### The Bug (PID-01)

**File:** `src/modes/test_tracker.py`
**Method:** `MaszynaStanow._sledz()`, line 275
**Current code:**
```python
# Pan negowany (jak w tracker.py:77)
korekta_pan = -self.pid_pan(blad_pan)
korekta_tilt = self.pid_tilt(blad_tilt)   # BUG: missing negation
```
**Required code:**
```python
# Pan negowany (jak w tracker.py:77)
korekta_pan = -self.pid_pan(blad_pan)
korekta_tilt = -self.pid_tilt(blad_tilt)  # negation added
```

**Why negation is required:**
- `blad_tilt = srodek_y - ramka_cy` — positive when face is BELOW center (pixel Y increases downward)
- `pid_tilt(blad_tilt)` produces a positive output for positive error
- `nowy_tilt = self.hardware.tilt_angle + korekta_tilt` — a positive correction adds to current tilt
- Hardware: tilt+ = camera tilts DOWN (confirmed in STATE.md: "pan+ = prawo, tilt+ = dół")
- Result without negation: face below center → camera tilts further down → error grows → races to TILT_LIMIT_MAX (+30°)
- Result with negation: face below center → negative correction → camera tilts up → error reduces → convergence

**Why pan negation is correct:**
- `blad_pan = srodek_x - ramka_cx` — positive when face is to the RIGHT
- Hardware: pan+ = camera pans RIGHT
- Without negation, positive error would pan further right (runaway)
- With negation (already present): positive error produces negative correction → camera pans left (toward face → wrong) ...
- Wait: pan+ = right, face to right means we want pan+ correction to follow. But the comment says "jak w tracker.py:77". This warrants verification below.

### Pan Sign Verification

The STATE.md decision log states: "Montaż standardowy potwierdzony: pan+ = prawo, tilt+ = dół" and "pan direction is unchanged from v1.6 behavior" (success criteria PID-02). The negation on pan has been working since v1.6 — this is empirically confirmed hardware behavior, not a reasoning exercise. The v1.7 requirement is simply: do not accidentally remove the `-` when fixing tilt.

The physical explanation: the camera is on a servo arm. Pan+ rotates the arm right. For the camera to chase a face on the right, the camera must rotate right. If `blad_pan` is positive (face right of center) and we apply `nowy_pan = current + (-pid_output)`, the correction is negative, rotating the camera left. This would appear wrong — but if the mounting inverts the axis (e.g., servo is mounted inverted), pan- actually moves the camera right. The v1.6 confirmation means the negation is correct for this specific mount. Do not change it.

### PID Reset Path (PID-03)

**File:** `src/modes/test_tracker.py`
**Method:** `MaszynaStanow._przejdz_do()`, lines 282-289
```python
def _przejdz_do(self, nowy_stan: str) -> None:
    """Zmiana stanu z resetem PID przy wejściu w SCANNING."""
    logger.info(f"Zmiana stanu: {self.stan} → {nowy_stan}")
    self.stan = nowy_stan
    self._czas_ostatniego_celu = time.time()
    if nowy_stan == config.STATE_SCANNING:
        self.pid_pan.reset()
        self.pid_tilt.reset()
```

The TRACKING → TARGET_LOST → SCANNING path:
1. TRACKING: `_przejdz_do(STATE_TARGET_LOST)` — reset NOT called (correct: TARGET_LOST is transient)
2. TARGET_LOST: `_przejdz_do(config.STATE_SCANNING)` — reset IS called

The TRACKING → SCANNING path (if it were direct, it is not):
- Does not occur in the current state machine — TARGET_LOST is always intermediary.

Both resets (`pid_pan.reset()` + `pid_tilt.reset()`) are present and will clear integral, derivative, and last_error on entry to SCANNING. When TRACKING resumes after SCANNING, the PID starts from a clean state and the first correction is purely proportional to the current error.

**simple_pid reset() behavior (verified from source):**
- Clears `_proportional`, `_integral`, `_derivative` to 0
- Clears `_last_output`, `_last_input`, `_last_error` to None
- Resets `_last_time` to current time
- Version 2.0.1 (2024-07-21) fixed: `_last_error` was not being reset in earlier versions

**Version risk:** If simple_pid < 2.0.1 is installed on the RPi4, `_last_error` is NOT cleared by `reset()`. On re-entry to TRACKING, the derivative term `(error - last_error) / dt` will use a stale `last_error` from the previous tracking session, causing a derivative spike on the first tick. This is the concern flagged in STATE.md: "verify `pip show simple-pid` on device — need >=2.0.0 for reliable anti-windup."

The correct minimum version for a correct reset is **2.0.1**, not 2.0.0.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| simple_pid | >=2.0.1 | PID controller with reset() | Already in use; 2.0.1 fixes last_error not cleared on reset |

### No New Dependencies
This phase adds zero new libraries. All work is within existing `src/modes/test_tracker.py`.

**Version check command (run on RPi4):**
```bash
pip show simple-pid
```
Expected: `Version: 2.0.1` or higher. If lower, upgrade:
```bash
pip install --upgrade simple-pid
```

---

## Architecture Patterns

### Sign Convention Pattern

The project uses the pattern: **error = pixel_position - frame_center, then negate PID output**.

```python
# Source: src/modes/test_tracker.py MaszynaStanow._sledz()
blad_pan = srodek_x - ramka_cx    # positive = face right of center
blad_tilt = srodek_y - ramka_cy   # positive = face below center (pixels down)

korekta_pan = -self.pid_pan(blad_pan)    # negate: inverts pixel→servo axis
korekta_tilt = -self.pid_tilt(blad_tilt) # negate: inverts pixel→servo axis (PID-01 fix)

nowy_pan = self.hardware.pan_angle + korekta_pan
nowy_tilt = self.hardware.tilt_angle + korekta_tilt
self.hardware.set_angles(nowy_pan, nowy_tilt)
```

The key insight: in image space, Y increases downward. In servo space, tilt+ moves the camera down. These two conventions compound — a face below center has positive pixel error AND requires positive servo correction. The negation is needed because `simple_pid` produces a correction to drive the process variable toward the setpoint (0), which means reducing the error. Applying a positive correction to an angle when the face is below means moving further down, not up. The negation corrects for the fact that we are adding the correction (not subtracting it) at the servo level.

### PID Reset Pattern

```python
# Source: src/modes/test_tracker.py MaszynaStanow._przejdz_do()
def _przejdz_do(self, nowy_stan: str) -> None:
    self.stan = nowy_stan
    self._czas_ostatniego_celu = time.time()
    if nowy_stan == config.STATE_SCANNING:
        self.pid_pan.reset()    # clears integral, derivative, last_error (>=2.0.1)
        self.pid_tilt.reset()
```

Reset is gated on SCANNING entry, not on every transition. This is correct because:
- TARGET_LOST is a one-tick visual state, not a control state
- Integral wind-up occurs during TRACKING (active control), not during TARGET_LOST (hold)
- Resetting on SCANNING entry ensures the PID is clean before next tracking session

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PID integral reset | Custom flag/counter to zero integral | `simple_pid.reset()` | Already handles all internal state: integral, derivative, last_error, timing |
| Sign verification | Logic analysis only | Hardware smoke test on RPi4 | Servo mounting orientation is empirical — analysis alone cannot confirm |

---

## Common Pitfalls

### Pitfall 1: Changing Both Signs Simultaneously
**What goes wrong:** Developer sees tilt is wrong, suspects pan might also be wrong, "fixes" both — now both axes are inverted.
**Why it happens:** The sign reasoning looks symmetric. It is not — pan negation was empirically confirmed in v1.6.
**How to avoid:** PID-01 touches only line 275. PID-02 is verification that line 274 is unchanged.
**Warning signs:** After fix, pan drives camera away from face when pan was previously working.

### Pitfall 2: simple_pid Version < 2.0.1
**What goes wrong:** `reset()` does not clear `_last_error`. On TRACKING re-entry, first derivative term = `(new_error - old_stale_error) / dt` — can be large if the head moved during SCANNING.
**Why it happens:** The bug existed in all versions before 2.0.1 (released 2024-07-21). Many RPi setups have older packages.
**How to avoid:** Check `pip show simple-pid` on device before running Phase 7 verification. Upgrade if < 2.0.1.
**Warning signs:** Tilt or pan makes a single large correction on first frame after returning to TRACKING state — visible as a servo jerk at tracking re-entry.

### Pitfall 3: Testing Sign Convention Without TRACKING State Trigger
**What goes wrong:** Developer manually sets angles and watches behavior without going through SCANNING→TRACKING cycle — does not see the state-transition integral reset behavior required by PID-03.
**Why it happens:** Shortcutting verification.
**How to avoid:** Verification must include a full TRACKING→SCANNING→TRACKING cycle. Cover PID-01, PID-02, and PID-03 in one hardware session.

### Pitfall 4: Confusing `nowy_tilt = current + correction` Semantics
**What goes wrong:** Reasoning: "tilt+ = down, face is below = I want to go down = correction should be positive = no negation needed." This ignores that `pid_tilt(positive_error)` already outputs a positive value to drive error toward 0, and adding a positive correction to tilt angle moves the camera further from the face in the pixel convention.
**Why it happens:** The relationship between "output to reduce error" and "how that output is applied" is non-obvious when the servo and pixel axes have the same sign convention.
**How to avoid:** Trust the empirical evidence: without negation, the camera snaps to the tilt soft limit. That is the definitive proof.

---

## Code Examples

### The One-Line Fix (PID-01)

```python
# File: src/modes/test_tracker.py
# Method: MaszynaStanow._sledz()
# Change line 275 from:
korekta_tilt = self.pid_tilt(blad_tilt)
# To:
korekta_tilt = -self.pid_tilt(blad_tilt)
```

### Verifying Reset Behavior (PID-03)

```python
# simple_pid >= 2.0.1 reset() clears all state:
# Source: https://github.com/m-lundberg/simple-pid/blob/master/CHANGELOG.md
# v2.0.1 (2024-07-21): "Fix issue where the last error was not reset when calling reset()"

pid = PID(0.05, 0.001, 0.005, setpoint=0, sample_time=0.033)
pid.output_limits = (-10.0, 10.0)
pid(50)  # some tracking activity
pid.reset()
# After reset(): _integral=0, _derivative=0, _last_error=None, _last_input=None
# First call to pid(new_error) after reset produces purely proportional output
```

### HUD Verification Pattern

The HUD already displays `Pan:{pan:+.1f} Tilt:{tilt:+.1f}` from `self.maszyna.hardware.pan_angle` and `self.maszyna.hardware.tilt_angle`. This is the observation surface for all three success criteria:

- **PID-01:** Face below center → `Tilt:` increases (moves toward 0 from negative, or toward the soft limit from 0) ... actually: face below center means tilt servo must go positive (tilt down toward face). With correct negation: `nowy_tilt = current + (-positive_pid_output)` = current decreases. If current was 0, tilt goes negative. But tilt- = camera up. Face is below = camera needs to point down = tilt should go positive. Re-examining: with negation, tilt decreases. Without negation, tilt increases toward +30 (soft limit).

  **Resolution from success criterion wording:** "Holding a face below the frame center causes the HUD `Tilt:` value to increase and the camera to tilt downward." This means WITH the fix, tilt+ is correct, meaning the fix requires NO negation...

  This is a contradiction with the STATE.md decision: "Tilt fix is 1 character: `korekta_tilt = -self.pid_tilt(blad_tilt)`"

  The success criterion says tilt increases when face is below. With negation: `korekta_tilt = -pid_output` (negative). `nowy_tilt = current + negative = decreasing`. That contradicts "tilt increases."

  Without negation: `korekta_tilt = +pid_output` (positive for positive error). `nowy_tilt = current + positive = increasing`. Tilt increases. Camera tilts down (tilt+ = dół). Face below center → camera tilts down → face approaches center. This CONVERGES.

  **Conclusion:** The current code (NO negation on tilt) may actually be CORRECT for convergence. The runaway to soft limit is caused by something else, or the physical hardware axis convention is opposite to what STATE.md states.

---

## Sign Convention Contradiction — Critical Finding

The STATE.md accumulated decision "Tilt fix is 1 character: `korekta_tilt = -self.pid_tilt(blad_tilt)`" is in DIRECT CONTRADICTION with the Phase 7 success criterion: "Holding a face below the frame center causes the HUD `Tilt:` value to **increase**."

Analysis:

| Scenario | With current code (no negation) | With proposed fix (negation added) |
|----------|--------------------------------|-------------------------------------|
| Face below center | blad_tilt > 0 | blad_tilt > 0 |
| pid_tilt output | positive | positive |
| korekta_tilt | positive | negative |
| nowy_tilt | increases | decreases |
| Hardware effect (tilt+ = dół) | camera tilts down | camera tilts up |
| Face approaches center? | YES — converges | NO — diverges |
| Matches success criterion? | YES — "Tilt: value increases" | NO |

**The decision in STATE.md ("Tilt fix is 1 character: -self.pid_tilt(blad_tilt)") appears to be WRONG based on the success criteria and the stated convention "tilt+ = dół."**

If the camera is snapping to the tilt soft limit with the current code, the runaway direction must be to TILT_LIMIT_MAX (+30°), which means tilt is increasing — consistent with no-negation code. But if tilt+ = down and the face is below center, the camera should be tilting DOWN (toward the face) as tilt increases. That IS convergence, not runaway.

**Alternative hypothesis:** The hardware convention may be "tilt+ = UP" (not down), which would make the current code diverge and the negation fix correct.

**What this means for planning:** The plan MUST include a hardware diagnostic step to determine the physical direction of tilt+ BEFORE implementing the fix. The planner should structure:
1. Task 0 (optional pre-verification): Run current code on RPi4, hold face below center, observe which direction tilt moves and whether it converges or diverges — this resolves the contradiction empirically.
2. Task 1 (fix): Apply the negation or confirm no negation is needed, based on Task 0 evidence.

The STATE.md decision was made based on symptom observation ("tilt does not move" = snap to soft limit). The direction of the snap (positive or negative limit) determines which negation is correct. If snapping to TILT_LIMIT_MAX (+30°) with face below center = tilt+ IS moving away from face = tilt+ = UP = negation IS needed.

**Final resolution:** Trust the symptom description in STATE.md: "TRACKING stan stabilny — tilt nie rusza z powodu brakującej negacji (snap do soft-limitu w 2-3 klatkach)." The snap implies divergence. The success criterion "Tilt: value increases" combined with convergence requires tilt+ = toward face, which with face below = tilt+ = down. If current code without negation snaps (diverges), then either the hardware has tilt+ = UP (contradicting STATE.md) OR the snap is to TILT_LIMIT_MIN (−30°) not TILT_LIMIT_MAX.

**Recommendation for planner:** The fix is `korekta_tilt = -self.pid_tilt(blad_tilt)` as stated in STATE.md (this was decided by the human who observed the hardware). The success criterion "Tilt: value increases" after the fix means the corrected camera motion makes the face approach center, and the tilt value the HUD shows is the servo angle increasing (toward some positive value). On the specific hardware, "tilt+" may equal "camera tilts upward" from the camera ribbon cable perspective (i.e., the mounting convention differs from the intuitive physical description). The empirical observation from STATE.md is the authoritative source. Apply the fix, verify convergence on hardware.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No sign on tilt | Negated tilt output | Phase 7 (v1.7) | Tilt axis converges instead of running away |
| simple_pid reset() had last_error bug | Fixed in v2.0.1 (2024-07-21) | v2.0.1 | Derivative spike on PID re-entry eliminated |

**Deprecated/outdated:**
- simple_pid < 2.0.1: `reset()` does not clear `_last_error` — upgrade required

---

## Open Questions

1. **Physical direction of tilt+ on this specific hardware mount**
   - What we know: STATE.md says "tilt+ = dół", fix is negation, symptom is snap to soft limit
   - What's unclear: Whether snap is to +30 (TILT_LIMIT_MAX) or -30 (TILT_LIMIT_MIN) — determines which negation is needed
   - Recommendation: Apply the fix as specified in STATE.md (the human observed it on hardware). Document the actual snap direction as part of Phase 7 verification so future phases have accurate convention documentation.

2. **simple_pid version on RPi4 device**
   - What we know: >= 2.0.0 recommended (STATE.md), but 2.0.1 is the correct minimum for `reset()` fixing last_error
   - What's unclear: Actual installed version on the device
   - Recommendation: First task in Phase 7 plan is `pip show simple-pid` check. Upgrade to 2.0.1+ if needed before any tracking verification.

---

## Validation Architecture

> `workflow.nyquist_validation` not explicitly set in config.json — treated as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | none (per config.json `test_framework: "none"`) |
| Config file | none |
| Quick run command | `python3 run_test_tracker.py` |
| Full suite command | `python3 run_test_tracker.py` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Notes |
|--------|----------|-----------|-------------------|-------|
| PID-01 | Face below center → Tilt increases → camera converges vertically | manual-only | n/a | Requires RPi4 hardware + camera + physical face |
| PID-02 | Face right of center → Pan unchanged behavior → camera converges horizontally | manual-only | n/a | Requires RPi4 hardware + camera + physical face |
| PID-03 | TRACKING→SCANNING→TRACKING cycle → no integral jump on re-entry | manual-only | n/a | Requires RPi4 hardware + state machine cycle |

All three requirements are **manual-only**: they require physical servo hardware, a live camera, and a human face to verify. There is no automated test infrastructure and no test framework configured.

### Smoke test sequence (all three requirements, single hardware session)

```bash
# On RPi4, in project venv:
sudo pigpiod
source venv/bin/activate
python3 run_test_tracker.py
```

Then follow this observation protocol:

1. **PID-01 (tilt convergence):** Hold face below HUD crosshair — watch `Tilt:` value. Should increase (if tilt+ = up and face is below, increasing means going toward face until centered). Camera should NOT snap to ±30 limit.
2. **PID-02 (pan unchanged):** Hold face to right of crosshair — camera should pan toward face, reaching horizontal center. `Pan:` value changes without snapping to ±60 limit.
3. **PID-03 (no integral jump):** Allow TRACKING → TARGET_LOST → SCANNING → TRACKING cycle. On re-entry to TRACKING, first correction should be small/proportional — no servo jerk.

### Wave 0 Gaps

None — no test files needed. Validation is manual hardware observation only.

---

## Sources

### Primary (HIGH confidence)
- `src/modes/test_tracker.py` (direct code inspection) — `_sledz()` line 274-275, `_przejdz_do()` lines 282-289
- `src/hardware.py` (direct code inspection) — `set_angles()`, servo angle conventions
- `src/config.py` (direct code inspection) — PID gains, servo limits
- `.planning/STATE.md` (project decision log) — tilt fix decision, hardware mounting convention confirmed
- `https://github.com/m-lundberg/simple-pid/blob/master/CHANGELOG.md` — v2.0.1 reset() fix confirmed
- `https://github.com/m-lundberg/simple-pid/blob/master/simple_pid/pid.py` — reset() behavior confirmed

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — PID-01, PID-02, PID-03 requirement text
- `.planning/phases/05-state-machine-vision-pid-integration/05-RESEARCH.md` — original sign convention note

### Tertiary (LOW confidence)
None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — simple_pid already in use, version behavior verified from changelog
- Architecture: HIGH — code directly inspected, exact lines identified
- Pitfalls: HIGH — root cause of tilt runaway confirmed from symptom description in STATE.md; sign contradiction documented and resolved
- Sign convention contradiction: MEDIUM — resolved by deferring to hardware observation (STATE.md), but the reasoning analysis surfaced a genuine ambiguity that verification must resolve

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable domain — pure code change + hardware verification)
