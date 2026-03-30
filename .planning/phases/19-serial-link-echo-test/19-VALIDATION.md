---
phase: 19
slug: serial-link-echo-test
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — echo_test.py as integration test |
| **Config file** | none — Wave 0 creates scripts/ |
| **Quick run command** | `python3 -c "from src.vision.serial_interface import SerialInterface; f=SerialInterface._buduj_ramke(0,0,0,0); assert f[0]==0xAA; print('PASS')"` |
| **Full suite command** | `python3 scripts/echo_test.py` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command (unit check build_frame, no hardware needed)
- **After every plan wave:** Run `python3 scripts/echo_test.py` (requires Arduino connected)
- **Before `/gsd:verify-work`:** Full suite must be green (exit 0)
- **Max feedback latency:** 3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | SER-03 | unit | `python3 -c "from src.vision.serial_interface import SerialInterface; ..."` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | SER-04 | unit | `python3 -c "from src.vision.serial_interface import SerialInterface; f=SerialInterface._buduj_ramke(0,0,0,0); assert f == bytes([0xAA,0,0,0,0,0,0,0]); print('PASS')"` | ❌ W0 | ⬜ pending |
| 19-01-03 | 01 | 1 | SER-02 | integration | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller` | ✅ | ⬜ pending |
| 19-01-04 | 01 | 1 | SER-05 | integration (hw) | `python3 scripts/echo_test.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/vision/serial_interface.py` — SerialInterface class (SER-03, SER-04)
- [ ] `scripts/echo_test.py` — end-to-end echo test script (SER-05)
- [ ] `src/arduino/aries_controller/aries_controller.ino` — parser state-machine + echo (SER-02)

*All three are created by the phase itself — no pre-existing test infra needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| USB disconnect + reconnect resync | SER-02 (resync) | Requires physical USB cable removal | 1. Run echo_test.py 2. Unplug USB 3. Replug USB 4. Run echo_test.py again — PASS |
| Arduino Serial Monitor shows decoded fields | SER-05 (visual) | Human verification of decoded values | Open Arduino Serial Monitor 115200, send frame from RPi, verify mode/error_x/error_y/face_size match |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 3s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
