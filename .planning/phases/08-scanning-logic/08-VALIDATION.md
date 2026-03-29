---
phase: 8
slug: scanning-logic
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-27
validated: 2026-03-29
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | standalone Python scripts (no pytest dependency) |
| **Config file** | none |
| **Quick run command** | `python3 tests/test_scan01_phase_offset.py && python3 tests/test_scan02_streak_reset.py` |
| **Full suite command** | same — both complete in < 2 seconds |
| **Hardware smoke command** | `python3 run_test_tracker.py` (on RPi4, visual observation) |
| **Estimated runtime** | < 2 seconds (automated); ~30 seconds (hardware smoke) |

---

## Sampling Rate

- **After every task commit:** `python3 tests/test_scan01_phase_offset.py && python3 tests/test_scan02_streak_reset.py`
- **After every plan wave:** Full visual verification on RPi4
- **Before `/gsd:verify-work`:** Both automated suites green + hardware checkpoint approved
- **Max feedback latency:** < 2 seconds (automated)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 1 | SCAN-01 | unit | `python3 tests/test_scan01_phase_offset.py` | tests/test_scan01_phase_offset.py | green |
| 8-01-02 | 01 | 1 | SCAN-02 | unit | `python3 tests/test_scan02_streak_reset.py` | tests/test_scan02_streak_reset.py | green |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

All phase requirements now have automated test coverage.

- `tests/test_scan01_phase_offset.py` — 6 tests covering SCAN-01: field init, math.asin computation at various pan positions, clamp guard against ValueError, offset application in _skanuj()
- `tests/test_scan02_streak_reset.py` — 6 tests covering SCAN-02: resetuj_streak() resets counter, STREAK_REQUIRED constant, reset triggers at TARGET_LOST entry (not SCANNING), state sequence TRACKING→TARGET_LOST→SCANNING, 3-frame accumulation requirement, streak drops on miss

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| No visible servo snap on TRACKING→SCANNING transition | SCAN-01 (hardware feel) | Physical servo motion requires RPi4 observation | Cover face to trigger TARGET_LOST → SCANNING; observe pan servo sweeps smoothly without snap/step change on first scan frame |
| Face shown during TARGET_LOST window requires 3 consecutive frames before TRACKING | SCAN-02 (hardware feel) | Visual HUD confirmation of streak enforcement | Rapidly show face during TARGET_LOST window; verify HUD transitions to TRACKING only after 3 consecutive frames |

---

## Validation Sign-Off

- [x] All tasks have automated verify command
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 2s (automated)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** nyquist-auditor 2026-03-29 — automated gaps filled, 12/12 tests green
