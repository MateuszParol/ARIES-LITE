# Project Research Summary

**Project:** ARIES-LITE v1.8 Critical Hardware Fix
**Domain:** Embedded real-time face tracking — RPi4 Bookworm 64-bit (Picamera2 + pigpio + simple_pid)
**Researched:** 2026-03-29
**Confidence:** HIGH

## Executive Summary

ARIES-LITE v1.8 is a focused bug-fix milestone targeting four confirmed hardware failures that survived v1.7 code changes: tilt axis frozen at 0.0 in the HUD, pan runaway on TRACKING entry, persistent blue tint from the camera, and HAAR detection triggering only under near-perfect conditions. All four symptoms were observed on physical RPi4 hardware despite syntactically correct v1.7 fixes being present in the codebase. The core research finding is that the primary root cause is a misdiagnosis cascade: HAAR detection is so restrictive (`minNeighbors=8`, `minSize=(80,80)`) that the state machine almost never enters TRACKING, making the PID and scan behaviors appear broken when they may be functionally correct.

The recommended approach is a strictly sequenced fix: detection first, AWB second, PID diagnosis third, scan continuity fourth. Detection must be confirmed stable before any PID conclusion is drawn, because fleeting 1-frame TRACKING events are visually indistinguishable from PID runaway. The highest-confidence, lowest-risk fix is relaxing HAAR parameters to `minNeighbors=4`, `minSize=(40,40)` before touching any other subsystem. If HAAR tuning proves insufficient, the OpenCV DNN `res10_300x300_ssd` model is the validated fallback — it ships inside `opencv-python-headless` already in `requirements.txt`, requires no new pip installs, and preserves the `wykryj()` interface contract.

The key implementation risk is invisible mock mode: `PanTiltSystem.set_angles()` updates software state (`tilt_angle`, `pan_angle`) unconditionally in both real and mock modes, meaning the HUD shows correct-looking values even when `pigpiod` is not running and no servo moves. All hardware debugging sessions must begin with a mock-mode preflight check. The AWB blue tint fix is straightforward but requires passing `ColourGains` in `create_video_configuration()` at configure time as the primary lock (not only via post-start `set_controls`), which guarantees correct color from frame 1 regardless of Picamera2/libcamera version quirks on Bookworm.

---

## Key Findings

### Recommended Stack

The existing pinned stack is correct and requires no new dependencies for v1.8. `opencv-python-headless==4.8.1.78` includes the DNN module with `res10_300x300_ssd` support. `simple-pid>=2.0.1` exposes the `components` property (`pid.components` returns `(P, I, D)` tuple) needed for PID diagnostics. `picamera2` (system package) supports `capture_metadata()["ColourGains"]` and `create_video_configuration(controls={...})` as the reliable AWB lock path. MediaPipe is explicitly rejected: no `aarch64` Linux wheel exists on PyPI as of 2026-03-29 and community builds are fragile.

**Core technologies:**
- `opencv-python-headless 4.8.1.78`: HAAR + DNN face detection — DNN module bundled, no extra pip install needed
- `picamera2` (system pkg): YUV420 lores capture + AWB ColourGains API — native libcamera stack on Bookworm
- `simple-pid >=2.0.1`: PID with `components` tuple — official API for per-component diagnostic logging; `pid.components` returns `(P, I, D)` after every `pid(error)` call
- `pigpio 1.78+` + `gpiozero`: hardware PWM for servos — only library providing true H-PWM on RPi4
- OpenCV DNN model files: `deploy.prototxt` (~28KB) + `res10_300x300_ssd_iter_140000.caffemodel` (~10MB) — one-time wget download to `models/`, not a pip install; needed only if HAAR tuning is insufficient

### Expected Features

All v1.8 features are bug fixes, not new functionality. The milestone has a narrow, well-defined scope.

**Must have (table stakes — all four required for milestone to ship):**
- Tilt axis physically moves during TRACKING — diagnose mock mode / call path before assuming PID sign error
- PAN converges to face center without runaway — confirm sustained TRACKING with logging before drawing any PID conclusions
- Camera renders neutral colors from frame 1 — configure-time `ColourGains` lock as primary; post-start `set_controls` as secondary verification
- HAAR detects real faces at 50-80 cm with slight angle — `minSize=(40,40)`, `minNeighbors=4`, keep `STREAK_REQUIRED=3`

**Should have (diagnostic support — same milestone, zero structural risk):**
- Per-tick PID debug logging in `_sledz()` — `logger.debug` with error, raw output, correction, resulting angle per axis
- ColourGains confirmation log at metadata capture point (before None check)
- Mock-mode indicator `[MOCK]` in HUD and `logger.info` of `_mock_mode` at startup
- HUD bbox dimension display (`w x h` pixels) to confirm whether `minSize` was the blocker

**Defer to future milestones:**
- OpenCV DNN `DetekcjaTwarzyDNN` class — only if HAAR tuning at `(40,40)/4` is empirically insufficient after hardware test
- CSRT tracker in test module — new scope; valid only after PID is confirmed working
- PID gain retuning — only after sign convention and hardware path are confirmed correct
- AWB mode presets (Indoor/Fluorescent) — only if dynamic lock still fails after configure-time fix

### Architecture Approach

All v1.8 changes are confined to a single file: `src/modes/test_tracker.py`. The four-layer architecture (Input → Detection → Control → Hardware) is unchanged. The `wykryj(klatka) -> Optional[Tuple[int,int,int,int]]` contract is the key interface boundary — any detector replacement (HAAR or DNN) must conform to this return type, keeping `TestTracker.uruchom()` and `MaszynaStanow.tick()` untouched. `hardware.py` has zero modifications; `config.py` may gain one constant (`DNN_CONFIDENCE_THRESHOLD = 0.5`) if DNN is added.

**Major components (all in `test_tracker.py`, in order of v1.8 change risk):**
1. `Picamera2Stream` — YUV420 capture + AWB lock; modified with configure-time `ColourGains` and full metadata log
2. `DetekcjaTwarzy` — HAAR + streak filter; parameters relaxed or replaced by `DetekcjaTwarzyDNN` with identical `wykryj()` interface
3. `MaszynaStanow._sledz()` — PID dual-axis tracking; modified with `logger.debug` diagnostic points P1-P4
4. `PanTiltSystem` (`hardware.py`) — unchanged; existing clamp WARNING logs already serve as P4 diagnostic output

### Critical Pitfalls

1. **HAAR never detects — tilt=0.0 is a detection symptom, not a PID symptom.** `minNeighbors=8` + `minSize=(80,80)` at 320x240 produces near-zero detections in practice. The state machine stays in SCANNING permanently; `_skanuj()` calls `set_angles(pan, 0.0)` with hardcoded tilt=0. HUD Tilt frozen at 0.0 looks identical to a PID failure. Fix: reduce to `minNeighbors=4`, `minSize=(40,40)`. Confirm with green rectangles visible at 1 m and TRACKING sustained 3+ seconds before touching PID code.

2. **Mock mode is invisible in HUD.** `set_angles()` updates `tilt_angle`/`pan_angle` software floats even when `_mock_mode=True`. HUD shows moving values while physical servos are frozen. Add `[MOCK]` label to HUD and `logger.info` of `_mock_mode` before main loop. Verify `sudo systemctl is-active pigpiod` is `active` before every hardware session.

3. **AWB blue tint from frame 1 — `set_controls()` after `start()` is too late.** Controls set via `set_controls()` after `start()` take effect 2-3 frames later. Pass `controls={"ColourGains": AWB_FALLBACK_GAINS}` in `create_video_configuration()` for first-frame guarantee. Do NOT set `AwbEnable: False` alongside `ColourGains` in the same `set_controls()` call — confirmed sequencing conflict on Bookworm versions. Setting `ColourGains` directly implicitly disables AWB.

4. **Diagnosing PID without stable detection — all PID fixes are unverifiable.** 1-frame TRACKING events produce observation windows too short to distinguish a sign bug from a gain problem from scan oscillation. The `SCAN_AMPLITUDE=45°` sinusoid can be mistaken for PAN runaway. Confirm TRACKING sustained for 10+ consecutive frames before drawing any PID conclusions.

5. **Phase offset formula non-convergent at SCANNING re-entry.** The `asin(pan/A)` offset is geometrically correct but does not cancel absolute `time.time()` drift. Results in a pan jerk at every TRACKING→SCANNING transition. Fix with a `_scan_start_time` reference instead of `_scan_phase_offset`. Lower priority — address after detection and PID are confirmed working.

---

## Implications for Roadmap

Based on research, the phase structure must follow a strict diagnostic dependency chain. Phases 1-3 cannot be parallelized: later phases cannot be validated without earlier ones passing on hardware.

### Phase 0: Pre-flight Diagnostics
**Rationale:** Mock mode is the most common silent failure mode on RPi4. Any hardware session that proceeds without confirming pigpiod status wastes diagnostic effort and may produce false PID conclusions. Zero code risk — pure log additions that cost nothing to keep permanently.
**Delivers:** Confirmed hardware mode at startup; HUD shows `[MOCK]` when pigpiod is absent; `_mock_mode` logged at INFO before main loop
**Addresses:** Mock-mode status log on `set_angles()` (FEATURES.md P1 diagnostic)
**Avoids:** Pitfall 5 (HUD software state mistaken for hardware state)
**Needs research-phase:** No — standard Python logging.

### Phase 1: Detection Fix
**Rationale:** This is the highest-probability root cause of all four reported symptoms. HAAR with current parameters (`minNeighbors=8`, `minSize=(80,80)`) barely triggers at 320x240 under real-world conditions. Without stable detection, the state machine stays in SCANNING and all other subsystems cannot be validated. Must come before any PID analysis.
**Delivers:** Green face rectangles visible at 1 m with slight off-angle; TRACKING sustained 3+ seconds
**Addresses:** HAAR minSize/minNeighbors tuning (FEATURES.md P1); HUD bbox dimension display (FEATURES.md P2)
**Avoids:** Pitfall 1 (HAAR too restrictive), Pitfall 2 (PID diagnosis without stable detection)
**Stack note:** HAAR parameter change only — no new files, no new dependencies.
**Needs research-phase:** No — parameter values fully specified in PITFALLS.md and FEATURES.md.

### Phase 2: AWB Fix
**Rationale:** AWB fix is independent of PID and can be validated visually without tracking. Correct colors are needed to confirm detection quality and face bounding box accuracy in all subsequent testing. The configure-time lock is the reliable path across all Bookworm libcamera versions.
**Delivers:** Neutral color from frame 1; `ColourGains` log fires with non-zero R and B values; blue tint absent
**Addresses:** AWB blue tint fix (FEATURES.md P1); ColourGains confirmation log (FEATURES.md P1)
**Avoids:** Pitfall 3 (configure-time lock missing), Pitfall 6 (wrong fallback gains — determine empirically on hardware)
**Stack note:** `create_video_configuration(controls={"ColourGains": gains})` as primary lock; float tuple required; `(0.0, 0.0)` re-enables AWB and must not be passed.
**Needs research-phase:** No — AWB API sequence fully specified in PITFALLS.md (Picamera2 issues #825, #933, #977).

### Phase 3: PID Diagnostic Logging + Tilt/Pan Fix
**Rationale:** Add diagnostics first to understand the actual failure mode before changing control logic. `_sledz()` is the single location for all PID diagnostic points P1-P4. Logging costs zero hardware risk and is permanent infrastructure for future debugging. Fix is derived from log evidence, not speculation.
**Delivers:** Per-tick PID debug output (`logger.debug`); tilt axis physically moves; pan converges without runaway
**Addresses:** Per-tick PID logging (FEATURES.md P1); Tilt axis fix (FEATURES.md P1); PAN runaway fix (FEATURES.md P1)
**Avoids:** Pitfall 2 (detection must be Phase 1 — do not reach Phase 3 without confirmed stable TRACKING)
**Stack note:** `simple-pid.components` tuple provides `(P, I, D)` per axis; use `logger.debug` not `logger.info` to avoid log flood at 20 FPS.
**Needs research-phase:** No — diagnostic pattern fully specified in STACK.md and ARCHITECTURE.md Pattern 2.

### Phase 4: Scan Continuity Fix (conditional)
**Rationale:** Lower priority. Execute only after Phases 0-3 are verified on hardware. Phase offset `asin` formula produces a pan jerk at every TRACKING→SCANNING transition. Visually noticeable but does not block basic tracking functionality.
**Delivers:** Smooth scan resume with no pan position discontinuity at TRACKING→SCANNING transition
**Addresses:** Scan continuity (deferred in FEATURES.md)
**Avoids:** Pitfall 4 (phase offset non-convergent with absolute `time.time()`)
**Needs research-phase:** No — replacement formula (`_scan_start_time` reference) specified in PITFALLS.md.

### Phase 5: Detector Upgrade to OpenCV DNN (conditional)
**Rationale:** Execute only if HAAR tuning in Phase 1 is empirically insufficient after hardware test. DNN integration is confined to a new `DetekcjaTwarzyDNN` class with identical `wykryj()` interface. Single substitution in `TestTracker.__init__()`. Zero changes to orchestrator or state machine.
**Delivers:** Detection at ±30° head angles, partial occlusion, lower contrast; faces detected without requiring near-frontal positioning
**Uses:** `opencv-python-headless` DNN module (already installed); `models/deploy.prototxt` + `models/res10_300x300_ssd_iter_140000.caffemodel` (one-time wget download)
**Implements:** Detector swap pattern (ARCHITECTURE.md Pattern 1 — interface `wykryj()` preserved)
**Needs research-phase:** No — integration path fully specified in STACK.md and ARCHITECTURE.md.

### Phase Ordering Rationale

- **Detection before PID:** PITFALLS.md explicitly identifies misdiagnosis as the structural risk. PID behavior cannot be validated through 1-frame TRACKING events. This is the single most important sequencing constraint.
- **Pre-flight before any hardware session:** Mock mode failure is silent and produces misleading HUD output. One log line prevents hours of incorrect diagnosis.
- **AWB independent but early:** Color correctness is needed for visual inspection of detection quality. Independent of PID — can be validated in a 2-second startup without triggering TRACKING at all.
- **Scan fix last:** Not blocking; only observable after tracking is working end-to-end. Mathematical fix is specified but has lower validation priority.
- **DNN conditional:** Research confirms HAAR at `(40,40)/4` is the correct first step. DNN adds model file download and moderate integration effort with no benefit if HAAR tuning is sufficient.

### Research Flags

Phases with well-documented patterns (research complete, skip research-phase):
- **Phase 0:** Standard Python logging — trivial
- **Phase 1:** HAAR parameter values fully specified; no API research needed
- **Phase 2:** Picamera2 AWB API sequence fully specified in PITFALLS.md
- **Phase 3:** PID component logging pattern fully specified in STACK.md
- **Phase 4:** Scan formula replacement fully specified in PITFALLS.md
- **Phase 5:** DNN integration pattern fully specified in ARCHITECTURE.md and STACK.md

Phases with a decision point requiring empirical hardware input (not research — on-device iteration):
- **Phase 2:** AWB fallback gains `(2.5, 1.9)` may need adjustment for deployment lighting — read `capture_metadata()["ColourGains"]` after 5 s auto-AWB and use those values
- **Phase 5 (if triggered):** YuNet (`FaceDetectorYN`, ~380KB) vs `res10` Caffe (~10MB) — ARCHITECTURE.md and STACK.md make conflicting recommendations; resolve with a quick empirical FPS test on hardware; default to `res10` if time-constrained

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommendations source-verified: official docs, GitHub issues, simple-pid source code. MediaPipe rejection confirmed via PyPI aarch64 wheel absence. |
| Features | HIGH | Direct code audit of v1.7 `test_tracker.py` + confirmed symptom list from STATE.md. No speculation. |
| Architecture | HIGH | Direct code audit of all modified and unchanged components. Interface contracts verified with exact line references. |
| Pitfalls | HIGH (code-derived) / MEDIUM (AWB API sequencing) | Mock mode, HAAR threshold, scan phase — confirmed from source code. AWB sequencing based on verified Picamera2 GitHub issues #825, #933, #977. |

**Overall confidence:** HIGH

### Gaps to Address

- **DNN model choice conflict:** ARCHITECTURE.md recommends OpenCV `FaceDetectorYN` (YuNet, `face_detection_yunet_2023mar.onnx`, ~380KB, built into `cv2.FaceDetectorYN` since OpenCV 4.5.4) while STACK.md recommends `res10_300x300_ssd` Caffe model via `cv2.dnn.readNetFromCaffe` (~10MB). Both are viable. Resolve at Phase 5 entry with an empirical FPS test on hardware. Default to `res10` if time-constrained — STACK.md confidence is higher for this specific model.

- **AWB fallback gains environment-specific:** `AWB_FALLBACK_GAINS = (2.5, 1.9)` is not verified for the deployment environment. PITFALLS.md recommends reading settled auto-gains after 5 seconds. This calibration step should be done once on hardware at Phase 2 entry before hardcoding.

- **True root cause of tilt=0.0:** Three candidate causes remain without hardware confirmation: (A) HAAR never detects → `_skanuj()` calls `set_angles(pan, 0.0)` with hardcoded zero — most likely given detection parameters; (B) pigpiod not running → mock mode; (C) tilt PID output zero due to `sample_time` not elapsed. Phase 0 (mock mode log) and Phase 1 (detection fix) will resolve this empirically on hardware without further research.

---

## Sources

### Primary (HIGH confidence — direct code analysis + official docs)
- `src/modes/test_tracker.py` — all class and method analysis; HAAR parameters, `_skanuj()` hardcoded tilt=0, `Picamera2Stream.start()` AWB sequence
- `src/hardware.py` — `set_angles()` mock mode behavior: software state always updated regardless of `_mock_mode`
- `src/config.py` — all constants: `PAN_LIMIT`, `TILT_LIMIT`, PID gains, `SCAN_AMPLITUDE=45.0`, `SCAN_FREQUENCY=0.1`
- GitHub `m-lundberg/simple-pid` source — `components` property confirmed; `reset()` behavior verified
- GitHub `raspberrypi/picamera2` issues #312, #825, #933, #977 — AWB API sequencing behavior confirmed
- PyPI `mediapipe 0.10.33` — no `aarch64` Linux wheel confirmed
- `.planning/STATE.md` — confirmed symptom list: "brak logu ColourGains", tilt frozen at 0.0, pan runaway

### Secondary (MEDIUM confidence — community sources, multiple agree)
- GitHub `Qengineering/Face-detection-Raspberry-Pi-32-64-bits` — OpenCV DNN FPS benchmarks on RPi4
- GitHub `sr6033/face-detection-with-OpenCV-and-DNN` — `res10` model files source and download URLs
- RPi Forums t=365052 — AWB lock sequence: `set_controls` must follow `configure`
- GitHub `raspberrypi/picamera2` discussions #592 — `ColourGains=(0,0)` re-enables AWB confirmed
- GitHub `google-ai-edge/mediapipe` issue #4673 — aarch64 install failures confirmed

### Tertiary (MEDIUM confidence — not hardware-verified for this project)
- OpenCV `FaceDetectorYN` YuNet model — availability confirmed via `opencv_zoo` GitHub; FPS on RPi4 not verified for ARIES-LITE pipeline

---
*Research completed: 2026-03-29*
*Ready for roadmap: yes*
