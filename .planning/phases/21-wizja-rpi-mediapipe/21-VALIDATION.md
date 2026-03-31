---
phase: 21
slug: wizja-rpi-mediapipe
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | arduino-cli compile (firmware) + python -c import checks + grep verification |
| **Config file** | none — no pytest, empirical verification on RPi hardware |
| **Quick run command** | `python3 -c "from src.vision.detector import DetekcjaTwarzyMP; print('OK')"` |
| **Full suite command** | `python3 -c "from src.vision.camera import Picamera2Stream; from src.vision.detector import DetekcjaTwarzyMP; from src.vision.brain import PiBrain; print('All imports OK')"` |
| **Estimated runtime** | ~5 seconds (import checks only, no hardware) |

---

## Sampling Rate

- **After every task commit:** Run quick import check
- **After every plan wave:** Run full import suite + grep acceptance criteria
- **Before `/gsd:verify-work`:** Full suite on RPi hardware
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | VIS-01,VIS-04 | import+grep | `grep -c "FaceDetector" src/vision/detector.py` | ❌ W0 | ⬜ pending |
| 21-01-02 | 01 | 1 | VIS-02 | grep | `grep -c "sticky\|histereza\|area" src/vision/detector.py` | ❌ W0 | ⬜ pending |
| 21-02-01 | 02 | 2 | VIS-05,VIS-06,VIS-07 | import+grep | `grep -c "send_frame\|send_heartbeat" src/vision/brain.py` | ❌ W0 | ⬜ pending |
| 21-02-02 | 02 | 2 | VIS-03 | grep | `grep -c "imshow\|HUD\|hud" src/vision/brain.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Download `blaze_face_short_range.tflite` model to `models/` directory
- [ ] Verify `pip install mediapipe` works in RPi venv (Python 3.11/3.12)
- [ ] Verify `numpy<2.0` pin in requirements

*Note: Wave 0 is hardware-dependent (RPi4 only). On dev machine only grep/import checks possible.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Face detection at >= 10 FPS | VIS-01 | Requires RPi4 + camera | Run pi_brain.py, check HUD FPS counter |
| Sticky tracking bez migotania | VIS-02 | Requires 2+ faces in frame | Show 2 faces, observe HUD — no bbox jumping |
| AWB bez poswiaty | VIS-04 | Visual inspection required | Check HUD image — neutral colors, no blue/green tint |
| Graceful shutdown | VIS-07 | Requires hardware | Ctrl+C during tracking — verify no exceptions in log |
| Heartbeat keeps watchdog alive | VIS-06 | Requires Arduino connected | Remove face from frame, verify Arduino stays in SCAN (not watchdog-triggered SCAN) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
