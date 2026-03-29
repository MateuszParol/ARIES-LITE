# Pitfalls Research — v1.8 Critical Hardware Fix

**Domain:** Debugging persistent hardware failures in RPi4 pan-tilt face tracking (Picamera2 + pigpio + simple_pid + HAAR)
**Researched:** 2026-03-29
**Confidence:** HIGH (code-derived pitfalls) / MEDIUM (AWB API sequencing alternatives)

**Scope:** This document targets v1.8 — bugs that survived v1.7 code changes but do NOT work on hardware.
v1.7 applied four fixes; all four appear syntactically correct in the current `src/modes/test_tracker.py`.
The bugs are still present on hardware. This means the root cause of each failure is NOT what v1.7 targeted.

---

## Critical Pitfalls

### Pitfall 1: Tilt PID Negation Applied But Tilt Still Frozen — The State Machine Is Never Calling _sledz()

**What goes wrong:**
The v1.7 fix added `-self.pid_tilt(blad_tilt)` (line 276 of `test_tracker.py`). This negation is present in the current code. Yet the HUD shows `Tilt: 0.0` frozen. This means the negation fix is syntactically correct but irrelevant to the actual failure. The `_sledz()` method is either not being called at all, or `set_angles()` is being called with zero tilt every time.

The HUD reads `tilt = self.maszyna.hardware.tilt_angle` — this is a pure software variable. It reflects whatever `set_angles()` last stored. If `tilt_angle` stays at 0.0, exactly one of these must be true:

1. `_sledz()` is never called (state machine stays in SCANNING — face never detected by HAAR)
2. `_sledz()` is called but `blad_tilt = srodek_y - ramka_cy` is always near zero (face always vertically centered)
3. `_sledz()` is called but `pid_tilt(blad_tilt)` returns 0.0 (sample_time not elapsed)
4. `nowy_tilt = self.hardware.tilt_angle + korekta_tilt` is always 0.0 (korekta_tilt exactly cancels current tilt)
5. `set_angles()` is called with non-zero tilt but something in the call path resets it to 0

The most likely root cause given "no green rectangles visible" is case 1: HAAR never detects a face with `HAAR_MIN_NEIGHBORS=8` and `HAAR_MIN_SIZE=(80, 80)` at 320x240 resolution. If no face is ever detected, the state machine stays in SCANNING permanently, `_skanuj()` always calls `set_angles(pan, 0.0)` with hardcoded tilt=0, and HUD shows Tilt frozen at 0.0. This is not a PID sign bug — it is a detection failure masquerading as a PID bug.

**Why it happens:**
`HAAR_MIN_SIZE=(80, 80)` on a 320x240 frame requires the face bounding box to be at least 80 pixels wide and 80 pixels tall. At 320px wide, this means the face must occupy at least 25% of the frame width — approximately 40-50cm distance from camera at normal field of view. The user must be extremely close to the camera and perfectly frontal.

`HAAR_MIN_NEIGHBORS=8` is significantly higher than the OpenCV default of 3. Each candidate region must be confirmed by 8 overlapping detections at different scales. This eliminates almost all non-frontal, partially occluded, or angled faces. Combined with the 80x80 minimum, this explains "requires perfect frontal face at very short distance."

**How to avoid:**
Reduce HAAR parameters to more permissive values for 320x240:
- `HAAR_MIN_SIZE = (40, 40)` — detects faces from 0.5-2m at normal FOV
- `HAAR_MIN_NEIGHBORS = 4` — still filters noise but detects non-perfect frontal faces
- Keep `STREAK_REQUIRED=3` to compensate for the increased false positive rate from looser parameters

Alternatively, replace HAAR entirely with OpenCV DNN (res10_300x300_ssd_iter_140000) or MediaPipe BlazeFace. Both provide better detection at angles and partial occlusion. DNN on RPi4 runs at 5-8 FPS; MediaPipe at ~10 FPS. Since the tracker loop already runs at ~30 FPS, running detection every 3-4 frames with DNN is viable.

**Warning signs:**
- HUD shows no green rectangles ever — confirms zero detection
- State machine log shows only SCANNING entries, never TRACKING
- `DetekcjaTwarzy._streak` counter stays at 0 (add a log line to verify)
- Moving face very close to camera (20-30cm, perfectly frontal) suddenly triggers detection

**Phase to address:**
Detection fix — must come first before any PID or AWB debugging. A system that never detects faces cannot be used to validate PID behavior.

---

### Pitfall 2: Diagnosing PID Behavior Without Confirmed Detection — All PID "Fixes" Are Invalid

**What goes wrong:**
v1.7 applied a PID sign fix and a phase offset fix. Neither can be validated if the face detector never triggers. If HAAR is too restrictive and detects only in ideal conditions, then:
- Any PID sign observation ("pan runs away") is based on 1-2 frames of detection before the face is lost
- The "runaway" behavior may be the scan sinusoid (pan oscillating ±45°) being mistaken for PID runaway
- The phase offset fix for smooth scan resume cannot be tested because TRACKING is never sustained

The developer makes code changes to PID, observes hardware behavior, and concludes the fix "didn't work" — but the behavior observed was not PID behavior at all. It was scan behavior with occasional 1-frame detection interruptions.

**Why it happens:**
When the detector is barely triggering, TRACKING state lasts for one tick (one frame). The state transition SCANNING→TRACKING→TARGET_LOST→SCANNING happens in 2-3 frames. The pan servo barely moves. This looks identical to "PID sign fix didn't work" or "pan still runs away."

The scan sinusoid with `SCAN_AMPLITUDE=45°` and `SCAN_FREQUENCY=0.1 Hz` moves the camera ±45° over 10 seconds. If the user sees the camera panning to a limit during "tracking," it may be the end of a scan cycle coinciding with a brief 1-frame detection, not a PID runaway.

**How to avoid:**
Before any PID diagnosis:
1. Confirm TRACKING state is sustained for at least 10 consecutive frames (add a frame counter to the TRACKING branch log)
2. Confirm `bbox` is non-None for those frames and the face is consistently off-center
3. Only then examine PID correction values and servo motion

**Warning signs:**
- HUD shows rapid SCANNING/TRACKING/TARGET_LOST cycling
- Total TRACKING duration per session is under 1 second
- Camera motion looks sinusoidal even during "tracking"

**Phase to address:**
Detection fix must precede PID validation. Do not touch PID code until detection is stable.

---

### Pitfall 3: AWB ColourGains — capture_metadata() Returns None on Lores-Only YUV420 Configuration

**What goes wrong:**
The current `Picamera2Stream.start()` code (lines 78-87) calls `time.sleep(2.0)` then `self._picam2.capture_metadata()` and reads `metadata.get("ColourGains")`. The code already handles the `None` case with a fallback to `(2.5, 1.9)` and logs a warning. However, the observed symptom is "blue tint still present from startup" and "ColourGains log line not observed."

If the warning line `"ColourGains niedostępne, używam fallback (2.5, 1.9)"` is not appearing in logs, it means one of:
1. `ColourGains` is NOT None (metadata returns a value) but `set_controls()` is not applying it
2. The `start()` method is completing but the AWB lock code is not executing (exception swallowed before it)
3. The `set_controls()` call is being issued but not taking effect because of a sequencing conflict

Picamera2 issue #977 (reported March 2024, Bookworm 64-bit) documents that `AwbMode` has no effect and `AwbEnable` True/False does not work as expected in certain Bookworm versions. Setting `ColourGains` directly is the confirmed workaround.

The forum thread for issue #365052 confirmed that `set_controls` must be called after `configure`, but the current code calls it after `start()` — which is also valid. However, issue #933 documents that the maintainer explicitly warns that setting `AwbEnable: False` alongside `ColourGains` in the same `set_controls()` call can cause sequencing conflicts in some versions. The current code does NOT set `AwbEnable`, which is correct.

The most likely cause of persistent blue tint when the code appears correct: the `controls` parameter was passed to `create_video_configuration` in an earlier version and is now absent. An alternative confirmed method is passing `controls={"ColourGains": (r, b)}` directly to `create_video_configuration()` — this applies the control value at configure time before the ISP starts, guaranteeing it takes effect on the very first frame.

**Why it happens:**
Two confirmed Picamera2 behaviors contribute:
1. Controls set via `set_controls()` after `start()` take effect 2-3 frames later due to the kernel driver request queue
2. In Bookworm with certain libcamera versions, `capture_metadata()["ColourGains"]` may return the auto-converged value correctly, but `set_controls({"ColourGains": gains})` may be applied but then overridden by the still-running AWB algorithm if there is a version bug in AWB disabling

The safest approach (confirmed working across Bookworm versions) is to pass `ColourGains` in the `controls` dict of `create_video_configuration()` so it is applied before `start()` and before any AWB algorithm runs. This also means `capture_metadata()` is not needed for this path.

**How to avoid:**
Use the two-phase approach for maximum reliability:
```python
# Phase 1: set at configure time (takes effect from first frame)
video_config = self._picam2.create_video_configuration(
    lores={"size": (self._width, self._height), "format": "YUV420"},
    controls={"ColourGains": AWB_FALLBACK_GAINS}
)
self._picam2.configure(video_config)
self._picam2.start()

# Phase 2: read settled auto-values and re-lock after warm-up
time.sleep(2.0)
metadata = self._picam2.capture_metadata()
gains = metadata.get("ColourGains")
if gains is not None and gains != (0.0, 0.0):
    self._picam2.set_controls({"ColourGains": (float(gains[0]), float(gains[1]))})
    logger.info(f"ColourGains zablokowane po warm-up: (R={gains[0]:.2f}, B={gains[1]:.2f})")
else:
    logger.info(f"ColourGains zablokowane fallback: {AWB_FALLBACK_GAINS}")
```

Setting `ColourGains=(0.0, 0.0)` in Picamera2 is interpreted as "re-enable AWB." Always check for this before re-applying.

**Warning signs:**
- Blue tint from the very first frame (suggests configure-time gains not applied)
- Blue tint for first 2-3 seconds then correct color (suggests set_controls timing issue only)
- No log line from the ColourGains lock code (suggests exception before that line)
- `capture_metadata()["ColourGains"]` returns `(0.0, 0.0)` (means AWB is still running)

**Phase to address:**
AWB fix — use configure-time `controls` dict as the primary lock, keep post-start `set_controls` as the secondary re-lock after warm-up.

---

### Pitfall 4: Pan Runaway Is Phase Offset Math Producing a Non-Convergent Initial Scan Value

**What goes wrong:**
v1.7 added phase offset calculation in `_przejdz_do()` (line 291-292):
```python
raw = self.hardware.pan_angle / SCAN_AMPLITUDE
self._scan_phase_offset = math.asin(max(-1.0, min(1.0, raw)))
```

This is mathematically correct: it finds the phase angle such that `SCAN_AMPLITUDE * sin(phase_offset) == current_pan_angle`. On the next `_skanuj()` tick, the formula is:
```python
pan = SCAN_AMPLITUDE * math.sin(2.0 * math.pi * SCAN_FREQUENCY * t + self._scan_phase_offset)
```

The problem: `t = time.time()` is an absolute Unix timestamp (approximately 1.7 billion seconds). At the moment the phase offset is computed, `2.0 * pi * 0.1 * t` is a very large number. The arcsin of `pan_angle/SCAN_AMPLITUDE` gives the correct geometric offset, but this offset must cancel the `2.0 * pi * f * t_transition` term from the transition time. Since `t` advances continuously, the phase offset becomes stale the instant time advances even by milliseconds.

Specifically: if the transition happens at time `t0`, then `phase_offset = asin(pan/A)`. On the next tick at `t0 + dt`, the scan value is `A * sin(2*pi*f*(t0+dt) + asin(pan/A))`. This is NOT equal to `pan` at `t0+dt` — the scan has already moved. For `f=0.1 Hz` and `dt=33ms`, the scan has moved by `2*pi*0.1*0.033 = 0.0207 radians`, equivalent to `45 * 0.0207 = 0.93°` per frame. Over 10 frames this is almost 10° of unexplained pan movement.

This is a minor issue for smooth scan resume, not a runaway. The actual pan runaway is almost certainly the detection failure (Pitfall 2) combined with incorrect diagnosis.

**Why it happens:**
Using absolute `time.time()` for the phase argument means the phase offset must account for the current position of the sinusoid in absolute time, not relative time. The correct approach uses relative time from a reference point, or stores the absolute time of the transition and adjusts the formula. The current formula computes the geometric offset but ignores the temporal offset.

**How to avoid:**
Track a `_scan_start_time` that resets at each SCANNING entry:
```python
def _przejdz_do(self, nowy_stan: str) -> None:
    if nowy_stan == config.STATE_SCANNING:
        self.pid_pan.reset()
        self.pid_tilt.reset()
        raw = self.hardware.pan_angle / SCAN_AMPLITUDE
        t_now = time.time()
        # Solve: A*sin(2*pi*f*(t_now - t_ref) + 0) = current_pan
        # t_ref = t_now - asin(raw) / (2*pi*f)
        self._scan_start_time = t_now - math.asin(max(-1.0, min(1.0, raw))) / (2.0 * math.pi * SCAN_FREQUENCY)
```

Then `_skanuj()` uses `t - self._scan_start_time` instead of `t + phase_offset`.

**Warning signs:**
- Small pan jerk at every TRACKING→SCANNING transition
- Pan position immediately after transition does not match pan position just before
- Logging `pan` value at transition vs first scan tick shows a discontinuity

**Phase to address:**
Scan continuity fix — lower priority than detection and AWB, but needed for smooth behavior after detection is working.

---

### Pitfall 5: HUD Tilt Display Shows Software State, Not Hardware State — Mock Mode Is Invisible

**What goes wrong:**
`_rysuj_hud()` reads `self.maszyna.hardware.tilt_angle` — a Python float stored in `PanTiltSystem`. This value is updated unconditionally in `set_angles()` regardless of `_mock_mode`:

```python
# hardware.py set_angles():
self.pan_angle = pan_clamped
self.tilt_angle = tilt_clamped     # always updated
if not self._mock_mode and self.pan_servo and self.tilt_servo:
    self.pan_servo.angle = self.pan_angle    # only in real mode
    self.tilt_servo.angle = self.tilt_angle  # only in real mode
```

This means: if `pigpiod` is not running and `_mock_mode=True`, the HUD will show moving `Pan:` and `Tilt:` values (software state), but the physical servos will not move. The developer may conclude the PID is working correctly based on HUD values, while the actual hardware is frozen.

Conversely, if `_mock_mode=False` but `pigpiod` crashes or disconnects mid-session, subsequent `set_angles()` calls in gpiozero may silently fail or raise exceptions caught elsewhere, causing the physical servos to stop while the HUD continues to show "correct" values.

**Why it happens:**
`PanTiltSystem.__init__` catches `Exception` during gpiozero initialization and falls back to mock mode. The log message "Uruchamiono obsluge serw w srodowisku okrojonym MOCK" is the only indicator. If the developer is not watching startup logs carefully (especially when connecting via SSH), this message is easily missed.

**How to avoid:**
1. At startup, explicitly log `maszyna.hardware._mock_mode` at INFO level in `TestTracker.uruchom()` before the main loop
2. Add mock mode indicator to the HUD: append `[MOCK]` to the state label when `_mock_mode=True`
3. Verify `pigpiod` is running before launching: `systemctl is-active pigpiod` must return `active`

**Warning signs:**
- HUD shows Pan/Tilt values changing smoothly but physical servos do not move
- Startup log contains "MOCK" after the hardware init line
- `sudo systemctl status pigpiod` shows inactive or failed

**Phase to address:**
Pre-flight diagnostic — add mock mode indicator to HUD and startup check before any hardware debugging.

---

### Pitfall 6: AWB Fallback Gains (2.5, 1.9) May Produce Wrong Colors for Specific Lighting

**What goes wrong:**
The fallback `AWB_FALLBACK_GAINS = (2.5, 1.9)` is used when `capture_metadata()["ColourGains"]` returns `None`. For IMX219 (Camera Module V2), typical indoor LED lighting has converged gains around `(1.6, 1.5)` to `(2.0, 1.7)`. A fallback of `(2.5, 1.9)` may produce a warm/yellow tint instead of blue, which will be reported as "AWB fix partially worked" or "different color problem."

Additionally, `ColourGains = (r, b)` where `r` is red gain and `b` is blue gain — a high `r` value reduces red (counter-intuitive naming: the gain multiplies the channel, so a high value means the ISP is applying more red correction because the sensor has a red deficit). Outdoor daylight typically needs `(1.4, 1.8)`, indoor fluorescent needs `(1.7, 1.4)`. The fallback values should be empirically determined for the actual deployment lighting, not hardcoded from documentation examples.

**Why it happens:**
IMX219 color response depends on the lens module, the sensor revision, and ambient lighting. There is no universal "correct" fallback. The camera tuning file (`imx219.json`) has factory-calibrated defaults, but these are overridden when `ColourGains` is set manually.

**How to avoid:**
Run the camera for 5 seconds in auto-AWB mode, then call `capture_metadata()["ColourGains"]` and log the result. Use that as the fallback value for the specific hardware and lighting environment. This value should be hardcoded per deployment, not fixed in source code.

**Warning signs:**
- Warm/yellow cast instead of blue (over-corrected red)
- Skin tones look orange or green (wrong channel emphasis)
- `capture_metadata()["ColourGains"]` after 5 seconds of auto-AWB shows values very different from the fallback

**Phase to address:**
AWB fix — empirically determine correct fallback gains for the deployment environment before hardcoding.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded `AWB_FALLBACK_GAINS` | No on-device tuning needed | Wrong colors in different lighting | Never — read from capture_metadata() at startup or make configurable |
| `HAAR_MIN_NEIGHBORS=8` and `HAAR_MIN_SIZE=(80, 80)` | Zero false positives | System never detects faces in practice | Never — use (4, (40,40)) baseline, tune streak for false positive filtering |
| Absolute `time.time()` in scan formula | Simple code | Phase offset arcsin fix has no effect on smooth resume | Acceptable until smooth resume is a requirement — replace with relative time reference |
| `_mock_mode` silent in HUD | Clean display | Invisible hardware failure during debugging | Never during active debugging — always show mock mode in HUD |
| Single `capture_metadata()` call for ColourGains | Simple code | Returns None on some Picamera2/libcamera combinations | Use configure-time `controls` dict as primary lock; metadata as secondary verification |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Picamera2 AWB lock | `set_controls` before `start()` — silently ignored | Pass `controls={"ColourGains": gains}` in `create_video_configuration()`, also re-apply after `start()` + sleep |
| Picamera2 AWB lock | Setting `AwbEnable: False` alongside `ColourGains` — sequencing conflict | Set only `ColourGains`; it implicitly disables AWB |
| Picamera2 ColourGains | Integer tuple `(2, 1)` instead of float `(2.0, 1.0)` | Always pass explicit floats; int input causes TypeError on some Picamera2 versions |
| gpiozero AngularServo | Assuming `pan_servo.angle` reads back hardware state | `pan_servo.angle` reads the last commanded value, not physical servo position — no encoder exists |
| gpiozero AngularServo | Not verifying `pigpiod` is running before init | Init exception falls back to mock mode silently; check `systemctl is-active pigpiod` first |
| simple_pid | Calling `pid.reset()` on face re-acquisition | Reset only at SCANNING entry — resetting during TRACKING loses integral that holds servo on target |
| HAAR CascadeClassifier | Same `minNeighbors`/`minSize` as desktop detection | 320x240 frames require `minSize=(40,40)`, `minNeighbors=4` — desktop defaults miss faces entirely |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `cv2.imshow` resize 2x every frame | High CPU on RPi4 | Resize only when display is active; skip in headless mode | Always on RPi4 — headless mode avoids this entirely |
| HAAR on every frame at 320x240 | ~5ms/frame = 20% of 33ms budget | Acceptable at 320x240; DNN would need frame-skip | Breaks if resolution increases or DNN is substituted without frame-skip |
| `capture_array("lores")` + `cvtColor` in capture thread | Extra copy per frame | Acceptable at 320x240; profile if latency increases | At higher resolutions or with multiple downstream consumers |
| `time.sleep(2.0)` blocking in `Picamera2Stream.start()` | 2s startup delay | Expected and documented; do not reduce below 1s | Not a performance trap — necessary for AWB convergence |

---

## "Looks Done But Isn't" Checklist

- [ ] **AWB fix:** `ColourGains` log line appears in startup output — verify `R=` and `B=` values are non-zero and non-`(0.0, 0.0)`
- [ ] **AWB fix:** Color is neutral from the very first frame — not just after 2 seconds of warm-up
- [ ] **HAAR detection:** Green rectangles visible in HUD when face is 1m away, slightly off-angle — not only at 0.3m perfectly frontal
- [ ] **Tilt tracking:** `Tilt:` HUD value changes when face is held above/below horizontal centerline
- [ ] **Mock mode:** Startup log confirms `_mock_mode=False` and `PIGPIO_AVAILABLE=True`
- [ ] **PID tracking:** TRACKING state sustained for at least 3 seconds without dropping to TARGET_LOST
- [ ] **Scan resume:** No pan jerk visible when transitioning from TRACKING back to SCANNING
- [ ] **Soft limits:** No continuous clamp warnings in logs during normal operation

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Detection never triggers (HAAR too restrictive) | LOW | Reduce `HAAR_MIN_SIZE` to `(40,40)` and `HAAR_MIN_NEIGHBORS` to 4 in `test_tracker.py` constants — no architectural change |
| AWB blue tint persists | LOW | Add `controls={"ColourGains": AWB_FALLBACK_GAINS}` to `create_video_configuration()` call — one line change at configure time |
| AWB wrong fallback gains | LOW | Run camera for 5s in auto mode, read `capture_metadata()["ColourGains"]`, update `AWB_FALLBACK_GAINS` constant |
| Mock mode active silently | LOW | Add `logger.info(f"Mock mode: {self._mock_mode}")` in `MaszynaStanow.__init__`; run `sudo pigpiod` if missing |
| Phase offset non-convergent | MEDIUM | Replace `_scan_phase_offset` with `_scan_start_time` reference; change `_skanuj()` to use relative time |
| Pan runaway (true PID sign bug) | LOW | Verify with `set_angles(+10, 0)` directly — confirm pan+ moves camera right; then re-derive sign from first principles |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| HAAR too restrictive — no detection | Phase 1: Detection fix | Green rectangles visible at 1m, slight angle; TRACKING sustained 3+ seconds |
| Diagnosing PID without stable detection | Phase 1: Detection fix | Confirm TRACKING lasts 10+ frames before any PID analysis |
| AWB blue tint — configure-time lock missing | Phase 2: AWB fix | Color neutral from frame 1; ColourGains lock log shows non-zero floats |
| AWB fallback gains wrong for lighting | Phase 2: AWB fix | Read and log auto-settled gains; update `AWB_FALLBACK_GAINS` to match |
| Mock mode invisible in HUD | Phase 0 (pre-flight) | Add `[MOCK]` to HUD state label; verify pigpiod active before run |
| Phase offset non-convergent scan resume | Phase 3: Scan fix | No pan jerk at TRACKING→SCANNING transition |
| Soft limits masking PID corrections | All phases | Clamp warning logs appear only at boundaries, not continuously |

---

## Sources

### Primary (HIGH confidence — direct code analysis)
- `src/modes/test_tracker.py` — `HAAR_MIN_NEIGHBORS=8`, `HAAR_MIN_SIZE=(80, 80)`, `_przejdz_do()` phase offset formula, `Picamera2Stream.start()` AWB sequence, `_rysuj_hud()` HUD value source
- `src/hardware.py` — `set_angles()` always updates software state regardless of `_mock_mode`; gpiozero init exception falls back to mock silently
- `src/config.py` — `PAN_LIMIT_MIN=-60`, `TILT_LIMIT_MIN=-30`, PID gains; `SCAN_AMPLITUDE=45.0`, `SCAN_FREQUENCY=0.1`

### Secondary (MEDIUM-HIGH confidence — verified community sources)
- [GitHub raspberrypi/picamera2 issue #977](https://github.com/raspberrypi/picamera2/issues/977) — AwbMode has no effect on Bookworm 64-bit (March 2024); `ColourGains` direct set is the working workaround
- [GitHub raspberrypi/picamera2 issue #933](https://github.com/raspberrypi/picamera2/issues/933) — Maintainer: "setting a control value does not mean it has happened immediately"; controls in `create_video_configuration()` apply at configure time and guarantee first-frame values
- [GitHub raspberrypi/picamera2 issue #825](https://github.com/raspberrypi/picamera2/issues/825) — `AwbEnable: False` + `ColourGains` in same `set_controls()` causes sequencing conflicts; set only `ColourGains`
- [GitHub raspberrypi/picamera2 discussions #592](https://github.com/raspberrypi/picamera2/discussions/592) — Maintainer confirms: setting `ColourGains` implicitly disables AWB; `capture_metadata()["ColourGains"]` returns settled auto values; `(0.0, 0.0)` means AWB still running
- [RPi Forums t=365052](https://forums.raspberrypi.com/viewtopic.php?t=365052) — AWB lock sequence: `set_controls` must follow `configure`; engineer confirms `calling configure wipes out any other settings`
- OpenCV HAAR documentation — `minNeighbors=3` is the standard default; values above 5 significantly reduce detection rate; `minSize` must be scaled for target resolution

---
*Pitfalls research for: v1.8 Critical Hardware Fix — ARIES-LITE RPi4 pan-tilt face tracker*
*Researched: 2026-03-29*
