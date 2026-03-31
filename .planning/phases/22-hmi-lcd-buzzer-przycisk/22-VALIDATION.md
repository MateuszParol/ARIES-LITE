---
phase: 22
slug: hmi-lcd-buzzer-przycisk
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | arduino-cli compile (weryfikacja kompilacji) + empiryczna weryfikacja na hardware |
| **Config file** | none — firmware Arduino, brak unit test framework |
| **Quick run command** | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/` |
| **Full suite command** | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/ && arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:leonardo src/arduino/aries_controller/` |
| **Estimated runtime** | ~15 seconds (compile) / ~30 seconds (compile+upload) |

---

## Sampling Rate

- **After every task commit:** Run `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/`
- **After every plan wave:** Compile + upload + empiryczna weryfikacja
- **Before `/gsd:verify-work`:** Kompilacja czysta (0 warnings) + hardware test
- **Max feedback latency:** 15 seconds (compile)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | HMI-01 | compile+grep | `arduino-cli compile ... && grep -q 'LiquidCrystal lcd' src/arduino/aries_controller/aries_controller.ino` | ✅ | ⬜ pending |
| 22-01-02 | 01 | 1 | HMI-04 | compile+grep | `grep -q 'ARIES-LITE' src/arduino/aries_controller/aries_controller.ino` | ✅ | ⬜ pending |
| 22-01-03 | 01 | 1 | HMI-01 | compile+grep | `grep -q 'lcd_tick' src/arduino/aries_controller/aries_controller.ino` | ✅ | ⬜ pending |
| 22-02-01 | 02 | 1 | HMI-02 | compile+grep | `grep -q 'tone(BUZZER_PIN' src/arduino/aries_controller/aries_controller.ino` | ✅ | ⬜ pending |
| 22-02-02 | 02 | 1 | HMI-03 | compile+grep | `grep -q 'przycisk_tick' src/arduino/aries_controller/aries_controller.ino` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — arduino-cli already installed, LiquidCrystal.h already #included in firmware.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LCD wyswietla tryb i katy serw | HMI-01 | Wymaga fizycznego LCD podlaczonego do Leonardo | 1. Upload firmware 2. Obserwuj LCD Row 0: tryb, Row 1: katy 3. Zmien stan — LCD aktualizuje w <200ms |
| Buzzer emituje ton przy TRACK | HMI-02 | Wymaga fizycznego buzzera na D8 | 1. Upload firmware 2. Wyslij ramke TRACK z RPi 3. Buzzer slyszalny z 1m |
| Przycisk abort TRACK→SCAN | HMI-03 | Wymaga fizycznego przycisku na D7 | 1. Wejdz w TRACK 2. Wcisnij przycisk 3. Stan zmienia sie na SCAN w <50ms |
| LCD bootscreen 2s | HMI-04 | Wymaga fizycznego LCD | 1. Reset Arduino 2. "ARIES-LITE v2.0" widoczne na LCD 3. Znika po 2s |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
