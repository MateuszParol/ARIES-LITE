# Project Research Summary

**Project:** ARIES-LITE v1.9 — Stabilizacja Ruchu i Obrazu
**Domain:** Embedded real-time vision + servo control (RPi4 / Picamera2 / pigpio / PID)
**Researched:** 2026-03-29
**Confidence:** HIGH

## Executive Summary

v1.9 is a focused bug-fix milestone targeting four confirmed behavioral defects in `run_test_tracker.py` / `src/modes/test_tracker.py`. All four bugs are narrow, isolated failures in an otherwise structurally sound system validated through v1.8. The existing architecture, PID gains, hardware abstraction, and DNN detection pipeline are all correct — the bugs are sequencing errors and single wrong constants, not design problems. No new libraries are required for any fix.

The recommended approach is to apply all four fixes exclusively in `src/modes/test_tracker.py` (one file), in dependency order: AWB/color fix first (independent, zero-risk), then PID reset on TRACKING entry, then tilt sinusoidal scanning, then scan jitter verification. No architectural changes, no changes to `hardware.py`, `config.py`, or `run_test_tracker.py`. This approach minimizes regression risk against empirically validated hardware components.

The primary risks are: (1) the AWB green tint having a dual cause — wrong YUV conversion flag (`COLOR_YUV420p2BGR` instead of `COLOR_YUV420p2RGB`) AND wrong `ColourGains` fallback value `(1.0, 1.0)` — both must be fixed; (2) the servo escape on TRACKING entry being caused by large initial P-term output in addition to missing `reset()`, requiring `PID_OUTPUT_LIMIT` to be reduced from 10.0 to 3.0; and (3) scan jitter requiring empirical verification on hardware before deciding whether a servo interpolation approach beyond `DNN_SKIP_EVERY` increase is needed.

## Key Findings

### Recommended Stack

No new packages are required for any v1.9 fix. The existing stack — Picamera2, pigpio/gpiozero `PiGPIOFactory`, `simple-pid 2.0.x`, OpenCV DNN (res10 SSD) — is sufficient. All four fixes are logic and constant changes within one Python file.

**Core technologies (unchanged from v1.8):**
- `Picamera2` + `libcamera`: YUV420 lores stream at 320x240 — fix requires `COLOR_YUV420p2RGB` (not `2BGR`) for correct R/B channel mapping from libcamera's YUV420
- `pigpio` / `gpiozero PiGPIOFactory`: hardware PWM eliminates electrical jitter but cannot smooth software-commanded angle jumps — smoothing must be in Python code via EMA if needed
- `simple-pid 2.0.x`: `output_limits` provides built-in anti-windup (clamps both output and integral accumulator); `reset()` clears integral and last_error — both mechanisms required for v1.9 PID fix
- OpenCV DNN (res10 SSD): `DNN_SKIP_EVERY=5` creates inference stalls that interrupt `set_angles()` calls, causing scan lurches — increase to 10 as first smoothing intervention

### Expected Features

**Must-fix for v1.9 to have operational value:**
- Tilt sinusoidal in `_skanuj()` — scan covers vertical field of view (current: 1D horizontal sweep only, tilt hardcoded to 0.0)
- AWB `cvtColor` flag correction (`COLOR_YUV420p2BGR` → `COLOR_YUV420p2RGB`) — root cause of green tint is R/B channel swap in YUV conversion, confirmed by Picamera2 official example and issue #848
- `AWB_FALLBACK_GAINS` update from `(1.0, 1.0)` to `(2.2, 1.8)` — unity gains suppress R and B relative to sensor's native green bias; fallback only fires when AWB metadata unavailable but must be realistic
- PID `reset()` on TRACKING entry + `PID_OUTPUT_LIMIT` reduced from 10.0 to 3.0 — reset removes carried integral; output limit prevents P-term alone from driving servo to limits on large initial errors
- Scan jitter empirical verification — confirm smooth motion or increase `DNN_SKIP_EVERY` from 5 to 10

**Should-fix (same milestone, low cost):**
- Tilt phase-offset continuity on SCANNING re-entry — extend existing `math.asin(clamp)` pattern to tilt axis to prevent jump discontinuity when resuming scan
- Startup diagnostic: `smooth_move_to(0, 20)` then `(0, 0)` in `inicjalizuj()` — hardware isolation confirms tilt servo is functional before state machine analysis
- Diagnostic logging: ColourGains values after AWB lock, tilt argument in `set_angles()` during scan, PID components on TRACKING entry first 5 ticks
- Optional deadband: `TRACKING_DEADBAND_PX = 15` — suppress micro-corrections when face is approximately centered

**Defer to future milestones:**
- `sample_time` dynamic calibration to actual loop FPS — only if `reset()` + tighter output limit is insufficient
- CSRT tracker between DNN detections in test module — architectural change, not a bug fix
- Lissajous frequency ratio empirical optimization — after tilt scan is confirmed working
- MG90S pulse width calibration (`min_pulse_width=0.0005, max_pulse_width=0.0024`) in `hardware.py` — hardware.py change, separate from v1.9 bug scope
- EMA servo smoothing (`update_servos()` with `SERVO_ALPHA=0.4`) — only if `DNN_SKIP_EVERY=10` is insufficient for scan jitter

### Architecture Approach

All four fixes are contained in `src/modes/test_tracker.py`. The architecture invariants from v1.8 are preserved: `MaszynaStanow` does not import `DetekcjaTwarzy`, `smooth_move_to()` remains the only safe-start path, `_przejdz_do()` remains the only state transition method, and `set_angles()` in `PanTiltSystem` remains the only servo command path. AWB lock sequence stays in `Picamera2Stream.start()`.

**Major components and their role in v1.9 fixes:**

1. `Picamera2Stream` (`test_tracker.py:55–170`) — color fix: change `cvtColor` constant on line 118; update `AWB_FALLBACK_GAINS` constant on line 38; optionally add `"AwbEnable": False` to post-warm-up `set_controls()` call for version robustness
2. `MaszynaStanow` (`test_tracker.py:242–345`) — tilt scan: add tilt sinusoidal to `_skanuj()` with new module-level constants `SCAN_AMPLITUDE_TILT=15.0`, `SCAN_FREQUENCY_TILT=0.07`; PID fix: add `pid_pan.reset()` + `pid_tilt.reset()` in `_przejdz_do()` for `STATE_TRACKING` entry; reduce `PID_OUTPUT_LIMIT` from 10.0 to 3.0
3. `DetekcjaTwarzy` (`test_tracker.py:173–239`) — scan jitter first pass: increase `DNN_SKIP_EVERY` from 5 to 10 to reduce inference stall frequency
4. `PanTiltSystem` (`hardware.py`) — no changes required for core fixes; optional EMA `update_servos()` method as Phase 4 fallback if jitter persists
5. `TestTracker` (`test_tracker.py:348–468`) — no changes required

### Critical Pitfalls

1. **AWB green tint has two independent causes, both must be fixed** — `COLOR_YUV420p2BGR` swaps R and B channels from libcamera's YUV420, making green dominant regardless of ColourGains values. AND `AWB_FALLBACK_GAINS=(1.0,1.0)` suppresses R and B relative to IMX219's green bias (expected gains are 1.6–2.5 for R and 1.4–2.0 for B). Fixing only one leaves visible tint. Fix the `cvtColor` flag first (one constant), then the fallback value.

2. **PID escape is P-term magnitude, not only integral windup** — with `PID_OUTPUT_LIMIT=10.0` and `P=0.05`, a face at the frame edge produces `0.05 × 160 = 8.0°` per tick from P-term alone, reaching the ±60° servo limit in ~8 ticks (200ms at 30 FPS). Adding `reset()` on TRACKING entry is necessary but not sufficient. `PID_OUTPUT_LIMIT` must also be reduced to 3.0. Do not change PID gains — v1.8 values are empirically validated.

3. **Tilt hardware must be verified before state machine analysis** — during SCANNING, tilt reads `0.0` in HUD because `_skanuj()` hardcodes `set_angles(pan, 0.0)` (this is the bug, but the HUD reading is technically correct behavior). If TRACKING never triggers or is too brief, tilt appears frozen even with a hardware-functional servo. Always confirm with `smooth_move_to(0, 20)` direct call before diagnosing state machine paths.

4. **`AwbEnable: False` sequencing is Picamera2 version-dependent** — setting `ColourGains` alone implicitly disables AWB on most versions (issue #592) but not all (issue #825 reports version-dependent failures). Add explicit `"AwbEnable": False` in the post-warm-up `set_controls()` call but NOT in configure-time controls (would prevent AWB from converging during warm-up). Verify color stability over 30 seconds after lock.

5. **`smooth_move_to()` is blocking and must never be called in the main tracking loop** — it is a while-loop with `time.sleep(0.05)` per step; moving 45° takes 2.25 seconds and freezes camera capture for that duration. Proposing it as the fix for scan jitter would break the entire pipeline. Scan smoothness must come from the sinusoidal formula plus optional EMA in `update_servos()`.

## Implications for Roadmap

Based on research, the recommended phase structure is 4 sequential phases confined to one file, ordered by independence and hardware verification dependency.

### Phase 1: AWB / Color Fix (BUG-3)

**Rationale:** Independent of all other fixes. Minimum of two one-line changes: `cvtColor` constant and `AWB_FALLBACK_GAINS` value. Zero regression risk. Fixing color first provides a correct visual output for all subsequent hardware verification steps — if colors are systematically wrong, servo behavior and detection quality are harder to judge.

**Delivers:** Neutral camera colors from first frame; no green tint; AWB warm-up lock producing meaningful ColourGains values (R>1.4, B>1.4).

**Addresses:** Fix 3 from FEATURES.md (camera neutral colors, P1); AWB fallback gains update (P2).

**Avoids:** Pitfall 3 (AWB green from fallback `(1.0,1.0)`), Pitfall 4 (AWB relock drifting after warm-up), ARCHITECTURE Anti-Pattern 1 (trying to fix YUV color error via AWB gains tuning).

**Changes in `test_tracker.py`:**
- Line 118: `COLOR_YUV420p2BGR` → `COLOR_YUV420p2RGB`
- Line 38: `AWB_FALLBACK_GAINS = (1.0, 1.0)` → `(2.2, 1.8)`
- Optional: `"AwbEnable": False` in post-warm-up `set_controls()` call

### Phase 2: PID Reset on TRACKING Entry + Output Limit (BUG-4)

**Rationale:** Independent of tilt scan. Fixing PID escape before tilt scan allows Phase 3 to confirm tilt servo hardware responds during TRACKING before adding tilt to scanning — separating the concerns cleanly.

**Delivers:** TRACKING state enters without immediate servo runaway; face acquisition converges within 1–3 seconds; no continuous clamp warnings at TRACKING entry.

**Addresses:** Fix 4 from FEATURES.md (PID-controlled tracking without escape, P1).

**Avoids:** Pitfall 5 (PID output accumulates unbounded on large initial error), ARCHITECTURE Anti-Pattern 2 (reset only on SCANNING entry, not TRACKING entry).

**Changes in `test_tracker.py`:**
- `_przejdz_do()`: add `pid_pan.reset()` and `pid_tilt.reset()` on `STATE_TRACKING` entry (2 lines)
- `PID_OUTPUT_LIMIT` constant: 10.0 → 3.0
- Optional: add `TRACKING_DEADBAND_PX = 15` and deadband guard in `_sledz()`

### Phase 3: Tilt Sinusoidal Scan (BUG-1)

**Rationale:** Depends on Phase 2 confirmation that tilt servo hardware is functional (TRACKING must be reachable and tilt must respond in `_sledz()` before adding tilt to `_skanuj()`). Extends scan from 1D to Lissajous 2D pattern covering the full vertical field.

**Delivers:** Both axes scan during SCANNING state; `SCAN_FREQUENCY_TILT=0.07 Hz` (slower than `SCAN_FREQUENCY=0.1 Hz` pan) produces aperiodic Lissajous coverage; phase-offset continuity prevents servo jump on SCANNING re-entry for tilt axis.

**Addresses:** Fix 1 from FEATURES.md (dual-axis sinusoidal scanning, P1); tilt phase-offset continuity (P1 — same change).

**Avoids:** Pitfall 1 (tilt masked by hardcoded 0.0 in scan), ARCHITECTURE Anti-Pattern 3 (1D scan only).

**Changes in `test_tracker.py`:**
- Add module-level constants: `SCAN_AMPLITUDE_TILT = 15.0`, `SCAN_FREQUENCY_TILT = 0.07`
- `_skanuj()`: compute `tilt = SCAN_AMPLITUDE_TILT * math.sin(2.0 * math.pi * SCAN_FREQUENCY_TILT * t)` and pass to `set_angles(pan, tilt)` (1 line change + 1 new expression)
- `_przejdz_do()` SCANNING branch: extend phase-offset logic to tilt axis

### Phase 4: Scan Jitter Verification and Smoothing (BUG-2)

**Rationale:** Depends on Phase 3 (jitter evaluation with both axes active). DNN inference blocking the main loop at `DNN_SKIP_EVERY=5` creates irregular `set_angles()` timing. Whether the resulting jitter is visible on hardware determines which fix path to take — this cannot be determined without a hardware run.

**Delivers:** Smooth continuous scan motion without visible lurching. Decision point: `DNN_SKIP_EVERY=10` is the minimal-risk first pass; if jitter persists, implement EMA servo smoothing via `update_servos()` with `SERVO_ALPHA=0.4`.

**Addresses:** Fix 2 from FEATURES.md (smooth servo interpolation, P2).

**Avoids:** Pitfall 6 (`smooth_move_to()` blocking — confirmed it must not be used here), Pitfall 7 (MG90S pulse width defaults — noted as future debt, not v1.9 scope).

**Changes (minimal path):**
- `test_tracker.py`: `DNN_SKIP_EVERY` 5 → 10

**Changes (if minimal insufficient):**
- `hardware.py`: add `_pan_target`, `_tilt_target` fields and `update_servos()` EMA method (`SERVO_ALPHA=0.4`)
- `test_tracker.py`: call `self.hardware.update_servos()` once per tick in `TestTracker.uruchom()` after `self.maszyna.tick(...)`

### Phase Ordering Rationale

- **Color first:** Correct visual output is prerequisite for all hardware verification. Cannot reliably judge servo behavior or detection quality with systematic channel swap and wrong white balance.
- **PID before tilt scan:** Confirms tilt servo hardware via TRACKING state before adding tilt to scanning. Prevents diagnosing tilt scan as broken when the actual cause is PID escape preventing sustained TRACKING.
- **Tilt scan before jitter fix:** Per-tick angle deltas change when tilt is added to scanning; jitter evaluation must run against the final scan formula.
- **Empirical jitter verification last:** The correct fix for jitter cannot be determined without running code on RPi4. Having a two-path plan (DNN_SKIP_EVERY vs. EMA) removes uncertainty from planning.
- **Each phase independently verifiable:** Matches the project's GSD empirical methodology — commit and verify per phase before proceeding.

### Research Flags

Phases with well-documented patterns (skip `/gsd:research-phase`):
- **Phase 1 (AWB/color):** Root cause confirmed with official Picamera2 examples and issue tracker. Two one-constant changes fully specified.
- **Phase 2 (PID reset + output limit):** `simple-pid` `reset()` and `output_limits` behavior source-verified. Implementation is 3 lines plus one constant change.
- **Phase 3 (tilt sinusoidal):** Lissajous scan pattern is standard control theory. Two new constants plus one expression in `_skanuj()`.

Phases requiring empirical hardware decision during execution:
- **Phase 4 (scan jitter):** Whether `DNN_SKIP_EVERY=10` is sufficient cannot be determined without a hardware run. Both fix paths are fully specified — decision is made on-device, not in planning.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new libraries needed. All fix mechanisms source-verified: Picamera2 official example (yuv_to_rgb.py), GitHub issues #848/#592/#322/#825, simple-pid source code, gpiozero docs. |
| Features | HIGH | All four bugs confirmed by direct code audit of `src/modes/test_tracker.py` with exact line references. Fix specifications include before/after code. Feature boundaries (fix vs. defer) clearly established. |
| Architecture | HIGH | All changes isolated to one file confirmed by tracing call paths. Component responsibility matrix complete with risk level per fix. Architecture invariants explicitly identified and preserved. |
| Pitfalls | HIGH (code-derived) / MEDIUM (ISP pipeline internals) | Pitfalls 1–2 (tilt hardware, tilt sign) derived from code and empirical history. Pitfalls 3–4 (AWB ISP pipeline) rely on community-confirmed Picamera2 issues with multiple corroborating sources. Pitfall 7 (MG90S pulse calibration) based on forum reports — medium confidence until hardware-verified. |

**Overall confidence:** HIGH

### Gaps to Address

- **`AwbEnable: False` interaction:** Whether to include alongside `ColourGains` in post-warm-up `set_controls()` is Picamera2 version-dependent. Recommendation: include it, then verify color stability over 30 seconds. If issues arise on the specific libcamera version installed, remove it and rely on implicit AWB disable.
- **`PID_OUTPUT_LIMIT` 3.0 vs. 5.0 exact value:** Requires empirical validation on hardware. Start with 3.0; if tracking is too sluggish for normal head movement speed, increase to 5.0. This cannot be resolved without a running test on RPi4.
- **EMA `SERVO_ALPHA=0.4` tuning (Phase 4 fallback path only):** Recommended starting value is based on standard robotics practice for ~10 FPS loops. Actual optimal value depends on measured loop FPS and physical servo response characteristics. Adjust empirically if the EMA path is activated.
- **Tilt phase offset value at SCANNING re-entry:** The `math.asin(clamp)` technique for tilt requires `hardware.tilt_angle` at the moment of TRACKING→SCANNING transition. Verify this value is meaningful (not a stale clamped escape value) before trusting it as the phase-offset source. If tilt was clamped to a limit during TRACKING, the offset will start from that limit rather than from a centered position.

## Sources

### Primary (HIGH confidence — direct code analysis)
- `src/modes/test_tracker.py` — `AWB_FALLBACK_GAINS = (1.0, 1.0)`, `_skanuj()` hardcoded `tilt=0.0` on line 302, `cvtColor(YUV420p2BGR)` wrong flag on line 118, `pid.reset()` absent on TRACKING entry in `_przejdz_do()`, `DNN_SKIP_EVERY = 5`, `PID_OUTPUT_LIMIT = 10.0`
- `src/hardware.py` — `AngularServo` default pulse widths; `smooth_move_to()` blocking while-loop with `time.sleep(0.05)` per step; `set_angles()` software-state tracking
- `src/config.py` — PID gains (`P=0.05, I=0.001, D=0.005`), servo limits (`PAN=±60°, TILT=±30°`), `SERVO_STEP=1.0`
- `.planning/PROJECT.md` — v1.9 problem statement; v1.7 tilt negation fix history; v1.8 ColourGains `(1.0,1.0)` history

### Secondary (HIGH confidence — official sources)
- [Picamera2 yuv_to_rgb.py official example](https://github.com/raspberrypi/picamera2/blob/main/examples/yuv_to_rgb.py) — confirms `COLOR_YUV420p2RGB` for correct BGR output from YUV420 lores stream; `COLOR_YUV420p2BGR` produces R/B channel swap
- [Picamera2 issue #848](https://github.com/raspberrypi/picamera2/issues/848) — maintainer documents R/B swap from `COLOR_YUV420p2BGR` on libcamera YUV420; added warning to documentation
- [Picamera2 issue #592](https://github.com/raspberrypi/picamera2/issues/592) — setting `ColourGains` disables AWB; `(1.0,1.0)` suppresses R and B, not neutral; green channel is always reference at 1.0
- [simple-pid source code](https://github.com/m-lundberg/simple-pid) — `output_limits` clamps output AND integral accumulator (anti-windup); `reset()` clears integral and last_error
- [Lissajous scan pattern](https://en.wikipedia.org/wiki/Lissajous_curve) — frequency ratio 1:2 produces figure-8 coverage of full vertical field per pan cycle

### Secondary (MEDIUM confidence — community sources)
- [Picamera2 issue #322](https://github.com/raspberrypi/picamera2/issues/322) — `ColourGains` AWB disable and CCM behavior; green channel always 1.0 in libcamera ColourGains (R/B are the only gain parameters)
- [Picamera2 issue #825](https://github.com/raspberrypi/picamera2/issues/825) — `AwbEnable: False` + `ColourGains` in same `set_controls()` causes sequencing issues on some Bookworm versions
- [Picamera2 issue #897](https://github.com/raspberrypi/picamera2/issues/897) — green tint root cause via lens shading mismatch; consistent finding with YUV channel swap
- [gpiozero RPi Forums thread](https://forums.raspberrypi.com/viewtopic.php?t=331790) — MG90S requires 500–2500µs range; default 1000–2000µs gpiozero defaults limit physical range and produce non-linear motion
- [sinusoidal scan jitter on RPi4](https://forums.raspberrypi.com/viewtopic.php?t=274329) — pigpio DMA resolves electrical jitter; software-side jitter from irregular call timing requires wall-clock sinusoidal formula (already implemented)

---
*Research completed: 2026-03-29*
*Ready for roadmap: yes*
