# Stack Research

**Domain:** Picamera2 + pigpio face tracking on RPi4 Bookworm 64-bit
**Researched:** 2026-03-26
**Confidence:** MEDIUM-HIGH (training data, not live-verified against Picamera2 docs)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| picamera2 | ≥0.3.x (system pkg) | Camera capture via libcamera | Native camera stack on Bookworm; replaces deprecated picamera/V4L2 |
| pigpio | 1.78+ | Hardware PWM for servos | Already validated in v1.5; only library providing true H-PWM on RPi4 |
| opencv-python-headless | 4.8+ | HAAR cascade face detection | Already in deps; headless variant avoids GUI libs on RPi |
| simple-pid | 2.0+ | PID controller | Already in deps; auto-integral clamping with output_limits |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | 1.24+ | Frame array manipulation | Required by both Picamera2 and OpenCV |
| libcamera (system) | 0.1+ | Camera HAL | Installed with RPi OS Bookworm; Picamera2 depends on it |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pigpiod | pigpio daemon | Must be running: `sudo pigpiod` before script launch |
| libcamera-hello | Camera test | Quick sanity check: `libcamera-hello -t 2000` |
| rpicam-hello | Bookworm camera test | Newer alias for libcamera-hello on Bookworm |

## Installation

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

# Capture for display (full-res)
frame_main = picam2.capture_array("main")    # 640x480 BGR numpy array
```

### Critical: BGR888 Format

Picamera2 defaults to RGB. OpenCV expects BGR. Set `format="BGR888"` at configure time — zero runtime cost, avoids silent HAAR degradation.

### Critical: Resource Cleanup

```python
try:
    picam2.start()
    # ... main loop
finally:
    picam2.stop()
    picam2.close()  # Both required — stop() alone leaves libcamera pipeline locked
```

### Capture Modes

| Mode | Method | Latency | Use Case |
|------|--------|---------|----------|
| Synchronous | `capture_array()` | ~33ms at 30fps | Simple loop, sufficient for test tracker |
| Callback | `pre_callback` / `post_callback` | Lower | High-throughput, more complex |
| Queue | `capture_array()` with `wait=False` | Varies | Non-blocking, needs queue management |

**Recommendation:** Synchronous `capture_array("lores")` in a dedicated thread. Simplest, sufficient for 30fps on RPi4. Matches existing VideoStream pattern.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| picamera2 | cv2.VideoCapture | Legacy Bullseye systems where V4L2 still works |
| picamera2 lores stream | Full-res + cv2.resize | If dual-stream not needed; adds CPU overhead |
| BGR888 at configure | cv2.cvtColor per frame | Never — runtime cost for no benefit |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| picamera (v1) | Deprecated, not compatible with Bookworm libcamera stack | picamera2 |
| cv2.VideoCapture(0) | V4L2 not available for RPi Camera on Bookworm 64-bit | picamera2 |
| gpiozero for PWM | Software PWM, jittery servo control | pigpio H-PWM (already validated) |
| face_recognition lib | Unnecessary wrapper; adds dlib dependency for simple HAAR detection | cv2.CascadeClassifier directly |

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| picamera2 ≥0.3 | RPi OS Bookworm 64-bit | Must use `--system-site-packages` venv |
| picamera2 | opencv-python-headless 4.x | Both use numpy arrays; BGR888 bridges format gap |
| pigpio 1.78 | RPi4 BCM2711 | Requires running `pigpiod` daemon |
| simple-pid 2.x | Python 3.9+ | Auto-clamping with output_limits; call `reset()` on state transitions |

## Sources

- Training data (Picamera2 docs, RPi forums, libcamera guides) — MEDIUM confidence
- Existing codebase analysis (src/hardware.py, src/config.py) — HIGH confidence
- **Needs on-device verification:** `libcamera-hello`, `python3 -c "from picamera2 import Picamera2; print(Picamera2())"` on target RPi4

---
*Stack research for: Picamera2 test tracker on RPi4 Bookworm*
*Researched: 2026-03-26*
