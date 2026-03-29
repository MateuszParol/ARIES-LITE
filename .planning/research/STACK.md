# Stack Research

**Domain:** Picamera2 + pigpio face tracking on RPi4 Bookworm 64-bit
**Researched:** 2026-03-26 (base), 2026-03-27 (v1.7 supplement), 2026-03-29 (v1.8 supplement)
**Confidence:** HIGH (source-verified against official docs, GitHub issues, and simple_pid source code)

---

## v1.8 Supplement: Critical Hardware Fix Research

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
*Base: 2026-03-26 | v1.7 supplement: 2026-03-27 | v1.8 supplement: 2026-03-29*
