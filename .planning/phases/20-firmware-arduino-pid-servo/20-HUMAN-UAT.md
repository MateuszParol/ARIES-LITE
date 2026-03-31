---
status: partial
phase: 20-firmware-arduino-pid-servo
source: [20-VERIFICATION.md]
started: 2026-03-31T12:00:00Z
updated: 2026-03-31T12:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Safe startup — brak skoku pradu
expected: Serwa plynnie dochodza do pozycji centralnej (90/90) w ciagu ok. 1 sekundy — bez skoku, bez uderzenia mechanicznego, bez brownoutu zasilacza.
result: [pending]

### 2. Watchdog 500ms i PID tracking
expected: Serwa reaguja na blad PID (ruch w kierunku korekcji). Po 500ms bez komunikacji serwa przechodza do autonomicznego skanu Lissajous.
result: [pending]

### 3. Konfigurowalny kierunek serw (PAN_INVERT / TILT_INVERT)
expected: Zmiana #define PAN_INVERT z (1) na (-1) odwraca kierunek ruchu serwa pan.
result: [pending]

### 4. Lissajous 2D — wizualna weryfikacja
expected: Pan i tilt poruszaja sie sinusoidalnie z rozna czestotliwoscia (0.05 Hz vs 0.073 Hz). Trajektoria Lissajous — nigdy nie powtarza sie identycznie. Zakresy: pan +-60 deg, tilt +-25 deg.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
