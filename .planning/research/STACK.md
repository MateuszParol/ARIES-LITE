# Stack Research

**Domain:** Picamera2 + pigpio face tracking on RPi4 Bookworm 64-bit
**Researched:** 2026-03-26 (base), 2026-03-27 (v1.7 bug-fix supplement)
**Confidence:** HIGH (source-verified against simple_pid source code and Picamera2 GitHub issues)

---

## v1.7 Supplement: Bug-Fix Research

This section answers the three specific questions raised for the v1.7 milestone.
It supersedes any previous speculation on these topics.

---

### 1. simple_pid Sign Convention — Verified from Source Code

**Source:** `github.com/m-lundberg/simple-pid` raw source `simple_pid/pid.py` — HIGH confidence.

**Exact line from source:**

```python
error = self.setpoint - input_
```

**Consequence for the current code:**

`pid_pan` and `pid_tilt` are both created with `setpoint=0`.
When a face is to the right of centre, `blad_pan = srodek_x - ramka_cx` is **positive**.
When `pid_pan(blad_pan)` is called:

```
error = 0 - blad_pan  →  negative error
output = Kp * negative_error  →  negative output
```

So `pid_pan(positive_error)` returns a **negative value**.

The current `_sledz` code:

```python
korekta_pan = -self.pid_pan(blad_pan)   # negates → positive correction
korekta_tilt = self.pid_tilt(blad_tilt)  # no negation → negative correction
```

**Pan analysis** (face right of centre):
- `blad_pan > 0`
- `pid_pan(blad_pan)` → negative
- `-pid_pan(blad_pan)` → positive
- `nowy_pan = hardware.pan_angle + positive` → pan moves right → **correct** (pan+ = prawo per PROJECT.md)

**Tilt analysis** (face below centre):
- `blad_tilt > 0`
- `pid_tilt(blad_tilt)` → negative
- No negation → `korekta_tilt` is **negative**
- `nowy_tilt = hardware.tilt_angle + negative` → tilt moves up (decreases angle)
- But tilt+ = dół (downward) per PROJECT.md, so face below centre should increase tilt
- **This is the sign bug causing tilt to not move or move wrong way**

**Fix required in `_sledz`:**

```python
korekta_pan  = -self.pid_pan(blad_pan)   # keep negation: pan+ = right, face right → pan+
korekta_tilt = -self.pid_tilt(blad_tilt) # add negation: tilt+ = down,  face down  → tilt+
```

Both axes follow the same pattern: output must be negated because `error = setpoint - input`
produces negative output when input > setpoint, but the servo must move *toward* the
positive direction when the face is in the positive pixel-offset direction.

---

### 2. Picamera2 AWB Configuration — Verified from Official GitHub

**Sources:** Picamera2 GitHub issues #825, #232, #592, RPi forums t=365052 — HIGH confidence.

#### The blue-tint root cause

YUV420 is a raw sensor stream. When AWB has not settled yet at the time the first
frames are captured (or when AWB overshoots for the IMX219 with default tuning),
the blue channel gain is applied incorrectly, producing the tint.

Current code in `Picamera2Stream.start()` starts capturing frames immediately with
no AWB warm-up or manual gain lock.

#### Correct API sequence

**Step A — Let AWB settle (1 second is enough):**

```python
self._picam2.start()
time.sleep(2.0)  # AWB needs ~1-2s to converge on IMX219
```

**Step B — Read settled gains from metadata:**

```python
metadata = self._picam2.capture_metadata()
colour_gains = metadata.get("ColourGains")
# Returns (red_gain, blue_gain) tuple, e.g. (2.52, 1.90) under warm white LED
```

**Step C — Lock the gains (disables AWB automatically):**

```python
self._picam2.set_controls({"ColourGains": colour_gains})
# Setting ColourGains implicitly disables AWB per libcamera behaviour.
# Explicit AwbEnable: False is optional but harmless.
```

**Alternative C — Hard-code gains for known lighting:**

```python
# Typical indoor daylight/LED values for IMX219 V2 camera:
self._picam2.set_controls({"ColourGains": (2.5, 1.9)})
# Red gain ~2.0-2.8, Blue gain ~1.6-2.2 for 5000-6500K illuminant
```

#### Critical sequencing rules

| Rule | Detail |
|------|--------|
| After `configure()`, not before | `configure()` wipes controls; `set_controls()` must follow `start()` |
| After `start()`, not at init | Controls applied pre-start have no effect |
| `set_controls` is per-frame delivery | Applied with next submitted request; not instantaneous |
| `ColourGains` disables AWB implicitly | Per libcamera design; explicit `AwbEnable: False` redundant but safe |

#### Recommended minimal patch in `Picamera2Stream.start()`:

```python
def start(self) -> None:
    self._picam2 = Picamera2()
    video_config = self._picam2.create_video_configuration(
        lores={"size": (self._width, self._height), "format": "YUV420"}
    )
    self._picam2.configure(video_config)
    self._picam2.start()

    # Wait for AWB to converge, then lock gains
    time.sleep(2.0)
    metadata = self._picam2.capture_metadata()
    colour_gains = metadata.get("ColourGains")
    if colour_gains:
        self._picam2.set_controls({"ColourGains": colour_gains})
        logger.info(f"AWB blokada: ColourGains={colour_gains}")
    else:
        # Fallback: hard-coded IMX219 indoor values
        self._picam2.set_controls({"ColourGains": (2.5, 1.9)})
        logger.warning("ColourGains nie dostepne w metadata — uzyta wartoc fallback (2.5, 1.9)")

    logger.info(f"Picamera2 uruchomiona: {self._width}x{self._height} YUV420")
    # ...rest of thread start
```

#### Separate known issue: YUV420p vs YUV420sp

The current code uses `cv2.COLOR_YUV420p2BGR`. If the Picamera2 YUV420 buffer is
semi-planar (NV12), the wrong conversion flag will produce colour artifacts that
look like a blue tint. Verify the actual buffer layout:

```python
logger.info(f"YUV shape: {klatka_yuv.shape}")
# For 320x240: planar (YUV420p) → shape (360, 320), semi-planar (NV12) → shape (360, 320)
# Both same shape — only difference is UV plane interleaving
```

If blue tint persists after AWB fix, try `cv2.COLOR_YUV2BGR_NV12` instead of
`cv2.COLOR_YUV420p2BGR`. The RPi camera on Bookworm typically outputs YUV420
in NV12 (semi-planar) format.

---

### 3. simple_pid `reset()` and Anti-Windup — Verified from Source Code

**Source:** `github.com/m-lundberg/simple-pid` raw source — HIGH confidence.

#### What `reset()` does (exact from source):

```python
def reset(self):
    self._proportional = 0
    self._integral = 0      # clears integral — anti-windup
    self._derivative = 0
    self._integral = _clamp(self._integral, self.output_limits)  # clamp 0 to limits
    self._last_time = self.time_fn()
    self._last_output = None
    self._last_input = None
    self._last_error = None
```

**`reset()` clears the integral term completely.** It also clears `_last_input` and
`_last_error`, which means the derivative term will also start fresh (no spike from
stale derivative state).

#### Anti-windup in simple_pid

simple_pid has built-in anti-windup via `output_limits`. The integral term is
clamped every iteration:

```python
self._integral += self.Ki * error * dt
self._integral = _clamp(self._integral, self.output_limits)
```

With `output_limits = (-10.0, 10.0)` as set in `MaszynaStanow.__init__()`, the
integral is clamped to [-10, 10] every tick. No additional anti-windup logic is
needed at the application level.

#### Current code assessment

The current `_przejdz_do` implementation is **correct**:

```python
def _przejdz_do(self, nowy_stan: str) -> None:
    self.stan = nowy_stan
    self._czas_ostatniego_celu = time.time()
    if nowy_stan == config.STATE_SCANNING:
        self.pid_pan.reset()    # clears integral, proportional, derivative
        self.pid_tilt.reset()   # same
```

Calling `reset()` on SCANNING entry is the correct anti-windup pattern. There is
**no need** to manually zero `_integral` or access internal attributes — `reset()`
handles everything.

#### One gap: transition SCANNING → TRACKING

`reset()` is only called when entering SCANNING. When re-entering TRACKING from
SCANNING (face acquired during scan), the PID state is already zeroed from the
prior `reset()` call, so this is fine. No change needed.

---

## Original Stack Reference (unchanged from v1.6 research)

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| picamera2 | >=0.3.x (system pkg) | Camera capture via libcamera | Native camera stack on Bookworm; replaces deprecated picamera/V4L2 |
| pigpio | 1.78+ | Hardware PWM for servos | Validated in v1.5; only library providing true H-PWM on RPi4 |
| opencv-python-headless | 4.8+ | HAAR cascade face detection | Already in deps; headless variant avoids GUI libs on RPi |
| simple-pid | 2.0+ | PID controller | Already in deps; auto-integral clamping with output_limits |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | 1.24+ | Frame array manipulation | Required by both Picamera2 and OpenCV |
| libcamera (system) | 0.1+ | Camera HAL | Installed with RPi OS Bookworm; Picamera2 depends on it |

### Installation

```bash
# System packages (Bookworm 64-bit)
sudo apt install -y python3-picamera2 python3-libcamera

# Venv with system site-packages (CRITICAL for picamera2)
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Python packages
pip install opencv-python-headless simple-pid numpy
```

## Picamera2 Key API Patterns

### Optimal Configuration for 320x240 Face Detection

```python
from picamera2 import Picamera2

picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "BGR888"},
    lores={"size": (320, 240), "format": "BGR888"},
    buffer_count=4,
    controls={"FrameRate": 30}
)
picam2.configure(config)
picam2.start()

# Capture for detection (low-res, fast)
frame_lores = picam2.capture_array("lores")  # 320x240 BGR numpy array
```

### Critical: Resource Cleanup

```python
try:
    picam2.start()
    # ... main loop
finally:
    picam2.stop()
    picam2.close()  # Both required — stop() alone leaves libcamera pipeline locked
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| picamera2 | cv2.VideoCapture | Legacy Bullseye systems where V4L2 still works |
| BGR888 at configure | cv2.cvtColor per frame | Never — runtime cost for no benefit |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| picamera (v1) | Deprecated, not compatible with Bookworm libcamera stack | picamera2 |
| cv2.VideoCapture(0) | V4L2 not available for RPi Camera on Bookworm 64-bit | picamera2 |
| Manual `_integral` manipulation | Accesses private state; `reset()` is the correct API | `pid.reset()` |

## Sources

### v1.7 supplement (HIGH confidence)
- simple_pid source code: `raw.githubusercontent.com/m-lundberg/simple-pid/master/simple_pid/pid.py`
  — direct read of `__call__` and `reset()` methods
- Picamera2 GitHub issue #825: ColourGains not working investigation
- Picamera2 GitHub issue #232: How to set AwbMode with camera controls
- Picamera2 GitHub discussion #592: Disabling AWB and controlling gains manually
- RPi Forums t=365052: How to lock AWB with Picamera2 API

### Base stack (MEDIUM confidence — training data, needs on-device verification)
- Existing codebase analysis (src/hardware.py, src/config.py) — HIGH confidence
- Training data (Picamera2 docs, RPi forums, libcamera guides) — MEDIUM confidence

---
*Stack research for: Picamera2 test tracker on RPi4 Bookworm*
*Base: 2026-03-26 | v1.7 supplement: 2026-03-27*
