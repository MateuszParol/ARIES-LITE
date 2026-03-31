---
status: partial
phase: 22-hmi-lcd-buzzer-przycisk
source: [22-VERIFICATION.md]
started: 2026-03-31T12:00:00Z
updated: 2026-03-31T12:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. LCD bootscreen widoczny przez 2s
expected: Po resecie Arduino LCD wyswietla "ARIES-LITE v2.0" i "Inicjalizacja..." przez 2 sekundy, potem przechodzi do normalnego wyswietlania
result: [pending]

### 2. Buzzer "Target Lock" slyszalny z 1m
expected: Przy przejsciu do trybu TRACK buzzer emituje krotki ton ~1kHz przez ~100ms, slyszalny z odleglosci 1m. Ton nie blokuje PID ani LCD.
result: [pending]

### 3. Przycisk abort TRACK→SCAN w ciagu 50ms
expected: Wcisniecie przycisku D7 w trybie TRACK przywraca tryb SCAN. Reakcja w ciagu 50ms. Debounce 20ms eliminuje false triggers. Przycisk ignorowany w SCAN i IDLE.
result: [pending]

### 4. LCD odswiezanie bez migotania
expected: LCD Row 0 (tryb + katy serw) i Row 1 (bledy X/Y) odswiezaja sie co 200ms bez widocznego migotania. Zmiana stanu widoczna natychmiast.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
