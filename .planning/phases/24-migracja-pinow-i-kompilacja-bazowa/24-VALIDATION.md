---
phase: 24
slug: migracja-pinow-i-kompilacja-bazowa
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | arduino-cli compile (weryfikacja kompilacji) + empiryczne testy hardware |
| **Config file** | none — arduino-cli juz zainstalowane |
| **Quick run command** | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/` |
| **Full suite command** | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/ && echo "PASS"` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/`
- **After every plan wave:** Full compile + grep for deprecated patterns
- **Before `/gsd:verify-work`:** Full compile + manual hardware verification
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 1 | MIG-04 | compile | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi` | TBD | ⬜ pending |
| 24-01-02 | 01 | 1 | MIG-06 | grep | `grep -c "dtostrf" src/arduino/aries_controller/aries_controller.ino` = 0 | TBD | ⬜ pending |
| 24-01-03 | 01 | 1 | MIG-07 | grep | `grep -c "while.*!Serial" src/arduino/aries_controller/aries_controller.ino` = 0 | TBD | ⬜ pending |
| 24-01-04 | 01 | 1 | MIG-08 | grep | `grep "delay(500)" src/arduino/aries_controller/aries_controller.ino` | TBD | ⬜ pending |
| 24-01-05 | 01 | 1 | MIG-03,05,09 | compile | zero errors + zero warnings na target renesas_uno | TBD | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — arduino-cli juz zainstalowane z Phase 18.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LCD bootscreen widoczny | MIG-04 | Wymaga fizycznego LCD 1602 | Flash firmware, sprawdz LCD wiersz 0: "ARIES-LITE v2.1" |
| Soft Start serw bez brownout | MIG-08 | Wymaga fizycznych serw + zasilacz 6V | 5 cykli zasilania, brak restartow Arduino |
| Servo Sweep plynny (brak jittera) | MIG-05 | Wymaga fizycznych serw na D6/D9 | Reczny Sweep test, obserwacja plynnosci |
| pi_brain.py serial connection | MIG-07 | Wymaga RPi4 + USB cable | Uruchom pi_brain.py, sprawdz polaczenie bez DTR workaround |
| QuickPID PID loop 100Hz | MIG-09 | Wymaga Serial Monitor + oscyloskop/millis debug | Sprawdz czy PID loop co 10ms na R4 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
