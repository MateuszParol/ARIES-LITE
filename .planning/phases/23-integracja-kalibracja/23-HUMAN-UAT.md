---
status: partial
phase: 23-integracja-kalibracja
source: [23-VERIFICATION.md]
started: 2026-03-31T20:00:00Z
updated: 2026-03-31T20:00:00Z
---

## Current Test

[awaiting human testing — Arduino Leonardo unavailable]

## Tests

### 1. Kalibracja kierunkow serw (INT-02)
expected: python3 scripts/kalibracja_serw.py — 4 kroki PASS (PAN prawo/lewo, TILT dol/gora). Jesli FAIL, zmien PAN_INVERT/TILT_INVERT w firmware i rekompiluj.
result: [pending]

### 2. Latencja E2E <100ms (INT-01)
expected: python3 run_pi_brain.py — logi [LAT] TX SLEDZENIE pokazuja wartosc <100ms. Mierzone time.monotonic_ns() przed/po send_frame().
result: [pending]

### 3. E2E bez regresji po OOP refaktorze (INT-01, INT-02, INT-03)
expected: Pelny test z twarz przed kamera — kamera sledzi, LCD pokazuje SLEDZ/SKAN/BEZCZ, buzzer przy TRACK, przycisk abort dziala, tilt oscyluje w SCAN i sledzi w TRACK.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
