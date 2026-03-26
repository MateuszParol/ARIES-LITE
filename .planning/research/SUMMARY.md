# Project Research Summary

**Project:** ARIES-LITE v1.6 — Test Tracker (Picamera2 Migration)
**Domain:** Embedded real-time face tracking on RPi4 with Picamera2 + PID servo control
**Researched:** 2026-03-26
**Confidence:** MEDIUM-HIGH

## Executive Summary

v1.6 is a focused proof-of-concept: a single isolated file (`src/modes/test_tracker.py`) that validates the complete hardware+PID control loop on RPi OS Bookworm 64-bit using the Picamera2 camera stack. The existing v1.5 system uses `cv2.VideoCapture` via V4L2, which is incompatible with Bookworm's libcamera-based Pi Camera stack. The test tracker is NOT a feature release — it is a camera-backend migration proof with a deliberately simplified vision pipeline (HAAR-only, any face, no identity verification). All other v1.5 components (state machine, PID tuning, hardware abstraction) are validated and reused directly.

The recommended approach is a self-contained module that imports only `PanTiltSystem` and `src.config` from the existing codebase, creates its own `simple_pid.PID` instances, and wraps Picamera2 in a thin `Picamera2Wrapper` class inside the module. The state machine mirrors `TrackerMachine` (SAFE_START → SCANNING → TRACKING → TARGET_LOST) but removes dlib identity verification entirely. The entry point (`run_test_tracker.py`) is a standalone script — completely separate from `main.py` and Flask. This isolation is non-negotiable: running both simultaneously causes a silent camera resource conflict.

The primary risks are hardware-level: a direct servo jump at startup causes brownout/reboot (documented critical issue), and Picamera2 not released on exit blocks all subsequent runs. Both are preventable with `try/finally` discipline and `smooth_move_to(0,0)` as the unconditional first operation. PID risks are secondary — integral windup on state transitions and variable-dt derivative spikes are known issues with straightforward mitigations already proven in the existing codebase.

---

## Key Findings

### Recommended Stack

The stack is largely locked by the existing v1.5 codebase. The only new dependency is Picamera2, which must be installed as a system package (`python3-picamera2`) with the venv created using `--system-site-packages`. This is the single most common Bookworm deployment pitfall. All other libraries (opencv-python-headless, simple-pid, numpy, pigpio) are already in `requirements.txt` and validated.

**Core technologies:**
- `picamera2 ≥0.3.x` (system pkg): Camera capture — native libcamera stack on Bookworm; `cv2.VideoCapture(0)` is incompatible with RPi Camera on Bookworm 64-bit
- `opencv-python-headless 4.8+`: HAAR cascade face detection — already validated; headless variant avoids GUI libs
- `pigpio 1.78+`: Hardware PWM servo control — already validated in v1.5; only library providing true H-PWM on RPi4
- `simple-pid 2.0+`: PID controller — already in deps; use `output_limits=(-10,10)` and `sample_time=0.033` for stable servo control

**Critical install note:** Picamera2 requires `python3 -m venv venv --system-site-packages`. A standard venv without system site-packages will fail to import picamera2.

**Avoid:** `cv2.VideoCapture(0)` for Pi Camera on Bookworm (V4L2 not available), `picamera` v1 (deprecated), `gpiozero` software PWM (jitter).

### Expected Features

This milestone is a test module, not a feature release. Features are evaluated by whether they are required to prove the hardware+PID loop works.

**Must have (table stakes):**
- Safe startup via `smooth_move_to(0,0)` — prevents brownout, mandatory before any loop
- HAAR face detection (any face, no identity) — simplest reliable detector at 30 FPS; no dlib dependency
- SCANNING state with sinusoidal sweep (time-based) — demonstrates behavior when no face; sinusoidal is immune to stale state bugs
- TRACKING state: dual-axis PID on face centroid → `set_angles()` — core proof of the control loop
- TARGET LOST timeout (2s) → return to SCANNING — graceful recovery, prevents servo lockup
- Picamera2 frame acquisition — the entire point of the milestone
- Single-file isolation — no modifications to existing v1.5 modules
- PID output limits ±10 deg/frame — prevents servo jerk on new bbox appearance
- Graceful cleanup on Ctrl+C (`try/finally`, servo to neutral before detach)

**Should have (quality of proof):**
- Minimal HUD overlay (state label + bbox + FPS counter) — enables empirical verification of state transitions and frame rate without external logging
- Detection streak filter (N=3 consecutive frames) — eliminates single-frame false positives that cause hunting
- PID reset on TRACKING → SCANNING transition — prevents integral windup overshoot on first tracking acquisition

**Defer (not needed for this proof):**
- dlib identity recognition — actively excluded; obscures PID behavior
- Flask/MJPEG streaming — out of scope; adds threading complexity
- CSRT/KCF visual tracker — excluded; direct HAAR→PID is cleaner for proof
- Multi-face priority logic, IDLE state, persistent config file

**PID tuning baseline (validated in v1.5):** Kp=0.05, Ki=0.001, Kd=0.005. Pan uses `- pid_pan(error)`, tilt uses `+ pid_tilt(error)` — sign inversion is intentional and must be copied exactly.

### Architecture Approach

The test tracker is a single new package (`src/modes/`) containing one file (`test_tracker.py`) plus an entry point at project root (`run_test_tracker.py`). It imports `PanTiltSystem` and `src.config` directly from the existing codebase, creates fresh `simple_pid.PID` instances (does NOT import `TrackerMachine`), and defines `Picamera2Wrapper` as an internal class. The existing `main.py` dependency graph is completely untouched. The test tracker and the Flask server are mutually exclusive — they cannot run in the same process or simultaneously.

**Major components:**
1. `Picamera2Wrapper` (internal to test_tracker.py) — thin camera backend producing BGR numpy frames; `try/finally` lifecycle; `BGR888` format configured at init
2. `TestTracker` (src/modes/test_tracker.py) — state machine (SAFE_START → SCANNING → TRACKING → TARGET_LOST) + HAAR detection + dual-axis PID
3. `PanTiltSystem` (src/hardware.py, reused) — servo PWM abstraction with soft limits and `smooth_move_to()`
4. `run_test_tracker.py` (project root) — standalone entry point with signal handling and `finally` cleanup

**Data flow:** `Picamera2.capture_array()` (async thread, deque buffer) → BGR frame → HAAR detectMultiScale → face centroid → PID correction → `PanTiltSystem.set_angles()`.

**Key patterns:**
- Async Picamera2 capture in background thread with `deque(maxlen=1)` — decouples camera I/O from PID tick rate
- Time-based sinusoidal scan: `target_pan = PAN_LIMIT_MAX * sin(2π * t / SCAN_PERIOD)` — immune to stale state on TRACKING → SCANNING transition
- `pid.reset()` on every transition into SCANNING state — prevents integral windup

### Critical Pitfalls

1. **Servo jump at startup (brownout/reboot)** — Always call `smooth_move_to(0,0)` as the unconditional first hardware operation. Never call `set_angles()` directly at init. Current spike from cold-start servo jump causes RPi4 under-voltage reboot. (HIGH confidence — documented in CLAUDE.md)

2. **Picamera2 not released — "Camera already in use"** — Wrap entire camera lifecycle in `try/finally` with both `picam2.stop()` AND `picam2.close()`. Register SIGINT/SIGTERM handlers. Skipping either step leaves libcamera pipeline locked; recovery requires `sudo killall libcamera-vid` or reboot. (MEDIUM confidence)

3. **RGB vs BGR frame format** — Configure `format="BGR888"` at Picamera2 configure time, not per-frame. Running HAAR on RGB frames silently degrades detection accuracy. Zero runtime cost to fix at configure time. (HIGH confidence)

4. **PID integral windup on state transitions** — Call `pid_pan.reset()` and `pid_tilt.reset()` on every TRACKING → SCANNING transition. Otherwise, accumulated integral causes overshoot servo snap when next face is acquired. Also set `sample_time=0.033` on both PID objects to stabilize the derivative term against variable loop timing. (HIGH confidence)

5. **HAAR false detections without dlib filter** — Use `minNeighbors=8` (not 5) and `minSize=(80,80)` in the test tracker. Add a 3-frame detection streak filter before SCANNING → TRACKING transition. Without dlib verification (intentionally excluded), every false positive drives the servo. (HIGH confidence)

---

## Implications for Roadmap

Based on the combined research, this milestone maps cleanly to two implementation phases driven by hardware safety and dependency ordering.

### Phase 1: Hardware Foundation and Camera Integration

**Rationale:** The two critical pitfalls (brownout, camera lock) are both Phase 1 issues. Hardware init and camera init must be proven safe before any vision or PID code is written. Getting these wrong costs significant recovery time on real hardware (reboot, camera unlock). Everything in Phase 2 depends on a clean camera frame stream and safe servo operation.

**Delivers:** A running loop that captures Picamera2 frames, displays them via `cv2.imshow()`, moves servos safely to (0,0) on startup, and exits cleanly on Ctrl+C with servos returned to neutral.

**Addresses features:** Safe startup, Picamera2 frame acquisition, graceful cleanup, single-file isolation, `BGR888` format correctness.

**Avoids pitfalls:** Pitfall 1 (brownout), Pitfall 2 (camera lock), Pitfall 3 (RGB/BGR), Pitfall 4 (dual opener), Pitfall 8 (pulse width), Pitfall 10 (servo falls on detach), Pitfall 11 (blocking capture), Pitfall 12 (missing dependency).

**Must verify before Phase 2:** `libcamera-hello` works, `from picamera2 import Picamera2` imports in venv, Picamera2 + pigpio coexist without DMAHEAP errors, servo centers correctly at (0,0).

### Phase 2: State Machine, Vision, and PID Integration

**Rationale:** With clean frame delivery and safe servo control proven, the full control loop can be assembled. Vision (HAAR), state machine (SCANNING/TRACKING/TARGET_LOST), and PID are tightly coupled — they should be implemented together in one phase rather than separately. The pitfalls in this phase are behavioral (windup, sign errors, false detections) rather than catastrophic, and all have clear smoke tests.

**Delivers:** Complete test tracker: face detected → servo follows → face lost → scan resumes. HUD overlay with state label, bbox, and FPS counter. Empirical proof that Picamera2 + PID loop achieves ~30 FPS on RPi4.

**Addresses features:** HAAR detection, SCANNING state (sinusoidal), TRACKING state (dual PID), TARGET LOST timeout, HUD overlay, detection streak filter, PID reset on transition.

**Avoids pitfalls:** Pitfall 5 (integral windup), Pitfall 6 (variable dt), Pitfall 7 (false detections), Pitfall 9 (stale scan state), Pitfall 13 (tilt sign convention).

**Implementation order within phase:** `Picamera2Wrapper` async capture → HAAR detection → state machine skeleton → PID instances → SCANNING sweep → TRACKING PID loop → TARGET_LOST timeout → HUD → `run_test_tracker.py` entry point.

### Phase Ordering Rationale

- Phase 1 before Phase 2 because: hardware safety failures are catastrophic (reboot, locked camera), while Phase 2 failures are behavioral and recoverable. You cannot tune PID without a working camera.
- Async capture pattern (deque + background thread) belongs in Phase 1, not Phase 2 — retrofitting it after PID is wired would require restructuring the entire control loop.
- Sinusoidal scan must be implemented from the start (not as a refactor) because time-based sinusoid eliminates Pitfall 9 (stale scan state) — the step-accumulator pattern from v1.5 is a known defect in this context.
- The detection streak filter belongs in Phase 2 initial implementation (not as a later fix) because without dlib, false positives immediately corrupt PID integral state.

### Research Flags

Phases likely needing verification during execution (not additional research, but on-device empirical checks):

- **Phase 1:** Picamera2 import in `--system-site-packages` venv must be verified on the actual target RPi4. Training data says it works but this is the most common Bookworm gotcha. Run `python3 -c "from picamera2 import Picamera2; print('OK')"` before writing any code.
- **Phase 1:** Verify exact format returned by `capture_array("main")` with `"BGR888"` config on the specific RPi revision and firmware version. Reports of XRGB (4-channel) on some firmware versions.
- **Phase 1:** Check for Picamera2 + pigpio DMA coexistence: run both simultaneously and check `dmesg` for DMAHEAP errors.
- **Phase 1:** Verify `opencv-python-headless` imports correctly on aarch64 Bookworm — the pinned version (`4.8.1.78`) was for armhf.
- **Phase 2:** Smoke-test tilt sign convention before any numerical PID tuning (move face left → servo pans left; move face up → servo tilts up).

Phases with standard patterns (no additional research needed):
- **Phase 2 (PID):** Gains are validated from v1.5. `sample_time` and `output_limits` patterns are well-documented `simple_pid` behavior.
- **Phase 2 (state machine):** Direct re-implementation of proven `TrackerMachine` logic with known simplifications.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Existing stack (pigpio, opencv, simple-pid) is HIGH — validated in v1.5. Picamera2 API patterns are MEDIUM — training data only, not live-verified against Bookworm hardware. |
| Features | HIGH | Sourced from existing production code (`tracker.py`, `hardware.py`, `config.py`) and authoritative `.planning/PROJECT.md`. Scope is narrow and well-defined. |
| Architecture | MEDIUM-HIGH | Component boundaries and isolation strategy are HIGH confidence. Picamera2 integration details (exact format, venv behavior) are MEDIUM — needs on-device verification. |
| Pitfalls | HIGH | Most pitfalls are grounded directly in existing codebase analysis (brownout, windup, sign convention) or widely-documented patterns (BGR/RGB, camera lock). Picamera2-specific pitfalls are MEDIUM. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Picamera2 in venv with system-site-packages:** Must be the first verification step in Phase 1. If `apt install python3-picamera2` + `--system-site-packages` does not work cleanly, consider `pip install picamera2` as fallback. This is a deployment blocker, not a code issue.
- **OpenCV aarch64 package:** The pinned `opencv-python-headless==4.8.1.78` may be armhf-only. Verify with `import cv2` before any HAAR code. May need to remove the version pin or use system OpenCV.
- **Picamera2 capture_array format:** ARCHITECTURE.md notes RGB888 returns 3-channel arrays but warns of XRGB (4-channel) on some firmware. The `Picamera2Wrapper.read()` method must check `frame.ndim` and handle both cases, or use `BGR888` at configure time (strongly preferred).
- **MG-90S pulse width calibration:** The existing `hardware.py` does not set explicit `min_pulse_width`/`max_pulse_width`. If servos do not center correctly at `set_angles(0,0)`, this must be characterized before PID tuning in Phase 2.

---

## Sources

### Primary (HIGH confidence)
- `src/hardware.py`, `src/tracker.py`, `src/config.py`, `src/vision.py`, `src/camera.py` — direct codebase analysis; hardware constraints, PID values, state machine logic
- `CLAUDE.md` — brownout warning, servo startup constraint, architecture overview
- `.planning/PROJECT.md` — v1.6 milestone scope, constraints, goals
- `.planning/STATE.md` — current decisions (Picamera2, any-face, Polish convention)

### Secondary (MEDIUM confidence)
- Training data: Picamera2 API patterns, libcamera on Bookworm 64-bit, `--system-site-packages` venv requirement
- Training data: Picamera2 resource cleanup behavior, libcamera IPC socket lifecycle
- Training data: V4L2 libcamera bridge on Bookworm — dual-opener conflict pattern

### Tertiary (LOW confidence — needs on-device verification)
- Exact format returned by `capture_array()` on specific RPi firmware versions
- Picamera2 + pigpio DMA coexistence on RPi4 BCM2711
- OpenCV `4.8.1.78` compatibility with aarch64 Bookworm

---
*Research completed: 2026-03-26*
*Ready for roadmap: yes*
