---
phase: 4
slug: hardware-foundation-camera-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None configured — empirical verification only |
| **Config file** | None |
| **Quick run command** | `python3 run_test_tracker.py` (on RPi4 with camera) |
| **Full suite command** | `scripts/validate-all.sh` |
| **Estimated runtime** | ~10 seconds (manual observation) |

---

## Sampling Rate

- **After every task commit:** Run `python3 run_test_tracker.py` on RPi4 — observe 10 seconds
- **After every plan wave:** Verify all HW-0X success criteria
- **Before `/gsd:verify-work`:** All four criteria must be TRUE
- **Max feedback latency:** Manual — requires RPi4 with camera connected

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | HW-01 | smoke | `python3 run_test_tracker.py` + observe no reboot | N/A (manual) | ⬜ pending |
| 04-01-02 | 01 | 1 | HW-02 | smoke | `python3 run_test_tracker.py` + observe frames/FPS | N/A (manual) | ⬜ pending |
| 04-01-03 | 01 | 1 | HW-03 | smoke | Ctrl+C + `fuser /dev/video0` empty | N/A (manual) | ⬜ pending |
| 04-01-04 | 01 | 1 | HW-04 | static | `git diff src/` shows no changes | N/A (static) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No test files needed — all validation is empirical on RPi4.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Servos move incrementally to (0,0) without brownout | HW-01 | Physical hardware observation | Run `python3 run_test_tracker.py`; observe smooth servo movement to neutral; check `dmesg` for no under-voltage |
| Picamera2 captures BGR 320x240 frames | HW-02 | Requires physical camera | Run tracker; observe cv2.imshow window or log output shows frames with FPS |
| Clean shutdown on Ctrl+C | HW-03 | Requires physical hardware | Press Ctrl+C; verify `fuser /dev/video0` returns empty, `ps aux \| grep libcamera` shows nothing |
| No Flask dependency or src/ modification | HW-04 | Static verification | `python3 -c "import ast; tree=ast.parse(open('run_test_tracker.py').read()); print('OK')"` — no flask imports; `git diff src/` empty |

---

## Validation Sign-Off

- [x] All tasks have verification (manual smoke tests)
- [x] Sampling continuity: every task verified per run
- [x] Wave 0 covers all MISSING references (none needed)
- [x] No watch-mode flags
- [ ] Feedback latency — manual, requires RPi4
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
