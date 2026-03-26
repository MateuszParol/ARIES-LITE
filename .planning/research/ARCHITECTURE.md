# Architecture Patterns

**Domain:** Isolated test tracker module for ARIES-LITE
**Researched:** 2026-03-26
**Confidence:** MEDIUM — based on direct codebase analysis + training knowledge of Picamera2 API (Picamera2 docs unavailable for live verification)

---

## Recommended Architecture

```
src/
├── config.py            (existing — unchanged, reused directly)
├── hardware.py          (existing — unchanged, imported directly)
├── tracker.py           (existing — unchanged, NOT imported by test_tracker)
├── camera.py            (existing — unchanged, NOT used by test_tracker)
├── vision.py            (existing — unchanged, NOT used by test_tracker)
├── __init__.py          (existing)
└── modes/
    ├── __init__.py      (NEW — empty)
    └── test_tracker.py  (NEW — self-contained control loop)

run_test_tracker.py      (NEW — standalone entry point, project root)
```

The test tracker is a **self-contained module** launched independently from `run_test_tracker.py`.
It does NOT involve Flask, shares NO globals with `web/server.py`, and does NOT modify any
existing source file. The existing `main.py` path is completely untouched.

---

## Component Boundaries

| Component | Responsibility | Origin | Communicates With |
|-----------|---------------|--------|-------------------|
| `PanTiltSystem` | Servo PWM abstraction, soft limits, smooth_move | Existing `src/hardware.py` | Imported directly by TestTracker |
| `src.config` | All tuning constants (PID gains, servo limits, camera res) | Existing `src/config.py` | Imported directly by TestTracker |
| `Picamera2Wrapper` | Thin wrapper around Picamera2, produces BGR numpy frames | NEW inside test_tracker.py | TestTracker's main loop |
| `TestTracker` | State machine (Safe Startup → Scanning → Tracking → Target Lost) + PID | NEW `src/modes/test_tracker.py` | PanTiltSystem, Picamera2Wrapper |
| `run_test_tracker.py` | Entry point: instantiate, run loop, signal handling | NEW at project root | TestTracker |

---

## Integration Decision: Reuse vs Own

### PanTiltSystem — IMPORT DIRECTLY (HIGH confidence)

`PanTiltSystem` from `src/hardware.py` is the correct choice. It already:
- Encapsulates pigpio/gpiozero setup with mock fallback
- Enforces safe angle limits via `config.PAN_LIMIT_MIN/MAX`, `TILT_LIMIT_MIN/MAX`
- Provides `smooth_move_to()` for safe startup (critical — prevents brownout)
- Is stateless enough to be instantiated standalone

```python
from src.hardware import PanTiltSystem
hardware = PanTiltSystem(pan_pin=12, tilt_pin=13)  # same pins as production
```

No reason to rewrite servo control. The mock mode means test_tracker also works
on Windows dev machine without pigpio.

### PIDController — OWN INSTANCES (HIGH confidence)

`TrackerMachine` owns its PID instances internally (not a separate importable class).
The PID logic in `src/tracker.py` is entangled with the full state machine and dlib
verification flow that the test tracker does not need.

Instead, instantiate `simple_pid.PID` directly — the same library already in requirements.txt:

```python
from simple_pid import PID
pid_pan  = PID(config.PID_PAN_P,  config.PID_PAN_I,  config.PID_PAN_D,  setpoint=0)
pid_tilt = PID(config.PID_TILT_P, config.PID_TILT_I, config.PID_TILT_D, setpoint=0)
pid_pan.output_limits  = (-10, 10)
pid_tilt.output_limits = (-10, 10)
```

This reuses tuned constants from `src/config.py` without importing any of `TrackerMachine`.

### VideoStream (camera.py) — DO NOT USE (HIGH confidence)

`VideoStream` uses `cv2.VideoCapture` via V4L2. On RPi OS Bookworm 64-bit, the Pi Camera
is exposed via libcamera, NOT V4L2. `cv2.VideoCapture(0)` will either fail or produce
degraded output on Bookworm. The test tracker must use Picamera2 natively.

### HybridVision (vision.py) — DO NOT USE (HIGH confidence)

`HybridVision` bundles CSRT tracker + async dlib identity verification. The test tracker
spec explicitly excludes identity verification — it tracks any face. Use HAAR directly:

```python
haar_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(haar_path)
```

This is the same cascade already loaded inside HybridVision. No additional dependency.

---

## Data Flow

```
Picamera2.capture_array("main")     # returns XRGB or RGB numpy array (HxWxC)
    ↓
cv2.cvtColor(frame, COLOR_RGB2BGR)  # convert to OpenCV-native BGR
    ↓
HAAR detectMultiScale(gray_frame)   # face detection, returns [(x,y,w,h)]
    ↓
if face found:
    compute error_pan, error_tilt vs frame center
    PID.pan(error_pan) → pan_correction
    PID.tilt(error_tilt) → tilt_correction
    PanTiltSystem.set_angles(target_pan + correction, target_tilt + correction)
    → state = TRACKING
else:
    if time_since_last_face > TIME_TO_LOST_SEC:
        → state = SCANNING
        sinusoidal scan via PanTiltSystem.set_angles()
```

---

## Picamera2 Integration Pattern

**Confidence: MEDIUM** — based on training knowledge; live Picamera2 docs were unavailable.

Picamera2 is the native camera API for RPi OS Bookworm. The recommended capture loop:

```python
from picamera2 import Picamera2

class Picamera2Wrapper:
    def __init__(self, width=640, height=480):
        self.cam = Picamera2()
        config = self.cam.create_preview_configuration(
            main={"size": (width, height), "format": "RGB888"}
        )
        self.cam.configure(config)
        self.cam.start()

    def read(self):
        """Returns BGR numpy array compatible with OpenCV."""
        frame = self.cam.capture_array("main")  # returns RGB HxWx3
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    def stop(self):
        self.cam.stop()
        self.cam.close()
```

Key points (MEDIUM confidence — verify against Picamera2 docs on target hardware):
- `create_preview_configuration` with `"RGB888"` format returns a 3-channel uint8 array
- `capture_array("main")` is synchronous but low-latency — suitable for 30fps loop
- The returned array is RGB, not BGR — one `cvtColor` call is required before OpenCV HAAR
- `"XBGR8888"` is an alternative 4-channel format; avoid it (extra channel conversion)
- Picamera2 does NOT share any state with the existing `VideoStream` class — completely parallel

**Threading note:** Picamera2 manages its own internal capture thread. The test tracker's
main loop simply calls `capture_array()` synchronously — no additional threading needed
for a single-mode isolated runner.

---

## State Machine

```
[startup]
    ↓
SAFE_START
    smooth_move_to(0, 0)   ← blocks until complete (same as TrackerMachine)
    ↓
SCANNING
    sinusoidal pan ±45° at config.SERVO_STEP per tick
    if face detected → TRACKING
    ↓
TRACKING
    PID correction applied each frame
    last_target_time = now
    if no face for TIME_TO_LOST_SEC (2s) → TARGET_LOST
    ↓
TARGET_LOST
    → SCANNING
```

State transitions mirror `TrackerMachine` in `src/tracker.py` but are re-implemented
locally — clean break, no shared state with production tracker.

---

## Module Dependency Graph (New State)

```
run_test_tracker.py
    └── src/modes/test_tracker.py   (TestTracker + Picamera2Wrapper)
            ├── src/hardware.py     (PanTiltSystem)  ← REUSED
            │       └── gpiozero / pigpio
            ├── src/config.py       (constants)      ← REUSED
            ├── simple_pid          (PID)             ← REUSED (new instances)
            ├── picamera2           (NEW dependency)
            └── cv2                 (HAAR cascade, cvtColor)
```

Existing `main.py` dependency graph is completely unchanged.

---

## Patterns to Follow

### Pattern 1: Dependency Injection via Direct Import (not subclassing)

Do not subclass `TrackerMachine`. Import only what is reusable:
- `from src.hardware import PanTiltSystem` — servo control
- `from src import config` — all constants
- `from simple_pid import PID` — PID instances

This keeps the isolation clean. If `TrackerMachine` changes in v1.7, test_tracker is
unaffected.

### Pattern 2: Picamera2Wrapper as an Internal Class

Define `Picamera2Wrapper` inside `src/modes/test_tracker.py`, not as a standalone module.
It is test-tracker-specific. If a future milestone generalizes camera backends, it can
be promoted to `src/camera_backends/picamera2.py` at that point.

### Pattern 3: Single-File Entry Point

`run_test_tracker.py` at project root (not inside src/) mirrors the existing `main.py`
convention. It handles:
- `signal.signal(SIGINT, ...)` for Ctrl+C
- Calls `hardware.detach_servos()` in finally block
- Calls `cam.stop()` in finally block

### Pattern 4: Scan Uses set_angles, Not smooth_move_to

During SCANNING, call `hardware.set_angles()` per-tick (incremental, not blocking).
`smooth_move_to()` blocks in a while loop — use it only for safe startup initialization,
identical to how `TrackerMachine.start_pipeline()` uses it.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Importing TrackerMachine Directly

**What:** `from src.tracker import TrackerMachine` in test_tracker.py
**Why bad:** TrackerMachine couples dlib identity verification with PID — test tracker
intentionally does not do identity verification. Importing it brings in `face_recognition`
and `dlib` as transitive dependencies (slow import, heavy memory footprint on RPi).
**Instead:** Instantiate `PID` directly from `simple_pid`.

### Anti-Pattern 2: Using cv2.VideoCapture for Pi Camera on Bookworm

**What:** `VideoStream(src=0)` using V4L2 backend
**Why bad:** RPi OS Bookworm deprecated legacy camera stack. Pi Camera is exposed via
libcamera, not V4L2 device nodes. `cv2.VideoCapture(0)` may open a USB webcam
accidentally or return black frames from the Pi Camera.
**Instead:** Use Picamera2 natively.

### Anti-Pattern 3: Shared Globals Between test_tracker and server.py

**What:** Storing `TestTracker` instance in `web/server.py` module globals
**Why bad:** Couples isolated test mode to Flask lifecycle, defeats the isolation goal,
and creates concurrent access to pigpio from two code paths.
**Instead:** `run_test_tracker.py` is a separate entry point. Flask is not involved.

### Anti-Pattern 4: Skipping smooth_move_to at Startup

**What:** Calling `hardware.set_angles(0, 0)` directly at module load or in __init__
**Why bad:** Servo jumps from unknown power-on position cause current spikes → brownout/reboot
documented in CLAUDE.md.
**Instead:** Always call `hardware.smooth_move_to(0, 0)` as first action before entering
the main loop.

### Anti-Pattern 5: Running Picamera2 and VideoStream Simultaneously

**What:** Instantiating both `Picamera2` and `cv2.VideoCapture` in the same process
**Why bad:** Both attempt to acquire the camera hardware. On RPi only one consumer can
hold the camera device. Will raise a resource conflict error.
**Instead:** test_tracker.py uses only Picamera2. The existing VideoStream is only active
when `main.py` is running.

---

## Build Order (Dependency-First)

| Step | Task | Why This Order |
|------|------|----------------|
| 1 | `src/modes/__init__.py` | Package must exist before importing test_tracker |
| 2 | `Picamera2Wrapper` class inside test_tracker.py | Camera backend needed before any frame processing |
| 3 | HAAR detection logic in test_tracker.py | Depends on having frames from Picamera2Wrapper |
| 4 | PID controller instances + tracking logic | Depends on having bounding boxes from HAAR |
| 5 | State machine (SCANNING / TRACKING / TARGET_LOST) | Depends on PID outputs and timing |
| 6 | SAFE_START via smooth_move_to | Depends on PanTiltSystem being initialized |
| 7 | `run_test_tracker.py` entry point + signal handling | Wires everything together, last |

Steps 2-6 can be developed in test_tracker.py as a single file; the order reflects
the conceptual dependency chain for implementation within that file.

---

## Scalability Considerations

This is a single-device embedded system. "Scalability" means hardware constraints:

| Concern | Current (test_tracker) | Note |
|---------|----------------------|------|
| CPU for HAAR on RPi4 | ~15-20ms/frame at 640x480 | Leaves headroom for 30fps loop |
| CPU with Picamera2 capture | Minimal (libcamera ISP offloads) | Better than V4L2 on Bookworm |
| Memory (no dlib) | ~40MB vs ~250MB with face_recognition | Intentional — test tracker is lightweight |
| Servo responsiveness | Limited by PID output_limits (-10, 10 deg/frame) | Same as production config |

---

## Open Questions / Flags for Phase Research

1. **Picamera2 format on specific RPi revision** (MEDIUM confidence): The exact array
   format returned by `capture_array("main")` with `"RGB888"` config should be verified
   empirically on the target hardware. There are reports of XRGB (4-channel) being
   returned depending on firmware version.

2. **Picamera2 + pigpio coexistence** (MEDIUM confidence): Both use Linux DMA resources.
   No known conflict documented, but should be verified — run both simultaneously and
   check for DMAHEAP allocation errors in `dmesg`.

3. **HAAR performance on Bookworm 64-bit OpenCV** (LOW confidence): The headless OpenCV
   package in requirements.txt (`4.8.1.78`) was pinned for armhf. The 64-bit (aarch64)
   build may need a different package or pip source. Verify `import cv2` works on
   Bookworm 64-bit before building vision logic.

4. **Picamera2 in virtual environment** (MEDIUM confidence): Picamera2 is typically
   installed system-wide via `apt`. Running inside `venv` may require either
   `--system-site-packages` or a `pip install picamera2` that resolves libcamera
   bindings correctly. This is a common Bookworm gotcha.

---

## Sources

- Direct codebase analysis: `src/hardware.py`, `src/tracker.py`, `src/config.py`, `src/camera.py`, `src/vision.py` (HIGH confidence)
- `.planning/codebase/ARCHITECTURE.md` — threading model (HIGH confidence)
- `.planning/codebase/STACK.md` — dependency versions (HIGH confidence)
- `.planning/PROJECT.md` — v1.6 goal and constraints (HIGH confidence)
- CLAUDE.md — hardware constraints, brownout warning (HIGH confidence)
- Picamera2 API patterns — training knowledge, August 2025 cutoff (MEDIUM confidence — verify on target hardware)
