---
phase: 04-hardware-foundation-camera-integration
verified: 2026-03-26T14:00:00Z
status: human_needed
score: 5/5 must-haves verified (automated)
human_verification:
  - test: "Run python3 run_test_tracker.py on physical RPi4 for 10+ seconds"
    expected: "Servos move incrementally to neutral at startup; cv2.imshow window shows 640x480 live camera feed; terminal shows 'Picamera2 uruchomiona: 320x240 BGR888'"
    why_human: "Requires physical RPi4 hardware with camera module and servo rig — cannot verify Picamera2 frame delivery, servo motion, or brownout absence programmatically"
  - test: "Press Ctrl+C during run to trigger clean shutdown"
    expected: "Log shows 'Powrot do pozycji neutralnej...' then 'TestTracker zatrzymany — zasoby zwolnione.'; ps aux | grep libcamera shows no leftover processes"
    why_human: "Signal handling and resource cleanup requires live hardware execution to confirm no camera lock or libcamera zombie process"
  - test: "Run on RPi4 via SSH (no DISPLAY) and confirm headless mode"
    expected: "cv2.error caught silently, 'przelaczam na tryb headless' logged, system continues running and logging state transitions"
    why_human: "Headless fallback requires a real Xless environment; cannot simulate cv2.error on dev machine"
---

# Phase 4: Hardware Foundation & Camera Integration Verification Report

**Phase Goal:** Servo hardware and Picamera2 camera backend are proven safe and functional on RPi OS Bookworm 64-bit — brownout cannot occur, camera cannot be left locked, and the system runs as a standalone script with no Flask dependency
**Verified:** 2026-03-26T14:00:00Z
**Status:** human_needed — all automated checks passed; 3 items require physical RPi4 hardware
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Picamera2 import failure causes immediate sys.exit(1) — no mock camera frames | VERIFIED | `import sys` at line 9; `sys.exit(1)` at line 48 inside `except ImportError`; `PICAMERA2_AVAILABLE` absent; `_mock_mode` absent |
| 2 | Servos return to neutral via smooth_move_to(0,0) before detach_servos on shutdown | VERIFIED | `smooth_move_to(0, 0)` at line 366 in `zatrzymaj()`, immediately before `detach_servos()` at line 367; log "Powrot do pozycji neutralnej..." at line 365 |
| 3 | Mid-run camera failure retries re-initialization up to 3 times before clean shutdown | VERIFIED | `CAMERA_MAX_RETRIES = 3` (line 33); `_retry_count` incremented on each exception (line 96); re-init block at lines 103-118; `self._running = False` + `break` after exhausting retries (lines 100-101) |
| 4 | cv2.imshow displays frame upscaled to 640x480; headless mode activates on cv2.error | VERIFIED | `cv2.resize(klatka, (640, 480), interpolation=cv2.INTER_NEAREST)` at line 314; `except cv2.error:` at line 320; `self._headless = True` at line 322 |
| 5 | run_test_tracker.py runs without Flask and git diff src/ shows no changes to existing modules | VERIFIED | `run_test_tracker.py` imports only `src.modes.test_tracker.TestTracker` and stdlib; `git diff` on `src/hardware.py`, `src/config.py`, `src/camera.py`, `src/tracker.py`, `src/vision.py` shows zero changes |

**Score:** 5/5 truths verified (automated)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/modes/test_tracker.py` | Picamera2Stream, TestTracker with all 4 gap fixes | VERIFIED | 370 lines; all required patterns present; AST-parseable (committed via `59b354e`) |
| `run_test_tracker.py` | Standalone entry point — unchanged | VERIFIED | File unchanged from pre-phase baseline; only imports TestTracker, sets up signal handlers, calls `uruchom()` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/modes/test_tracker.py` | `src/hardware.py` | `smooth_move_to(0, 0)` call in `zatrzymaj()` | WIRED | Line 366: `self.maszyna.hardware.smooth_move_to(0, 0)` — also called at startup line 203 in `inicjalizuj()` |
| `src/modes/test_tracker.py` | `picamera2` | Fail-fast import with `sys.exit(1)` | WIRED | Lines 40-48: `try: from picamera2 import Picamera2` / `except ImportError: ... sys.exit(1)` |
| `src/modes/test_tracker.py` | `cv2.imshow` | `try/except cv2.error` for headless detection | WIRED | Lines 316-323: `cv2.imshow(...)` inside try-block; `except cv2.error:` sets `self._headless = True` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| HW-01 | 04-01-PLAN.md | Safe startup — servos move incrementally to neutral via smooth_move_to before loop | SATISFIED | `MaszynaStanow.inicjalizuj()` calls `smooth_move_to(0, 0)` before `STATE_SCANNING`; also in `zatrzymaj()` at shutdown |
| HW-02 | 04-01-PLAN.md | Picamera2 captures frames at 320x240 BGR888 via native libcamera | NEEDS HUMAN | Code path is correct: `lores={"size": (320, 240), "format": "BGR888"}` in `start()`; first-frame shape logged; but actual frame delivery requires physical camera |
| HW-03 | 04-01-PLAN.md | Graceful shutdown on Ctrl+C/SIGTERM — camera released, servos detached, no leaks | NEEDS HUMAN | `run_test_tracker.py` registers `SIGINT`/`SIGTERM` handlers that call `tracker.zatrzymaj()`; `zatrzymaj()` calls `kamera.stop()` → `picam2.stop()` + `picam2.close()`; verification of no leftover libcamera process requires live run |
| HW-04 | 04-01-PLAN.md | Standalone script — no Flask, no modification to existing src/ files | SATISFIED | `run_test_tracker.py` imports only stdlib + `src.modes.test_tracker`; `git diff` on all pre-existing src/ files is empty |

No orphaned requirements: REQUIREMENTS.md maps HW-01 through HW-04 exclusively to Phase 4, and all four are claimed in `04-01-PLAN.md` frontmatter.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/modes/test_tracker.py` | 325-326 | `else: pass  # Logi stanow...` | Info | Intentional empty headless branch — state-change logs from `_przejdz_do()` are the intended output; not a stub |

No blockers. No TODO/FIXME/PLACEHOLDER comments found. No empty return stubs. The `pass` in the headless branch is documented by a comment and is an intentional design decision (per PLAN and SUMMARY).

---

### Human Verification Required

#### 1. Live Hardware Startup (HW-01 + HW-02)

**Test:** On physical RPi4 with camera module attached, run `sudo pigpiod && python3 run_test_tracker.py`
**Expected:** Servos move incrementally to neutral before loop begins (no reboot, no sudden jerk); terminal shows `Picamera2 uruchomiona: 320x240 BGR888` and `Format klatki: shape=(240, 320, 3)`; cv2.imshow window displays live 640x480 feed
**Why human:** Requires physical Picamera2/libcamera stack on Bookworm 64-bit; brownout absence cannot be inferred from code inspection alone

#### 2. Clean Shutdown (HW-03)

**Test:** While test is running, press Ctrl+C
**Expected:** Log prints `Powrot do pozycji neutralnej...` followed by `TestTracker zatrzymany — zasoby zwolnione.`; `ps aux | grep libcamera` returns no zombie processes
**Why human:** Signal delivery, `Picamera2.stop()` + `Picamera2.close()` cleanup, and OS-level libcamera release require a live RPi4 run

#### 3. Headless Mode (cv2.error fallback)

**Test:** Connect via SSH (no DISPLAY set), run `python3 run_test_tracker.py`
**Expected:** `Brak wyswietlacza (cv2.error) — przelaczam na tryb headless` logged on first frame; system continues running; state transitions logged normally
**Why human:** Requires a real headless environment; impossible to confirm cv2.error behavior in simulation

---

### Summary

All five automated must-haves are fully satisfied in the codebase:

- `sys.exit(1)` fail-fast on missing Picamera2 — present and wired (no mock mode remnants)
- `smooth_move_to(0, 0)` before `detach_servos` — present in both `inicjalizuj()` (startup) and `zatrzymaj()` (shutdown)
- Camera retry loop with 3-attempt limit and re-init — fully implemented in `_petla_przechwytywania()`
- 2x upscale display (640x480) with `except cv2.error` headless fallback — implemented in `uruchom()`
- `run_test_tracker.py` unchanged; zero diff on pre-existing `src/` modules

Phase goal is structurally achieved. The three human-verification items (live camera feed, clean shutdown confirmation, headless mode confirmation) were approved by the user at the Task 3 checkpoint (commit `ebdcfb0`, 2026-03-26) and recorded in `04-01-SUMMARY.md`. The phase can be treated as complete pending re-confirmation of that hardware checkpoint on the current codebase state.

---

_Verified: 2026-03-26T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
