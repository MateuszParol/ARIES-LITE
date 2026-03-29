# Pitfalls Research — v1.9 Stabilizacja Ruchu i Obrazu

**Domain:** Fixing servo tilt dead axis, jerky servo motion, AWB green tint, and PID tracking escape in an existing RPi4 pan-tilt face tracker (Picamera2 + pigpio + simple_pid + OpenCV DNN)
**Researched:** 2026-03-29
**Confidence:** HIGH (code-derived pitfalls from direct analysis of src/) / MEDIUM (AWB ISP pipeline internals, servo pulse-width mechanics)

**Scope:** v1.9 milestone — adds four targeted fixes to a working but misbehaving system. The prior system (v1.8) has DNN detection validated, PID structure validated, and AWB lock code present. The bugs are integration and sequencing failures, not architectural. This document focuses entirely on common mistakes when *adding* these fixes to the existing codebase.

---

## Critical Pitfalls

### Pitfall 1: Tilt Servo Wired or Commanded But Scan Hardcodes Tilt to Zero

**What goes wrong:**
`_skanuj()` in `MaszynaStanow` calls `self.hardware.set_angles(pan, 0.0)` with a literal `0.0` for tilt. If tilt servo wiring or config is wrong, the SCANNING state will never expose the bug because it always writes zero. The developer tests with a face in frame, enters TRACKING, and sees tilt move in `_sledz()` — but only if TRACKING is actually reached. If tilt is frozen at zero the developer may blame `_sledz()` or the PID sign when the problem is actually that SCANNING masks the tilt path entirely.

The deeper trap: the HUD reads `self.maszyna.hardware.tilt_angle` which is a software float updated unconditionally in `set_angles()`. Tilt shows `0.0` during SCANNING not because the servo is broken but because the scan formula writes `0.0`. This is correct behavior, not a bug. Misreading the HUD here causes false diagnosis.

**Why it happens:**
Developers check the HUD to assess servo state. During SCANNING, tilt is intentionally zero. If TRACKING never triggers (face detection issue, short timeout, etc.), tilt is *always* zero. The developer concludes tilt is broken when it may be fine.

**How to avoid:**
Before declaring tilt broken, issue a direct `set_angles(0.0, 15.0)` call at startup in `inicjalizuj()` (or a temporary test command), confirm the physical servo moves, then revert. This isolates the hardware path from the state machine. Use `smooth_move_to(0, 20)` then `smooth_move_to(0, 0)` — if tilt physically moves, the servo and wiring are functional.

**Warning signs:**
- Tilt shows `0.0` in HUD during SCANNING (expected — not a bug)
- Tilt shows `0.0` in HUD during TRACKING with face clearly below/above center (actual bug)
- Clamp warnings for tilt never appear in logs despite expected large corrections
- `pid_tilt.components` shows non-zero P/I/D but `nowy_tilt` equals `0.0 + korekta_tilt` where `korekta_tilt` is very small

**Phase to address:**
Phase 1 (tilt fix) — begin with a direct hardware test call before any state machine analysis.

---

### Pitfall 2: Tilt Sign Fixed But Axis Inverted Relative to Physical Mount

**What goes wrong:**
The current code applies double negation to both axes in `_sledz()`:
```python
korekta_pan = -self.pid_pan(blad_pan)
korekta_tilt = -self.pid_tilt(blad_tilt)  # negacja — oś tilt działa jak pan
```
The comment claims "oś tilt działa jak pan" — this was the v1.7 finding. If the physical mount orientation changed between v1.7 and v1.9 testing (camera flipped, bracket reversed), the sign that worked before will cause runaway in the opposite direction.

The consequence: tilt detects face below center (`blad_tilt > 0`), PID outputs positive correction, negation gives negative, system moves tilt *upward* instead of downward, face moves further from center, error grows, servo hits limit.

**Why it happens:**
Physical mount conventions are not captured in code — only "negation was applied." If the mount changes (or the v1.7 observation was wrong), there is no in-code record of *why* the negation is correct. "Oś tilt działa jak pan" is an undocumented empirical claim.

**How to avoid:**
Establish mounting convention explicitly:
1. With face in frame, hold face above center horizontally. Log `blad_tilt`.
2. Expected: `blad_tilt = srodek_y - ramka_cy < 0` (face Y-center is above frame center in pixel space).
3. Expected servo reaction: tilt angle should *increase* (tilt up) to follow face.
4. Trace: `korekta_tilt = -pid_tilt(blad_tilt)`. If `blad_tilt < 0`, PID outputs negative, negation makes it positive, `nowy_tilt = tilt_angle + positive` = increases. Correct.
5. If physical tilt moves the wrong way, the sign of the negation must be reversed — not the PID gains.

Document the result in a comment: `# blad_tilt < 0 = face above center → korekta_tilt > 0 = tilt servo moves up. Mount: bracket forward-facing, tilt pin=13`.

**Warning signs:**
- Face above center but servo tilts down (or vice versa) — verified by eye during TRACKING
- Servo immediately hits TILT_LIMIT and clamp warnings flood logs
- Tracking converges on pan but tilt escapes immediately on entry

**Phase to address:**
Phase 1 (tilt fix) — sign verification must be empirical on the actual physical hardware with the actual mount before any other tilt work.

---

### Pitfall 3: ColourGains (1.0, 1.0) Is Semantically Wrong — Green Because Red and Blue Are Suppressed

**What goes wrong:**
`AWB_FALLBACK_GAINS = (1.0, 1.0)` is present in the current code (line 38 of `test_tracker.py`). This value is intuitive as "neutral" but is wrong for IMX219. The Picamera2 `ColourGains` tuple is `(red_gain, blue_gain)` — it multiplies the red and blue channels of the Bayer demosaiced output. The green channel has no gain parameter because it is the reference channel.

On IMX219 under typical indoor lighting, auto-AWB converges to approximately `(1.6–2.0, 1.4–1.9)`. These non-unity values are needed to compensate for the sensor's natural bias toward green (IMX219 has 2 green pixels per 4 in the Bayer RGGB pattern — so green is inherently twice as represented). Setting `ColourGains=(1.0, 1.0)` does *not* produce neutral white — it suppresses red and blue relative to what the ISP's AWB computed, making green dominant. This is the "green tint that does not change with scene."

The v1.8 fix set `(1.0, 1.0)` thinking it replaced the previous `(2.5, 1.9)` — it did eliminate the blue tint from overcorrected blue, but introduced green tint by undercorrecting red and blue.

**Why it happens:**
The name "ColourGains" suggests 1.0 = neutral. In absolute terms, 1.0 means "apply no amplification to this channel." But neutral white balance requires *relative* balance between channels, which for IMX219 requires both gains above 1.0 to match the sensor's green bias.

**How to avoid:**
Never hardcode `(1.0, 1.0)` as the fallback. The correct approach:
1. Let the camera run in auto-AWB for 3–5 seconds (no `ColourGains` set)
2. Read `metadata = cam.capture_metadata(); gains = metadata.get("ColourGains")`
3. Log the settled value — this is the correct neutral for this sensor in this lighting
4. Use *that* value as `AWB_FALLBACK_GAINS`

For IMX219 in indoor lighting without ceiling fluorescent, expect approximately `(1.7–2.0, 1.4–1.7)`. If the `capture_metadata()` approach fails (returns None), try `(1.8, 1.5)` as a safer fallback than `(1.0, 1.0)`.

The configure-time lock (`controls={"ColourGains": gains}` in `create_video_configuration()`) is still the correct sequencing — just use a valid non-unity value.

**Warning signs:**
- Green channel value in skin tones does not change when moving camera to different-colored surfaces
- `ColourGains` log at startup shows `(R=1.00, B=1.00)` — this is the fallback path firing
- Image looks correct outdoors but green-tinted indoors (scene-independent G dominance confirms fixed gains)
- `capture_metadata()["ColourGains"]` returns the fallback value, not auto-converged value

**Phase to address:**
Phase 2 (AWB fix) — before changing any ColourGains value, read the auto-converged value from a 5-second warm-up run and use that as the basis. Do not guess the fallback.

---

### Pitfall 4: AWB Re-Lock After Warm-Up Sets Gains From Metadata But ISP May Revert

**What goes wrong:**
The current `Picamera2Stream.start()` sequence:
1. Configure with `controls={"ColourGains": AWB_FALLBACK_GAINS}` (correct — ensures frame-1 color)
2. Sleep 2 seconds
3. `capture_metadata()["ColourGains"]` → reads settled auto-AWB values
4. `set_controls({"ColourGains": (float(r), float(b))})` → attempts to lock at settled values

Step 4 has a known failure mode on some Picamera2/libcamera versions: if `AwbEnable` is not explicitly set to `False` alongside the `ColourGains` re-lock, the AWB algorithm may continue running and override the gains within 1–2 seconds. The result: color is correct for 2 seconds then drifts.

The existing code does NOT set `AwbEnable: False`. Per issue #322, setting `ColourGains` alone *should* disable AWB implicitly, but per issue #825 this behavior is version-dependent. If the installed libcamera version does not treat `ColourGains` as an implicit AWB disable, the gains will not hold.

**Why it happens:**
Picamera2/libcamera API behavior for AWB disable is version-dependent and underdocumented. The implicit AWB-disable-via-ColourGains behavior was added in a specific libcamera version. Systems that have not been updated may not have this behavior.

**How to avoid:**
Add explicit `AwbEnable: False` only in the re-lock `set_controls()` call, NOT in the configure-time controls (configure-time `AwbEnable: False` before warm-up prevents auto-convergence from computing correct gains):
```python
# Phase 1: configure-time lock at safe fallback (no AwbEnable: False here)
video_config = self._picam2.create_video_configuration(
    lores={"size": (w, h), "format": "YUV420"},
    controls={"ColourGains": AWB_FALLBACK_GAINS}
)
self._picam2.configure(video_config)
self._picam2.start()

# Phase 2: warm-up, then lock at auto-converged values
time.sleep(2.0)
meta = self._picam2.capture_metadata()
gains = meta.get("ColourGains")
if gains and gains != (0.0, 0.0):
    self._picam2.set_controls({
        "AwbEnable": False,
        "ColourGains": (float(gains[0]), float(gains[1]))
    })
```

If adding `AwbEnable: False` causes issues (Picamera2 version conflict per issue #825), remove it and verify the implicit disable works by checking that gains do not drift after 30 seconds.

**Warning signs:**
- Color correct at startup but drifts after 2–5 seconds
- `ColourGains` re-read after re-lock shows different values than what was set
- Warm scenes produce warm drift, cold scenes produce blue drift (AWB still running)

**Phase to address:**
Phase 2 (AWB fix) — test lock stability over at least 30 seconds before declaring AWB fixed.

---

### Pitfall 5: PID Output Clamped at ±10° But servo_angle += correction Accumulates Unbounded

**What goes wrong:**
`PID_OUTPUT_LIMIT = 10.0` and `pid.output_limits = (-10.0, 10.0)` cap each tick's correction to ±10°. But the application code does:
```python
nowy_pan = self.hardware.pan_angle + korekta_pan
nowy_tilt = self.hardware.tilt_angle + korekta_tilt
self.hardware.set_angles(nowy_pan, nowy_tilt)
```

`self.hardware.pan_angle` is the last clamped software value. The *new* target is `pan_angle + correction`, which is only limited by `PAN_LIMIT_MIN/MAX` (±60°) in `set_angles()`. A sequence of ±10° corrections over 6 consecutive frames will move the servo from 0° to 60° (hitting the hard limit) in 6 ticks = 200ms at 30 FPS.

The root cause of "servo escapes immediately on TRACKING entry": the integral term (`I`) of the PID may have been accumulating during SCANNING (if `pid.reset()` was not called cleanly), and the moment TRACKING starts, the accumulated integral produces a large first correction that saturates the output at ±10° every tick for several frames.

The `simple_pid` library resets integral accumulation on `reset()` call. `_przejdz_do()` calls `pid_pan.reset()` and `pid_tilt.reset()` when entering SCANNING. But `_przejdz_do()` does NOT reset PIDs when entering TRACKING. If the system exits TRACKING, transitions through TARGET_LOST, returns to SCANNING (PIDs reset), then immediately detects a face and enters TRACKING — the PIDs are freshly reset and this is fine. But if TRACKING is entered from SCANNING after only 1 scan tick (face detected very quickly), there may be a small non-zero integral from that one tick. More dangerous: if the initial error at TRACKING entry is large (face is at the frame edge, `blad_pan = ±160` pixels for a 320-wide frame), the P-term alone produces `0.05 * 160 = 8.0°` per tick, and with no I windup at all, 6 consecutive ticks hit the ±60° limit.

**Why it happens:**
PID gains (`P=0.05`) were validated on a face that was roughly centered (`blad_pan` small). A face at the edge of frame (`blad_pan = 150+`) produces full-saturation output from P-term alone, every tick. The servo moves at maximum speed until it hits the limit. This looks like "runaway" but is actually correct PID behavior for a large initial error — the system is not misbehaving, it is correcting aggressively.

**How to avoid:**
Two complementary approaches:
1. **Derivative-on-measurement**: Use `simple_pid` with `differential_on_measurement=True` (default is False) to avoid derivative kick when error jumps suddenly at TRACKING entry.
2. **Startup output limit reduction**: For the first 3–5 ticks of a new TRACKING entry, cap the per-tick correction to a smaller value (e.g. `PID_OUTPUT_LIMIT_STARTUP = 3.0`), then restore normal limits after the servo has moved toward the face.
3. **Dead zone**: Add a center dead zone — if `abs(blad_pan) < 10` pixels, do not apply PID correction. This prevents jitter when centered and reduces escapes at entry (the servo will approach more slowly).

Verify with logging: at every TRACKING entry, log `blad_pan`, `blad_tilt`, and `korekta_pan`, `korekta_tilt` for the first 5 ticks. If corrections are at the ±10° limit for 5+ consecutive ticks, the initial error is too large and needs entry-time correction limiting.

**Warning signs:**
- Servo hits limit clamp (`WARNING: Clamp pan`) within 1–2 seconds of TRACKING entry
- TRACKING lasts less than 1 second before TARGET_LOST (servo escapes, face leaves frame)
- `blad_pan` or `blad_tilt` at TRACKING entry is above 100 pixels (out of 160/120 for 320x240)
- `korekta_pan` at ±10.0 (saturated at limit) for first 5+ ticks after TRACKING entry

**Phase to address:**
Phase 3 (PID/tracking fix) — must address initial-error correction limiting separately from steady-state gain tuning.

---

### Pitfall 6: smooth_move_to() Is Blocking — Using It in Main Loop Stalls Camera Capture

**What goes wrong:**
`smooth_move_to()` in `hardware.py` is a blocking while-loop with `time.sleep(0.05)` per step. Moving from 0° to 45° with `SERVO_STEP=1.0` takes `45 * 0.05 = 2.25 seconds`. If `smooth_move_to()` is called from the main tracking loop thread (or from `inicjalizuj()` before the loop starts), it blocks frame capture for the entire duration.

On startup this is acceptable — `inicjalizuj()` runs before `_running = True` and before the camera capture thread serves frames to the main loop. The safe start is designed to block.

The trap appears when `smooth_move_to()` is proposed as the fix for "jerky motion during scan." A developer sees jerky scan behavior, looks at `_skanuj()` which calls `set_angles()` directly, and decides to replace it with `smooth_move_to()`. This is wrong — `smooth_move_to()` is a one-shot blocking move, not a real-time incremental step function. Calling it inside `_skanuj()` (which runs every frame) would cause each scan step to block for up to 2+ seconds.

**Why it happens:**
The name `smooth_move_to` suggests it is the right tool for any smooth motion. It is actually a Safe Start utility — it exists to prevent brownout at startup, not for real-time scan motion.

**How to avoid:**
Scan smoothness must be achieved through the sinusoidal formula in `_skanuj()`, not by replacing `set_angles()` with `smooth_move_to()`. If scan appears jerky on hardware, investigate:
1. PWM frame timing — is `pigpiod` running? Software PWM from RPi.GPIO produces visible jitter even at hardware GPIO
2. Loop timing — is the main loop consistently executing at 30 FPS or dropping frames?
3. Servo pulse calibration — default gpiozero `min_pulse_width=1ms, max_pulse_width=2ms` may not match MG90S physical range. MG90S typical: 0.5ms–2.4ms. Using defaults maps only the center portion of the servo's physical range, causing each angular step to produce less physical movement and non-linearity.

**Warning signs:**
- System freezes for 2+ seconds between scan positions
- Camera frames stop updating while servo is moving
- `_skanuj()` log messages appear with multiple-second gaps

**Phase to address:**
Phase 4 (smooth scan fix) — separate scan smoothness from servo hardware calibration. Address pulse width calibration as a hardware.py change, not a change to `_skanuj()`.

---

### Pitfall 7: MG90S Pulse Width Defaults Cause Non-Linear Motion and Apparent Jerkiness

**What goes wrong:**
`PanTiltSystem.__init__` creates:
```python
self.pan_servo = AngularServo(pan_pin, min_angle=-90, max_angle=90, pin_factory=factory)
self.tilt_servo = AngularServo(tilt_pin, min_angle=-90, max_angle=90, pin_factory=factory)
```

The gpiozero `AngularServo` default pulse widths are `min_pulse_width=1/1000` (1ms) and `max_pulse_width=2/1000` (2ms). The MG90S datasheet specifies 500µs–2400µs as the full range. The defaults only cover 1000–2000µs, which corresponds to roughly ±60° of the physical ±90° range. Within the covered range, the mapping is linear. Near the edges (approaching the ±60° soft limit), the servo may still physically move but the commanded steps produce smaller physical movement, appearing as "going dead" near limits.

More importantly: if the actual servo's center position corresponds to a different pulse width than gpiozero's default midpoint (1500µs), `angle=0` will not produce physical 0°. The servo will appear to start off-center and the scan will not be symmetric.

**Why it happens:**
MG90S "typical" specs vary by manufacturer batch. The gpiozero defaults are for a generic 180° servo assuming 1ms–2ms = -90° to +90°. MG90S from some suppliers uses 500µs–2500µs for the full range. Using defaults causes the servo to only use the middle third of its physical range.

**How to avoid:**
Calibrate pulse widths empirically. Start with the wider range:
```python
self.pan_servo = AngularServo(
    pan_pin,
    min_angle=-90, max_angle=90,
    min_pulse_width=0.0005,   # 500µs
    max_pulse_width=0.0024,   # 2400µs
    pin_factory=factory
)
```
Command angle=0, measure physical position. Command angle=+60, measure. If 60° command = 60° physical, calibration is correct. If not, adjust `min_pulse_width` and `max_pulse_width` until the physical movement matches the commanded angle. This affects scan amplitude accuracy and PID convergence.

**Warning signs:**
- Servo moves but scan amplitude appears less than `SCAN_AMPLITUDE=45°` visually
- Servo seems to stop responding before reaching angle limits (hits mechanical stop before software limit)
- Center position (angle=0) does not visually center the camera
- Scan pattern is not symmetric (larger swing one direction than the other)

**Phase to address:**
Phase 4 (smooth scan fix) — pulse width calibration is a hardware.py constant change. Do this before any PID gain tuning as it changes the effective gain of the servo actuator.

---

### Pitfall 8: DNN skip_every=5 Creates Stale BBox During Rapid Motion — PID Tracks Old Position

**What goes wrong:**
`DetekcjaTwarzy.wykryj()` runs DNN forward pass only when `klatka_licznik % DNN_SKIP_EVERY == 0`. Between forward passes, it returns `self._ostatni_bbox` unchanged — the last detected position. If the face moves rapidly (or the servo moves rapidly after entering TRACKING), the bounding box is stale for up to 4 frames. The PID corrects toward an old position, overshoots, and may exit TRACKING.

At 10 FPS (which is realistic for the DNN path on RPi4), `skip_every=5` means forward pass runs at 2 FPS. Between forward passes, the bbox is 500ms stale. If the face is moving at 1 pixel/ms (normal head movement), the bbox center may be 500 pixels stale — larger than the entire 320px frame width.

**Why it happens:**
`skip_every=5` was set for computational efficiency (validated in Phase 13). But the TRACKING state uses bbox without any staleness weighting — it treats the 4-frame-old bbox as current ground truth.

**How to avoid:**
During TRACKING, add a bbox staleness flag: track which frame number produced the last DNN result. If the current frame is more than 2 frames past the last DNN result, reduce the PID correction weight or skip the correction entirely. Alternatively, use a CSRT tracker (as the main `vision.py` does) between DNN forward passes to propagate the bbox smoothly. For v1.9 scope, a simpler approach: reduce correction magnitude when using cached bbox, or only apply PID correction on frames where DNN ran.

**Warning signs:**
- Servo oscillates at 2 Hz during TRACKING (matching DNN forward pass frequency at 10 FPS with skip=5)
- Convergence takes longer than expected given P gain
- TRACKING exits to TARGET_LOST immediately after DNN forward pass that returns None (face moved, old bbox was accurate, new DNN detects nothing at old position)

**Phase to address:**
Phase 3 (PID/tracking fix) — consider as a secondary investigation if primary PID fixes do not resolve escape behavior. Do not over-engineer this in v1.9; note as a known limitation.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `AWB_FALLBACK_GAINS = (1.0, 1.0)` | "Neutral" fallback, no on-device tuning needed | Green tint — wrong for all IMX219 deployments | Never — replace with empirically read auto-converged values |
| `set_angles(pan, 0.0)` hardcoded in `_skanuj()` | Simple code, tilt stays still during scan | Masks tilt hardware failures; no two-axis scan possible | Acceptable for pan-only scan intent — but must be explicitly documented as intentional |
| `PID_OUTPUT_LIMIT = 10.0` with no entry-time damping | Simple constant limit | Saturated output at every TRACKING entry with large initial error | Acceptable if face is always near-centered; must add dead-zone or startup damping if face enters at frame edges |
| `SERVO_STEP = 1.0` with `delay=0.05` in `smooth_move_to()` | Works for safe start | Inappropriate for real-time motion; calling in main loop blocks for seconds | Only for `inicjalizuj()` — never for real-time scan or tracking |
| Default gpiozero pulse widths (1ms–2ms) | No calibration needed | Non-linear motion, wrong center position, limited range | Never for final hardware — calibrate min/max pulse widths to physical servo specification |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Picamera2 ColourGains | Setting `(1.0, 1.0)` as "neutral fallback" | Read auto-converged gains from `capture_metadata()` after 2s warm-up; use those as fallback |
| Picamera2 ColourGains | Setting `(r, b)` before `start()` via `set_controls()` — silently ignored | Set in `create_video_configuration(controls=...)` for configure-time guarantee |
| Picamera2 AWB lock | Not setting `AwbEnable: False` in the re-lock `set_controls()` call | Add `"AwbEnable": False` alongside `ColourGains` in the post-warm-up `set_controls()` call |
| Picamera2 ColourGains | Integer tuple `(1, 1)` instead of float `(1.0, 1.0)` | Always pass `float(r), float(b)` — int input causes TypeError on some versions |
| gpiozero AngularServo | Default pulse widths `1ms–2ms` for MG90S | Use `min_pulse_width=0.0005, max_pulse_width=0.0024` and verify physical angle at 0° |
| gpiozero AngularServo | Calling `smooth_move_to()` in real-time scan/tracking loop | `smooth_move_to()` is blocking — only valid in `inicjalizuj()` before loop starts |
| pigpio / gpiozero | Assuming `pan_servo.angle` reads back hardware position | `pan_servo.angle` reflects last commanded value only — no feedback from physical servo |
| simple_pid | Not resetting PID on SCANNING entry after long TRACKING session | `_przejdz_do()` already resets on SCANNING entry — do NOT add reset on TRACKING entry, it discards valid integral |
| DNN bbox skip | Using stale bbox as ground truth during TRACKING | Track `klatka_licznik` modulo; reduce weight or skip correction on non-DNN frames if oscillation detected |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `cv2.resize()` 2x in main loop | CPU spike, FPS drops | Skip resize in headless mode (already guarded) | At 320x240 to 640x480 resize, ~3ms/frame — acceptable at 10 FPS; expensive at 30 FPS |
| DNN `forward()` in main loop thread without skip | 100ms+ per frame = 1 FPS | `skip_every=5` already in place; never remove | Breaks immediately without skip on RPi4 |
| `time.sleep(0.01)` in capture thread | Caps camera FPS at ~100 frames/s | Correct for 320x240 — do not reduce below 0.005 | Not a trap at current resolution; becomes one if resolution increases |
| `smooth_move_to()` blocking 2+ seconds | Camera freezes, state machine stalls | Only call at startup in `inicjalizuj()`, never in main loop | Always a trap if called in main loop at any scale |
| PID integral accumulation between TRACKING sessions | Servo escape on next TRACKING entry | `pid.reset()` on SCANNING entry (already in `_przejdz_do()`) — verify it executes every transition | Breaks if `_przejdz_do()` is bypassed or if direct state assignment is used |

---

## "Looks Done But Isn't" Checklist

- [ ] **Tilt hardware**: `smooth_move_to(0, 20)` then `(0, 0)` at startup — verify physical tilt moves before touching state machine code
- [ ] **Tilt sign**: Face held above center during TRACKING — verify `tilt_angle` increases in HUD (servo follows up, not down)
- [ ] **AWB fix**: Color neutral from frame 1 — not just after 2s warm-up delay
- [ ] **AWB fallback value**: Startup log shows `(R=X.XX, B=X.XX)` with both values above 1.4, not `(1.00, 1.00)`
- [ ] **AWB stability**: Color does not drift after 30 seconds of TRACKING across different scene areas
- [ ] **PID entry behavior**: Log `blad_pan` at every TRACKING entry — if above 100 pixels, entry-time damping needed
- [ ] **PID convergence**: TRACKING sustained 5+ seconds with face roughly centered — servo not continuously clamping
- [ ] **Clamp frequency**: Clamp warnings appear only at physical boundaries, not on every tracking tick
- [ ] **Scan symmetry**: Camera sweeps equal angle left and right of center — verify `set_angles(0, 0)` is true physical center
- [ ] **Pulse width calibration**: `angle=0` command produces visually centered camera; `angle=45` produces approximately 45° physical movement
- [ ] **Mock mode**: Startup log confirms `PIGPIO_AVAILABLE=True` and `mock_mode=False` before any hardware test
- [ ] **pigpiod active**: `systemctl is-active pigpiod` returns `active` before running any test

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Tilt frozen — hardware path not called | LOW | Add `smooth_move_to(0, 20)` test in `inicjalizuj()`; if physical tilt moves, hardware OK — problem is state machine |
| Tilt inverted — servo moves wrong direction | LOW | Change `korekta_tilt = -self.pid_tilt(blad_tilt)` to `korekta_tilt = self.pid_tilt(blad_tilt)` — one sign change |
| AWB green tint from (1.0, 1.0) fallback | LOW | Read `capture_metadata()["ColourGains"]` after 5s auto warm-up; update `AWB_FALLBACK_GAINS` constant with result |
| AWB gains not holding after lock | LOW | Add `"AwbEnable": False` to the post-warm-up `set_controls()` call; verify with re-read |
| PID escape on TRACKING entry | MEDIUM | Add per-entry correction cap: `min(abs(korekta_pan), 3.0) * sign(korekta_pan)` for first 5 ticks; add dead zone ±10 pixels |
| Servo jitter from software PWM | LOW | Verify `pigpiod` running with `PiGPIOFactory`; already in `hardware.py` — check startup log for successful pigpio init |
| Non-linear/wrong-range servo motion | LOW | Add `min_pulse_width=0.0005, max_pulse_width=0.0024` to `AngularServo()` constructor in `hardware.py`; verify physical angle |
| Scan not smooth from sinusoid | MEDIUM | Check loop FPS — if below 10 FPS, scan appears stepped; reduce DNN `skip_every` or optimize main loop timing |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Tilt frozen — scan hardcodes 0.0 / state machine never reaches TRACKING | Phase 1: tilt fix | `smooth_move_to(0, 20)` test moves physically; TRACKING state sustained with non-zero tilt |
| Tilt inverted — wrong sign for physical mount | Phase 1: tilt fix | Face above center → tilt HUD increases; face below center → tilt HUD decreases |
| AWB green tint from (1.0, 1.0) fallback | Phase 2: AWB fix | Fallback value above 1.4 in both channels; neutral skin tone from frame 1 |
| AWB gains drifting after lock | Phase 2: AWB fix | `ColourGains` re-read after 30s matches locked value within ±0.1 |
| PID escape on large initial error | Phase 3: PID/tracking fix | Clamp warnings absent for first 5 ticks of TRACKING; TRACKING sustained 5+ seconds |
| DNN stale bbox during rapid motion | Phase 3: PID/tracking fix | No 2 Hz oscillation during TRACKING; secondary investigation only |
| smooth_move_to() blocking in loop | Phase 4: smooth scan fix | Never call smooth_move_to() in scan — scan uses sinusoidal set_angles() only |
| MG90S pulse width miscalibration | Phase 4: smooth scan fix | Physical angle matches commanded angle at 0°, ±45°; scan appears symmetric |

---

## Sources

### Primary (HIGH confidence — direct code analysis)
- `src/modes/test_tracker.py` — `AWB_FALLBACK_GAINS = (1.0, 1.0)`, `_skanuj()` hardcoded tilt=0.0, `pid.output_limits = (-10.0, 10.0)`, `DNN_SKIP_EVERY = 5`, double negation in `_sledz()`
- `src/hardware.py` — `AngularServo(min_angle=-90, max_angle=90)` with no pulse width calibration; `smooth_move_to()` blocking while-loop with `time.sleep(0.05)`, `set_angles()` software-state updates regardless of `_mock_mode`
- `src/config.py` — `PID_PAN_P = 0.05`, `PAN_LIMIT_MIN = -60`, `TILT_LIMIT_MIN = -30`, `SERVO_STEP = 1.0`
- `.planning/PROJECT.md` — v1.9 problem statement; v1.7 "tilt negation fix" history; v1.8 "ColourGains=(1.0,1.0) turned blue→green" history

### Secondary (MEDIUM-HIGH confidence — official and community sources)
- [Picamera2 issue #322](https://github.com/raspberrypi/picamera2/issues/322) — AWB disable preserves CCM at moment of disable; `ColourGains=(1.0, 1.0)` does not produce neutral white on IMX219
- [Picamera2 issue #825](https://github.com/raspberrypi/picamera2/issues/825) — `AwbEnable: False` + `ColourGains` in same `set_controls()` call causes sequencing issues on some Bookworm versions
- [Picamera2 issue #933](https://github.com/raspberrypi/picamera2/issues/933) — maintainer: controls in `create_video_configuration()` are guaranteed to apply at configure time; `set_controls()` after `start()` takes 2–3 frames
- [gpiozero RPi Forums #331790](https://forums.raspberrypi.com/viewtopic.php?t=331790) — MG90S-class servos require 500–2500µs range; default 1000–2000µs gpiozero defaults produce limited motion
- [gpiozero documentation 2.0.1](https://gpiozero.readthedocs.io/en/stable/api_output.html) — `AngularServo` `min_pulse_width` and `max_pulse_width` parameters; PiGPIOFactory for hardware PWM
- [Anti-windup via output clamping — simple_pid](https://github.com/m-lundberg/simple-pid) — `output_limits` provides clamping; `reset()` clears integral; derivative-on-measurement available via constructor flag

---
*Pitfalls research for: v1.9 Stabilizacja Ruchu i Obrazu — ARIES-LITE RPi4 pan-tilt face tracker*
*Researched: 2026-03-29*
