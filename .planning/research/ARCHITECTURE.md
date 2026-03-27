# Architecture Patterns — v1.7 Bug Fix Integration

**Domain:** Existing test_tracker.py — targeted bug fixes
**Researched:** 2026-03-27
**Confidence:** HIGH — based on direct source analysis + live verification of simple_pid and Picamera2 APIs on target hardware

---

## Overview

This document answers one question: **where exactly does each v1.7 fix land, what is the
minimal change, and do the fixes depend on each other?**

All four bugs are isolated to `src/modes/test_tracker.py`. No other file requires modification.
`src/hardware.py` and `src/config.py` are unchanged.

---

## Component Map (Current v1.6 State)

```
TestTracker.uruchom()                      ← main loop (orchestrator)
    │
    ├── Picamera2Stream                    ← camera (Picamera2Stream.start → _petla_przechwytywania)
    │       .start()                       ← Bug AWB: no controls passed here
    │
    ├── DetekcjaTwarzy.wykryj()            ← HAAR + streak filter
    │
    └── MaszynaStanow.tick()               ← state machine
            │
            ├── _skanuj()                  ← sinusoidal pan, tilt forced to 0.0
            ├── _sledz()                   ← PID error → correction → set_angles
            │       blad_pan  = srodek_x - ramka_cx
            │       blad_tilt = srodek_y - ramka_cy  ← Bug TILT: wrong sign applied
            │       korekta_pan  = -pid_pan(blad_pan)   (negated — correct)
            │       korekta_tilt =  pid_tilt(blad_tilt) (not negated — BUG)
            │
            └── _przejdz_do()             ← state transition + PID reset on SCANNING
                    pid_pan.reset()        ← Bug SCAN: reset is correct
                    pid_tilt.reset()       ← Bug SCAN: reset is correct
                                           ← Bug SCAN: streak reset is one frame late (in uruchom)
```

---

## Fix 1: Tilt PID Sign (Runaway Camera)

### Root Cause

`simple_pid.PID.__call__(input_)` computes `error = setpoint - input_` where `setpoint=0`.

With the face **below** center: `blad_tilt = srodek_y - ramka_cy` is positive (pixel coords,
y increases downward). PID receives positive input, computes `error = 0 - blad_tilt = negative`.
Output is negative (P + I + D are all negative for sustained positive error).

Current code: `korekta_tilt = self.pid_tilt(blad_tilt)` → negative correction applied to
`tilt_angle`. Camera tilts upward — away from the face. This is the runaway: the servo
actively drives the face out of frame.

Negating (same as pan): `korekta_tilt = -self.pid_tilt(blad_tilt)` → positive correction →
`tilt_angle` increases → camera tilts down → face moves toward center. Correct behavior.

### Integration Point

**File:** `src/modes/test_tracker.py`
**Method:** `MaszynaStanow._sledz()` — line 263

**Current (line 263):**
```python
korekta_tilt = self.pid_tilt(blad_tilt)
```

**Fixed:**
```python
korekta_tilt = -self.pid_tilt(blad_tilt)
```

**Change set:** 1 character added (`-` prefix). Nothing else changes.

**Verification:** With face below center, `tilt_angle` should increase (servo moves down).
With face above center, `tilt_angle` should decrease (servo moves up). Observable on hardware
by comparing HUD `Tilt:` readout direction vs face position.

---

## Fix 2: AWB / Blue Tint

### Root Cause

`Picamera2Stream.start()` calls `create_video_configuration()` with no `controls` argument.
The IMX219 sensor defaults to `AwbMode=Auto (0)`. Under indoor artificial lighting the Auto
AWB algorithm overcorrects toward blue because it is calibrated for a wide range and may
settle on a wrong white point without stable scene lighting.

The fix is to lock AWB to a specific mode that matches the deployment environment. Two options
verified against live Picamera2 API on target hardware:

**Option A — Set AwbMode to Indoor (value 4):**
Instructs the AWB algorithm to assume indoor artificial lighting. Algorithm continues to run
but within a constrained color temperature range. Lower residual tint, no manual gain tuning.

**Option B — Disable AWB and set ColourGains manually:**
`AwbEnable=False` + `ColourGains=(r_gain, b_gain)`. Eliminates algorithmic drift entirely.
Requires empirical calibration of r_gain/b_gain for the specific scene and lighting.

**Recommendation: Option A first.** It is a one-parameter change that handles varying indoor
lighting automatically. If tint persists after Option A, escalate to Option B with measured
gains.

Available AwbMode enum values (verified via libcamera on hardware):
- `Auto = 0` (current default — problematic)
- `Incandescent = 1`
- `Indoor = 4` (recommended for indoor LED/fluorescent)
- `Daylight = 5`
- `Cloudy = 6`

### Integration Point

**File:** `src/modes/test_tracker.py`
**Method:** `Picamera2Stream.start()` — lines 65-70
**Parameter:** `controls` argument of `create_video_configuration()` (confirmed in signature)

**Current (lines 65-69):**
```python
video_config = self._picam2.create_video_configuration(
    lores={"size": (self._width, self._height), "format": "YUV420"}
)
```

**Fixed (Option A):**
```python
video_config = self._picam2.create_video_configuration(
    lores={"size": (self._width, self._height), "format": "YUV420"},
    controls={"AwbMode": 4}           # 4 = Indoor
)
```

**Fixed (Option B, if Option A insufficient):**
```python
video_config = self._picam2.create_video_configuration(
    lores={"size": (self._width, self._height), "format": "YUV420"},
    controls={"AwbEnable": False, "ColourGains": (2.0, 1.4)}  # tune empirically
)
```

**Change set:** 1 line added to `create_video_configuration` call. Nothing else changes.

**Note on re-initialization path:** `_petla_przechwytywania` lines 110-115 also calls
`create_video_configuration` in the retry/reinit block. That call is on lines 111-114 and
must receive the same `controls` argument. This is a second insertion point in the same method.

**Re-initialization path (lines 111-113), also needs the fix:**
```python
video_config = self._picam2.create_video_configuration(
    lores={"size": (self._width, self._height), "format": "YUV420"},
    controls={"AwbMode": 4}           # must match start() controls
)
```

**Change set total:** 2 lines (one in `start()`, one in `_petla_przechwytywania` reinit block).

---

## Fix 3: SCANNING Transition (I-term Anti-Windup + Streak Reset)

### Root Cause Analysis

Two sub-issues in the TRACKING → SCANNING transition path:

**Sub-issue A: PID reset** — `_przejdz_do(config.STATE_SCANNING)` calls `pid_pan.reset()`
and `pid_tilt.reset()`. Verified via `simple_pid` source: `reset()` zeroes `_proportional`,
`_integral`, `_derivative`, `_last_output`, `_last_input`, `_last_error`. This is correct
and complete. **No change needed for PID reset.** The I-term anti-windup is already handled.

**Sub-issue B: Streak reset timing** — In `uruchom()` lines 323-324:
```python
if stan == config.STATE_SCANNING and poprzedni_stan != config.STATE_SCANNING:
    self.detekcja.resetuj_streak()
```
This runs AFTER `tick()` returns. On the transition frame itself, `tick()` has already called
`_przejdz_do(STATE_TARGET_LOST)`, returning `STATE_TARGET_LOST`, not `STATE_SCANNING`. The
next `tick()` call transitions `STATE_TARGET_LOST → STATE_SCANNING`. Only then does the
condition trigger. The streak reset is **one full frame late** relative to state entry.

The practical consequence: if a face is detected on the very first SCANNING tick after
transition, the streak counter carries residual count from before the TARGET_LOST transition.
In practice HAAR detection is not instantaneous so this rarely causes a visible problem, but
it is a logical inconsistency.

**Correct fix:** Move streak reset into `_przejdz_do()` alongside the PID reset, making both
resets atomic at state entry. Alternatively, the uruchom() condition is sufficient if changed
to check the previous-to-previous state, but that adds state tracking complexity.

The `_przejdz_do` approach is minimal and consistent with the existing PID reset pattern.

**Sub-issue C: TARGET_LOST duration** — `TARGET_LOST` state is intentionally one-frame visible
in the HUD (per comment on line 238). This is design, not a bug. No change needed.

### Integration Point

**File:** `src/modes/test_tracker.py`
**Method:** `MaszynaStanow._przejdz_do()` — lines 270-277

**Current:**
```python
def _przejdz_do(self, nowy_stan: str) -> None:
    logger.info(f"Zmiana stanu: {self.stan} → {nowy_stan}")
    self.stan = nowy_stan
    self._czas_ostatniego_celu = time.time()
    if nowy_stan == config.STATE_SCANNING:
        self.pid_pan.reset()
        self.pid_tilt.reset()
```

The streak reset needs a reference to `DetekcjaTwarzy`. `MaszynaStanow` currently has no
reference to it — `DetekcjaTwarzy` is owned by `TestTracker`.

**Two valid options:**

**Option A — Pass detekcja reference to _przejdz_do (minimal coupling):**
```python
def _przejdz_do(self, nowy_stan: str, detekcja=None) -> None:
    logger.info(f"Zmiana stanu: {self.stan} → {nowy_stan}")
    self.stan = nowy_stan
    self._czas_ostatniego_celu = time.time()
    if nowy_stan == config.STATE_SCANNING:
        self.pid_pan.reset()
        self.pid_tilt.reset()
        if detekcja is not None:
            detekcja.resetuj_streak()
```
Callers that need streak reset pass `detekcja=self.detekcja`. Callers inside `MaszynaStanow`
(which don't have access to detekcja) omit it and get no streak reset — safe default.

**Option B — Keep uruchom() approach but reset one frame earlier:**
Change the uruchom() check to trigger on TARGET_LOST entry (not SCANNING entry):
```python
if stan == STATE_TARGET_LOST and poprzedni_stan == config.STATE_TRACKING:
    self.detekcja.resetuj_streak()
```
This fires on the TARGET_LOST frame, before the next SCANNING tick. Simpler structural
change — no coupling change between MaszynaStanow and DetekcjaTwarzy.

**Recommendation: Option B.** It is a one-line change in uruchom(), keeps MaszynaStanow
self-contained, and achieves the same effect. Option A introduces coupling between state
machine and detector that was intentionally avoided in the original design.

**Change set (Option B):**
In `uruchom()` lines 323-324, replace the existing streak-reset block:

**Current:**
```python
if stan == config.STATE_SCANNING and poprzedni_stan != config.STATE_SCANNING:
    self.detekcja.resetuj_streak()
```

**Fixed:**
```python
if stan == STATE_TARGET_LOST and poprzedni_stan == config.STATE_TRACKING:
    self.detekcja.resetuj_streak()
```

**Change set:** 1 condition rewritten (same line count, same location). Nothing else changes.

---

## Ordering Dependencies Between Fixes

```
Fix 1 (tilt sign)     — INDEPENDENT. No dependency on any other fix.
Fix 2 (AWB)           — INDEPENDENT. Isolated to Picamera2Stream constructor/reinit.
Fix 3 (scan streak)   — INDEPENDENT. Isolated to uruchom() conditional.

Recommended apply order: Fix 2 → Fix 1 → Fix 3
```

**Rationale for order:**

1. **Fix 2 first (AWB)** — Camera quality fix. Applying it first means all subsequent
   hardware tests observe correct color. No logic dependencies.

2. **Fix 1 second (tilt sign)** — The most impactful functional fix. Applying it after
   AWB means the first motion test under correct color confirms both simultaneously.
   This fix is a single character change with immediate observable effect.

3. **Fix 3 last (streak reset)** — The most subtle fix. Its effect is only visible in
   rapid TRACKING→SCANNING→TRACKING transition sequences. Saving it last allows
   verification of fixes 1 and 2 in a stable tracking scenario first.

None of the three fixes conflict with each other. They can be applied in a single commit
or separately per fix.

---

## Summary Table

| Fix | File | Method | Change Set | Dependencies |
|-----|------|--------|------------|--------------|
| Tilt PID sign | `src/modes/test_tracker.py` | `MaszynaStanow._sledz()` line 263 | Add `-` prefix to `pid_tilt()` call | None |
| AWB Indoor | `src/modes/test_tracker.py` | `Picamera2Stream.start()` lines 66-68 + reinit lines 111-113 | Add `controls={"AwbMode": 4}` to 2 `create_video_configuration` calls | None |
| Scan streak | `src/modes/test_tracker.py` | `TestTracker.uruchom()` lines 323-324 | Change condition from `STATE_SCANNING` entry to `TARGET_LOST` entry | None |

**Total change surface:** 4 lines in 1 file. No other file is modified.

---

## What Does NOT Need Changing

| Item | Status | Reason |
|------|--------|--------|
| PID reset on SCANNING (`pid_pan.reset()`, `pid_tilt.reset()`) | Correct as-is | `simple_pid.reset()` verified to zero all terms including integral |
| `korekta_pan = -self.pid_pan(blad_pan)` | Correct as-is | Pan negation is correct for standard mounting (pan+ = right) |
| `_skanuj()` tilt forced to 0.0 | Correct as-is | Tilt neutral during scan is expected behavior |
| `TIME_TO_LOST_SEC = 2.0` timeout | Correct as-is | Not a bug, design parameter |
| `PanTiltSystem.set_angles()` soft limits | Correct as-is | Limits in config.py protect ribbon cable |
| `smooth_move_to(0, 0)` in `inicjalizuj()` | Correct as-is | Safe startup anti-brownout pattern preserved |
| `src/hardware.py` | No changes needed | Servo abstraction layer is correct |
| `src/config.py` | No changes needed | PID gains, limits, timing constants unchanged |

---

## Architecture Invariants (Must Not Break)

1. `Picamera2Stream` must remain a separate class from `MaszynaStanow` — camera lifecycle
   and control logic have different failure modes.

2. `MaszynaStanow` must not import `DetekcjaTwarzy` — the streak reset fix (Option B)
   keeps this boundary intact.

3. `smooth_move_to()` must remain the only startup path to servos — no direct `set_angles()`
   call before safe startup completes.

4. `_przejdz_do()` remains the single state transition method — no inline `self.stan =`
   assignments outside it.

---

## Sources

- Direct source analysis: `src/modes/test_tracker.py` (all methods read in full) — HIGH confidence
- Direct source analysis: `src/hardware.py` (PanTiltSystem) — HIGH confidence
- Direct source analysis: `src/config.py` (all constants) — HIGH confidence
- Live verification: `simple_pid.PID.__call__` and `reset()` source inspected on target machine — HIGH confidence
- Live verification: `Picamera2.create_video_configuration` signature on target machine — HIGH confidence
- Live verification: `libcamera.controls.AwbModeEnum` values on target machine — HIGH confidence
- `.planning/PROJECT.md` — v1.7 bug descriptions and hardware context — HIGH confidence
