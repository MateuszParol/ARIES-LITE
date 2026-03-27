# Domain Pitfalls — v1.7 Bug Fix Milestone

**Domain:** Fixing critical bugs in `src/modes/test_tracker.py` on RPi4 hardware
**Researched:** 2026-03-27
**Confidence:** HIGH — all pitfalls grounded in direct code analysis of `test_tracker.py`,
`src/hardware.py`, `src/config.py`, `simple_pid` source, and verified Picamera2 community
documentation.

---

## Scope

This document covers pitfalls specific to the four v1.7 fixes:

1. PID sign inversion (runaway camera, tilt non-movement)
2. AWB / color correction (blue tint on IMX219)
3. PID reset on state transition (anti-windup at TRACKING → SCANNING)
4. Servo limit masking PID output (correction silently clamped)

---

## Critical Pitfalls

---

### Pitfall 1: Fixing One PID Axis Sign and Introducing Double-Negation on the Other

**What goes wrong:**
`_sledz()` in `test_tracker.py` lines 261–263 uses asymmetric negation:
```python
korekta_pan  = -self.pid_pan(blad_pan)   # pan negated
korekta_tilt =  self.pid_tilt(blad_tilt) # tilt NOT negated
```
The tilt axis is currently observed to produce no movement. The reflex fix is to add
`-self.pid_tilt(...)` to mirror pan. This is wrong if the physical cause is something
else (clamped output, wrong error formula, zero gain). If tilt truly needs negation,
applying it is correct. But if pan's negation is also wrong (it drives the face away
from center instead of toward it), then negating pan again to "fix" it creates a
double-negation: both axes drive away from center simultaneously.

**Why it happens:**
The sign of the correction depends on **two independent choices** that must be consistent:

1. Error direction: `blad_pan = srodek_x - ramka_cx` (positive when face is right of
   center). This is correct for standard image coordinates (x increases left-to-right).

2. Servo direction: for the standard mounting confirmed in PROJECT.md (`pan+ = right`),
   moving the camera right (pan+) when the face is right of center makes the error
   larger, not smaller. Therefore the correction must be negated: `korekta = -pid(error)`.

The existing pan negation `korekta_pan = -self.pid_pan(blad_pan)` is correct for the
stated mounting. The tilt axis: `blad_tilt = srodek_y - ramka_cy` is positive when the
face is below center. For standard mounting (`tilt+ = down`), moving tilt down when the
face is below center also increases error — so tilt correction also needs negation.

The current code does NOT negate tilt. Adding `-self.pid_tilt(blad_tilt)` is therefore
the correct fix — but only after verifying the error calculation is correct.

**Double-negation scenario (the actual trap):**
Developer sees runaway camera on pan AND tilt non-movement. Concludes pan sign is wrong,
adds a second negation to pan: `korekta_pan = self.pid_pan(blad_pan)` (removing the
existing minus). Now pan has no negation and drives away from center. Developer adds
negation to tilt, getting `korekta_tilt = -self.pid_tilt(...)`. Result: pan is wrong,
tilt is right, but the pan runaway was caused by something else entirely (e.g., servo
limit being reached silently, see Pitfall 4).

**Consequences:**
- Pan diverges: camera runs to limit and stays there
- System appears to track but always moves face further from center
- Very hard to diagnose because the servo does move — just in the wrong direction

**Prevention:**
Before touching any sign:
1. Verify error formula independently: print `blad_pan` when face is known to be right of
   center. It must be positive.
2. Verify servo direction independently: command `set_angles(+10, 0)` directly and
   observe if camera pans right. Confirm PROJECT.md claim `pan+ = right`.
3. From those two facts, derive required sign mathematically rather than by trial and error.
4. Change one axis at a time. Verify each axis in isolation before touching the other.

**Detection (warning signs):**
- After fix, face moves further from center on one or both axes
- `blad_pan` logs show sign is correct, but correction moves servo toward larger error
- Servo reaches limit within 2–3 frames of acquiring a target

**Phase:** Task targeting runaway camera / tilt non-movement. Verify error signs before
modifying any negation.

---

### Pitfall 2: Tilt Non-Movement Misdiagnosed as Sign Error When Root Cause Is Clamped Output

**What goes wrong:**
Tilt does not move at all during tracking. The reflex conclusion is "tilt PID sign is
wrong." But the actual cause may be that `korekta_tilt` is computed correctly yet the
commanded `nowy_tilt` always equals `self.hardware.tilt_angle` after clamping in
`set_angles()`.

Specifically, if tilt starts at 0° and the PID correction is, say, +2°, the new tilt
is 2° — well within the ±30° soft limit. That is fine. But if tilt is already at 0°
and the correction computed is actually 0.0 because `pid_tilt` has not been called with
a non-zero error yet (e.g., `blad_tilt` is near zero because the face happens to be
vertically centered), then there is no movement regardless of sign.

The more dangerous scenario: `pid_tilt` gains in `config.py` are the same as pan
(`PID_TILT_P = 0.05`), which produces a correction of `0.05 * error_pixels`. For a
vertical error of 10 pixels (face 10px above center), the correction is 0.5°. After
clamping to tilt soft limits (±30°), this is applied. But `set_angles()` calls
`max(config.TILT_LIMIT_MIN, min(config.TILT_LIMIT_MAX, tilt))` — if the current
`tilt_angle` tracked in software diverged from hardware state (e.g., due to a previous
test run that did not complete cleanly), this clamp operates on a wrong base value.

**Why it happens:**
`PanTiltSystem.tilt_angle` is a software variable, not an encoder readback. If the
hardware servo moved but the software state was not updated (e.g., mock mode was
inadvertently active, or `set_angles` was called in mock mode), `tilt_angle` stays at 0
while the physical servo is at +20°. PID corrections are then applied to the wrong base,
and the resulting commanded angle after clamping may equal the current `tilt_angle`
(no apparent movement in logs even though the servo should have moved).

**Consequences:**
- Developer chases a sign problem that does not exist
- Wastes debug cycles on the wrong fix
- May introduce an actual sign bug while trying to "fix" a non-existent one

**Prevention:**
Before diagnosing sign errors for tilt non-movement:
1. Check `PIGPIO_AVAILABLE` and `_mock_mode` at startup. If pigpiod is not running,
   `PanTiltSystem` silently falls back to mock mode — no servo movement, no error.
   Verify with: `systemctl is-active pigpiod` on the RPi4.
2. Log `korekta_tilt` values in `_sledz()` for 10 consecutive frames. If the values are
   all zero or near-zero, the PID is computing correctly but there is no tilt error to
   correct (face is vertically centered, or HAAR bbox is inaccurate on the Y axis).
3. Issue a direct `set_angles(0, 10)` call to confirm the tilt servo physically moves.
   If it does, the servo is functional and the PID path is the issue.
4. Only then investigate PID sign.

**Detection (warning signs):**
- `maszyna.hardware._mock_mode` is `True` (check at startup)
- `korekta_tilt` logs show values near 0 consistently
- `blad_tilt` logs show values near 0 (face is always near vertical center)
- Direct `set_angles(0, 10)` works, tilt servo moves — problem is in PID path not hardware

**Phase:** Tilt non-movement investigation. Rule out mock mode and zero-error before
any sign change.

---

### Pitfall 3: AWB set_controls Called Before Camera Starts — Silently Ignored

**What goes wrong:**
`Picamera2Stream.start()` calls `self._picam2.configure(video_config)` then
`self._picam2.start()`. There is no AWB configuration anywhere in the current code.
To fix the blue tint, the natural place to add it is in `start()` before calling
`self._picam2.start()`. This does not work.

Picamera2 requires `set_controls()` to be called **after** `start()`. Calling it after
`configure()` but before `start()` either raises a runtime error or is silently ignored —
the camera starts with its default AWB algorithm active and the blue tint persists.

**Why it happens:**
Picamera2's control pipeline is established when `start()` is called. `configure()` sets
the stream format and buffer allocation, not the ISP algorithm parameters. Setting ISP
controls (AWB, exposure, colour gains) before the ISP is running has no effect. The
Picamera2 maintainer has explicitly confirmed this ordering requirement in GitHub issue
#825 and the RPi forums thread on locking AWB.

**Consequences:**
- Blue tint persists even though AWB configuration code appears correct
- Developer concludes the gain values are wrong and keeps changing them
- Never finds correct gains because the configuration is never applied

**Prevention:**
Set AWB controls in the capture thread (`_petla_przechwytywania`) **after** the first
successful `capture_array()` call, or in `start()` after `self._picam2.start()` with a
brief warm-up delay (1–2 frames). The safest pattern for the current architecture:

```python
self._picam2.start()
# Allow camera to start ISP pipeline
time.sleep(0.1)
self._picam2.set_controls({"ColourGains": (red_gain, blue_gain)})
# Setting ColourGains implicitly disables AWB — do NOT also set AwbEnable=False
# as the Picamera2 maintainer warns this can cause sequencing issues
```

Do NOT call `set_controls({"AwbEnable": False})` explicitly alongside `ColourGains`.
Setting `ColourGains` already disables AWB. Adding `AwbEnable: False` separately can
cause control sequencing conflicts in some Picamera2 versions.

**Detection (warning signs):**
- Blue tint persists after adding AWB configuration
- No error or warning in logs from Picamera2
- `picam2.capture_metadata()` after start shows `ColourGains` as the auto-computed value,
  not the manually set one

**Phase:** AWB fix. Always add the `time.sleep(0.1)` guard after `start()` before
setting any ISP controls.

---

### Pitfall 4: AWB Warm-Up Flicker — First N Frames Ignore Manual Gains

**What goes wrong:**
Even with correct `set_controls({"ColourGains": (r, b)})` called after `start()`, the
first 3–10 frames from the camera may still show blue tint or color fluctuation. The
capture thread stores these early frames in `self._frame` and the main loop processes
them normally. If the HUD or debug capture happens to screenshot during this warm-up
window, the AWB "fix" appears to have failed.

**Why it happens:**
Picamera2 has an internal frame pipeline with latency. Controls set via `set_controls()`
take effect 2–3 frames after being issued (the control must pass through the kernel
driver's request queue). During this 2–3 frame window, the old AWB values are still
active.

**Consequences:**
- Developer thinks AWB configuration is wrong, starts changing gain values
- Gains get tuned against the warm-up artifact instead of the steady-state image
- Result: overcorrected warm gains that look correct during initialization but wrong in
  steady state

**Prevention:**
In `_petla_przechwytywania`, skip the first 5 frames before storing into `self._frame`.
Or alternatively, read `picam2.capture_metadata()["ColourGains"]` and only store frames
once the reported gains match the commanded values.

Simple approach that fits the existing code structure:
```python
# In _petla_przechwytywania, add a warm-up counter:
_warmup_frames = 0
_WARMUP_REQUIRED = 5

# Inside the loop:
if _warmup_frames < _WARMUP_REQUIRED:
    _warmup_frames += 1
    continue  # discard early frames

with self._lock:
    self._frame = klatka
```

**Detection (warning signs):**
- Color is correct after ~1 second of running, wrong in the first second
- Screenshot taken immediately after start shows blue tint, later screenshots are correct
- Adding `time.sleep(1.0)` before first screenshot makes the problem disappear

**Phase:** AWB fix. Add warm-up skip as part of the same change that adds ColourGains.

---

### Pitfall 5: PID reset() Clears Derivative State — Causes Derivative Spike on First Post-Reset Tick

**What goes wrong:**
`_przejdz_do()` calls `self.pid_pan.reset()` and `self.pid_tilt.reset()` when
transitioning into SCANNING state (line 276–277). `simple_pid`'s `reset()` clears ALL
internal state: `_proportional`, `_integral`, `_derivative`, `_last_output`,
`_last_input`, and `_last_time`.

On the first call to `pid_pan(blad_pan)` after reset (when a face is re-acquired and
the state machine transitions SCANNING → TRACKING → first `_sledz()` call), `_last_input`
is `None`. `simple_pid` handles `None` last_input by skipping the derivative term on
the first tick, which is correct.

However, the transition sequence in `tick()` is:
1. `_przejdz_do(STATE_TRACKING)` — state changes to TRACKING
2. `_sledz(bbox, w, h)` — called immediately in the same tick

This means the PID is called for the first time in the same frame that triggered the
state transition. `_last_time` was reset to `time.time()` inside `reset()`, and the
immediately following PID call happens within microseconds. `simple_pid` uses
`sample_time=0.033` — if `dt < sample_time`, the PID returns the last output (which
is `None` after reset) and produces `0` correction. This is actually benign for the
derivative spike concern.

The real issue is the opposite: if `reset()` is called at the wrong moment (e.g., inside
TRACKING state when tracking is re-acquired after a brief miss, not just at
TRACKING → SCANNING), the integral accumulated during successful tracking is discarded,
causing the servo to drift away from center until the integral rebuilds.

**Why it happens:**
The current code only resets on transition to SCANNING, which is correct. But if a
developer adds a "re-acquire" reset (thinking "start fresh on each face acquisition"),
they will reset during active TRACKING, losing the integral correction needed to hold
the servo on target.

**Consequences:**
- Servo drifts from center when face is briefly re-acquired after occlusion
- PID takes 2–5 seconds to re-accumulate integral and re-center
- Appears as "tracking instability" rather than "reset too frequently"

**Prevention:**
Call `pid.reset()` only in `_przejdz_do()` when `nowy_stan == config.STATE_SCANNING`.
Never reset PID inside TRACKING state, even on face re-acquisition after brief occlusion.
The existing code does this correctly — do not add any additional reset points.

Additionally: do not call `pid.reset()` on the SCANNING → TRACKING transition itself.
The integral and derivative state should be zero already (reset happened when entering
SCANNING), but explicitly not resetting on TRACKING entry ensures a brief scan
interruption (face visible for 1 frame, then lost, then visible) does not cause an
unnecessary reset.

**Detection (warning signs):**
- Servo centers correctly then drifts ~1–2 seconds after face reappears from occlusion
- Log shows `_integral` near 0 immediately after face re-acquisition during TRACKING
- If `pid.reset()` is called inside TRACKING logic, it appears in the call stack

**Phase:** PID reset fix / state machine transition review. Add reset() only in the
one correct location; document why other locations are intentionally excluded.

---

### Pitfall 6: Integral Cleared but Previous Derivative State Stale — Reset Does Not Guarantee Clean Start

**What goes wrong:**
`simple_pid.PID.reset()` clears `_last_input = None`. On the first tick after reset,
the derivative term is skipped (because `_last_input is None`). On the second tick,
`_last_input` has a real value and the derivative is computed normally.

The danger is if `reset()` is NOT called on TRACKING → SCANNING (e.g., a developer
removes the reset thinking "the output_limits handle windup anyway"). The integral
accumulates during SCANNING if `_sledz()` is mistakenly called while in SCANNING state
(the current code guards against this with the `if self.stan == config.STATE_TRACKING`
check, but if that check were removed or bypassed during refactoring, the integrator
winds up silently).

Separately, `output_limits = (-10, 10)` in `test_tracker.py` line 197 caps the PID
output but `simple_pid`'s anti-windup clamping of the integral depends on version.
In `simple_pid >= 2.0`, when `output_limits` are set, the integral is clamped to stay
within those limits. In `simple_pid < 2.0`, the integral can exceed limits even though
the output is capped.

**Why it happens:**
`pip install simple-pid` without a version pin may install either 1.x or 2.x depending
on the environment. The anti-windup behavior differs between versions.

**Prevention:**
1. Pin `simple-pid>=2.0.0` in `requirements.txt` to get reliable anti-windup clamping.
2. Keep the `pid.reset()` call in `_przejdz_do()` for SCANNING transition — even with
   output_limits and anti-windup clamping, an explicit reset guarantees a clean start.
3. Verify installed version: `pip show simple-pid | grep Version`.

**Detection (warning signs):**
- Servo overshoots significantly on first tracking tick after a long scan period
- Log `pid_pan._integral` value at SCANNING → TRACKING transition: should be 0 or near 0
- `pip show simple-pid` reports version < 2.0

**Phase:** PID reset / anti-windup fix. Version-pin `simple-pid` as part of this task.

---

### Pitfall 7: Correction Silently Eaten by Soft Limits — Servo Appears Broken When It Is at the Boundary

**What goes wrong:**
`hardware.py` `set_angles()` clamps pan to `[-60, +60]` and tilt to `[-30, +30]`.
`_sledz()` computes:
```python
nowy_pan  = self.hardware.pan_angle + korekta_pan
nowy_tilt = self.hardware.tilt_angle + korekta_tilt
self.hardware.set_angles(nowy_pan, nowy_tilt)
```

If `self.hardware.pan_angle` is already at +60° (limit), and `korekta_pan = +2°`, then
`nowy_pan = 62°`, which `set_angles()` clamps back to 60°. The servo does not move. The
PID correctly computes a correction, the code appears correct, but there is no observable
movement. This is indistinguishable from "PID is computing zero correction" or "servo is
broken" during debugging.

The specific trap for tilt: tilt starts at 0°. Correction is computed as +2° (face below
center). `nowy_tilt = 2°`. Fine, within limits. But if the scan function `_skanuj()`
calls `set_angles(pan, 0.0)` directly — hardcoding tilt to 0 — and then `_sledz()` runs
in the same tick (due to a race in the state machine), `tilt_angle` gets reset to 0
before the correction is applied. The correction is applied to the 0 base, works
correctly, but the next scan call zeros it out. Net effect: tilt oscillates around 0
instead of tracking.

**Why it happens:**
In `MaszynaStanow.tick()` (lines 220–241), the SCANNING path calls `_skanuj()` which
calls `set_angles(pan, 0.0)`. The TRACKING path calls `_sledz()`. These are mutually
exclusive via the state machine, so under normal operation there is no race. However,
in the SCANNING→TRACKING transition tick (lines 221–223):
```python
if bbox is not None:
    self._przejdz_do(config.STATE_TRACKING)
    self._sledz(bbox, w, h)
```
The transition happens first, then `_sledz()` is called. `_skanuj()` is NOT called on
this tick. This is correct. The race scenario only matters if the state machine logic
is modified.

The limit-masking concern is real for any axis at its boundary. If runaway camera is the
bug (wrong sign), the pan servo hits the limit within 2–3 frames, then appears "stuck"
— which is not a sign problem but a consequence of it.

**Prevention:**
Add a diagnostic log when `set_angles()` applies clamping. In `hardware.py`:
```python
def set_angles(self, pan: float, tilt: float) -> None:
    clamped_pan  = max(config.PAN_LIMIT_MIN,  min(config.PAN_LIMIT_MAX,  pan))
    clamped_tilt = max(config.TILT_LIMIT_MIN, min(config.TILT_LIMIT_MAX, tilt))
    if abs(clamped_pan - pan) > 0.1 or abs(clamped_tilt - tilt) > 0.1:
        logger.debug(
            f"Soft limit applied: pan {pan:.1f}→{clamped_pan:.1f}, "
            f"tilt {tilt:.1f}→{clamped_tilt:.1f}"
        )
    self.pan_angle  = clamped_pan
    self.tilt_angle = clamped_tilt
    ...
```
This makes limit-hitting visible in logs immediately.

**Detection (warning signs):**
- Servo appears to stop responding after initial movement
- `pan_angle` or `tilt_angle` stays at the limit value for many consecutive frames
- `korekta_pan` / `korekta_tilt` logs show non-zero values while `pan_angle` does not change
- Adding soft-limit logging shows continuous clamping events

**Phase:** Runaway camera / tilt non-movement investigation. Add soft-limit logging as
first diagnostic step before any code changes.

---

## Moderate Pitfalls

---

### Pitfall 8: YUV420 capture_array Shape — cv2.COLOR_YUV420p2BGR vs COLOR_YUV2BGR_I420

**What goes wrong:**
The existing code uses `cv2.cvtColor(klatka_yuv, cv2.COLOR_YUV420p2BGR)`. Picamera2 in
lores YUV420 mode returns an array of shape `(height * 3 // 2, width)` — a single-channel
planar YUV array, NOT a 3-channel array. `cv2.COLOR_YUV420p2BGR` (also spelled
`COLOR_YUV2BGR_YV12`) expects YV12 planar format. Picamera2 outputs I420 (YUV420p)
which has U and V planes in the opposite order.

If the wrong constant is used, the output BGR frame has U and V planes swapped, producing
a color artifact that is distinct from the AWB blue tint: it appears as a green-magenta
shift on skin tones rather than an overall blue cast.

**Why it happens:**
OpenCV has multiple YUV420 conversion constants with similar names that differ in Cb/Cr
plane ordering:
- `COLOR_YUV420p2BGR` = I420 (Y + U + V, this is what Picamera2 produces)
- `COLOR_YUV2BGR_YV12` = YV12 (Y + V + U, planes reversed)

These are actually the same constant value in current OpenCV (both map to I420), but in
some OpenCV versions built differently they differ. The existing code's
`COLOR_YUV420p2BGR` is correct for Picamera2's output — do not change it while fixing
the AWB issue, as the AWB problem is ISP-level, not format-conversion-level.

**Prevention:**
Do not touch the `cv2.cvtColor` line when fixing AWB. The two problems are independent:
- AWB blue tint: fix with `set_controls({"ColourGains": (r, b)})` after camera start
- YUV conversion: already correct, leave it alone

If the YUV constant needs to be investigated, verify by inspecting `klatka_yuv.shape`
in the format verification log (line 92): must be `(360, 320)` for 320x240 YUV420
(height * 1.5 = 360 rows, 320 columns, single channel).

**Detection (warning signs):**
- Green-magenta skin tone cast (not blue) = wrong YUV constant
- Blue overall cast = AWB issue (different problem)
- `klatka_yuv.shape` has 3 channels = wrong Picamera2 capture format configuration

**Phase:** AWB fix. Treat AWB and YUV conversion as independent; fix only AWB.

---

### Pitfall 9: State Transition Timing — TARGET_LOST One-Frame Latency Causes PID Reset Delay

**What goes wrong:**
The `_przejdz_do(STATE_TARGET_LOST)` path (lines 234–238) transitions to TARGET_LOST on
timeout, then on the next tick transitions directly to SCANNING. PID reset happens in
`_przejdz_do()` only when `nowy_stan == config.STATE_SCANNING`. So the reset happens
on the second tick after the timeout.

Between the two ticks, the state is TARGET_LOST and `_sledz()` is not called. The PID
receives no new input. `simple_pid` with `sample_time=0.033` will not update if no call
is made. So the integral holds its value for one extra tick. This is not a bug — the
effect is a ~33 ms delay before reset, which is imperceptible.

However, if a developer adds `self.pid_pan.reset()` in the TARGET_LOST branch directly
(trying to reset "earlier"), they break the invariant that the reset happens exactly at
SCANNING entry. If SCANNING is entered via a path that does NOT go through TARGET_LOST
(e.g., direct TRACKING → SCANNING for a future feature), the reset in the TARGET_LOST
branch would not execute.

**Prevention:**
Keep PID reset exclusively in `_przejdz_do()` with the `if nowy_stan == STATE_SCANNING`
guard. This is the single authoritative reset point and handles all transition paths.
Do not add reset logic in state-specific branches.

**Phase:** State machine review. Note this is already correct in the existing code — do
not "improve" it.

---

### Pitfall 10: IMX219 ColourGains — Gain Values Must Be Float Tuples, Not Int

**What goes wrong:**
`set_controls({"ColourGains": (2, 1)})` passes integer values. Picamera2's control
pipeline expects `float` for gain values. Passing integers may work on some versions but
raises `TypeError: Cannot convert int to float` or silently applies 1.0 for both gains
on others, leaving the blue tint unchanged.

**Prevention:**
Always pass explicit floats: `set_controls({"ColourGains": (2.0, 1.4)})`.
For IMX219 (Camera Module V2) in typical indoor fluorescent lighting, starting values
of `(1.8, 1.5)` (red_gain, blue_gain) are a reasonable starting point. Outdoor daylight
typically needs `(1.5, 1.8)`. Tune empirically on the actual hardware in the target
lighting conditions by adjusting in 0.1 increments.

**Detection (warning signs):**
- `TypeError` at camera start
- Blue tint unchanged after adding ColourGains — check that gains were actually applied
  by reading back `picam2.capture_metadata()["ColourGains"]` after a few frames

**Phase:** AWB fix. Use explicit floats from the first implementation.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| PID sign fix: tilt non-movement | Misdiagnosed sign error (actually mock mode or zero error) | Rule out mock mode and zero blad_tilt before touching sign (Pitfall 2) |
| PID sign fix: runaway camera | Pan at limit masking true sign direction | Add soft-limit logging first; sign fix is secondary (Pitfall 7) |
| PID sign fix: both axes | Double-negation from fixing one, breaking other | Verify error formula and servo direction independently before any change (Pitfall 1) |
| AWB fix: set_controls timing | Controls silently ignored before camera start | Call set_controls after start() with time.sleep(0.1) (Pitfall 3) |
| AWB fix: warm-up artifact | First frames wrong, developer tunes against artifact | Add 5-frame warm-up skip in capture thread (Pitfall 4) |
| AWB fix: YUV conversion | Temptation to change cvtColor constant while fixing AWB | Treat as independent; existing YUV constant is correct (Pitfall 8) |
| AWB fix: gain type | Integer ColourGains silently misapplied | Always use float tuple (Pitfall 10) |
| PID reset: state transition | Adding extra reset inside TRACKING state | Reset only in _przejdz_do() for SCANNING entry, never in TRACKING (Pitfall 5) |
| PID reset: anti-windup version | simple_pid < 2.0 does not clamp integral | Pin simple-pid>=2.0.0 in requirements.txt (Pitfall 6) |
| Servo limits: correction masked | Correction applied but silently clamped at limit | Add soft-limit logging to set_angles() immediately (Pitfall 7) |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| PID double-negation (Pitfall 1) | HIGH | Derived from direct code reading and confirmed mounting convention from PROJECT.md |
| Tilt non-movement misdiagnosis (Pitfall 2) | HIGH | Mock mode path verified in hardware.py; zero-error scenario is mathematically straightforward |
| AWB set_controls timing (Pitfall 3) | HIGH | Confirmed by Picamera2 maintainer in RPi forums and GitHub issue #825; ordering requirement is documented |
| AWB warm-up flicker (Pitfall 4) | HIGH | Standard Picamera2 pipeline behavior; documented in multiple community threads |
| PID reset() clears derivative (Pitfall 5) | HIGH | simple_pid source verified: reset() clears _last_input, _integral, _proportional, _derivative, _last_time |
| simple_pid version anti-windup (Pitfall 6) | MEDIUM | Anti-windup behavior change between 1.x and 2.x documented in simple_pid changelog; exact version on test RPi4 unverified |
| Soft limit masking (Pitfall 7) | HIGH | Derived directly from hardware.py set_angles() clamp logic; clamping is silent and confirmed by code |
| YUV420 conversion constant (Pitfall 8) | MEDIUM | OpenCV constant naming is documented; Picamera2 YUV420 plane ordering confirmed I420; interaction between specific OpenCV build and constant requires hardware verification |
| STATE_TARGET_LOST latency (Pitfall 9) | HIGH | Direct code analysis of tick() and _przejdz_do(); one-tick delay is intentional and documented |
| ColourGains type requirement (Pitfall 10) | MEDIUM | Float requirement is standard for Picamera2 controls; specific TypeError on int input is version-dependent |

---

## Sources

- `src/modes/test_tracker.py` — direct code analysis: `_sledz()` sign convention, `_przejdz_do()` reset logic, `Picamera2Stream.start()` AWB absence
- `src/hardware.py` — direct code analysis: `set_angles()` clamping behavior, mock mode fallback
- `src/config.py` — PID gains, servo limits, state names
- `.planning/PROJECT.md` — confirmed mounting: `pan+ = right`, `tilt+ = down`; v1.7 bug descriptions
- `CLAUDE.md` — architecture, threading model, hardware constraints
- simple_pid source code (`github.com/m-lundberg/simple-pid`) — `reset()` clears `_proportional`, `_integral`, `_derivative`, `_last_output`, `_last_input`, `_last_time` (HIGH confidence)
- Raspberry Pi Forums: "How to lock AWB with Picamera2" — `set_controls` must follow `start()`; setting `ColourGains` implicitly disables AWB; do not set `AwbEnable=False` alongside `ColourGains` (HIGH confidence)
- GitHub raspberrypi/picamera2 issue #825 — AWB/ColourGains not working root causes: adaptive algorithms, camera warm-up, control ordering (HIGH confidence)
- PyImageSearch pan-tilt face tracking tutorial — error sign convention: `error = center - object`, servo angles negated; explicit negation of both pan and tilt (MEDIUM confidence — different mounting, but error formula pattern is standard)
