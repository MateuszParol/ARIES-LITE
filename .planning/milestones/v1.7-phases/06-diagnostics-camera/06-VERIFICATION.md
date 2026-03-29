---
phase: 06-diagnostics-camera
verified: 2026-03-27T16:00:00Z
status: human_needed
score: 4/5 must-haves verified
re_verification: false
human_verification:
  - test: "Run python3 run_test_tracker.py on RPi4 with camera attached. Observe terminal output during startup (first 5 seconds)."
    expected: "INFO line 'Czekam na stabilizację AWB (2s)...' appears, followed by INFO 'ColourGains zablokowane: (R=X.XX, B=X.XX)' with real sensor values. After ~3 seconds, live video shows neutral skin tones without blue cast."
    why_human: "Requires physical Picamera2 hardware and live ISP pipeline — cannot mock capture_metadata() return value or verify visual color output programmatically."
  - test: "While run_test_tracker.py is running, either move the face target far to one edge or temporarily set SCAN_AMPLITUDE=65.0 in test_tracker.py and restart."
    expected: "Terminal shows 'WARNING ... Clamp pan: X.X -> 60.0 (limit)' when the sinusoidal scan or PID output exceeds ±60° on pan. WARNING appears for only the clamped axis."
    why_human: "Clamp logic is verified programmatically, but confirming it appears during the live system run — and is readable at the expected log level in the configured logging handler — requires an actual execution on hardware."
---

# Phase 6: Diagnostics & Camera Verification Report

**Phase Goal:** Hardware clamping is observable in logs and the camera delivers neutral color rendering — every subsequent test can be trusted visually and every servo limit event is traceable
**Verified:** 2026-03-27T16:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | `set_angles()` emits WARNING in terminal for each axis whose value was clamped to the soft limit (pan ±60°, tilt ±30°) | VERIFIED | `src/hardware.py` lines 52-55: two independent `if` blocks emit `logger.warning(f"Clamp pan: ...")` and `logger.warning(f"Clamp tilt: ...")`. Automated test confirms output for OOB values (75.0, -35.0) → two warnings; in-limit (30.0, 10.0) → zero warnings. |
| 2  | Both axes are logged independently — only the axis that was clamped gets a WARNING line | VERIFIED | Separate `if pan_clamped != pan` and `if tilt_clamped != tilt` (not `if/elif`). Automated test confirms pan-only OOB (70.0, 5.0) produces exactly one WARNING for pan, none for tilt. |
| 3  | AWB warm-up runs after camera start(); terminal shows INFO 'Czekam na stabilizację AWB (2s)...' then INFO 'ColourGains zablokowane: (R=X.XX, B=X.XX)' | VERIFIED (code path) / NEEDS HUMAN (live execution) | `src/modes/test_tracker.py` lines 78-87: `logger.info("Czekam na stabilizację AWB (2s)...")`, `time.sleep(2.0)`, `capture_metadata()`, conditional fallback, `set_controls({"ColourGains": gains})`, `logger.info(f"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})")`. All strings verified present. Sequencing: `self._thread.start()` line 76 → `time.sleep(2.0)` line 79. Cannot verify actual sensor return value without RPi4 hardware. |
| 4  | Live video feed shows neutral skin tones within 3 seconds of startup — blue cast clears after warm-up | NEEDS HUMAN | Visual quality — requires physical camera and human observation. |
| 5  | If ColourGains metadata returns None, AWB_FALLBACK_GAINS (2.5, 1.9) is applied with a WARNING log — no crash | VERIFIED | Lines 82-84: `if gains is None: logger.warning("ColourGains niedostępne, używam fallback (2.5, 1.9)"); gains = AWB_FALLBACK_GAINS`. Module constant `AWB_FALLBACK_GAINS = (2.5, 1.9)` at line 35. `metadata.get("ColourGains")` used (not direct key access — no KeyError possible). |

**Score:** 4/5 truths verified programmatically (truth #4 requires human; truth #3 code path verified, live execution needs hardware)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/hardware.py` | Clamp detection + per-axis WARNING logging in set_angles() | VERIFIED | Lines 49-58: `pan_clamped`/`tilt_clamped` computed, two independent `if` comparisons, `logger.warning` with format `"Clamp pan: {pan:.1f} -> {pan_clamped:.1f} (limit)"`. WARNING block (lines 52-55) precedes `if not self._mock_mode` guard (line 60) — fires in both mock and hardware modes. Commit `ea5e41d`. |
| `src/modes/test_tracker.py` | AWB warm-up lock in Picamera2Stream.start() + AWB_FALLBACK_GAINS constant | VERIFIED | `AWB_FALLBACK_GAINS = (2.5, 1.9)` at line 35. Full warm-up block at lines 78-87 inside `Picamera2Stream.start()`, after `self._thread.start()`. `AwbEnable` absent (verified by grep). Commit `fc9fd55`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `set_angles()` raw input | `logger.warning` | per-axis comparison before assignment | WIRED | `pan_clamped != pan` comparison at line 52; `tilt_clamped != tilt` at line 54; both trigger `logger.warning` before the servo assignment and before the mock-mode guard. |
| `Picamera2Stream.start()` | `self._picam2.set_controls` | `capture_metadata()` after `time.sleep(2.0)` | WIRED | Sequence confirmed: `self._picam2.start()` (line 71) → `self._thread.start()` (line 76) → `time.sleep(2.0)` (line 79) → `capture_metadata()` (line 80) → `set_controls({"ColourGains": gains})` (line 85). Pattern `set_controls.*ColourGains` present. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DIAG-01 | 06-01-PLAN.md | `set_angles()` logs WARNING when value is clamped to soft-limit (pan ±60°, tilt ±30°) | SATISFIED | `src/hardware.py` lines 52-55: per-axis independent WARNING logs. Automated test passed. Commit `ea5e41d`. |
| CAM-01 | 06-01-PLAN.md | Picamera2 executes 2s warm-up after start() and locks ColourGains — image without blue cast | SATISFIED (code) / NEEDS HUMAN (visual) | `src/modes/test_tracker.py` lines 78-87: full warm-up + lock sequence implemented. Visual result requires hardware run. Commit `fc9fd55`. |
| CAM-02 | 06-01-PLAN.md | If ColourGains lock does not eliminate blue tint, YUV conversion format verified (NV12 vs planar) | SATISFIED | Format locked as `cv2.COLOR_YUV420p2BGR` (line 100) — planar YUV420, not NV12. Locked decision documented in SUMMARY decisions. `AwbEnable` correctly absent to avoid ISP conflict. |

**Orphaned requirements check:** REQUIREMENTS.md Traceability table maps DIAG-01, CAM-01, CAM-02 to Phase 6. No additional Phase 6 requirements found. Zero orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | No anti-patterns detected |

Checks performed on both modified files:
- No `TODO`/`FIXME`/`PLACEHOLDER` comments in the new code blocks
- No `return null` / empty stub implementations
- No `console.log`-only handlers
- `AwbEnable` correctly absent (locked anti-pattern from CONTEXT.md)
- No rate-limiting state added to clamp logging (as required)

### Human Verification Required

#### 1. AWB warm-up log output and color rendering

**Test:** On RPi4 with camera attached, run `python3 run_test_tracker.py`. Watch terminal for the first 5 seconds.

**Expected:**
- `INFO ... Czekam na stabilizację AWB (2s)...` appears immediately after camera start
- `INFO ... ColourGains zablokowane: (R=X.XX, B=X.XX)` appears ~2 seconds later with real numeric gain values
- Live cv2.imshow window (or headless log) shows normal skin tones within 3 seconds — no persistent blue cast

**Why human:** `capture_metadata()` requires a live Picamera2/libcamera pipeline. The sensor's actual ColourGains values depend on lighting conditions and cannot be simulated. Visual color rendering cannot be assessed programmatically.

#### 2. Clamp WARNING visibility during live run

**Test:** While `run_test_tracker.py` is running, temporarily change `SCAN_AMPLITUDE = 65.0` in `src/modes/test_tracker.py` (sinusoidal scan will exceed ±60° pan limit), restart, and observe terminal.

**Expected:** `WARNING ... Clamp pan: 65.0 -> 60.0 (limit)` appears at each scan peak. No corresponding `Clamp tilt` warning during pure sinusoidal scan (tilt=0.0 throughout). Restore `SCAN_AMPLITUDE = 45.0` after test.

**Why human:** Clamp logic verified programmatically in mock mode, but log level configuration and actual output visibility during a live `run_test_tracker.py` session depends on the logging handler setup in that entry point.

### Gaps Summary

No gaps found. All code-verifiable must-haves pass. Two items require hardware execution on RPi4 to confirm the live experience:

1. The visual color rendering after AWB lock (inherently a human/visual check)
2. The clamp WARNING appearing during actual live operation at the configured log level

Both items have correct implementation in the codebase. The human verification is a confirmation of correct behavior on hardware, not a fix for missing code.

---

_Verified: 2026-03-27T16:00:00Z_
_Verifier: Claude (gsd-verifier)_
