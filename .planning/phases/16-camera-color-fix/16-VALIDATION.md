---
phase: 16
slug: camera-color-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Empiryczna weryfikacja (logi CSV z DataLogger + obserwacja wizualna) |
| **Config file** | none — firmware Arduino, brak test framework |
| **Quick run command** | `Kompilacja: arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/` |
| **Full suite command** | `Upload + run + analiza logow SD CSV` |
| **Estimated runtime** | ~60 seconds (kompilacja) + ~120 seconds (test empiryczny) |

---

## Sampling Rate

- **After every task commit:** Kompilacja firmware (`arduino-cli compile`)
- **After every plan wave:** Upload na sprzet + weryfikacja empiryczna z logami CSV
- **Before `/gsd:verify-work`:** Pelna weryfikacja SC #1, SC #2, SC #3 na sprzecie
- **Max feedback latency:** 60 seconds (kompilacja)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | SCN-01 | empirical | `arduino-cli compile` + logi CSV tilt | ✅ | ⬜ pending |
| 16-01-02 | 01 | 1 | SCN-02 | empirical | `arduino-cli compile` + logi CSV pan≠tilt freq | ✅ | ⬜ pending |
| 16-01-03 | 01 | 1 | SCN-03 | empirical | `arduino-cli compile` + logi CSV skok ≤5° | ✅ | ⬜ pending |
| 16-02-01 | 02 | 2 | SCN-01,SCN-02 | empirical | logi CSV + wizualne | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — DataLogger juz loguje CSV co 10 klatek na SD card.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tilt oscyluje w SKANOWANIE | SCN-01 | Wymaga fizycznego sprzetu + serw | Upload firmware → stan SKANOWANIE → obserwacja tilt + logi CSV |
| Wzorzec Lissajous 2D | SCN-02 | Wymaga analizy logow CSV na sprzecie | Logi CSV: pan i tilt zmieniaja sie z roznymi czestotliwosciami |
| Brak skoku ≤5° przy przejsciu | SCN-03 | Wymaga przejscia SLEDZENIE→SKANOWANIE na zywo | Logi CSV: roznica ostatni kat SLEDZENIE vs pierwszy kat SKANOWANIE ≤5° na obu osiach |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
