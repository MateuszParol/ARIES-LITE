---
phase: 14
slug: pid-sign-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Brak — `test_framework: "none"` w config.json |
| **Config file** | Brak |
| **Quick run command** | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/` |
| **Full suite command** | `python3 scripts/kalibracja_serw.py` (empiryczna weryfikacja na RPi z R4 WiFi) |
| **Estimated runtime** | ~30 seconds (kompilacja) / ~60 seconds (kalibracja) |

---

## Sampling Rate

- **After every task commit:** Run `arduino-cli compile` — brak bledow kompilacji
- **After every plan wave:** Run `python3 scripts/kalibracja_serw.py` na RPi z podlaczonym R4 WiFi
- **Before `/gsd:verify-work`:** SC-1 i SC-2 PASS w skrypcie kalibracyjnym; SC-3 i SC-4 przez obserwacje pelnego systemu
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Kryterium | Zachowanie | Typ testu | Komenda | Status |
|-----------|-----------|-----------|---------|--------|
| SC-1 | Twarz po prawej → pan obraca w prawo | manual obserwacja | `python3 scripts/kalibracja_serw.py` krok 1 | ⬜ pending |
| SC-2 | Twarz ponizej → tilt w dol | manual obserwacja | Krok 3 skryptu | ⬜ pending |
| SC-3 | Serwa nie docieraja do limitow w 2s | manual obserwacja | Uruchom pelny system + kamera | ⬜ pending |
| SC-4 | Twarz wycentrowana w 1-3s | manual obserwacja | Pelny system na RPi | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Brak — nie ma infrastruktury testow do tworzenia. Weryfikacja empiryczna.
