---
phase: 8
slug: scanning-logic
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — empirical hardware verification only |
| **Config file** | none |
| **Quick run command** | `python3 run_test_tracker.py` |
| **Full suite command** | `python3 run_test_tracker.py` (on RPi4, visual observation) |
| **Estimated runtime** | ~30 seconds (startup + visual check) |

---

## Sampling Rate

- **After every task commit:** Run `python3 run_test_tracker.py` (smoke — does it start without AttributeError or ValueError)
- **After every plan wave:** Full visual verification on RPi4
- **Before `/gsd:verify-work`:** Both SCAN-01 and SCAN-02 confirmed visually
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 1 | SCAN-01 | manual visual | `python3 run_test_tracker.py` | N/A | ⬜ pending |
| 8-01-02 | 01 | 1 | SCAN-02 | manual visual | `python3 run_test_tracker.py` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

*No test files needed — verification is empirical by project convention (CLAUDE.md: "There are no unit tests or linting tools configured. Verification is empirical").*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| No visible servo snap on TRACKING→SCANNING transition | SCAN-01 | Hardware servo motion requires physical observation on RPi4 | Cover face to trigger TARGET_LOST → SCANNING; observe pan servo sweeps smoothly without snap/step change on first scan frame |
| Face shown during TARGET_LOST window requires 3 consecutive frames before TRACKING | SCAN-02 | Streak counter state not exposed via CLI; requires visual HUD observation | Rapidly show face during TARGET_LOST window; verify HUD shows state transitions only after 3 consecutive detections |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
