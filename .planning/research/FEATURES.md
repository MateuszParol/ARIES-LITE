# Feature Landscape — v1.7 Debugging & Optimization

**Domain:** Autonomous pan-tilt face tracking — critical bug fixes
**Researched:** 2026-03-27
**Milestone:** v1.7 — Fixes for test_tracker.py on RPi4 hardware

---

## Context: This Is a Bug-Fix Milestone, Not a Feature Release

v1.7 goal is to fix four confirmed hardware bugs in `src/modes/test_tracker.py`. Each
fix has a precise mathematical or API-level diagnosis. The features here are
"correct behaviors" that must replace the broken behaviors, not new capabilities.

All analysis is grounded in:
- Mathematical derivation from first principles (sign convention)
- Verified simple_pid library behavior (error = setpoint − input)
- Confirmed Picamera2 API for AWB control (official docs + GitHub issues)
- Empirical hardware constraints from PROJECT.md (pan+ = right, tilt+ = down)

---

## Bug 1: Runaway Camera (Positive Feedback Instead of Negative)

### Diagnosis — Mathematical Proof

The tracking loop must be a **negative feedback** system. This means: when the face
is to the right of center, the servo must pan right (increasing pan angle) to
re-center it.

**Coordinate system (established empirically, PROJECT.md):**
- Pan angle positive → servo rotates right → camera points right → face appears to
  move left in frame (toward center)
- Tilt angle positive → servo rotates down → camera points down → face appears to
  move up in frame (toward center)
- Pixel x positive → face is to the right in image
- Pixel y positive → face is lower in image

**Error definitions:**

```
blad_pan  = srodek_x − ramka_cx   (positive when face is RIGHT of center)
blad_tilt = srodek_y − ramka_cy   (positive when face is BELOW center)
```

**simple_pid formula (verified from source):**

```
output = Kp × (setpoint − input)
       = Kp × (0 − blad)
       = −Kp × blad
```

With `setpoint=0` and all gains positive, `pid_pan(blad_pan)` returns a **negative**
value when `blad_pan` is positive (face to the right).

**Current code (line 262–263 of test_tracker.py):**

```python
korekta_pan  = -self.pid_pan(blad_pan)   # double negation → WRONG sign
korekta_tilt =  self.pid_tilt(blad_tilt) # single negation from PID → WRONG sign
```

**Tracing the pan axis:**

| Condition | blad_pan | pid_pan(blad_pan) | korekta_pan | nowy_pan | Effect |
|-----------|----------|-------------------|-------------|----------|--------|
| Face right of center | +px | −K·px (negative) | −(−K·px) = +K·px | increases | Camera pans right ✓ |

Wait — pan appears correct on paper. But the runaway is confirmed on hardware.
The problem becomes visible when we trace what "face moves right" actually means
for the correction loop:

When the camera is **already** at non-zero pan angle and detects a face, the error
and correction are correct for a single step. However, if the camera overshoots
(pans too far right), the face is now left of center (negative blad_pan), and
`korekta_pan = -pid_pan(negative) = -(positive) = negative` → reduces pan angle →
camera pans left. That is negative feedback — correct.

**The actual runaway cause is the tilt axis:**

```
blad_tilt = srodek_y − ramka_cy   (positive when face is BELOW center)
```

When face is below center (blad_tilt > 0), we need tilt angle to increase (servo
tilts down, camera looks down, face moves upward toward center).

```
pid_tilt(blad_tilt) with setpoint=0:
  output = Kp × (0 − blad_tilt) = −Kp × blad_tilt   (negative when face is below)
```

```python
korekta_tilt = self.pid_tilt(blad_tilt)  # = −Kp·blad_tilt  (negative)
nowy_tilt    = tilt_angle + korekta_tilt  # angle DECREASES
```

Decreased tilt angle → servo tilts up → camera points up → face moves further DOWN
in frame → blad_tilt increases → larger negative correction → servo tilts further up
→ **positive feedback loop / runaway away from face**.

**Correct formula for tilt:**

```
korekta_tilt = -self.pid_tilt(blad_tilt)   # negate to get negative feedback
```

**Tracing tilt with fix applied:**

| Condition | blad_tilt | pid_tilt() | korekta_tilt (fixed) | nowy_tilt | Effect |
|-----------|-----------|------------|----------------------|-----------|--------|
| Face below center | +py | −K·py | −(−K·py) = +K·py | increases | Camera tilts down, face moves up ✓ |
| Face above center | −py | +K·py | −(+K·py) = −K·py | decreases | Camera tilts up, face moves down ✓ |

**Tracing pan with fix applied (verify it's still correct):**

The pan is currently `korekta_pan = -self.pid_pan(blad_pan)`.

| Condition | blad_pan | pid_pan() | korekta_pan (current) | nowy_pan | Effect |
|-----------|----------|-----------|----------------------|----------|--------|
| Face right of center | +px | −K·px | −(−K·px) = +K·px | increases | Camera pans right, face moves left ✓ |
| Face left of center | −px | +K·px | −(+K·px) = −K·px | decreases | Camera pans left, face moves right ✓ |

**Pan is already correctly negated. Tilt is not negated — that is the bug.**

**Correct final code:**

```python
korekta_pan  = -self.pid_pan(blad_pan)    # negated — already correct
korekta_tilt = -self.pid_tilt(blad_tilt)  # must negate — FIX HERE
```

**Expected behavior after fix:**
- Face right of center → camera pans right until face is centered
- Face below center → camera tilts down until face is centered
- No runaway in either axis
- System converges to face-centered steady state

**Confidence:** HIGH — derived from first principles + verified simple_pid formula
(error = setpoint − input = 0 − blad = −blad)

---

## Bug 2: Tilt Axis Does Not Move During TRACKING

### Diagnosis

The tilt axis has two failure modes. The sign error (Bug 1) causes it to apply
corrections in the wrong direction, but the reason it "doesn't move" visually may
be a combination of:

1. **Sign error causes immediate saturation at tilt limit:** If the tilt servo starts
   at 0° and the runaway correction drives it toward the 30° limit in the first few
   frames, it hits `TILT_LIMIT_MAX = 30` and `set_angles()` clamps it. The servo
   is at max travel. All subsequent corrections are clamped. HUD shows tilt
   angle ≠ 0 but servo appears frozen at limit.

2. **PID integral windup at saturation:** Once clamped, I-term accumulates. Even
   after the face moves, the I-term must unwind before the output reverses. This
   creates the appearance of the tilt axis being unresponsive.

3. **Bug exclusion:** The `set_angles()` call at line 268 receives `nowy_tilt`.
   Confirm `nowy_tilt` is not always 0. Looking at the code: `self.hardware.tilt_angle`
   is initialized to 0.0 (hardware.py line 22). `korekta_tilt = self.pid_tilt(blad_tilt)`
   returns a very small number (Kp=0.05, blad_tilt≤240 px → max output clamped to
   10.0). So `nowy_tilt = 0 + small_positive_correction`. This reaches `set_angles()`.
   The tilt servo does receive the command.

**Root cause:** The sign bug (Bug 1 above) causes the tilt correction to push
the servo away from neutral and into the soft limit within the first few TRACKING
frames. Once at the limit, tilt appears frozen. The fix for Bug 1 also resolves
Bug 2.

**Verification method:** After applying Bug 1 fix, enable verbose logging of
`nowy_tilt` and `self.hardware.tilt_angle` on every tick. Confirm tilt angle
oscillates around 0° when face is centered.

**Expected behavior after fix:**
- Tilt angle changes on every tick where face centroid y ≠ frame center y
- Tilt angle converges toward 0° when face is vertically centered
- HUD shows `Tilt:+XX.X` varying in real time

**Confidence:** HIGH — mechanistic explanation consistent with observed symptoms

---

## Bug 3: Blue Tint on Camera Image (AWB with IMX219)

### Diagnosis

The IMX219 (Pi Camera v2) blue tint has two common root causes:

1. **YUV420→BGR conversion ambiguity:** OpenCV's `cv2.COLOR_YUV420p2BGR` is correct
   for the standard YUV420 planar layout Picamera2 delivers. If the layout is
   YUV420sp (semi-planar), the wrong constant causes a color cast. Verify by
   checking actual frame shape and testing `COLOR_YUV420sp2BGR`.

2. **AWB not converging before first frames are delivered:** Picamera2 starts AWB
   asynchronously. The first 10-30 frames may have incorrect white balance while
   the algorithm converges, appearing blue under indoor lighting.

3. **AWB settled on wrong color temperature:** Indoor incandescent/fluorescent
   lighting can fool the auto algorithm, leaving a persistent blue cast.

### Fix: Freeze AWB After Convergence

The authoritative pattern (confirmed from Picamera2 GitHub discussion #592 and
the official Picamera2 manual approach) is:

```python
# Step 1: Start camera with AWB enabled (default)
picam2.configure(video_config)
picam2.start()

# Step 2: Wait for AWB to converge (2 seconds is typical)
time.sleep(2.0)

# Step 3: Read the gains AWB settled on
metadata = picam2.capture_metadata()
colour_gains = metadata["ColourGains"]

# Step 4: Lock those gains (automatically disables AWB)
picam2.set_controls({"ColourGains": colour_gains})
```

This approach is preferable to hardcoded values because it adapts to the actual
lighting environment at startup.

**Alternative: Explicit AWB mode selection**

If the freeze approach is insufficient, force a specific AWB preset before locking:

```python
import libcamera
# Use indoor (tungsten/fluorescent) preset if camera is used indoors
picam2.set_controls({"AwbMode": libcamera.controls.AwbModeEnum.Indoor})
time.sleep(1.0)
metadata = picam2.capture_metadata()
picam2.set_controls({"ColourGains": metadata["ColourGains"]})
```

Available AwbModeEnum values: `Auto`, `Incandescent`, `Tungsten`, `Fluorescent`,
`Indoor`, `Daylight`, `Cloudy`.

**Alternative: Hardcoded gains for known environment**

If lighting is constant and the freeze approach is impractical, typical IMX219
gains for indoor incandescent light are approximately `(1.5, 1.8)` (red, blue).
These must be empirically determined for the specific installation. Use
`capture_metadata()` once to discover the correct values, then hard-code them.

### Important API constraint

`set_controls()` must be called **after** `configure()` but may be called either
before or after `start()`. Calling it before `start()` risks being wiped by
`configure()` if called again. Calling it after `start()` + sleep is the
recommended sequence.

The control name is `"ColourGains"` (capital C, capital G). The older name
`"Colourgains"` causes a RuntimeError on current libcamera versions.

**Expected behavior after fix:**
- Neutral white rendering of skin tones and white backgrounds
- Color stable across frames (no frame-to-frame AWB hunting)
- Blue cast eliminated within 2 seconds of startup

**Confidence:** MEDIUM — AWB freeze pattern confirmed via multiple Picamera2
GitHub discussions and official manual approach. YUV conversion variant is LOW
confidence (depends on actual frame layout, needs empirical verification on RPi4).

---

## Bug 4: Scanning Transition Needs Smooth PID Reset (Anti-Windup)

### Diagnosis

When TRACKING → TARGET_LOST → SCANNING transition occurs, `_przejdz_do()` calls
`pid_pan.reset()` and `pid_tilt.reset()`. This is the correct approach.

However, two issues remain:

1. **Anti-windup during TRACKING saturation:** If the servo hits a soft limit while
   tracking (e.g., pan reaches ±60°), `set_angles()` clamps the output but the PID
   I-term continues accumulating. When the face reappears, the wound-up I-term
   produces a large initial correction that can cause a jerk or overshoot.

   **Fix:** At the point of I-term windup, the simple_pid library handles this
   through `output_limits`. The library **does** clamp the integral term to the
   output limits (verified from source). This is sufficient anti-windup for this
   system. No additional code is needed, but `PID_OUTPUT_LIMIT = 10.0` must remain
   set.

2. **Abrupt scan position after transition:** When TRACKING ends, the servo stays
   at the last tracked position. The sinusoidal scan resumes from whatever the
   formula gives for `t = time.time()` — not from the servo's current position.
   This causes a step change (potential jerk) when scan resumes.

   **Fix (correct behavior):** On entry to SCANNING, the servo should be at the
   scan's natural position for the current time `t`. If the scan formula gives
   `pan = 45°` at `t=now` but the servo is at `pan = -10°`, a 55° step occurs.

   **Required change:** After `pid.reset()`, add a brief `smooth_move_to()` to
   the initial scan position, OR shift the scan phase offset so `sin(2π·f·t + φ)`
   evaluates to the current servo position, eliminating the jump. The simplest fix
   is to call `smooth_move_to(current_scan_position, 0.0)` with a fast step
   (SERVO_STEP=5.0) before resuming sinusoidal updates.

   Alternatively, replace the absolute time-based sinusoid with a phase-continuous
   sinusoid that anchors at the current position when SCANNING starts.

   **Recommended approach:** On SCANNING entry, set `_scan_phase_offset` such that
   `SCAN_AMPLITUDE × sin(2π·f·t + offset) = current_pan_angle` at `t = now`.
   Solve: `offset = arcsin(pan_angle / SCAN_AMPLITUDE) − 2π·f·t`.

   ```python
   def _inicjuj_faze_skanowania(self) -> None:
       """Wyznacza offset fazy sinusoidy tak by zacząć od bieżącej pozycji."""
       t = time.time()
       ratio = max(-1.0, min(1.0, self.hardware.pan_angle / SCAN_AMPLITUDE))
       self._scan_phase_offset = math.asin(ratio) - 2.0 * math.pi * SCAN_FREQUENCY * t

   def _skanuj(self) -> None:
       t = time.time()
       pan = SCAN_AMPLITUDE * math.sin(2.0 * math.pi * SCAN_FREQUENCY * t + self._scan_phase_offset)
       self.hardware.set_angles(pan, 0.0)
   ```

   This eliminates the position jump entirely without any blocking movement.

**Expected behavior after fix:**
- SCANNING resumes smoothly from last tracking position — no servo jerk
- PID I-term properly bounded by output_limits during tracking (already working)
- No windup-induced overshoot when TRACKING resumes after a brief face loss

**Confidence:** HIGH for anti-windup (simple_pid clamps I-term to output_limits,
verified from source). MEDIUM for phase-continuity fix (math is correct, but
the `arcsin` branch choice may need testing when `pan_angle > SCAN_AMPLITUDE`).

---

## Table Stakes — Required Fixes

| Fix | Changed Lines | Expected Behavior | Test Method |
|-----|--------------|-------------------|-------------|
| Tilt sign inversion | `korekta_tilt = -self.pid_tilt(blad_tilt)` | Face below center → tilt increases; converges to center | Hold face below camera center; observe tilt HUD increasing |
| AWB freeze after convergence | `Picamera2Stream.start()` — add 2s sleep + metadata read + `set_controls` | Neutral colors, no blue cast | Visual check of displayed frame; skin tones should look natural |
| Scan phase continuity | Add `_scan_phase_offset` to `MaszynaStanow._skanuj()` and `_inicjuj_faze_skanowania()` | No jerk when SCANNING resumes | Observe servo physically; no sudden jump at TRACKING→SCANNING transition |

---

## Anti-Features for This Milestone

| Anti-Feature | Why Exclude |
|--------------|-------------|
| Replacing simple_pid with custom PID | simple_pid is correct and tested; bugs are in sign convention, not the library |
| Changing Kp/Ki/Kd values | Gains are empirically validated; sign bugs mimic gain problems but are not |
| Adding Kalman filter | Locked architectural decision; not needed for these bug fixes |
| Switching from HAAR to deep learning detection | Out of scope; detection layer is not the bug source |
| Adding dlib identity verification | Anti-feature from v1.6 still applies; no change needed |
| Rewriting MaszynaStanow | State transitions are correct; only _sledz() and _skanuj() need changes |

---

## Feature Dependencies for Bug Fixes

```
Bug 1 fix (tilt sign)
  └─→ Bug 2 resolves automatically (tilt no longer saturates at limit)

Bug 3 fix (AWB)
  └─→ Independent of Bug 1/2; purely camera initialization

Bug 4 fix (scan continuity)
  └─→ Requires Bug 1 fix first (scan from wrong position makes continuity test ambiguous)
  └─→ Requires _scan_phase_offset field added to MaszynaStanow.__init__
```

**Implementation order:**
1. Bug 1 + 2 (single line change in `_sledz()`)
2. Bug 3 (AWB freeze in `Picamera2Stream.start()`)
3. Bug 4 (scan phase offset — new field + two method changes)

---

## Sign Convention Reference Card

For future maintenance — canonical sign conventions for this system:

```
PIXEL COORDINATES (OpenCV):
  origin = top-left corner of frame
  x increases right
  y increases down

ERROR DEFINITIONS (test_tracker.py _sledz()):
  blad_pan  = face_center_x − frame_center_x   (+  = face is RIGHT of center)
  blad_tilt = face_center_y − frame_center_y   (+  = face is BELOW center)

SIMPLE_PID OUTPUT (setpoint=0, positive gains):
  pid(error) = Kp × (0 − error) = −Kp × error
  → positive error  → negative PID output
  → negative error  → positive PID output

HARDWARE (empirically verified, PROJECT.md):
  pan_angle increases  → servo rotates RIGHT → face moves LEFT in frame
  tilt_angle increases → servo rotates DOWN  → face moves UP in frame

REQUIRED CORRECTION DIRECTION:
  face RIGHT (+blad_pan)  → pan_angle must INCREASE  → korekta_pan must be POSITIVE
  face BELOW (+blad_tilt) → tilt_angle must INCREASE → korekta_tilt must be POSITIVE

DERIVATION:
  korekta_pan  = −pid_pan(blad_pan)  = −(−Kp×blad_pan) = +Kp×blad_pan  ✓  (positive when face right)
  korekta_tilt = −pid_tilt(blad_tilt) = −(−Kp×blad_tilt) = +Kp×blad_tilt ✓  (positive when face below)

CONCLUSION: Both axes require negation of PID output.
  korekta_pan  = -self.pid_pan(blad_pan)    ← already in code, CORRECT
  korekta_tilt = -self.pid_tilt(blad_tilt)  ← MISSING negation, BUG
```

---

## Sources

- [Pan/Tilt PID sign convention — PyImageSearch tutorial](https://pyimagesearch.com/2019/04/01/pan-tilt-face-tracking-with-a-raspberry-pi-and-opencv/)
  Uses `panAngle = -1 * pan.value` and `tiltAngle = -1 * tlt.value` (MEDIUM confidence)
- [simple-pid source code — m-lundberg/simple-pid](https://github.com/m-lundberg/simple-pid/blob/master/simple_pid/pid.py)
  `error = setpoint − input_`, integral clamped to output_limits (HIGH confidence — official source)
- [Picamera2 AWB lock discussion — GitHub #592](https://github.com/raspberrypi/picamera2/discussions/592)
  `set_controls({"ColourGains": gains})` after `configure()` + sleep (HIGH confidence — maintainer response)
- [Picamera2 ColourGains API — GitHub #168](https://github.com/raspberrypi/picamera2/issues/168)
  `ColourGains` control name, (red, blue) tuple format, range 0.0–32.0 (HIGH confidence)
- [Picamera2 AWB mode fix — GitHub #803](https://github.com/raspberrypi/picamera2/issues/803)
  AwbMode not always effective; freezing ColourGains is more reliable (MEDIUM confidence)
- [IMX219 blue tint — Arducam forum](https://forum.arducam.com/t/imx219-camera-is-appearing-blue/5961)
  Blue tint on IMX219 is a known issue; AWB mode selection or gain lock resolves it (MEDIUM confidence)
- `src/hardware.py` — `PanTiltSystem` sign conventions, `pan_angle`/`tilt_angle` state
  (HIGH confidence — project source, empirically validated per PROJECT.md)
- `src/modes/test_tracker.py` — current buggy implementation, lines 258–268
  (HIGH confidence — source under analysis)
- `.planning/PROJECT.md` — hardware mounting convention: pan+=right, tilt+=down
  (HIGH confidence — empirically confirmed entry)
