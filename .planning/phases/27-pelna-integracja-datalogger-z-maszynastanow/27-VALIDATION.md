---
phase: 27
slug: pelna-integracja-datalogger-z-maszynastanow
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — no test framework configured (CLAUDE.md: "Verification is empirical") |
| **Config file** | none |
| **Quick run command** | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/` |
| **Full suite command** | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/ && arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/` |
| **Estimated runtime** | ~15 seconds (compile) / ~30 seconds (compile + upload) |

---

## Sampling Rate

- **After every task commit:** Run `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/`
- **After every plan wave:** Run full compile + upload
- **Before `/gsd:verify-work`:** Full compile + upload + E2E serial verification
- **Max feedback latency:** 15 seconds (compile)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 1 | INT-06 | compile | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/` | ✅ | ⬜ pending |
| 27-01-02 | 01 | 1 | INT-06 | compile | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/` | ✅ | ⬜ pending |
| 27-01-03 | 01 | 1 | INT-06 | compile | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/` | ✅ | ⬜ pending |
| 27-01-04 | 01 | 1 | INT-08 | compile | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/` | ✅ | ⬜ pending |
| 27-02-01 | 02 | 2 | INT-08 | empirical | Serial `'D'` command + pyserial read | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* Arduino CLI already configured from Phase 24-28. No new frameworks or test stubs needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Zmiana stanu SCAN→TRACK logowana w CSV | INT-06 | Wymaga fizycznej kamery + twarzy + karty SD | Staw twarz przed kamera, zakryj, odkryj. Wyjmij SD, sprawdz CSV w pandas |
| Ciagla telemetria co ~10 klatek w SLEDZENIE | INT-06 | Wymaga dzialajacego RPi + Arduino + kamery | Sledz twarz 30s, sprawdz regularne wpisy w CSV |
| Brak zawieszenia serw przy zmianie stanu | INT-08 | Wymaga obserwacji fizycznych serw | Obserwuj serwa podczas zakrywania/odkrywania twarzy — brak zatrzymania |
| face_size > 0 w wierszach SLEDZENIE | INT-08 | Wymaga danych z RPi | Sprawdz kolumne face_size w CSV po sesji sledzenia |
| latency_ms ~33ms przy normalnym sledzeniu | INT-08 | Wymaga stabilnego polaczenia serial | Sprawdz kolumne latency_ms — mediana ~33ms |
| Komenda 'D' zrzuca 10 wpisow na Serial | INT-08 | Wymaga pyserial + dzialajacego systemu | `ser.write(b'D')` + odczyt odpowiedzi |
| Pelna sesja E2E exportowalna na PC | INT-08 | Wymaga pelnego hardware setup | Uruchom sesje, zatrzymaj, przeczytaj CSV na PC |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
