---
phase: 13
slug: dnn-detector
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (not installed — manual verification primary) |
| **Config file** | none |
| **Quick run command** | `python3 -c "from src.modes.test_tracker import DetekcjaTwarzy; d=DetekcjaTwarzy(); print('DNN load OK')"` |
| **Full suite command** | `python3 run_test_tracker.py --debug` (empirical on RPi4) |
| **Estimated runtime** | ~5 seconds (import test), manual for full |

---

## Sampling Rate

- **After every task commit:** Run quick import/load command
- **After every plan wave:** Full empirical test on RPi4
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | DET-03 | integration | `python3 -c "from src.modes.test_tracker import DetekcjaTwarzy; d=DetekcjaTwarzy(); print('OK')"` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | DET-03 | manual | RPi4 empirical: --debug + face tracking | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `models/deploy.prototxt` — DNN model definition file
- [ ] `models/res10_300x300_ssd_iter_140000.caffemodel` — DNN model weights

*Existing infrastructure covers test framework requirements — empirical verification per CLAUDE.md.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DNN detects angled face | DET-03 | Requires physical face + camera | Stand at 30-45° angle before RPi4 camera, verify green bbox |
| FPS >= 10 with DNN | DET-03 | Requires RPi4 hardware timing | Run --debug, observe HUD FPS counter |
| PID tracking with DNN | DET-03 | Requires servos + camera | Verify smooth tracking after DNN switch |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
