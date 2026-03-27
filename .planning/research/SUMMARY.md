# Project Research Summary

**Project:** ARIES-LITE v1.7 — Debugging Milestone (test_tracker.py)
**Domain:** Pan-tilt face tracking bug fixes on RPi4 (Picamera2 + pigpio + simple_pid)
**Researched:** 2026-03-27
**Confidence:** HIGH

---

## Executive Summary

This milestone is a precision bug-fix release targeting four confirmed defects in `src/modes/test_tracker.py`. All four bugs are isolated to a single file and require a combined total of roughly 4 lines changed across 3 methods. There is no architectural redesign, no new dependencies, and no change to `src/hardware.py` or `src/config.py`. Research is grounded in direct source-code inspection of `simple_pid`, live verification of the Picamera2 API on target hardware, and first-principles derivation from the system's coordinate conventions documented in PROJECT.md.

The most critical fix is a single missing minus sign on `korekta_tilt` in `MaszynaStanow._sledz()`. This one character error creates a positive feedback loop on the tilt axis: the servo actively drives the camera away from the face rather than toward it. Because `simple_pid` computes `error = setpoint - input_` (with `setpoint=0`), a positive tilt error (face below center) produces a negative PID output. Without negation, the tilt angle decreases, the camera tilts upward, and the face moves further down the frame — a runaway. The tilt servo hits its soft limit within 2-3 frames, which explains both observed symptoms (tilt "not moving" and apparent camera runaway) as a single mechanical root cause. The AWB blue tint is an independent ISP initialization issue: Picamera2 starts AWB asynchronously and the current code provides no warm-up or gain lock. The scanning streak-reset is a logical off-by-one where the detection counter is cleared one frame later than state entry requires.

The key implementation risk is in the AWB fix: `set_controls()` must be called after `picam2.start()`, not before or during `configure()`. Any controls placed before `start()` are silently ignored by the Picamera2 ISP pipeline. A secondary risk is the temptation to also modify the YUV-to-BGR conversion constant while fixing AWB — these are independent issues and the existing `cv2.COLOR_YUV420p2BGR` constant is correct for Picamera2's I420 output; do not change it.

---

## Key Findings

### Recommended Stack

All existing dependencies remain unchanged. No new libraries are required for v1.7 fixes.

**Core technologies:**

- `simple_pid 2.0+` — PID control; `error = setpoint - input_` is the confirmed formula from source; `reset()` zeroes all terms including integral; `output_limits=(-10, 10)` provides anti-windup automatically in 2.x. Pin `>=2.0.0` in requirements.txt to guarantee integral clamping behavior.
- `picamera2 0.3+` (system package) — Camera capture; `set_controls()` must follow `start()` with a warm-up delay; `ColourGains` control accepts float tuples `(red_gain, blue_gain)` and implicitly disables AWB when set. Do not set `AwbEnable: False` alongside it — the Picamera2 maintainer warns this causes control sequencing conflicts.
- `opencv-python-headless 4.8+` — HAAR detection and YUV conversion; `cv2.COLOR_YUV420p2BGR` is correct for Picamera2 I420 output — do not change it when fixing AWB.
- `pigpio 1.78+` — Hardware PWM; unchanged and correct; `smooth_move_to()` must remain the only startup path to servos.

### Expected Fixes (Bug-Fix Milestone, Not Feature Release)

**Must fix (table stakes — system is broken without these):**

- Tilt PID sign inversion — one character: `korekta_tilt = -self.pid_tilt(blad_tilt)` in `_sledz()` line 263. Without this the tilt axis exhibits positive feedback; system cannot track vertically.
- AWB gain lock after convergence — add `time.sleep(2.0)` + `capture_metadata()` + `set_controls({"ColourGains": gains})` after `picam2.start()` in both `Picamera2Stream.start()` and the reinit path in `_petla_przechwytywania`.

**Should fix (logical correctness, low visual impact):**

- Scanning streak reset timing — change the streak-reset condition in `TestTracker.uruchom()` from firing on `STATE_SCANNING` entry to firing on `STATE_TARGET_LOST` entry. One condition rewrite, same line count.

**Defer to v1.8+ (confirmed not needed for v1.7):**

- Scan phase continuity — a phase-offset arcsin approach to eliminate the pan jerk at TRACKING → SCANNING resumption is fully specified in FEATURES.md (lines 316-328). Valid improvement but the current sinusoidal scan is functional. Defer unless servo jerk is confirmed as a visible user-experience issue after v1.7 fixes.
- Kalman filter, deep-learning detection, dlib identity changes, custom PID replacement — locked architectural decisions; all confirmed out of scope.

**Anti-features for this milestone:**

- Do not change Kp/Ki/Kd values — gains are empirically validated; sign bugs mimic gain problems but are distinct.
- Do not rewrite `MaszynaStanow` — state transitions are correct; only `_sledz()` and the streak-reset condition need changes.
- Do not add `AwbEnable: False` alongside `ColourGains`.

### Architecture Approach

All four fixes land in `src/modes/test_tracker.py` only. The component boundary is unchanged: `Picamera2Stream` owns camera lifecycle, `MaszynaStanow` owns state and PID logic, `DetekcjaTwarzy` owns detection and streak counting. The streak-reset fix deliberately preserves the existing boundary by modifying `uruchom()`'s condition rather than passing `DetekcjaTwarzy` into `_przejdz_do()`.

**Exact integration points:**

| Fix | File | Method | Change |
|-----|------|--------|--------|
| Tilt PID sign | `src/modes/test_tracker.py` | `MaszynaStanow._sledz()` line 263 | Add `-` prefix to `pid_tilt()` call (1 character) |
| AWB lock — start path | `src/modes/test_tracker.py` | `Picamera2Stream.start()` lines 66-70 | Add sleep + metadata read + `set_controls` after `picam2.start()` (~5 lines) |
| AWB lock — reinit path | `src/modes/test_tracker.py` | `Picamera2Stream._petla_przechwytywania` lines 111-113 | Add matching `controls={"AwbMode": 4}` to reinit `create_video_configuration` call (1 line) |
| Streak reset timing | `src/modes/test_tracker.py` | `TestTracker.uruchom()` lines 323-324 | Change condition from SCANNING entry to TARGET_LOST entry (1 condition rewrite) |

Total change surface: 4 locations in 1 file. No other file is modified.

**Sign convention reference (canonical, for maintenance):**

```
PIXEL COORDINATES (OpenCV): origin = top-left, x right, y down

ERROR DEFINITIONS:
  blad_pan  = srodek_x - ramka_cx   (positive = face RIGHT of center)
  blad_tilt = srodek_y - ramka_cy   (positive = face BELOW center)

simple_pid OUTPUT (setpoint=0):  pid(error) = -Kp * error

HARDWARE (PROJECT.md, empirically confirmed):
  pan_angle+  → camera rotates right → face moves LEFT in frame
  tilt_angle+ → camera rotates down  → face moves UP in frame

REQUIRED:
  face right  (+blad_pan)  → pan_angle must INCREASE → korekta_pan POSITIVE
  face below  (+blad_tilt) → tilt_angle must INCREASE → korekta_tilt POSITIVE

DERIVATION:
  korekta_pan  = -pid_pan(blad_pan)   = +Kp*blad_pan  ✓  (already in code)
  korekta_tilt = -pid_tilt(blad_tilt) = +Kp*blad_tilt ✓  (MISSING — the bug)
```

**Architecture invariants that must not be broken:**

1. `Picamera2Stream` and `MaszynaStanow` remain separate classes.
2. `MaszynaStanow` must not import `DetekcjaTwarzy`.
3. `smooth_move_to()` must remain the only startup path to servos.
4. `_przejdz_do()` remains the single state transition method.

### Critical Pitfalls

1. **AWB set_controls before start() — silently ignored.** The ISP pipeline is not active until `start()` is called. Placing `set_controls()` before `start()` or inside `configure()` has no effect and produces no error. Always: `start()` → `time.sleep(2.0)` → `capture_metadata()` → `set_controls({"ColourGains": gains})`. (HIGH confidence — confirmed by Picamera2 maintainer, GitHub issue #825)

2. **Double-negation trap on PID corrections.** Pan is already correctly negated. Adding a second negation to pan while fixing tilt will reverse pan behavior. Verify each axis independently before changing signs: (a) confirm `blad_pan` is positive when face is right of center, (b) confirm `set_angles(+10, 0)` pans camera right. Only then derive required correction sign from first principles. Only tilt needs to change. (HIGH confidence)

3. **Tilt non-movement root cause check — pigpiod first.** If `pigpiod` is not running, `PanTiltSystem` falls back to mock mode silently — no servo movement, no error. Run `systemctl is-active pigpiod` before any PID sign analysis. Also check `maszyna.hardware._mock_mode` at startup. (HIGH confidence)

4. **Soft limit masking PID output.** The sign bug drives the tilt servo to the ±30° limit within 2-3 frames; all subsequent corrections are clamped silently. The servo appears frozen while PID computes valid outputs. Add debug logging to `hardware.py` `set_angles()` to make clamping visible during diagnosis — do not assume "no movement" means "zero correction." (HIGH confidence)

5. **AWB warm-up flicker — first 3-10 frames ignore manual gains.** Controls set via `set_controls()` take effect 2-3 frames after being issued. Evaluate color correctness only after steady state. A 5-frame warm-up skip in `_petla_przechwytywania` prevents these pre-convergence frames from being stored. (HIGH confidence)

6. **`simple_pid` version anti-windup difference.** Integral clamping to `output_limits` is reliable in `simple_pid >= 2.0` but not guaranteed in 1.x. Check `pip show simple-pid` on device; update `requirements.txt` to pin `simple-pid>=2.0.0`. (MEDIUM confidence — depends on installed version)

---

## Implications for Roadmap

### Phase 1: Camera Fix (AWB Blue Tint)

**Rationale:** Camera quality fix first — all subsequent hardware tests observe correct color rendering. Independent of all logic fixes; isolated to `Picamera2Stream`. Low risk of interaction with servo or PID logic.

**Delivers:** Blue tint eliminated; neutral skin-tone rendering; stable color across frames after ~2s warm-up.

**Changes:**
- `Picamera2Stream.start()` — add `time.sleep(2.0)` + `capture_metadata()` + `set_controls({"ColourGains": colour_gains})` after `picam2.start()`; add fallback to `(2.5, 1.9)` if metadata unavailable.
- `Picamera2Stream._petla_przechwytywania` reinit block — add matching `controls={"AwbMode": 4}` to the `create_video_configuration` call.

**Avoids:** Pitfall 3 (controls before start), Pitfall 4 (warm-up flicker), Pitfall 10 (int vs float ColourGains), Pitfall 8 (do not touch YUV constant).

**Needs research-phase:** No — AWB API sequence is fully specified in STACK.md with exact code samples.

---

### Phase 2: PID Sign Fix (Tilt Runaway / Tilt Not Moving)

**Rationale:** The most impactful functional fix. Applying after AWB means the first motion test under correct color simultaneously validates both fixes. One-character change with immediately observable hardware effect.

**Delivers:** Tilt axis moves toward face; no runaway on either axis; system converges to face-centered steady state in both pan and tilt.

**Changes:**
- `MaszynaStanow._sledz()` line 263: `korekta_tilt = -self.pid_tilt(blad_tilt)` (add `-` prefix).

**Verification:** Hold face below frame center; confirm `Tilt:` HUD value increases (servo moves down); face moves toward vertical center. Hold face left; confirm `Pan:` HUD value decreases (servo moves left). No runaway in either axis.

**Avoids:** Pitfall 1 (double-negation), Pitfall 2 (mock-mode misdiagnosis before fix), Pitfall 7 (soft limit masking).

**Needs research-phase:** No — fix is fully derived and verified in FEATURES.md and ARCHITECTURE.md with before/after traces.

---

### Phase 3: Scanning Streak Reset Timing

**Rationale:** Most subtle fix; effect only visible in rapid TRACKING → SCANNING → TRACKING transition sequences. Saving it last allows phases 1 and 2 to be verified in stable tracking scenarios first.

**Delivers:** Detection streak counter resets at the correct frame — on `STATE_TARGET_LOST` entry rather than one frame late at `STATE_SCANNING` entry.

**Changes:**
- `TestTracker.uruchom()` lines 323-324: change condition from `stan == config.STATE_SCANNING and poprzedni_stan != config.STATE_SCANNING` to `stan == STATE_TARGET_LOST and poprzedni_stan == config.STATE_TRACKING`.

**Avoids:** Pitfall 9 (state transition timing), Pitfall 5 (PID reset in wrong location — keep reset only in `_przejdz_do()` for SCANNING entry).

**Needs research-phase:** No — ARCHITECTURE.md provides exact before/after code for the recommended Option B approach.

---

### Phase Ordering Rationale

- AWB first because correct color rendering is needed to evaluate tracking behavior visually in all subsequent tests. Fixing color first eliminates a confounding variable.
- PID sign second because it is the highest-impact functional fix. A working tilt axis enables meaningful verification of the full tracking loop.
- Streak timing last because it requires an already-working tracking system to exercise the TRACKING → TARGET_LOST → SCANNING transition path at test time.
- All three phases are independent with no shared state. They could be applied in a single commit, but sequential verification on hardware is the safer path given the physical servo risks.

### Research Flags

All three phases have no need for additional research-phase runs. Fixes are fully specified with exact line numbers, before/after code, and verification methods.

Phases that may benefit from empirical tuning on-device (not research — on-device iteration):

- **Phase 1 (AWB):** If `capture_metadata()["ColourGains"]` returns `None`, the fallback `(2.5, 1.9)` may need adjustment for specific indoor lighting. Read back `capture_metadata()["ColourGains"]` after 3-5 seconds of running to confirm settled values before hard-coding.
- **Phase 2 (PID):** If tilt tracking oscillates significantly after the sign fix, consider reducing `PID_TILT_P` from 0.05 to 0.03 as a first tuning step. The existing gains are validated for pan; tilt dynamics may differ if camera mass distribution is asymmetric.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | simple_pid source inspected directly from GitHub; Picamera2 AWB API verified from maintainer responses and GitHub issues #825, #232, #592; pigpio and OpenCV are unchanged from v1.6 |
| Features | HIGH | All four bugs diagnosed from first principles + verified library behavior; PID sign derivation is a mathematical proof; AWB API sequence confirmed by maintainer |
| Architecture | HIGH | Based on direct source analysis of test_tracker.py (all methods), hardware.py, config.py; all integration points identified with exact line numbers; live verification of Picamera2 API on target hardware |
| Pitfalls | HIGH (7/10) / MEDIUM (3/10) | Pitfalls 1, 2, 3, 4, 5, 7, 9 are HIGH confidence from direct code or verified community sources; Pitfalls 6, 8, 10 are MEDIUM due to version-dependence and hardware-specific format variations |

**Overall confidence:** HIGH

### Gaps to Address

- **YUV420 plane ordering on actual hardware (Pitfall 8):** Research confirms `cv2.COLOR_YUV420p2BGR` is correct for Picamera2 I420 output. If a green-magenta cast (distinct from the blue AWB tint) appears after the AWB fix, verify `klatka_yuv.shape` and test `cv2.COLOR_YUV2BGR_I420` as an alternative. Do not preemptively change this.

- **AWB fallback gain values (Phase 1):** The fallback `(2.5, 1.9)` is a starting point for indoor LED/fluorescent on IMX219 V2. Tune empirically in 0.1 increments if skin tones are still incorrect. Read back `capture_metadata()["ColourGains"]` after warm-up to discover the correct values for the specific deployment environment.

- **simple_pid version on RPi4 (Pitfall 6):** Anti-windup integral clamping behavior differs between 1.x and 2.x. Verify with `pip show simple-pid` on the device; update `requirements.txt` to `simple-pid>=2.0.0` if not already pinned.

- **Scan phase continuity (deferred):** The arcsin-based phase offset approach described in FEATURES.md (lines 316-328) is mathematically complete and ready to implement if servo jerk at TRACKING → SCANNING resumption is confirmed as a visible issue after v1.7. The math is correct; implementation requires adding `_scan_phase_offset` field to `MaszynaStanow.__init__` and modifying `_inicjuj_faze_skanowania()` and `_skanuj()`.

---

## Sources

### Primary (HIGH confidence)

- `simple_pid` source code, `raw.githubusercontent.com/m-lundberg/simple-pid/master/simple_pid/pid.py` — `__call__` formula, `reset()` complete behavior, integral clamping
- Picamera2 GitHub issue #825 — ColourGains not working, AWB control ordering requirement
- Picamera2 GitHub issue #232 — setting AwbMode with camera controls
- Picamera2 GitHub discussion #592 — disabling AWB and controlling gains manually; ColourGains implicitly disables AWB
- RPi Forums t=365052 — AWB lock with Picamera2, `set_controls` after `start()` requirement; do not use `AwbEnable: False` alongside `ColourGains`
- `src/modes/test_tracker.py` — direct source analysis: all affected methods, exact line numbers
- `src/hardware.py` — `set_angles()` clamping behavior, mock mode fallback, sign conventions
- `src/config.py` — PID gains, output limits, servo soft limits, state names
- `.planning/PROJECT.md` — hardware mounting: `pan+ = right`, `tilt+ = down` (empirically confirmed)
- `CLAUDE.md` — threading model, hardware constraints, architecture overview

### Secondary (MEDIUM confidence)

- PyImageSearch pan-tilt face tracking tutorial — error sign convention pattern using `panAngle = -1 * pan.value`; different mounting but formula structure confirms standard approach
- GitHub raspberrypi/picamera2 issue #803 — AwbMode not always effective; ColourGains freeze is more reliable
- Arducam forum — IMX219 blue tint is a known issue; AWB mode selection or gain lock resolves it
- `simple_pid` changelog — anti-windup integral clamping behavior change between 1.x and 2.x

---
*Research completed: 2026-03-27*
*Ready for roadmap: yes*
