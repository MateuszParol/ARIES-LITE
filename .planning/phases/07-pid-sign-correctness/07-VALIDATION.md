---
phase: 7
slug: pid-sign-correctness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none (no test framework configured) |
| **Config file** | none |
| **Quick run command** | `python3 run_test_tracker.py` |
| **Full suite command** | `python3 run_test_tracker.py` |
| **Estimated runtime** | ~30 seconds (manual hardware observation session) |

---

## Sampling Rate

- **After every task commit:** Run `python3 run_test_tracker.py` (smoke check — imports OK, starts without crash)
- **After every plan wave:** Full manual hardware verification session (all three success criteria)
- **Before `/gsd:verify-work`:** Full hardware session must pass all three criteria
- **Max feedback latency:** One hardware session (~5 min) per wave

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 0 | PID-03 | manual | `pip show simple-pid` | ✅ | ⬜ pending |
| 7-01-02 | 01 | 1 | PID-01 | manual | n/a — hardware only | ✅ | ⬜ pending |
| 7-01-03 | 01 | 2 | PID-01, PID-02, PID-03 | manual | `python3 run_test_tracker.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files needed — validation is manual hardware observation only.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Face below center → `Tilt:` value increases → camera converges vertically, no snap to ±30° limit | PID-01 | Requires RPi4 hardware + live camera + physical face | `sudo pigpiod && python3 run_test_tracker.py` → Hold face below HUD crosshair → verify `Tilt:` value increases and camera tilts toward face, NOT toward soft limit |
| Face right of center → camera pans toward face → `Pan:` converges horizontally, no snap to ±60° limit | PID-02 | Requires RPi4 hardware + live camera + physical face | Same session → Hold face to right of crosshair → verify camera pans toward face and `Pan:` converges |
| TRACKING → TARGET_LOST → SCANNING → TRACKING cycle produces no servo jerk on re-entry | PID-03 | Requires RPi4 hardware + live state machine cycle | Same session → Allow face to disappear (→ SCANNING) then reappear (→ TRACKING) → verify first correction is smooth/proportional, no jerk |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
