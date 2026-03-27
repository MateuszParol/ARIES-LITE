---
phase: 07-pid-sign-correctness
verified: 2026-03-27T16:00:00Z
status: human_needed
score: 5/8 must-haves verified (3 require hardware)
human_verification:
  - test: "PID-01 tilt convergence — hold face below frame center"
    expected: "HUD Tilt: value changes, camera tilts toward face. No snap to ±30 soft limit in 2-3 frames."
    why_human: "Requires RPi4 hardware, physical face, live servo response. Cannot simulate in code."
  - test: "PID-02 pan no regression — hold face right of center"
    expected: "HUD Pan: value increases, camera pans right. Stabilizes when face reaches horizontal center."
    why_human: "Requires RPi4 hardware. Pan behavior only verifiable with physical servo feedback."
  - test: "PID-03 integrator clean re-entry — TRACKING → SCANNING → TRACKING cycle"
    expected: "First correction after re-entering TRACKING is proportional to error distance, no jerk."
    why_human: "Requires physical servo observation across state transitions. simple-pid reset() fix unverifiable without hardware."
---

# Phase 7: PID Sign Correctness Verification Report

**Phase Goal:** The tilt axis drives the camera toward the face and neither axis runs away — the control loop converges to a face-centered steady state in both pan and tilt
**Verified:** 2026-03-27
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `python3 run_test_tracker.py` parses without error — module syntax valid | VERIFIED | `ast.parse` passes on dev machine. `parse OK` confirmed. |
| 2 | Line 275 in `_sledz()` contains negation: `korekta_tilt = -self.pid_tilt(blad_tilt)` | VERIFIED | `grep` output: line 275 = `korekta_tilt = -self.pid_tilt(blad_tilt)  # negacja — oś tilt działa jak pan` |
| 3 | Line 274 in `_sledz()` preserves negation: `korekta_pan = -self.pid_pan(blad_pan)` — unchanged | VERIFIED | `grep` output: line 274 = `korekta_pan = -self.pid_pan(blad_pan)` |
| 4 | `requirements.txt` contains `simple-pid>=2.0.1` | VERIFIED | Line 10 of `requirements.txt`: `simple-pid>=2.0.1` |
| 5 | Both PIDs are reset on SCANNING entry — `pid_pan.reset()` and `pid_tilt.reset()` called in `_przejdz_do()` | VERIFIED | Lines 288-289 in `test_tracker.py`: both `reset()` calls present under `if nowy_stan == config.STATE_SCANNING` |
| 6 | Tilt convergence on hardware: face below center → camera moves toward face, no soft-limit snap (PID-01) | HUMAN NEEDED | Empirical RPi4 + physical face required. SUMMARY claims confirmed, code fix is present, but behavioral outcome needs hardware gate. |
| 7 | Pan unchanged from v1.6 behavior: face right → camera pans right (PID-02) | HUMAN NEEDED | Requires physical servo response on RPi4. |
| 8 | No integrator jump on TRACKING re-entry (PID-03) | HUMAN NEEDED | `simple-pid>=2.0.1` pinned (code side verified). Actual servo behavior requires hardware observation. |

**Score:** 5/8 truths verified by code inspection. 3 truths require hardware verification.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/modes/test_tracker.py` | `MaszynaStanow._sledz()` with correct tilt sign | VERIFIED | Line 275 confirmed negated. Line 274 pan negation preserved. Both reset() calls present. Syntax valid. |
| `requirements.txt` | `simple-pid>=2.0.1` pin | VERIFIED | Line 10: `simple-pid>=2.0.1`. Previous value was `==2.0.0` (per commit `a64542a`). |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `MaszynaStanow._sledz()` line 275 | `PanTiltSystem.set_angles()` | `nowy_tilt = self.hardware.tilt_angle + korekta_tilt` | WIRED | Line 278: `nowy_tilt = self.hardware.tilt_angle + korekta_tilt`. Line 280: `self.hardware.set_angles(nowy_pan, nowy_tilt)`. `set_angles()` confirmed defined in `src/hardware.py` line 41. |
| `_przejdz_do(STATE_SCANNING)` | `PID.reset()` | `self.pid_pan.reset(); self.pid_tilt.reset()` | WIRED | Lines 288-289 in `_przejdz_do()` under the `STATE_SCANNING` branch. Both PIDs reset. |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PID-01 | 07-01-PLAN.md, 07-02-PLAN.md | Korekta tilt jest negowana (-pid_tilt) — kamera podąża za twarzą w pionie w poprawnym kierunku | PARTIAL — code verified, hardware pending | Negation present at line 275. Behavioral confirmation from SUMMARY 07-02 claims hardware pass, but this is a human-gated checkpoint requiring empirical observation. |
| PID-02 | 07-01-PLAN.md, 07-02-PLAN.md | Korekta pan zachowuje istniejącą negację — weryfikacja że oś X nadal działa poprawnie | PARTIAL — code verified, hardware pending | Negation at line 274 unchanged. Pan direction behavioral test requires RPi4. |
| PID-03 | 07-01-PLAN.md, 07-02-PLAN.md | Oba PID resetowane (integral+derivative) przy wejściu w SCANNING — brak skoku po zmianie stanu | PARTIAL — code verified, hardware pending | `reset()` calls at lines 288-289. `simple-pid>=2.0.1` pinned. Servo jerk behavior requires hardware observation. |

**Orphaned requirements check:** REQUIREMENTS.md traceability table maps PID-01, PID-02, PID-03 exclusively to Phase 7. No orphaned requirements found.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No TODO/FIXME/placeholder/empty-return patterns found in phase-modified files. |

Anti-pattern scan performed on `src/modes/test_tracker.py` and `requirements.txt`. No stubs, placeholder returns, or empty handlers found. Both `korekta_pan` and `korekta_tilt` flow through to `set_angles()` with no dead ends.

---

### Human Verification Required

#### 1. PID-01: Tilt Convergence

**Test:** On RPi4 — `sudo pigpiod && source venv/bin/activate && python3 run_test_tracker.py`. Wait for SCANNING state. Hold face below the center crosshair in HUD.
**Expected:** HUD `Tilt:` value changes (decreases toward face), camera physically tilts upward toward face. Face reaches vertical center and `Tilt:` stabilizes. No snap to ±30° in 2-3 frames.
**Why human:** Servo convergence requires physical hardware feedback — code confirms sign is correct, but whether the gain produces visible convergence (vs. overdamping or oscillation) cannot be determined statically.

#### 2. PID-02: Pan No Regression

**Test:** Same session. Hold face to the right of center crosshair.
**Expected:** HUD `Pan:` value increases, camera pans right. Stabilizes when face is horizontally centered. Same behavior as v1.6.
**Why human:** Pan axis was not modified in this phase, but regression test requires physical observation to confirm nothing in the tilt fix changed pan behavior.

#### 3. PID-03: No Integrator Jump on Re-entry

**Test:** Same session. Allow TRACKING (hold face 3+ frames), hide face until TARGET_LOST then SCANNING, show face again.
**Expected:** First servo correction after re-entering TRACKING is proportional to face distance from center — no sudden jerk or servo jump on the first frame.
**Why human:** `simple-pid>=2.0.1` fixes the `_last_error` reset bug in code, but whether this eliminates the physical servo jerk requires observation across the state transition.

**Note:** SUMMARY 07-02 claims all three criteria were approved in a single hardware session on 2026-03-27. However, plan 07-02 is a `checkpoint:human-verify gate=blocking` task — it explicitly requires a human `"approved"` signal. The SUMMARY records the approval was given. Verification of that claim is not repeatable by static analysis. The hardware session result stands as reported by the operator.

---

### Gaps Summary

No gaps in code implementation. All programmatically verifiable must-haves pass. Three truths (PID-01, PID-02, PID-03 behavioral outcomes) require hardware verification and were gated as such in the plan design.

The SUMMARY for 07-02 records operator approval of all three hardware criteria. If the operator approval is accepted as evidence, phase goal is achieved. If independent re-verification on hardware is required, the three items above provide the exact test protocol.

---

### Commit Verification

| Commit | Hash | Description | Files |
|--------|------|-------------|-------|
| Task 1 (simple-pid pin) | `a64542a` | `chore(07-01): pin simple-pid>=2.0.1` | `requirements.txt` |
| Task 2 (tilt sign fix) | `cd6776e` | `fix(07-01): negate korekta_tilt in MaszynaStanow._sledz()` | `src/modes/test_tracker.py` |

Both commit hashes verified present in git history. Commit messages match plan intent.

---

_Verified: 2026-03-27_
_Verifier: Claude (gsd-verifier)_
