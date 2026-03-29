---
phase: 10
slug: detection-fix
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-29
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual + Python inline verification |
| **Config file** | none — no test framework for test_tracker |
| **Quick run command** | `python3 -c "from src.modes.test_tracker import DetekcjaTwarzy; print('Import OK')"` |
| **Full suite command** | `python3 -c "from src.modes.test_tracker import HAAR_MIN_SIZE, HAAR_MIN_NEIGHBORS; assert HAAR_MIN_SIZE == (40, 40); assert HAAR_MIN_NEIGHBORS == 4; print('OK')"` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | DET-01, DET-02 | inline | `python3 -c "from src.modes.test_tracker import HAAR_MIN_SIZE, HAAR_MIN_NEIGHBORS; assert HAAR_MIN_SIZE == (40, 40); assert HAAR_MIN_NEIGHBORS == 4; print('OK')"` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Verification is via constant assertion and empirical hardware test.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Green rectangles at 40-100cm | DET-01 | Requires RPi4 + camera + real face | Run `python3 run_test_tracker.py`, stand 60cm from camera, check HUD for green bbox |
| Detection at ±30° angle | DET-02 | Requires physical head rotation | Same setup, tilt head ~30° left/right, verify green bbox persists |
| TRACKING sustained 3s | DET-01 | Requires real-time state observation | Watch HUD state label — should show TRACKING for 3+ seconds continuously |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-29
