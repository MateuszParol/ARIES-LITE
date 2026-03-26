# Feature Landscape

**Domain:** Autonomous pan-tilt face tracking control loop (isolated test module)
**Researched:** 2026-03-26
**Milestone:** v1.6 — Test Tracker

---

## Context: This Is a Test Module, Not a Feature Release

v1.6 goal is a single isolated file (`src/modes/test_tracker.py`) that proves the
hardware+PID loop works smoothly on Bookworm with Picamera2. The question "what
features to build?" must be answered through the lens of **what a clean proof
of concept requires** — not what a production tracker needs.

Existing system (v1.5): state machine, dual-axis PID, HAAR+dlib hybrid vision,
sinusoidal scan, 2s timeout, pigpio hardware PWM — all working. This module does
NOT reuse identity recognition (dlib) — any face = valid target.

---

## Table Stakes

Features the test tracker must have to constitute a valid proof. Missing any of
these = the module does not demonstrate its stated goal.

| Feature | Why Required | Complexity | Depends On |
|---------|--------------|------------|------------|
| Safe startup (incremental servo move to 0,0) | Prevents current spike / brownout on MG-90S at cold start | Low | `PanTiltSystem.smooth_move_to()` — reuse existing |
| SCANNING state — sinusoidal or linear sweep | Demonstrates system behavior when no face present; provides interesting range of servo motion for visual verification | Low | `src/config.py` angle limits |
| HAAR face detection (any face, no identity) | Simplest reliable face detector at 30 FPS on RPi4; no dlib dependency needed in this module | Low | OpenCV built-in haarcascades |
| TRACKING state — dual-axis PID on face centroid | Core proof: servo follows face smoothly; validates Kp/Ki/Kd values | Medium | `PanTiltSystem.set_angles()`, `simple_pid` |
| TARGET LOST — 2s timeout → return to SCANNING | Demonstrates graceful recovery; prevents servo lockup at last position | Low | `time.time()` comparison |
| Soft angle limits enforced (pan ±60°, tilt ±30°) | Physical safety for camera ribbon cable; already in `set_angles()` | None | `PanTiltSystem.set_angles()` already clamps |
| Picamera2 frame acquisition | Bookworm 64-bit native path; replaces `VideoStream` which uses `cv2.VideoCapture` | Medium | `picamera2` library |
| Single-file isolation — no modifications to existing modules | Constraint from milestone scope; existing v1.5 code must not break | N/A | Architecture discipline |
| PID output limits (±10 deg/frame) | Prevents sudden servo jerk when new bbox appears; already proven in `tracker.py` | None | `simple_pid` output_limits |

---

## Differentiators

Features that improve quality of the proof but are not strictly required to
demonstrate Scan→Detect→Track→Lost. Worth adding if complexity is low.

| Feature | Value | Complexity | Notes |
|---------|-------|------------|-------|
| Minimal HUD overlay (state label + bbox rectangle) | Makes verification visual without external logging; easy to confirm state transitions on screen | Low | `cv2.putText`, `cv2.rectangle` — no new dependency |
| Separate PID instances per axis (X/Y independent) | Avoids coupling between axes during diagonal movement; already proven pattern in `tracker.py` | None | Copy from existing `TrackerMachine` |
| FPS counter on HUD | Allows immediate empirical check that Picamera2 path hits ~30 FPS | Low | `time.time()` delta |
| Detection confidence gate (minNeighbors=5, minSize 60x60) | Reduces false positives from background textures during scan; prevents jitter on spurious detections | None | HAAR parameter tuning only |
| Configurable constants in module header (not hard-coded) | Makes tuning easier without editing logic; aligns with project `config.py` convention | Low | Local constants block at top of file |
| Graceful cleanup on Ctrl+C | Detaches servos cleanly; prevents servo humming after exit | Low | `try/finally` wrapping main loop |

---

## Anti-Features

Features to explicitly exclude from the test tracker module.

| Anti-Feature | Why Exclude | What to Do Instead |
|--------------|-------------|-------------------|
| dlib identity recognition | Defeats the purpose of isolation; adds 200-500ms latency that obscures PID behavior; test tracker goal is "any face" | HAAR detection only — if it looks like a face, track it |
| CSRT/KCF visual tracker wrapping detection | Adds a layer of indirection that makes PID debugging harder; HAAR→PID direct pipeline is clearer for a proof module | Detect face every frame with HAAR; feed centroid directly to PID |
| Flask web interface / MJPEG streaming | Out of scope; adds threading complexity; test tracker is a standalone script run from terminal | Run as `python3 -m src.modes.test_tracker`, show cv2.imshow preview locally |
| Multi-face handling / priority logic | Complexity that obscures PID proof; adds decision branching | Take largest face by bounding box area (single sort, same as existing vision.py) |
| Async verification thread | No identity check needed; async pattern here would create false "waiting for verification" state with no purpose | Synchronous HAAR detect → immediate PID input |
| IDLE state | Out of scope for test; test tracker runs until Ctrl+C | SCANNING is the resting state |
| Persistent config file / YAML settings | Overkill for a test module | Constants block at top of `test_tracker.py` |
| Kalman filter for prediction | PID is the proven choice (locked architectural decision); Kalman adds complexity for marginal gain on low-speed servo hardware | Stay with PID |

---

## Feature Dependencies

```
Picamera2 frame capture
  └─→ HAAR face detection (any face)
        └─→ SCANNING state (no face found)
        └─→ TRACKING state (face centroid → dual PID → set_angles)
              └─→ TARGET LOST timeout (2s) → back to SCANNING
                    └─→ SCANNING state (sweep resumes)

Safe Startup (smooth_move_to(0,0))
  └─→ enters SCANNING (prerequisite — must complete before loop starts)

PanTiltSystem.set_angles()  ← called by both SCANNING sweep and TRACKING PID
  └─→ angle clamping (built-in, passive feature)
  └─→ pigpio hardware PWM (transparent below set_angles)
```

---

## MVP Recommendation

The minimal test tracker that proves the loop works:

1. Safe startup to (0,0) via `smooth_move_to()`
2. HAAR detect any face → feed centroid to dual PID → `set_angles()`
3. Linear sweep scan (±45° pan, ±15° tilt) when no face — simpler than sinusoid, easier to verify
4. 2s timeout back to scanning on face loss
5. `cv2.imshow()` preview with state label and bbox rectangle
6. `try/finally` for servo detach on exit

**Defer:**
- FPS counter: add only if 30 FPS confirmation is needed during testing
- Sinusoidal scan: nice-to-have but linear sweep proves the same behavior

---

## PID Tuning Guidance for MG-90S

This belongs in features because "PID that works smoothly" is the core deliverable.

**Starting values (from existing `config.py`, already validated):**
- Kp = 0.05 (proportional — main correction driver)
- Ki = 0.001 (integral — corrects persistent offset; keep very low to avoid windup)
- Kd = 0.005 (derivative — damps oscillation; keep low because HAAR detection has frame-to-frame noise)

**Why these work for MG-90S at 640x480:**
- Error input is in pixels (0-640 range for pan, 0-480 for tilt)
- Output is in degrees/frame added to current angle
- `output_limits = (-10, 10)` prevents degree jumps > 10 per frame regardless of large sudden errors
- At 30 FPS, 10 deg/frame = 300 deg/sec max — more than MG-90S can physically achieve (500 deg/sec stall), so limit acts as rate limiter not physical limiter

**One known issue to avoid:** PID integral windup when servo hits angle limit. When `set_angles()` clamps the output, the PID doesn't know the actuator is saturated and accumulates I-term. Mitigation: reset `pid_pan.reset()` and `pid_tilt.reset()` when entering SCANNING from TRACKING. This is NOT done in existing `tracker.py` — the test tracker should add it.

**Tilt axis note:** Current `tracker.py` inverts tilt correction sign differently from pan. Verify empirically — camera ribbon orientation determines which axis needs sign inversion. Pan uses `- pid_pan(error)`, tilt uses `+ pid_tilt(error)`. Test tracker should make this explicit with a comment.

---

## Sources

- Existing `src/tracker.py` — PID implementation, state machine, timeout logic (HIGH confidence — production code)
- Existing `src/hardware.py` — `smooth_move_to()`, `set_angles()`, angle clamping (HIGH confidence — production code)
- Existing `src/config.py` — Kp/Ki/Kd values, angle limits, servo step (HIGH confidence — empirically validated)
- Existing `src/vision.py` — HAAR parameters (scaleFactor=1.1, minNeighbors=5, minSize=60x60) (HIGH confidence — production code)
- `.planning/PROJECT.md` — v1.6 milestone scope, constraints (HIGH confidence — authoritative spec)
- `.planning/STATE.md` — current decisions: Picamera2, any-face detection, Polish convention (HIGH confidence)
- Training knowledge: PID windup behavior at actuator saturation, HAAR vs CSRT tradeoffs on embedded hardware (MEDIUM confidence — well-established control theory, not hardware-specific)
