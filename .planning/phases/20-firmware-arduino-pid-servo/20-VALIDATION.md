---
phase: 20
slug: firmware-arduino-pid-servo
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — empirical verification per CLAUDE.md |
| **Config file** | none |
| **Quick run command** | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller` |
| **Full suite command** | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller && arduino-cli upload --fqbn arduino:avr:leonardo --port /dev/ttyACM0 src/arduino/aries_controller` |
| **Estimated runtime** | ~15 seconds (compile) |

---

## Sampling Rate

- **After every task commit:** Run `arduino-cli compile` (weryfikacja kompilacji bez hardware)
- **After every plan wave:** Upload + Serial Monitor observation (wymaga Arduino)
- **Before `/gsd:verify-work`:** Kompilacja OK + empiryczna weryfikacja na hardware
- **Max feedback latency:** 15 seconds (compile)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | ARD-02 | compile | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller` | ✅ | ⬜ pending |
| 20-01-02 | 01 | 1 | ARD-01 | compile | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller` | ✅ | ⬜ pending |
| 20-01-03 | 01 | 1 | ARD-03,ARD-05 | compile | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller` | ✅ | ⬜ pending |
| 20-01-04 | 01 | 1 | ARD-04 | compile | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller` | ✅ | ⬜ pending |
| 20-01-05 | 01 | 1 | ARD-06 | compile | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — compilation is the primary automated check.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Safe startup smooth ramp | ARD-02 | Physical servo observation | Upload, power on with 6V supply, observe servo ramp to 90/90 — no sudden jump |
| PID convergence | ARD-01 | Servo movement observation | Send TRACK frames with error, observe servo correction speed and stability |
| Watchdog timeout → SCAN | ARD-03 | Timing observation | Send TRACK frames, stop sending, wait 500ms+ — observe SCAN start in Serial Monitor |
| PAN/TILT_INVERT | ARD-04 | Direction verification | Send positive error_x, observe pan direction; flip #define, recompile, compare |
| State machine transitions | ARD-05 | Serial Monitor + servo observation | Send mode=0/1/2 frames, observe state changes in Serial Monitor |
| Lissajous scan pattern | ARD-06 | Visual servo movement | Set SCAN mode, observe both axes moving simultaneously with different frequencies |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
