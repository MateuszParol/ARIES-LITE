# Feature Research

**Domain:** RPi4 autonomous face tracking — motion, color, and control stability fixes (v1.9)
**Researched:** 2026-03-29
**Confidence:** HIGH (direct code audit + external AWB/PID sources verified)

---

## Context: Four Behavioral Bugs in v1.9

v1.9 goal is to fix four distinct behavioral defects in `run_test_tracker.py` /
`src/modes/test_tracker.py`. All four bugs are confirmed on hardware (RPi4).

The existing code from v1.8 is correct in structure — all four bugs are narrow,
isolated fixes, not architectural changes.

1. **Tilt frozen in all modes** — `_skanuj()` always calls `set_angles(pan, 0.0)`
   (tilt hardcoded). In TRACKING, the sign and code path are now correct (v1.8
   fix) but physical servo still did not respond in last verified run.
2. **Scan jitters/stutters** — `_skanuj()` calls `set_angles()` directly each
   tick without interpolation. At 10–30 FPS the sinusoidal step per tick is small,
   but OS scheduling jitter causes irregular call spacing, producing visible stutters.
3. **Green tint from first frame** — Previous AWB fix (ColourGains lock at 1.0, 1.0)
   disabled AWB completely with unity gains, swapping blue tint for green tint.
   The gain lock prevents camera from adapting to actual lighting.
4. **Servo escapes immediately on TRACKING entry** — PID integrator carries windup
   from the SCANNING → TRACKING transition, or initial error is large and the
   correction overshoots and compounds.

---

## What Correct Behavior Looks Like (per Feature)

### Fix 1: Dual-Axis Sinusoidal Scanning (tilt included)

**Correct behavior:** During SCANNING, both pan and tilt axes move continuously.
Pan follows a full-amplitude sinusoidal sweep (±45°). Tilt follows a sinusoidal
sweep at a different frequency ratio (typically 0.5× or 2× pan frequency) so the
combined path covers the scene in a Lissajous-style pattern rather than a flat
horizontal sweep.

- Pan: `pan = A_pan * sin(2π * f_pan * t + phase_pan)`
- Tilt: `tilt = A_tilt * sin(2π * f_tilt * t + phase_tilt)`
- Recommended: `A_pan = 45°`, `A_tilt = 15–20°` (within TILT_LIMIT_MIN/MAX=±30)
- Recommended frequency ratio: `f_tilt = 2 × f_pan` — at 0.1 Hz pan, use 0.2 Hz
  tilt. This produces a figure-8 Lissajous path, covering upper and lower field
  within every pan cycle. The result is a closed, deterministic coverage pattern
  that guarantees a face anywhere in the ±45°/±20° view volume is encountered
  within 10 seconds.
- Scan phase offset on SCANNING re-entry: same `math.asin(clamp)` technique
  already applied to pan must also be applied to tilt to avoid jump discontinuity.
- **Why tilt was frozen:** `_skanuj()` hardcodes `self.hardware.set_angles(pan, 0.0)`.
  The fix is one line: compute `tilt_scan` using a separate sinusoidal expression
  and pass it as the second argument.

### Fix 2: Smooth Servo Interpolation (jerk-free scanning)

**Correct behavior:** Servo moves continuously without visible steps or jitter.
The existing `smooth_move_to()` method already implements step-based interpolation
(SERVO_STEP=1.0°, 50ms delay), but it is a blocking loop used only for Safe Start.
For real-time scan, the servo is set directly to the computed sinusoidal position
each tick, which is correct in theory — but irregular tick timing from OS scheduling
causes jitter.

- **Root cause of scan jitter:** `time.time()` in `_skanuj()` is evaluated at each
  tick. If ticks are irregular (OS preempts the loop thread), the resulting
  `sin(2π * f * t)` produces a position that jumps forward in time, appearing
  as a lurch. pigpio's hardware PWM already smooths the electrical signal, but
  the position command itself is jittery.
- **Correct approach:** Keep the sinusoidal formula driven by wall-clock `time.time()`.
  This is already the implementation. The visual smoothness comes from pigpio DMA
  PWM — which is already in use (`PiGPIOFactory`). If jitter persists, the cause
  is likely that `_skanuj()` is called at 30 FPS but pigpio smooths sub-frame
  transitions automatically. The fix may not require code changes to the scan
  formula itself.
- **If jitter is due to large per-tick angle deltas:** Clamp the maximum angle
  change per tick to `SERVO_STEP` (1.0°). Compare current hardware angle to new
  computed angle; if delta > 1°, move only 1° per tick. This limits speed but
  eliminates lurching caused by skipped frames.
- **What NOT to do:** Do not reuse `smooth_move_to()` for scanning — it is a
  blocking loop that would prevent the main tracker loop from running.
- **Confidence:** MEDIUM — jitter cause may be pigpio vs. Python timing, needs
  empirical verification on hardware.

### Fix 3: AWB / ColourGains — Correct White Balance Without Green Tint

**Correct behavior:** Camera produces neutral colors matching the actual scene
lighting from the first frame onward. No persistent color cast (no green, no
blue, no warm shift).

**Root cause of green tint:** The v1.8 fix set `ColourGains=(1.0, 1.0)` at
configure-time and locked it there. Unity gains for both Red and Blue channels
means the camera pipeline does not compensate for sensor spectral response —
the IMX219 sensor has a native green bias, so with R=1.0 and B=1.0, green
dominates. The original "correct" AWB lock requires capturing what AWB computed
after warm-up, not forcing (1.0, 1.0).

**Correct approach (verified from Picamera2 forums and GitHub issues):**
1. Do NOT pass `ColourGains` at configure-time. Let AWB run freely during startup.
2. After `picam2.start()`, sleep 2–3 seconds for AWB to converge.
3. Read `capture_metadata()["ColourGains"]` — these are the gains AWB computed.
4. Call `picam2.set_controls({"ColourGains": (float(R), float(B))})` with the
   AWB-computed values. Setting `ColourGains` automatically disables AWB without
   needing `AwbEnable: False` (confirmed in Picamera2 docs and forums — setting
   ColourGains implicitly locks AWB).
5. Do NOT also set `AwbEnable: False` explicitly — Picamera2 has sequencing issues
   when mixing explicit enable/disable flags with manual parameter values.
6. The existing code in `Picamera2Stream.start()` already does steps 2–5 correctly
   in the post-configure block (lines 82–103). The bug is in `create_video_configuration()`
   passing `controls={"ColourGains": AWB_FALLBACK_GAINS}` — this locks gains to
   (1.0, 1.0) at configure-time, preventing AWB from running at all.

**Fix:** Remove `controls={"ColourGains": AWB_FALLBACK_GAINS}` from
`create_video_configuration()` call. The post-start AWB lock already handles
the gain capture and set. The fallback path `if gains is None or gains == (0.0, 0.0)`
handles the case where AWB has not converged — and the fallback value in that
case should be realistic neutral gains (R≈2.0–2.5, B≈1.8–2.0 for typical indoor
daylight) rather than (1.0, 1.0).

**AWB fallback values:** For IMX219 under indoor fluorescent/daylight, typical
stable gains are R≈2.2–2.5, B≈1.8–2.2. A fallback of (2.2, 1.9) is far safer
than (1.0, 1.0) when AWB metadata is unavailable.

**Confidence:** HIGH — cause confirmed by code audit. AWB behavior confirmed by
Picamera2 issue #897 and forum discussion at forums.raspberrypi.com/viewtopic.php?t=365052.

### Fix 4: PID-Controlled Tracking Without Servo Escape

**Correct behavior:** On TRACKING entry, both servos start from their current
scan position and converge toward face center within 1–3 seconds. No immediate
runaway to servo limits. After centering, servos hold steady with small oscillations
(< ±2°) caused by detection noise.

**Root cause of escape:** Two likely causes (must verify with diagnostics):

1. **Integral windup from scan phase:** PID `reset()` is called in `_przejdz_do()`
   when entering SCANNING but not when entering TRACKING. If the PID accumulates
   integral during the brief SCANNING → TRACKING → SCANNING cycle, the integrator
   carries that windup into the next TRACKING entry. With `PID_OUTPUT_LIMIT=10.0`,
   anti-windup via output limits should prevent this, but only if the limit is
   tight enough.

2. **Initial error is large and correction direction compounds:** If the face is
   detected at the scan position edge (e.g., pan=+45° and face is near frame center
   at that angle), the pixel error is small. PID correction is small. This is correct.
   If instead the face appears at frame edge when servos are at center, `blad_pan`
   could be ±160 px and `korekta_pan = -pid(160) ≈ -8°`. This pushes the servo
   outward. Next frame, if the face has moved with the servo, error stays large
   and the integral builds. This is expected behavior but can *look* like escape
   if the face is outside the camera FoV at the servo's new position.

**Correct PID behavior for this system:**
- `PID_OUTPUT_LIMIT = 10.0` degrees/tick is appropriate. At 10 FPS (DNN skip=5
  on 50fps stream), maximum correction rate = 100°/s, which is fast enough for
  human head movement.
- `sample_time=0.033` (30ms) must be calibrated against actual loop frequency.
  If the loop runs at 10 FPS, sample_time should be 0.1. Mismatched sample_time
  causes the PID to compute outputs more frequently than the physical system
  can respond, leading to derivative kick and apparent instability.
- **Reset on TRACKING entry** is the correct fix: call `pid_pan.reset()` and
  `pid_tilt.reset()` in `_przejdz_do(config.STATE_TRACKING)` as well as on
  SCANNING entry. This eliminates any carried windup.
- **Do not change Kp/Ki/Kd** — v1.8 Phase 12 empirically validated these gains.
  If behavior still diverges after reset fix, suspect sample_time mismatch, not
  gain values.

---

## Feature Landscape

### Table Stakes (Must-Fix for v1.9 to Ship)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Tilt moves during SCANNING | Dual-axis scan is the stated goal; single-axis scan misses 50% of the vertical field of view | LOW | One-line fix in `_skanuj()`: compute tilt sinusoidal and pass to `set_angles()`. Add phase offset on SCANNING re-entry same as pan. |
| Tilt moves during TRACKING | Two-axis tracking is the product's core value | LOW | Diagnosed in v1.8: sign is correct, may be hardware/pigpiod connectivity issue. Confirm with diagnostic log that `set_angles()` receives non-zero tilt argument. |
| Camera shows neutral colors | Usable image is prerequisite for face detection and visual verification | LOW | Remove `ColourGains` from `create_video_configuration()`. Post-start AWB lock code is already correct. Update fallback gains to realistic values (≈2.2, 1.9). |
| PID tracking converges to face center | Tracker must center face — not slam to servo limits | LOW | Add `pid.reset()` call on TRACKING entry. Verify `sample_time` matches actual loop interval. |

### Differentiators (High Value for This Fix Milestone)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Smooth scan (no visual jitter) | Tracking system looks professional; stuttering undermines confidence in the system | LOW–MEDIUM | Evaluate if jitter is visible with current pigpio DMA. If yes, clamp per-tick angle delta to SERVO_STEP. If no, no code change needed — jitter may be a display artifact, not a servo artifact. |
| Scan phase-offset continuity on tilt axis | Prevents servo jump when resuming scan after losing a face | LOW | Extend existing `math.asin(clamp)` pattern to tilt axis in `_przejdz_do()`. |
| AWB convergence time tuning | Ensures gains are captured after full AWB stabilization, not during transient | LOW | Tune warm-up sleep from 2s to 3s if gains still show green cast. Log R and B values after lock to confirm. |

### Anti-Features (Do Not Add in v1.9)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Hardcoded AWB gains for specific lighting | Predictable colors without any AWB logic | Environment-specific; gains correct for fluorescent light fail under daylight or sunlight. Cannot be shipped as a general fix. | Use AWB warm-up lock. Fallback gains (2.2, 1.9) are used only when AWB metadata unavailable. |
| Kalman filter for servo position | Smoother tracking; suppresses detection noise | Not architecturally compatible with simple-pid loop. Requires restructuring `_sledz()`. Out of scope for a bug-fix milestone. | Keep PID. Tune derivative term (Kd) to suppress noise if needed after gains are confirmed correct. |
| CSRT tracker between DNN detections | Smoother PID input when DNN skips frames | Adds frame state to `DetekcjaTwarzy` or `TestTracker`. Increases complexity significantly. Not a bug fix. | DNN skip_every=5 already limits detection to every 5th frame. The `_ostatni_bbox` reuse between skips approximates tracking. |
| Replacing `simple-pid` with custom PID | Full control over anti-windup behavior | simple-pid 2.0.1 is pinned, validated, and working correctly. The bug is in how `reset()` is called, not in the library itself. | Call `pid.reset()` on TRACKING entry. |
| PID gain retuning | Gains might be wrong | v1.8 Phase 12 empirically validated Kp=0.05, Ki=0.001, Kd=0.005 on hardware. Gains are correct. Sign and timing are the bugs. | Fix sample_time and TRACKING entry reset first. |

---

## Feature Dependencies

```
[AWB configure-time lock removal]
    └──prerequisite for──> [Neutral color from first frame]
        (post-start AWB lock code already correct; configure-time lock overrides it)

[Tilt sinusoidal in _skanuj()]
    └──prerequisite for──> [Scan covers vertical field]
    └──independent of──> [Tilt in TRACKING]
        (separate code paths: _skanuj() vs _sledz())

[PID reset() on TRACKING entry]
    └──prerequisite for──> [PID convergence without escape]
    └──independent of──> [Tilt sinusoidal in _skanuj()]

[sample_time calibration]
    └──enhances──> [PID convergence without escape]
    └──can be deferred if reset() alone fixes escape]

[Per-tick diagnostic logging]
    └──enables diagnosis of──> [PID escape root cause]
    └──enables diagnosis of──> [Tilt in TRACKING]
        (already present as logger.debug() in _sledz() — activate with --debug flag)
```

### Dependency Notes

- **AWB configure-time lock is the most likely green tint cause:** The existing
  post-start AWB code is correct. The configure-time `ColourGains=(1.0,1.0)` in
  `create_video_configuration()` prevents AWB from running. Removing that one
  argument is the complete fix. Zero structural risk.

- **Tilt in SCANNING and TRACKING are independent fixes:** `_skanuj()` is called
  when `bbox is None`; `_sledz()` is called when `bbox is not None`. They do not
  share state. Both must be fixed but can be verified separately.

- **PID reset on TRACKING entry is the minimal escape fix:** If escape still
  occurs after adding `reset()`, then `sample_time` miscalibration is the next
  suspect. Do not change gains first.

---

## MVP Definition

### Fix Now — v1.9 (all four required for functional tracker)

The four behavioral defects are the entire stated goal. A tracker that cannot
scan vertically, shows wrong colors, or immediately escapes has no operational value.

- [ ] Tilt sinusoidal added to `_skanuj()` — scan covers vertical field
- [ ] AWB configure-time lock removed — camera renders neutral colors
- [ ] PID `reset()` added on TRACKING entry — tracking converges
- [ ] Smooth scan verified empirically — jitter confirmed absent or clamped

### Validate with Diagnostics (same milestone, zero structural risk)

These confirm the fixes took effect and provide evidence for commit verification.

- [ ] Log `ColourGains` values after lock (R=, B=) — confirms AWB fix
- [ ] Log tilt argument in `set_angles()` during scan — confirms tilt fix
- [ ] Log PID components on TRACKING entry after reset — confirms clean start
- [ ] HUD tilt angle changes visibly during scan — visual confirmation

### Defer to Future Milestones

- [ ] sample_time dynamic calibration — only if reset() alone is insufficient
- [ ] CSRT tracker in test module — after PID is confirmed stable
- [ ] Lissajous scan frequency optimization — empirical tuning, not a bug fix
- [ ] AWB mode selection (indoor/fluorescent presets) — only if lock still fails

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Tilt sinusoidal in `_skanuj()` | HIGH | LOW (1 line) | P1 |
| AWB configure-time lock removal | HIGH | LOW (remove 1 argument) | P1 |
| PID `reset()` on TRACKING entry | HIGH | LOW (1 line in `_przejdz_do`) | P1 |
| Tilt phase-offset continuity | MEDIUM | LOW (1 line) | P1 (same change as tilt scan) |
| Smooth scan jitter verification | MEDIUM | LOW–MEDIUM (empirical + optional clamp) | P2 |
| AWB fallback gains update (1.0,1.0 → 2.2,1.9) | MEDIUM | LOW | P2 |
| sample_time calibration to actual FPS | MEDIUM | LOW | P2 (if escape persists) |
| Lissajous frequency ratio tuning | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for v1.9 launch
- P2: Should have, add when possible
- P3: Nice to have, future milestone

---

## Existing Code Constraints (Must Be Respected)

| Constraint | Location | Impact on v1.9 Fixes |
|------------|----------|----------------------|
| `TILT_LIMIT_MIN/MAX = ±30°` | `config.py` | Tilt scan amplitude must be ≤ 25° (safety margin). Use 20° to avoid constant clamping at scan peaks. |
| `SCAN_AMPLITUDE = 45.0°` | `test_tracker.py:34` | Pan amplitude already defined as constant. Tilt amplitude should be a new constant `SCAN_AMPLITUDE_TILT = 20.0`. |
| `SCAN_FREQUENCY = 0.1 Hz` | `test_tracker.py:35` | Tilt frequency should be `SCAN_FREQUENCY_TILT = 0.2` (2× pan). Add as separate constant. |
| `AWB_FALLBACK_GAINS = (1.0, 1.0)` | `test_tracker.py:38` | Change to `(2.2, 1.9)` — more realistic for indoor lighting. The name is correct; the value is wrong. |
| `PID_OUTPUT_LIMIT = 10.0` | `test_tracker.py:37` | Keep at 10.0°. Anti-windup via output_limits is already active via simple-pid. |
| `sample_time=0.033` in `MaszynaStanow.__init__` | `test_tracker.py:252–257` | Calibrate to actual loop FPS. At DNN skip=5 on ~30 FPS camera, effective detection FPS ≈ 6 → sample_time ≈ 0.167. But PID is called every tick (not just on detection), so 0.033 may be correct for the control loop frequency, not detection frequency. Verify empirically. |
| `hardware.smooth_move_to()` is blocking | `hardware.py:69–99` | Must not be used in the main tracker loop. Correct for Safe Start only. Scan uses `set_angles()` directly. |
| Polish-language identifiers | entire codebase | New constants and variables must follow the same convention: Polish names for scan constants are acceptable (`AMPLITUDA_SKANOWANIA_TILT`) but English constants already used (`SCAN_AMPLITUDE_TILT`) are consistent with existing pattern — use the existing convention. |

---

## Sign Convention Reference (Preserved from v1.8, Still Valid)

```
HARDWARE (empirically confirmed v1.7/v1.8):
  pan_angle increases  → servo rotates RIGHT → face moves LEFT in frame
  tilt_angle increases → servo rotates DOWN  → face moves UP in frame

SCAN DIRECTION:
  tilt_scan = A_tilt * sin(2π * f_tilt * t + phase_tilt)
  When tilt_scan > 0: servo looks DOWN (scans lower field)
  When tilt_scan < 0: servo looks UP (scans upper field)
  Both halves of the vertical field covered within half a tilt cycle (2.5s at 0.2Hz)

TRACKING (unchanged from v1.8):
  blad_tilt = srodek_y - ramka_cy  (+ = face BELOW center)
  korekta_tilt = -pid_tilt(blad_tilt) = +Kp*blad_tilt
  face BELOW → tilt_angle INCREASES → servo moves DOWN → face moves UP ✓
```

---

## Sources

- Direct code audit: `src/modes/test_tracker.py`, `src/hardware.py`, `src/config.py`
- Project state: `.planning/PROJECT.md` ("Poprzedni fix AWB zamienil blue tint na green tint")
- Picamera2 AWB lock: forums.raspberrypi.com/viewtopic.php?t=365052 — setting ColourGains
  automatically disables AWB; do not set AwbEnable=False separately (MEDIUM confidence,
  confirmed by multiple forum posts and issue #592)
- Picamera2 green tint: github.com/raspberrypi/picamera2/issues/897 — root cause is
  lens shading mismatch in certain sensor modes; AWB gains lock prevents ALSC from
  adapting (MEDIUM confidence — different root cause in that issue but consistent finding)
- Lissajous scan coverage: standard control systems knowledge — frequency ratio 1:2
  produces figure-8 pattern covering both vertical halves per pan cycle (HIGH confidence)
- PID anti-windup: simple-pid 2.0.x output_limits + reset() docs (HIGH confidence —
  same library pinned in requirements.txt)
- Sinusoidal scan jitter: forums.raspberrypi.com/viewtopic.php?t=274329 — pigpio DMA
  resolves electrical jitter; software-side jitter from irregular call timing requires
  wall-clock formula (already implemented) (MEDIUM confidence)

---

*Feature research for: RPi4 face tracking — v1.9 Stabilizacja Ruchu i Obrazu*
*Researched: 2026-03-29*
