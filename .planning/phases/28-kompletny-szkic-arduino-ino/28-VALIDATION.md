---
phase: 28
slug: kompletny-szkic-arduino-ino
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — manual hardware verification (checkpoints) |
| **Config file** | none |
| **Quick run command** | `arduino-cli monitor --port /dev/ttyACM0 --config baudrate=115200` |
| **Full suite command** | Manual 6-test checkpoint sequence (T1-T6) |
| **Estimated runtime** | ~15-20 minutes (manual observation per test) |

---

## Sampling Rate

- **After every task commit:** Visual/serial verification per checkpoint
- **After every plan wave:** All prior checkpoints re-confirmed
- **Before `/gsd:verify-work`:** All 6 tests PASS
- **Max feedback latency:** Real-time (manual observation)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 28-01-01 | 01 | 1 | MIG-10 | manual | `arduino-cli upload ...` + visual | N/A | pending |
| 28-01-02 | 01 | 1 | MIG-10 | manual | LCD visual check | N/A | pending |
| 28-01-03 | 01 | 1 | MIG-10 | manual | Servo visual check | N/A | pending |
| 28-01-04 | 01 | 1 | MIG-10 | manual | Buzzer audio check | N/A | pending |
| 28-01-05 | 01 | 1 | MIG-10 | manual | Button press check | N/A | pending |
| 28-01-06 | 01 | 1 | MIG-10 | manual | `python3 run_pi_brain.py` + visual | N/A | pending |
| 28-01-07 | 01 | 1 | MIG-10 | manual | 5x power cycle visual | N/A | pending |

*Status: pending*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — arduino-cli and libraries already installed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LCD bootscreen display | MIG-10 | Physical LCD observation | Power on, read "ARIES-LITE v2.1" on LCD |
| Servo Soft Start + scan | MIG-10 | Physical servo movement | Watch ramp to center, Lissajous scan pattern |
| Buzzer tone on state change | MIG-10 | Audio perception | Trigger SLEDZENIE, listen for 1kHz tone |
| Button D7 abort | MIG-10 | Physical button press | In SLEDZENIE, press D7, confirm SKANOWANIE on LCD |
| Serial E2E tracking | MIG-10 | Full hardware loop | Run pi_brain.py, show face, confirm servo tracks |
| Power cycle stability | MIG-10 | Physical power cycling | 5x on/off, no Arduino restart during servo scan |

*All phase behaviors require manual verification — embedded hardware testing.*

---

## Validation Sign-Off

- [x] All tasks have manual verify checkpoints
- [x] Sampling continuity: every task has a checkpoint
- [x] Wave 0 covers all MISSING references (N/A — no automated tests)
- [x] No watch-mode flags
- [x] Feedback latency: real-time manual
- [ ] `nyquist_compliant: true` set in frontmatter (N/A — manual-only phase)

**Approval:** pending
