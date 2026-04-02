---
phase: 26
slug: sd-card-datalogger-csv
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none (Arduino — no unit test framework configured) |
| **Config file** | none |
| **Quick run command** | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/aries_controller.ino` |
| **Full suite command** | Kompilacja + upload + reczna weryfikacja Serial Monitor i karta SD |
| **Estimated runtime** | ~15 seconds (kompilacja), ~60 seconds (upload + weryfikacja manualna) |

---

## Sampling Rate

- **After every task commit:** Run `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/aries_controller.ino`
- **After every plan wave:** Kompilacja + upload na Uno R4 WiFi + reczna weryfikacja kryteriow sukcesu
- **Before `/gsd:verify-work`:** Wszystkie 4 SC musza byc potwierdzone
- **Max feedback latency:** 15 seconds (kompilacja)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | LOG-01 | compile | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/aries_controller.ino` | N/A | ⬜ pending |
| 26-01-02 | 01 | 1 | LOG-03 | compile | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/aries_controller.ino` | N/A | ⬜ pending |
| 26-01-03 | 01 | 1 | LOG-04 | compile | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/aries_controller.ino` | N/A | ⬜ pending |
| 26-01-04 | 01 | 1 | LOG-02 | compile | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/aries_controller.ino` | N/A | ⬜ pending |
| 26-01-05 | 01 | 1 | LOG-05 | compile | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/aries_controller.ino` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Brak automatycznych testow — projekt nie ma frameworka testowego
- Kompilacja pod R4 WiFi jest jedynym automatyzowalnym sprawdzeniem
- Weryfikacja empiryczna: Serial Monitor + odczyt karty SD na komputerze

*Existing infrastructure (arduino-cli compile) covers compilation verification only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Plik LYYMMDD.CSV z naglowkiem i wierszami po 60s SLEDZENIE | LOG-01 | Wymaga fizycznej karty SD + kamery + twarzy | Upload firmware, uruchom tracking 60s, wyjmij SD, sprawdz CSV |
| Nowy plik po zmianie dnia RTC | LOG-02 | Wymaga recznej zmiany daty RTC lub czekania do polnocy | Zmien date RTC, restart, sprawdz nowy plik LYYMMDD.CSV |
| Start bez karty SD — brak zawieszenia | LOG-04 | Wymaga fizycznego wyjecia karty SD | Wyjmij karte, uruchom, sprawdz Serial "SD fail", PID dziala |
| Benchmark micros() < 1000us | LOG-05 | Wymaga fizycznego zapisu na karte SD | Odczytaj Serial Monitor — szukaj linii z wynikiem micros() |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
