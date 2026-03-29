# Stack Research

**Domain:** Picamera2 + pigpio face tracking on RPi4 Bookworm 64-bit
**Researched:** 2026-03-26 (base), 2026-03-27 (v1.7 supplement), 2026-03-29 (v1.8 supplement), 2026-03-29 (v1.9 supplement)
**Confidence:** HIGH (source-verified against official docs, GitHub issues, and simple_pid source code)

---

## v1.9 Supplement: Motion Stabilization and Color Fix Research

**Milestone:** v1.9 Stabilizacja Ruchu i Obrazu
**Researched:** 2026-03-29

This section answers the four specific fix questions for v1.9:
1. Tilt servo unresponsive in all modes (SCANNING and TRACKING)
2. Scanning is jerky/choppy — smooth servo interpolation needed
3. Green tint from start (G channel constant, scene-independent)
4. Servo escape immediately on TRACKING entry

No new pip packages are required for any of these fixes.

---

### Fix 1: Tilt Servo Unresponsive — Diagnosis Paths

**Problem:** Tilt servo does not react in either SCANNING or TRACKING mode.
Physical servo is confirmed working (resists manual force).

#### Root Cause Path A: `_skanuj()` sends `tilt=0.0` always (HIGH confidence)

Looking at `src/modes/test_tracker.py` line 303:
```python
def _skanuj(self) -> None:
    pan = SCAN_AMPLITUDE * math.sin(...)
    self.hardware.set_angles(pan, 0.0)   # tilt hardcoded to 0.0
```

During SCANNING the tilt is intentionally held at 0.0. This is correct design — the sinusoidal scan is pan-only. Tilt movement only happens in `_sledz()` during TRACKING.

If TRACKING is never reached (face not detected reliably enough to pass streak filter and trigger `_przejdz_do(STATE_TRACKING)`), tilt never fires.

**Diagnosis:** Enable `--debug` flag and watch for `TRACKING` entry log. If it never appears, tilt not moving in SCANNING is expected behavior.

#### Root Cause Path B: tilt_angle attribute not being updated (HIGH confidence)

`set_angles()` in `src/hardware.py` stores the clamped value to `self.tilt_angle`.
If `tilt_clamped` equals the current `self.tilt_angle` on every call (i.e., the
servo is already at the clamped limit), the servo receives the same PWM value and
appears frozen.

This is the servo-escape-then-freeze pattern: PID drives tilt to limit on first tick,
then every subsequent call is clamped at that same limit — log shows WARNING clamp on
every tick but physical servo position does not change.

**Diagnosis:** Add `logger.debug` after `set_angles` call in `_sledz`:
```python
self.hardware.set_angles(nowy_pan, nowy_tilt)
logger.debug(f"set_angles called: pan={nowy_pan:.1f} tilt={nowy_tilt:.1f} "
             f"stored: pan={self.hardware.pan_angle:.1f} tilt={self.hardware.tilt_angle:.1f}")
```

#### Root Cause Path C: pigpio tilt pin not initialized (MEDIUM confidence)

If `pigpiod` daemon was restarted between sessions, gpiozero may silently lose the
tilt servo reference while pan works. Pan pin 12 and tilt pin 13 are initialized
together in `PanTiltSystem.__init__`. If the `AngularServo(tilt_pin, ...)` call
raises an exception and is silently caught, `self.tilt_servo` remains None.

Current `hardware.py` logs this at ERROR level:
```python
logger.error(f"Nie mozna uruchomic pigpio. Sprawdz czy dziala demon (sudo pigpiod): {e}")
self._mock_mode = True
```

But if `self.tilt_servo` is None while `self.pan_servo` is valid (partial failure),
the condition `if not self._mock_mode and self.pan_servo and self.tilt_servo:` prevents
any servo from being commanded. Check: add per-servo init logging.

**Recommendation for tilt diagnosis:** Add explicit guard and log in `set_angles`:
```python
if not self._mock_mode:
    if self.pan_servo:
        self.pan_servo.angle = self.pan_angle
    else:
        logger.warning("pan_servo is None — skip pan command")
    if self.tilt_servo:
        self.tilt_servo.angle = self.tilt_angle
    else:
        logger.warning("tilt_servo is None — skip tilt command")
```

This separates the two servos so one None does not silence both.

**No new libraries needed.** Pure logic fix in `hardware.py`.

---

### Fix 2: Smooth Servo Interpolation for Scanning

**Problem:** Sinusoidal scanning appears jerky/choppy. Each call to `_skanuj()` directly
sets a new absolute angle with no interpolation between positions.

**Root cause analysis:**

The main loop in `TestTracker.uruchom()` calls `self.maszyna.tick()` on every frame.
Each frame where SCANNING is active calls `_skanuj()` which calls `set_angles(pan, 0.0)`
directly. At 8–12 FPS (DNN inference on RPi4), the sinusoidal function is sampled 8–12
times per second. Between samples, the servo jumps discretely — this is the jitter.

**Why pigpio hardware PWM still jerks:**

pigpio eliminates OS-level PWM jitter. It does not smooth the angle commands that the
Python code issues. If Python sends pan=10 on frame N and pan=18 on frame N+1, the
servo moves instantly from 10 to 18 degrees — no interpolation, no easing.

**Recommended solution: Per-tick angle interpolation in `set_angles` (or a wrapper)**

Implement exponential smoothing (low-pass filter) on the commanded angle:
```python
SERVO_ALPHA = 0.4  # smoothing factor, 0 = no movement, 1 = instant
                   # 0.3–0.5 is good starting range for 10 FPS

class PanTiltSystem:
    def __init__(self, ...):
        ...
        self._pan_target = 0.0   # desired angle
        self._tilt_target = 0.0  # desired angle
        # pan_angle / tilt_angle remain as current (smoothed) angle

    def set_angles(self, pan: float, tilt: float) -> None:
        pan_clamped = max(config.PAN_LIMIT_MIN, min(config.PAN_LIMIT_MAX, pan))
        tilt_clamped = max(config.TILT_LIMIT_MIN, min(config.TILT_LIMIT_MAX, tilt))
        self._pan_target = pan_clamped
        self._tilt_target = tilt_clamped

    def update_servos(self) -> None:
        """Call once per main loop tick to advance smoothed position."""
        alpha = config.SERVO_ALPHA
        self.pan_angle += alpha * (self._pan_target - self.pan_angle)
        self.tilt_angle += alpha * (self._tilt_target - self.tilt_angle)
        if not self._mock_mode and self.pan_servo and self.tilt_servo:
            self.pan_servo.angle = self.pan_angle
            self.tilt_servo.angle = self.tilt_angle
```

Call `self.hardware.update_servos()` once per main loop tick in `TestTracker.uruchom()`
after `self.maszyna.tick(...)`.

**Why exponential smoothing (not linear interpolation or easing curves):**

- Linear interpolation requires knowing start and end and a fixed step count — adds
  complexity and breaks when the setpoint changes every frame (which it does during PID).
- Easing curves (sine, cubic) are designed for scripted motions to fixed targets —
  not for real-time dynamic control where target changes continuously.
- Exponential smoothing (EMA) is a single-line, stateless operation. Alpha controls
  the bandwidth: small alpha = very smooth but slow; large alpha = fast but less smooth.
- This is the standard technique for servo smoothing in robotics control loops.
  HIGH confidence — used in virtually all real-time servo tracking implementations.

**SERVO_ALPHA tuning guidance:**

| Alpha | Behavior | Use |
|-------|----------|-----|
| 0.2 | Very smooth, slow response | OK for scanning, too slow for tracking |
| 0.4 | Balanced — smooth scan, acceptable tracking lag | Recommended starting point |
| 0.6 | Fast response, small smoothing benefit | Aggressive tracking with slight smoothing |
| 1.0 | No smoothing (current behavior) | Instant jump, jerky |

**Important: smooth_move_to() is unaffected** — it uses blocking while-loop and calls
`set_angles()` with immediate application. The smoothing wrapper should be optional,
activated only in the real-time loop. If `update_servos()` approach is used, ensure
`smooth_move_to()` bypasses it (use direct servo assignment) to preserve safe-start behavior.

**Alternative considered: separate background thread for servo interpolation**

A dedicated servo thread sleeping 20ms could interpolate at 50Hz independent of
the camera/detection rate. This decouples servo smoothness from detection FPS.
However, it adds thread complexity and requires shared state synchronization.
For this project's scope, EMA in the main loop is simpler and sufficient.

**No new libraries needed.** Pure Python implementation.

---

### Fix 3: AWB / ColourGains Green Tint — Root Cause and Fix

**Problem:** Green tint visible from first frame, constant G channel regardless of scene.
Previous fix set `ColourGains=(1.0, 1.0)` in `create_video_configuration()`, replacing
a blue tint with a green tint.

#### Why `(1.0, 1.0)` causes green tint (HIGH confidence)

`ColourGains = (red_gain, blue_gain)` — green is NOT a direct parameter.

In a camera's ISP pipeline, the white balance gains are applied to R and B channels.
Green is used as the reference channel and is not directly amplified. When you set:
- `red_gain = 1.0` — red suppressed relative to daylight calibration (typically 1.5–2.5)
- `blue_gain = 1.0` — blue suppressed relative to daylight calibration (typically 1.5–2.0)

The result is that R and B are underamplified. Since G is the reference, the image
appears green because G is relatively brighter than R or B.

Setting `(1.0, 1.0)` does not mean "neutral" — it means "suppress both red and blue
to 1x amplification." For the IMX219 under typical indoor lighting, the correct AWB
gains are approximately R=1.5–2.5, B=1.5–2.0 (scene-dependent).

**Source:** raspberrypi/picamera2 discussion #592 — maintainer confirms that
setting ColourGains disables AWB and sets exact gains as specified. (HIGH confidence)

#### Why the current code produces wrong gains

Current `Picamera2Stream.start()` sets `ColourGains=(1.0, 1.0)` in
`create_video_configuration()`. This locks the gains at configure time, BEFORE AWB
has run at all. The camera never gets to auto-calculate appropriate gains.

This is doubly wrong:
1. Gains set at configure time may not be applied the same way as gains set after start
2. `(1.0, 1.0)` is not a neutral value — it suppresses red and blue

#### Correct AWB lock sequence (HIGH confidence — picamera2 official docs + issue #592)

The only reliable sequence to get correct white balance:

```python
def start(self) -> None:
    self._picam2 = Picamera2()
    video_config = self._picam2.create_video_configuration(
        lores={"size": (self._width, self._height), "format": "YUV420"}
        # Do NOT set ColourGains here — let AWB run first
    )
    self._picam2.configure(video_config)
    self._picam2.start()

    # Wait for AWB to converge on actual scene illumination
    logger.info("Czekam na stabilizację AWB (2s)...")
    time.sleep(2.0)

    # Read what AWB converged to
    metadata = self._picam2.capture_metadata()
    gains = metadata.get("ColourGains")
    logger.info(f"ColourGains z AWB: {gains}")

    if gains is None or gains == (0.0, 0.0):
        # AWB did not produce gains — use realistic fallback for IMX219 daylight
        gains = (2.2, 1.8)   # NOT (1.0, 1.0) — see above
        logger.warning(f"AWB nie zwróciło gains — używam fallback {gains}")

    # Lock at AWB-determined values — this also disables auto AWB
    self._picam2.set_controls({"ColourGains": (float(gains[0]), float(gains[1]))})

    # Verify application (next metadata read reflects new gains)
    time.sleep(0.1)
    post_meta = self._picam2.capture_metadata()
    post_gains = post_meta.get("ColourGains")
    r, b = gains
    logger.info(f"ColourGains żądane=(R={r:.2f}, B={b:.2f}) zastosowane={post_gains}")
```

#### AWB_FALLBACK_GAINS constant update required

The constant `AWB_FALLBACK_GAINS = (1.0, 1.0)` in `test_tracker.py` must be changed
to a realistic neutral value. Recommended:
```python
AWB_FALLBACK_GAINS = (2.2, 1.8)  # IMX219 typowe oświetlenie wewnętrzne
```

Rationale: This matches the real-world range documented in RPi forum discussions
(ColourGains values like `(2.522, 1.897)` and `(1.88, 0.941)` are commonly reported
for IMX219). The fallback is only used when `capture_metadata()` returns None or (0.0, 0.0),
which indicates AWB did not complete — the realistic fallback avoids visible green tint.

#### YUV conversion flag — confirm NV12 vs YUV420p (from v1.8 research, still relevant)

If correcting ColourGains does not eliminate tint, the YUV conversion flag may be wrong.
Picamera2 on Bookworm typically produces NV12 (semi-planar). Using `cv2.COLOR_YUV420p2BGR`
on NV12 data produces systematic color error. Test `cv2.COLOR_YUV2BGR_NV12` instead.

**No new libraries needed.** Fix is configuration-only in `Picamera2Stream.start()`.

---

### Fix 4: Servo Escape on TRACKING Entry — PID Anti-Windup and Output Clamping

**Problem:** Servos immediately run to limits when TRACKING state is entered.

#### Why this happens: integral windup across state transitions (HIGH confidence)

When the system is in SCANNING and a face is detected, `_przejdz_do(STATE_TRACKING)`
is called. This calls `pid_pan.reset()` and `pid_tilt.reset()` correctly.

However, if the face detection produces an initial large error (e.g., face is at the
extreme edge of frame at 150px offset), the first `_sledz()` call computes:
- `blad_pan = 150` (large)
- `pid_pan(150)` with P=0.05 → P-term = 0.05 × 150 = 7.5 degrees
- `output_limits = (-10.0, 10.0)` — this is within limits, so output = -7.5
- `nowy_pan = current_pan + (-7.5)` — large jump immediately

At 10 FPS with `sample_time=0.033` (30ms), the PID controller updates faster than
`sample_time` allows but the integral has not accumulated yet. The P-term alone on
a large initial error creates the escape.

**Root cause confirmation:** with `PID_PAN_P = 0.05` and pixel error of 160px (max,
face at frame edge):
- P-term = 0.05 × 160 = 8.0 degrees per tick
- After 2 ticks: 16 degrees → 60-degree limit reached in ~8 ticks

This is the expected P-gain behavior with large initial error, not a bug in the PID
library. The fix is output clamping that is already in place — the issue is the
output_limits value relative to the P gain.

#### Fix A: Tighten PID_OUTPUT_LIMIT (HIGH confidence, immediate effect)

`PID_OUTPUT_LIMIT = 10.0` in `test_tracker.py` allows 10 degrees/tick correction.
At 10 FPS this is 100 degrees/second — too fast for smooth tracking.

Recommended range: 3.0–5.0 degrees per tick.

```python
PID_OUTPUT_LIMIT = 3.0   # Maximum correction per PID tick (degrees)
```

This means at 10 FPS: max 30 degrees/second servo velocity. The servo will still
reach the target but more gradually, preventing escape to limits.

The `output_limits` on the PID objects must be updated to match:
```python
self.pid_pan.output_limits = (-PID_OUTPUT_LIMIT, PID_OUTPUT_LIMIT)
self.pid_tilt.output_limits = (-PID_OUTPUT_LIMIT, PID_OUTPUT_LIMIT)
```

**Why simple-pid output_limits is the correct tool here (HIGH confidence — source verified):**

From `simple_pid/pid.py` source: output limits clamp both the final output AND the
integral accumulator on every call. This is the built-in anti-windup mechanism.
The integral is not allowed to grow beyond the output limit bounds. So tightening
`output_limits` directly reduces maximum per-tick correction AND prevents windup.

The `reset()` call already in `_przejdz_do()` is correct behavior. The problem is
not windup on TRACKING entry (integral is zero after reset) — it is the P-term
magnitude on large initial errors. Output limiting is the right fix.

#### Fix B: Add error deadband (MEDIUM confidence — standard technique)

Ignore small errors to prevent micromovement:
```python
TRACKING_DEADBAND_PX = 15  # pixels — don't correct if error below this

def _sledz(self, bbox, w, h):
    ...
    if abs(blad_pan) < TRACKING_DEADBAND_PX:
        blad_pan = 0.0
    if abs(blad_tilt) < TRACKING_DEADBAND_PX:
        blad_tilt = 0.0
    ...
```

This prevents continuous micro-corrections when the face is approximately centered,
reducing servo wear and oscillation. Does not prevent escape on large initial errors —
use in combination with Fix A, not as a replacement.

#### Fix C: Proportional on measurement vs. on error

`simple-pid` supports `proportional_on_measurement=True` which computes the P-term
from the rate of change of input rather than error magnitude. This prevents the
"derivative kick" on large setpoint changes.

For face tracking with setpoint=0 (error is the input), this mode is equivalent to
using the derivative term as the primary dampener. The current code uses
`proportional_on_measurement=False` (default), which is correct for this application.
Changing this would reduce initial P-term response but would require re-tuning all gains.

**Verdict: Do not change proportional_on_measurement.** Fix A (tighten output_limits)
is the correct and simpler intervention.

#### Recommended PID configuration for v1.9

```python
# In test_tracker.py constants
PID_OUTPUT_LIMIT = 3.0    # was 10.0 — tighter clamp prevents escape
TRACKING_DEADBAND_PX = 15  # new — suppress micro-corrections

# In config.py (if PID gains need retuning post output-limit change)
# Start with existing values, reduce if still oscillating:
PID_PAN_P = 0.05   # unchanged
PID_PAN_I = 0.001  # unchanged
PID_PAN_D = 0.005  # unchanged
PID_TILT_P = 0.05  # unchanged — only adjust if still escaping after limit change
```

**Tuning protocol after fix (empirical, per project methodology):**

1. Deploy with `PID_OUTPUT_LIMIT = 3.0` — confirm no escape
2. If tracking is too sluggish (face moves fast, servo can't keep up), increase to 5.0
3. If oscillation occurs, reduce `PID_PAN_P` by 20% (0.05 → 0.04)
4. If steady-state offset remains (face held right of center permanently), increase `PID_PAN_I` by 50%

**No new libraries needed.** Fix is constant and logic change only.

---

## Recommended Stack Additions for v1.9

### New Dependencies

**None.** All four fixes use existing installed libraries.

### Constants / Configuration Changes Required

| File | Constant | Old Value | New Value | Reason |
|------|----------|-----------|-----------|--------|
| `src/modes/test_tracker.py` | `AWB_FALLBACK_GAINS` | `(1.0, 1.0)` | `(2.2, 1.8)` | `(1.0, 1.0)` suppresses R and B, causing green tint |
| `src/modes/test_tracker.py` | `PID_OUTPUT_LIMIT` | `10.0` | `3.0` | 10 deg/tick at 10 FPS = uncontrolled escape; 3.0 limits velocity |
| `src/modes/test_tracker.py` | `TRACKING_DEADBAND_PX` | (new) | `15` | Suppress micro-corrections, reduce oscillation |
| `src/config.py` | `SERVO_ALPHA` | (new) | `0.4` | Exponential smoothing factor for scan smoothness |

### Code Changes Required

| File | Class/Function | Change Type | Description |
|------|---------------|-------------|-------------|
| `src/modes/test_tracker.py` | `Picamera2Stream.start()` | Logic fix | Remove `ColourGains` from `create_video_configuration()`, read AWB metadata after 2s, use realistic fallback |
| `src/hardware.py` | `PanTiltSystem` | New method | Add `update_servos()` with EMA smoothing, add `_pan_target`/`_tilt_target` fields |
| `src/hardware.py` | `set_angles()` | Refactor | Store to target fields instead of direct servo command |
| `src/modes/test_tracker.py` | `TestTracker.uruchom()` | Add call | Call `self.hardware.update_servos()` once per main loop tick |
| `src/modes/test_tracker.py` | `MaszynaStanow._sledz()` | Add deadband | Zero blad_pan/blad_tilt below TRACKING_DEADBAND_PX before PID call |
| `src/hardware.py` | `set_angles()` | Split per-servo | Separate pan_servo and tilt_servo null-checks to diagnose tilt freeze |

---

## Alternatives Considered for v1.9

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Exponential smoothing (EMA) in main loop | Separate servo interpolation thread | Thread adds shared state complexity; EMA in main loop is simpler and sufficient at 10 FPS |
| EMA alpha=0.4 | Fixed step size (smooth_move_to style) | Fixed step breaks for dynamic PID targets that change every frame; EMA adapts automatically |
| Tighten PID_OUTPUT_LIMIT to 3.0 | Reduce PID_PAN_P | Output limit is the correct tool for escape prevention; gain reduction changes convergence behavior and requires full re-tuning |
| AWB metadata read + set_controls | Manual ColourGains values hardcoded | Hardcoded values are scene-specific; reading actual AWB output adapts to room lighting |
| AWB fallback (2.2, 1.8) | Keep fallback (1.0, 1.0) | (1.0, 1.0) suppresses R and B, causing green tint as documented |
| Per-servo null-check in set_angles | Mock mode flag for full system | Per-servo check pinpoints whether only tilt init failed vs. whole hardware layer |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `ColourGains: (1.0, 1.0)` | Suppresses red and blue relative to green reference; causes green tint. Not a neutral value. | Read actual AWB gains from `capture_metadata()` after 2s warmup |
| `ColourGains` in `create_video_configuration()` | Applied before AWB has run; gains may not reflect actual scene illumination | Set via `set_controls()` after `start()` + sleep |
| `PID_OUTPUT_LIMIT = 10.0` with P=0.05 | At 10 FPS, 10 deg/tick = 100 deg/s max velocity; face at frame edge (160px error) drives P-term to 8 deg/tick — escape in 8 frames | `PID_OUTPUT_LIMIT = 3.0` limits to 30 deg/s maximum |
| Direct `servo.angle = value` in main loop for scanning | Servo receives discrete angle commands at frame rate (10 FPS); produces visible stepping | EMA filter in `update_servos()` smooths position between frames |
| `smooth_move_to()` for real-time tracking | Blocking while-loop; will block the entire tracking thread until target is reached | EMA in non-blocking `update_servos()` called once per tick |

---

## Version Compatibility (v1.9)

| Package | Version | Notes |
|---------|---------|-------|
| simple-pid | >=2.0.1 (pinned) | `output_limits` clamps integral (anti-windup confirmed from source); `reset()` zeroes all terms |
| picamera2 | system pkg (>=0.3.x) | `capture_metadata()["ColourGains"]` returns `(red, blue)` tuple; `set_controls({"ColourGains": ...})` disables AWB implicitly |
| gpiozero | 2.0 (pinned) | `AngularServo.angle` accepts float; direct assignment is immediate (no built-in smoothing) |
| pigpio | 1.78 (pinned) | Hardware PWM eliminates OS-level jitter; Python-level angle stepping still discrete |

---

## v1.8 Supplement (preserved from 2026-03-29)

This section answers the three specific questions raised for the v1.8 milestone:
1. Better face detector on RPi4 (replaces overly strict HAAR cascade)
2. Picamera2 AWB/ColourGains debugging for IMX219 sensor on Bookworm
3. PID diagnostic logging patterns for servo runaway debugging

It supersedes any previous speculation on these topics.

---

### 1. Face Detector Replacement — Decision: OpenCV DNN (res10_300x300)

**Recommendation: OpenCV DNN with `res10_300x300_ssd_iter_140000.caffemodel`**

**Rationale:** Three options were evaluated.

#### Option A: MediaPipe Face Detection — REJECTED

**Installation blocker on RPi4 Bookworm (64-bit):**

MediaPipe PyPI (latest 0.10.33 as of March 2026) does NOT publish a Linux aarch64 wheel.
The PyPI page lists wheels only for: Windows x86-64, Linux x86-64, macOS ARM64.
Linux ARM64 (which RPi4 Bookworm 64-bit requires) is absent.

Workarounds exist but add maintenance cost:
- PINTO0309/mediapipe-bin: community-maintained, tracks behind official releases,
  not a reliable dependency for a production system
- Build from source: requires Docker + 4+ hour compile time on RPi4

Additionally, MediaPipe achieves 9–12 FPS on RPi4 CPU-only (confirmed by benchmark
from SaraEye/SaraKIT project) — competitive but with a heavyweight installation
that is not straightforward on the target platform.

**Verdict: Do not use MediaPipe for this project.**

Sources:
- PyPI mediapipe 0.10.33: no aarch64 Linux wheel listed
- GitHub google-ai-edge/mediapipe issue #4673: confirms aarch64 install problems
- PINTO0309/mediapipe-bin: community wheel workaround (fragile)

#### Option B: OpenCV DNN (res10_300x300_ssd) — RECOMMENDED

**Why this is the right choice:**

Already on the system. `opencv-python-headless==4.8.1.78` is pinned in requirements.txt.
The DNN module is bundled with OpenCV — no additional pip install needed.
Only two external model files are required (~2MB total), downloaded once and committed.

**Performance on RPi4 (64-bit, 300x300 input):**
- DNN SSD res10 at 320x240 input: approximately 8–12 FPS (MEDIUM confidence — Q-engineering
  benchmarks show the Ultra-Light-Fast slim-320 model at ~35–40 FPS with OpenCV,
  but that is a different model; the res10 SSD Caffe model is slower due to ResNet-10 backbone)
- HAAR at current settings (minNeighbors=8, minSize=80px): measured in project as
  producing near-zero detections — the bottleneck is sensitivity, not FPS

At 320x240 input the inference cost is lower than 300x300 because the blob resize
is from a smaller input. Real throughput in the 8–15 FPS range is acceptable for the
control loop (HAAR runs similarly on the same hardware when detection fires).

**Accuracy advantage:** DNN SSD detects faces at non-frontal angles (+/-30 degrees),
partial occlusions, and lower contrast. HAAR with minNeighbors=8 requires near-perfect
frontal alignment — verified as the root cause of "brak zielonej ramki" in PROJECT.md.

**Integration path is minimal:**
```python
# Drop-in replacement inside DetekcjaTwarzy
net = cv2.dnn.readNetFromCaffe(prototxt_path, caffemodel_path)
blob = cv2.dnn.blobFromImage(klatka, 1.0, (300, 300), (104, 177, 123))
net.setInput(blob)
detections = net.forward()
# detections[0, 0, i, 2] is confidence; [3:7] is x1,y1,x2,y2 normalized
```

The class `DetekcjaTwarzy` in `src/modes/test_tracker.py` becomes a thin wrapper
around this net — streak filter and bbox selection logic stays identical.

**Model files (must be downloaded and committed to repo or a `models/` directory):**

| File | Size | Source |
|------|------|--------|
| `deploy.prototxt` | ~28KB | github.com/sr6033/face-detection-with-OpenCV-and-DNN |
| `res10_300x300_ssd_iter_140000.caffemodel` | ~10.1MB | same repo or OpenCV samples |

**Confidence threshold:** 0.5 is the standard default. For a face-tracking system with
streak filter in place, 0.5 works well. Lower to 0.4 if detections are sparse.

#### Option C: OpenCV HAAR (improved parameters) — PARTIAL FIX ONLY

Relaxing `minNeighbors` from 8 to 4–5 and `minSize` from (80,80) to (50,50) will
improve detection rate without any new dependency. However:
- Still fails at head rotation > ~15 degrees
- False-positive rate increases noticeably without dlib backup
- Appropriate only as a quick interim test, not the final fix

**Verdict: Use OpenCV DNN as the replacement. Keep HAAR fallback path available for
testing, controlled by a constructor flag.**

---

### 2. Picamera2 AWB/ColourGains Debugging — IMX219 on Bookworm

**Context:** v1.7 shipped AWB lock code. PROJECT.md says "AWB lock via set_controls
after start()+2s sleep — Good — eliminates blue tint." v1.8 reports blue tint has
returned or the fix did not execute correctly.

**Diagnostic checklist (in priority order):**

#### Check A: `ColourGains` capitalization (HIGH confidence — confirmed bug in picamera2)

GitHub issue #312 documented a case-sensitivity bug in older picamera2 versions.
The correct key is `"ColourGains"` (capital G). Using `"Colourgains"` silently fails
in older versions and raises `RuntimeError` in newer ones.

Verify the exact string in `Picamera2Stream.start()`:
```python
self._picam2.set_controls({"ColourGains": gains})  # capital G — correct
```

#### Check B: `ColourGains = (0.0, 0.0)` treated as AWB-on

Confirmed from picamera2 issue #825: setting `ColourGains` to exactly `(0.0, 0.0)`
is interpreted by libcamera as "enable AWB". If `capture_metadata()` returns
`ColourGains = (0.0, 0.0)` (which can happen if the sensor has not yet computed
AWB at 2s warmup — e.g., dark room, camera just reset), the fallback `(2.5, 1.9)`
is used. But if the fallback gains are wrong for current lighting, blue tint persists.

**Fix: Add verification log after set_controls to confirm gains were applied:**
```python
time.sleep(0.1)  # brief settle after set_controls
post_meta = self._picam2.capture_metadata()
applied = post_meta.get("ColourGains")
logger.info(f"Gains po ustawieniu: {applied}")
```

The second `capture_metadata()` call reads the controls from the next delivered frame,
confirming the gains were actually applied to the pipeline.

#### Check C: YUV420 subformat (NV12 vs YUV420p) — HIGH confidence

This was documented in the v1.7 research STACK.md but may not have been acted upon.
Picamera2 on Bookworm with IMX219 delivers YUV420 as NV12 (semi-planar), NOT YUV420p
(fully planar). Using `cv2.COLOR_YUV420p2BGR` on NV12 data produces a systematic colour
error that LOOKS like a blue tint because the UV plane interleaving is misread.

**Test: print the YUV frame shape before conversion:**
```python
logger.info(f"YUV klatka shape: {klatka_yuv.shape}")
# 320x240 YUV → expected (360, 320) for both NV12 and YUV420p
# Shape alone does not distinguish — must test both flags
```

**Diagnostic code for `_petla_przechwytywania`:**
```python
# Try NV12 first — this is what Picamera2/libcamera produces on Bookworm
klatka_nv12 = cv2.cvtColor(klatka_yuv, cv2.COLOR_YUV2BGR_NV12)
klatka_p = cv2.cvtColor(klatka_yuv, cv2.COLOR_YUV420p2BGR)
# Log average B channel value of both; correct one will have B ~= G ~= R under white light
b_nv12 = klatka_nv12[:,:,0].mean()
b_p = klatka_p[:,:,0].mean()
logger.debug(f"NV12 avg B={b_nv12:.1f}  YUV420p avg B={b_p:.1f}")
```

The correct conversion flag produces roughly equal mean values across R, G, B channels
under neutral white light. A blue tint produces B significantly higher than R.

**Recommendation:** Change default to `cv2.COLOR_YUV2BGR_NV12` and verify. If image
looks correct, the old flag was wrong. This is the single most likely cause of
persistent blue tint after AWB gains are set correctly.

#### Check D: AWB warm-up duration

2 seconds is documented to be sufficient for IMX219 under normal conditions.
However, on cold start in a dark room or with significant backlight, AWB may need
longer. If `ColourGains` from `capture_metadata()` looks unreasonable (e.g., gains
below 1.0 or above 4.0), extend sleep to 3–4 seconds and re-test.

#### Recommended minimal AWB debug patch for v1.8:

```python
def start(self) -> None:
    self._picam2 = Picamera2()
    video_config = self._picam2.create_video_configuration(
        lores={"size": (self._width, self._height), "format": "YUV420"}
    )
    self._picam2.configure(video_config)
    self._picam2.start()

    logger.info("Czekam na stabilizację AWB (2s)...")
    time.sleep(2.0)

    metadata = self._picam2.capture_metadata()
    gains = metadata.get("ColourGains")
    logger.info(f"ColourGains z metadanych: {gains}")  # NEW: log raw value

    if gains is None or gains == (0.0, 0.0):
        logger.warning("ColourGains niedostępne lub zerowe — używam fallback (2.5, 1.9)")
        gains = AWB_FALLBACK_GAINS

    self._picam2.set_controls({"ColourGains": gains})

    # NEW: verify gains were applied
    time.sleep(0.1)
    post_meta = self._picam2.capture_metadata()
    applied_gains = post_meta.get("ColourGains")
    r, b = gains
    logger.info(f"ColourGains żądane: (R={r:.2f}, B={b:.2f}) | zastosowane: {applied_gains}")

    self._running = True
    self._thread = threading.Thread(target=self._petla_przechwytywania, daemon=True)
    self._thread.start()
```

No new dependencies required. Pure Picamera2 API.

---

### 3. PID Diagnostic Logging — simple-pid `components` Property

**Context:** v1.8 reports pan runaway (instant escape to limit) and tilt frozen at 0.0.
These are opposite failure modes requiring different root causes. Per-tick PID logging
is the only reliable way to distinguish them without physical access to the hardware.

**simple-pid `components` property — HIGH confidence (verified from source code)**

Since v2.0, simple-pid exposes a `components` property returning `(P, I, D)` tuple
of the last computed terms:

```python
p_term, i_term, d_term = pid.components
# Available after any pid(error) call — read immediately after the call
```

Source: `github.com/m-lundberg/simple-pid/blob/master/simple_pid/pid.py`

**Diagnostic logging pattern for `_sledz` in `MaszynaStanow`:**

```python
def _sledz(self, bbox, w, h):
    x, y, bw, bh = bbox
    srodek_x = x + bw // 2
    srodek_y = y + bh // 2
    ramka_cx, ramka_cy = w // 2, h // 2

    blad_pan = srodek_x - ramka_cx
    blad_tilt = srodek_y - ramka_cy

    korekta_pan = -self.pid_pan(blad_pan)
    p_pan, i_pan, d_pan = self.pid_pan.components

    korekta_tilt = -self.pid_tilt(blad_tilt)
    p_tilt, i_tilt, d_tilt = self.pid_tilt.components

    nowy_pan = self.hardware.pan_angle + korekta_pan
    nowy_tilt = self.hardware.tilt_angle + korekta_tilt

    logger.debug(
        f"blad=({blad_pan:+.0f},{blad_tilt:+.0f}) "
        f"pid_out=({korekta_pan:+.2f},{korekta_tilt:+.2f}) "
        f"PID_pan=P{p_pan:+.3f}/I{i_pan:+.3f}/D{d_pan:+.3f} "
        f"PID_tilt=P{p_tilt:+.3f}/I{i_tilt:+.3f}/D{d_tilt:+.3f} "
        f"angles=({nowy_pan:+.1f},{nowy_tilt:+.1f})"
    )

    self.hardware.set_angles(nowy_pan, nowy_tilt)
```

Use `logger.debug` (not `info`) to avoid flooding normal output. Enable with:
```bash
python3 run_test_tracker.py --log-level DEBUG
# or temporarily change basicConfig level to DEBUG in main
```

**What each failure mode looks like in this log:**

| Symptom | Log pattern | Root cause |
|---------|-------------|------------|
| Pan runaway to limit | `blad_pan` small, `korekta_pan` large and growing | I-term windup — integral not reset, or sign error causing positive feedback |
| Tilt frozen at 0.0 | `blad_tilt` non-zero, `korekta_tilt=0.00` every tick | `pid_tilt(blad_tilt)` returns 0 — possible: `output_limits` set to (0,0), or `pid_tilt` never called |
| Tilt frozen at 0.0 (v2) | `korekta_tilt` non-zero, `nowy_tilt` non-zero, but HUD shows 0.0 | `set_angles()` not called, or `tilt_angle` attribute not updated |

**I-term windup detection:** If `i_pan` grows each tick toward `PID_OUTPUT_LIMIT`
(currently 10.0) and the total output is dominated by I-term even when error is small,
that confirms integral windup. Fix: verify `pid_pan.reset()` is called at SCANNING entry.

**Additional: log `set_angles` actual writes (already in hardware.py via WARNING on clamp)**

The clamp WARNING in `set_angles()` (already present in v1.7 hardware.py) will fire
every tick if the servo is hitting limits — that confirms runaway vs. frozen.

**CSV logging (if needed for post-session analysis):**

```python
import csv, io
_pid_log_buffer = io.StringIO()
_pid_csv = csv.writer(_pid_log_buffer)
_pid_csv.writerow(["t","blad_pan","blad_tilt","k_pan","k_tilt","p_pan","i_pan","d_pan","p_tilt","i_tilt","d_tilt"])

# Inside _sledz, after computing terms:
_pid_csv.writerow([time.time(), blad_pan, blad_tilt, korekta_pan, korekta_tilt,
                   p_pan, i_pan, d_pan, p_tilt, i_tilt, d_tilt])
```

Flush to file on shutdown. Visualize with any CSV viewer or numpy/matplotlib.
No additional libraries required — `csv` and `io` are stdlib.

---

## Recommended Stack Additions for v1.8

### New Dependencies

| Package | Version | Source | Purpose | Install |
|---------|---------|--------|---------|---------|
| OpenCV DNN models | n/a | Downloaded once (not pip) | res10 SSD face detection | `models/` directory in repo |

No new pip packages required. All additions use existing installed libraries.

### Model Files to Add

```
models/
  deploy.prototxt                          (~28KB)
  res10_300x300_ssd_iter_140000.caffemodel (~10.1MB — add to .gitignore or LFS)
```

Download script (run once on RPi):
```bash
mkdir -p models
wget -O models/deploy.prototxt \
  "https://raw.githubusercontent.com/sr6033/face-detection-with-OpenCV-and-DNN/master/deploy.prototxt"
wget -O models/res10_300x300_ssd_iter_140000.caffemodel \
  "https://raw.githubusercontent.com/sr6033/face-detection-with-OpenCV-and-DNN/master/res10_300x300_ssd_iter_140000.caffemodel"
```

### requirements.txt — No Changes Needed

The existing pinned stack handles all v1.8 changes:
```
opencv-python-headless==4.8.1.78  # DNN module bundled
simple-pid>=2.0.1                  # components property available since 2.0
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| OpenCV DNN res10_300x300 | MediaPipe Face Detection | No aarch64 Linux wheel on PyPI as of 2026-03-29; requires community builds or compile-from-source |
| OpenCV DNN res10_300x300 | HAAR minNeighbors=4 relaxed | Fixes threshold, not detector — still fails >15deg rotation; acceptable only as interim test |
| simple-pid components property | Custom PID wrapper with logging | components is the official API; wrapping adds indirection for no benefit |
| cv2.COLOR_YUV2BGR_NV12 | cv2.COLOR_YUV420p2BGR | Picamera2 on Bookworm delivers NV12 semi-planar; wrong flag produces systematic blue shift |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `mediapipe` pip install | No aarch64 Linux wheel; PINTO0309 community builds lag behind and add fragile dependency | OpenCV DNN res10_300x300 |
| `ColourGains: (0.0, 0.0)` in set_controls | libcamera interprets (0.0, 0.0) as "enable AWB" — will re-enable auto white balance | Use actual measured gains or fallback (2.5, 1.9) |
| `cv2.COLOR_YUV420p2BGR` without verification | Picamera2 on Bookworm likely outputs NV12 (semi-planar), not planar YUV420p | Test both flags; default to COLOR_YUV2BGR_NV12 |
| Manual `_integral` attribute access in simple-pid | Private attribute; may break between versions | `pid.components` tuple — official public API |
| `logger.info` per tick for PID values | Floods logs at 30 FPS, makes debugging harder | `logger.debug` + enable DEBUG level only when diagnosing |

---

## Version Compatibility

| Package | Version | Notes |
|---------|---------|-------|
| simple-pid | >=2.0.1 (pinned) | `components` property available since 2.0; `reset()` behavior verified |
| opencv-python-headless | 4.8.1.78 (pinned) | DNN module stable, res10 Caffe model compatible |
| picamera2 | system pkg (>=0.3.x) | `capture_metadata()` + `set_controls(ColourGains)` API stable; case-sensitive key required |

---

## v1.7 Supplement (preserved from 2026-03-27)

### 1. simple_pid Sign Convention

**Source:** `github.com/m-lundberg/simple-pid` raw source — HIGH confidence.

```python
error = self.setpoint - input_   # setpoint=0: error = -input
output = Kp * error              # positive input → negative output
```

Both axes require negation of PID output:
```python
korekta_pan  = -self.pid_pan(blad_pan)   # pan+ = right, face right → pan increases
korekta_tilt = -self.pid_tilt(blad_tilt) # tilt+ = down,  face down  → tilt increases
```

### 2. Picamera2 AWB Configuration

Correct API sequence: `configure()` → `start()` → `sleep(2)` → `capture_metadata()`
→ `set_controls({"ColourGains": gains})`. Setting ColourGains implicitly disables AWB.

### 3. simple_pid `reset()` and Anti-Windup

`reset()` clears `_proportional`, `_integral`, `_derivative`, `_last_input`, `_last_error`.
Anti-windup via `output_limits` clamping integral every iteration. Current code is correct —
`reset()` called on SCANNING entry is the right pattern.

---

## Original Stack Reference (unchanged from v1.6 research)

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| picamera2 | >=0.3.x (system pkg) | Camera capture via libcamera | Native camera stack on Bookworm; replaces deprecated picamera/V4L2 |
| pigpio | 1.78+ | Hardware PWM for servos | Validated in v1.5; only library providing true H-PWM on RPi4 |
| opencv-python-headless | 4.8+ | HAAR + DNN face detection | Already in deps; DNN module bundled |
| simple-pid | 2.0+ | PID controller with components property | Already in deps; auto-integral clamping with output_limits |

### Installation

```bash
# System packages (Bookworm 64-bit)
sudo apt install -y python3-picamera2 python3-libcamera

# Venv with system site-packages (CRITICAL for picamera2)
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Python packages (unchanged from v1.7)
pip install -r requirements.txt

# Model files (one-time download)
mkdir -p models
wget -O models/deploy.prototxt \
  "https://raw.githubusercontent.com/sr6033/face-detection-with-OpenCV-and-DNN/master/deploy.prototxt"
wget -O models/res10_300x300_ssd_iter_140000.caffemodel \
  "https://raw.githubusercontent.com/sr6033/face-detection-with-OpenCV-and-DNN/master/res10_300x300_ssd_iter_140000.caffemodel"
```

---

## Sources

### v1.9 supplement (2026-03-29)

- GitHub raspberrypi/picamera2 discussion #592 — maintainer confirms ColourGains=(R,B) tuple where G is reference channel, (1.0,1.0) suppresses R and B (HIGH confidence)
- GitHub raspberrypi/picamera2 issue #897 — green tint root cause: lens shading correction ISP block; workaround: different sensor mode or disable ALSC (MEDIUM confidence)
- RPi Forums t=365052 — correct AWB lock sequence: set_controls after configure(), ColourGains implicitly disables AWB (HIGH confidence)
- GitHub m-lundberg/simple-pid pid.py source — output_limits clamps integral (anti-windup), reset() clears all terms (HIGH confidence)
- PyImageSearch pan/tilt face tracking — PID gains kP=0.09/kI=0.08/kD=0.002 for pan; in_range() clamping prevents runaway (MEDIUM confidence)
- simple-pid readthedocs user guide — output_limits anti-windup, sample_time, proportional_on_measurement (HIGH confidence — blocked by Cloudflare but source code verified separately)
- Hackaday smooth servo animatronics article — EMA smoothing for real-time servo control; alpha tuning guidelines (MEDIUM confidence)
- RPi Forums servo jitter thread t=313651 — pigpio eliminates hardware jitter; Python discrete commands still produce stepping (HIGH confidence)

### v1.8 supplement (2026-03-29)

- PyPI mediapipe 0.10.33 release page — confirmed no aarch64 Linux wheel (HIGH confidence)
- GitHub google-ai-edge/mediapipe issue #4673 — aarch64 install failures confirmed
- PINTO0309/mediapipe-bin — community aarch64 wheel workaround (MEDIUM confidence)
- GitHub Qengineering/Face-detection-Raspberry-Pi-32-64-bits — OpenCV DNN FPS benchmarks on RPi4
- GitHub sr6033/face-detection-with-OpenCV-and-DNN — model files source
- ai.google.dev/edge/mediapipe/solutions/vision/face_detector/python — official MediaPipe Face Detector API
- GitHub raspberrypi/picamera2 issue #312 — ColourGains case-sensitivity confirmed fix
- GitHub raspberrypi/picamera2 issue #825 — ColourGains (0,0) = AWB-on behaviour
- GitHub raspberrypi/picamera2 issue #322 — CCM and AWB disabled behaviour
- GitHub m-lundberg/simple-pid pid.py source — `components` property verified (HIGH confidence)

### v1.7 supplement (2026-03-27, HIGH confidence)

- simple_pid source code `raw.githubusercontent.com/m-lundberg/simple-pid/master/simple_pid/pid.py`
- Picamera2 GitHub issues #825, #232, #592
- RPi Forums t=365052

### Base stack (2026-03-26, MEDIUM confidence — training data + codebase analysis)

- Existing codebase analysis (src/hardware.py, src/config.py) — HIGH confidence
- Training data (Picamera2 docs, RPi forums, libcamera guides) — MEDIUM confidence

---
*Stack research for: Picamera2 test tracker on RPi4 Bookworm*
*Base: 2026-03-26 | v1.7 supplement: 2026-03-27 | v1.8 supplement: 2026-03-29 | v1.9 supplement: 2026-03-29*
