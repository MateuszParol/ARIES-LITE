---
phase: 05-state-machine-vision-pid-integration
verified: 2026-03-26T15:30:00Z
status: human_needed
score: 9/9 must-haves verified
human_verification:
  - test: "Run python3 run_test_tracker.py on RPi4 — confirm SCANNING sinusoidal sweep is visible, state label appears in orange"
    expected: "Pan servo sweeps ±45° smoothly, HUD shows STAN: SCANNING in orange"
    why_human: "Servo movement and real camera display cannot be verified from source code alone"
  - test: "Hold face in front of camera for 3+ consecutive frames — confirm state changes to TRACKING"
    expected: "HUD changes from SCANNING to TRACKING (green) after 3 frames; single-frame appearances do not trigger TRACKING"
    why_human: "Streak filter behavior requires live camera input; confirmed by user on 2026-03-26 per SUMMARY"
  - test: "Remove face while in TRACKING — confirm TARGET_LOST appears briefly then SCANNING resumes"
    expected: "After ~2 seconds: HUD briefly shows STAN: TARGET_LOST in red (one frame), then returns to SCANNING with sinusoidal pan"
    why_human: "Two-tick transient state timing and HUD visibility require live observation"
  - test: "Confirm FPS counter reads approximately 25-33 in bottom-right corner (gray text)"
    expected: "FPS:XX.X text appears right-aligned in gray at bottom-right; confirmed by user on 2026-03-26 per SUMMARY"
    why_human: "Real-time FPS value depends on RPi4 camera throughput"
  - test: "Move face left/right and up/down — confirm pan and tilt servos track in correct direction"
    expected: "No sign inversion on either axis; user confirmed tilt direction correct on hardware"
    why_human: "PID sign convention correctness requires physical servo observation"
---

# Phase 5: State Machine, Vision & PID Integration — Verification Report

**Phase Goal:** The complete isolated test tracker is running — HAAR detects any face, PID drives servos to center it, sinusoidal scan resumes when face is lost, and the HUD makes every state transition empirically observable
**Verified:** 2026-03-26T15:30:00Z
**Status:** human_needed (all automated checks pass; hardware behavior confirmed by user in SUMMARY)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | HAAR detects faces at minSize=(80,80) on 320x240 frames | VERIFIED | Line 28: `HAAR_MIN_SIZE = (80, 80)`; passed to `detectMultiScale` at line 163 |
| 2 | Detection requires 3 consecutive frames (streak filter) before TRACKING transition | VERIFIED | `STREAK_REQUIRED = 3` at line 29; `if self._streak >= STREAK_REQUIRED` at line 175; only returns bbox when streak met |
| 3 | Streak counter resets to 0 when returning to SCANNING | VERIFIED | Lines 320-321: `if stan == config.STATE_SCANNING and poprzedni_stan != config.STATE_SCANNING: self.detekcja.resetuj_streak()` |
| 4 | PID controllers have sample_time=0.033 stabilizing derivative term | VERIFIED | Lines 192-197: both `pid_pan` and `pid_tilt` constructed with `sample_time=0.033` (count=2) |
| 5 | TARGET_LOST state is visible in HUD for at least one frame before transitioning to SCANNING | VERIFIED | Line 231: TRACKING branch calls `_przejdz_do(STATE_TARGET_LOST)` only; line 234-236: `elif self.stan == STATE_TARGET_LOST: self._przejdz_do(config.STATE_SCANNING)` runs on the *next* tick |
| 6 | State machine cycles SCANNING -> TRACKING -> TARGET_LOST -> SCANNING | VERIFIED | Full cycle implemented in `tick()` lines 217-237; each branch exclusive, no chaining within tick |
| 7 | Sinusoidal scan sweeps pan +/-45 degrees at 0.1 Hz during SCANNING | VERIFIED | `_skanuj()` lines 241-244: `SCAN_AMPLITUDE=45.0`, `SCAN_FREQUENCY=0.1`, `pan = 45.0 * math.sin(2π * 0.1 * t)` |
| 8 | HUD shows FPS counter in bottom-right corner in gray text | VERIFIED | Lines 377-380: `fps_tekst`, `cv2.getTextSize` for right-alignment, color `(150, 150, 150)` at `(w - tw - 5, h - 10)` |
| 9 | HUD shows green bounding box, state label, crosshair, and servo angles | VERIFIED | `_rysuj_hud()` lines 349-374: crosshair (cyan lines), green rectangle on bbox, colored state label, servo angle text |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/modes/test_tracker.py` | Complete test tracker with all 5 gaps patched | VERIFIED | 391 lines, parses cleanly, all 5 patches present and functional |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `TestTracker.uruchom()` | `DetekcjaTwarzy.resetuj_streak()` | state change detection `(poprzedni_stan != SCANNING)` | WIRED | Line 320-321: condition check correct, `self.detekcja.resetuj_streak()` called; `resetuj_streak()` defined at line 179 resets `self._streak = 0` |
| `MaszynaStanow.__init__()` | `simple_pid.PID` | `sample_time=0.033` constructor arg | WIRED | Lines 192-197: both PID instances constructed with `sample_time=0.033`; count=2 matches requirement |
| `MaszynaStanow.tick()` TRACKING branch | `MaszynaStanow.tick()` TARGET_LOST branch | two-tick transition (TARGET_LOST visible one frame) | WIRED | Line 231: `self._przejdz_do(STATE_TARGET_LOST)` appears exactly once in TRACKING branch; line 236: `self._przejdz_do(config.STATE_SCANNING)` appears exactly once in TARGET_LOST branch — no chaining |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| VIS-01 | 05-01-PLAN.md | HAAR cascade detects any face in grayscale frame | SATISFIED | `HAAR_MIN_SIZE=(80,80)` at line 28; `detectMultiScale` with `minSize=HAAR_MIN_SIZE` at line 163 |
| VIS-02 | 05-01-PLAN.md | Detection streak filter requires 3 consecutive frames before TRACKING | SATISFIED | `STREAK_REQUIRED=3` at line 29; streak logic lines 167-177; reset wired lines 320-321 |
| VIS-03 | 05-01-PLAN.md | HUD overlay shows bbox, state label, center crosshair, servo angles | SATISFIED | `_rysuj_hud()` lines 345-380: all 5 elements present (bbox, state, crosshair, servo angles, FPS counter) |
| CTL-01 | 05-01-PLAN.md | State machine cycles SCANNING → TRACKING → TARGET_LOST → SCANNING | SATISFIED | `tick()` lines 217-237: all four state branches implemented; complete cycle verified structurally |
| CTL-02 | 05-01-PLAN.md | Dual-axis PID with reset on SCANNING entry | SATISFIED | `pid_pan` and `pid_tilt` with `sample_time=0.033`; `_przejdz_do()` lines 272-274: PID reset on SCANNING entry |
| CTL-03 | 05-01-PLAN.md | SCANNING state sweeps sinusoidally (±45° pan, 0.1 Hz) | SATISFIED | `_skanuj()` lines 241-244: `SCAN_AMPLITUDE=45.0`, `SCAN_FREQUENCY=0.1`, correct sinusoidal formula |
| CTL-04 | 05-01-PLAN.md | TARGET_LOST triggers after 2 seconds, returns to SCANNING | SATISFIED | Line 230: `config.TIME_TO_LOST_SEC` timeout check; two-tick transient pattern ensures visibility; line 236 returns to SCANNING |

All 7 requirements are satisfied. No orphaned requirements — REQUIREMENTS.md traceability table maps VIS-01..CTL-04 exclusively to Phase 5; all are marked complete.

---

### Anti-Patterns Found

No anti-patterns detected.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TODO/FIXME/PLACEHOLDER found | — | — |
| — | — | No empty return stubs found | — | — |
| — | — | No disconnected handlers found | — | — |

---

### Human Verification Required

The phase was verified on RPi4 hardware by the user on 2026-03-26 (recorded in 05-01-SUMMARY.md). The following tests are documented as approved but cannot be independently confirmed from source code:

#### 1. SCANNING sinusoidal sweep

**Test:** Run `python3 run_test_tracker.py` on RPi4 with camera and servos connected; observe HUD.
**Expected:** HUD shows `STAN: SCANNING` in orange; pan servo sweeps smoothly between ±45°.
**Why human:** Servo movement and live display output cannot be verified statically.
**Status:** Approved by user per SUMMARY.md (2026-03-26).

#### 2. Streak filter behavior

**Test:** Hold a face in front of camera; count frames before TRACKING transition; briefly flash face for 1 frame and confirm no premature TRACKING.
**Expected:** TRACKING triggered after 3+ consecutive frames only; single-frame appearances do not trigger state change.
**Why human:** Live camera input and frame timing required.
**Status:** Approved by user per SUMMARY.md (2026-03-26).

#### 3. TARGET_LOST transient and SCANNING resume

**Test:** While in TRACKING, cover camera; wait ~2 seconds; observe HUD transitions.
**Expected:** `STAN: TARGET_LOST` briefly visible in red (one frame), then `STAN: SCANNING` with sinusoidal pan resuming.
**Why human:** Real-time HUD frame visibility requires live observation.
**Status:** Approved by user per SUMMARY.md (2026-03-26).

#### 4. PID tracking direction (no sign inversion)

**Test:** Move face left/right and up/down while in TRACKING; observe servo response direction.
**Expected:** Pan tracks horizontally correct; tilt tracks vertically correct — no axis inversion.
**Why human:** PID sign correctness requires physical servo observation.
**Status:** Tilt sign confirmed correct on hardware per SUMMARY.md; no inversion needed.

#### 5. FPS counter readout

**Test:** Observe bottom-right corner of HUD display during operation.
**Expected:** `FPS:XX.X` in gray text, reading approximately 25-33 on RPi4.
**Why human:** Real-time frame rate depends on RPi4 camera throughput.
**Status:** Confirmed present and readable per SUMMARY.md (2026-03-26).

---

### Commit Verification

| Commit | Description | Files Changed |
|--------|-------------|---------------|
| `28ae2cf` | feat(05-01): patch all 5 gaps in test_tracker.py | `src/modes/test_tracker.py` only |
| `2c7a1e1` | docs(05-01): complete plan — hardware verified | `.planning/` docs only |

No changes to `src/config.py`, `src/hardware.py`, or `run_test_tracker.py` — confirmed by `git diff --name-only 28ae2cf^ 28ae2cf` returning only `src/modes/test_tracker.py`.

---

### Summary

Phase 5 goal is **achieved**. All 9 observable truths are verified in the codebase, all 7 requirement IDs (VIS-01, VIS-02, VIS-03, CTL-01, CTL-02, CTL-03, CTL-04) are satisfied with direct evidence, all three key links are wired correctly, and no anti-patterns were found.

The complete autonomous control loop is implemented in `src/modes/test_tracker.py`:
- HAAR detection at minSize=(80,80) with 3-frame streak filter prevents false transitions
- Dual-axis PID with `sample_time=0.033` stabilizes the D-term against variable RPi4 frame timing
- TARGET_LOST is a real two-tick transient state (visible in HUD for one frame, not dead code)
- Streak reset is wired at the `TestTracker` orchestrator level on every SCANNING re-entry
- FPS counter renders right-aligned in gray using `cv2.getTextSize` for correct alignment

Hardware behavior (servo movement, live HUD display, real-time state transitions) was confirmed by the user on RPi4 on 2026-03-26 and recorded in 05-01-SUMMARY.md. The human_needed status reflects that those confirmations are empirical observations that cannot be re-derived from source inspection alone.

---

_Verified: 2026-03-26T15:30:00Z_
_Verifier: Claude (gsd-verifier)_
