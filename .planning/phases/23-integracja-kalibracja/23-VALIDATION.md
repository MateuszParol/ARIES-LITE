---
phase: 23
slug: integracja-kalibracja
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual verification (hardware-dependent) + arduino-cli compile |
| **Config file** | none |
| **Quick run command** | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/` |
| **Full suite command** | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/ && python3 -c "from src.vision.brain import MozgRPi; print('import OK')"` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | INT-01 | manual+script | `python3 scripts/kalibracja_serw.py` | ❌ W0 | ⬜ pending |
| 23-01-02 | 01 | 1 | INT-02 | manual | visual observation of servo direction | N/A | ⬜ pending |
| 23-01-03 | 01 | 1 | INT-03 | manual | tilt observation in SCAN and TRACK | N/A | ⬜ pending |
| 23-02-01 | 02 | 2 | INT-04 | compile | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/` | ✅ | ⬜ pending |
| 23-02-02 | 02 | 2 | INT-05 | grep | `grep -c "//.*[a-z]" src/arduino/aries_controller/aries_controller.ino` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/kalibracja_serw.py` — calibration script for servo direction verification
- [ ] Existing infrastructure covers compilation and import checks

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E2E tracking latency <100ms | INT-01 | Requires live camera + Arduino hardware | Run pi_brain.py, observe servo response to face movement, check log timestamps |
| Negative feedback direction | INT-02 | Requires physical servo observation | Run kalibracja_serw.py, send error_x=+50, verify pan moves right |
| Tilt in SCAN and TRACK | INT-03 | Requires physical observation | Observe tilt oscillation in SCAN, tilt tracking in TRACK mode |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
