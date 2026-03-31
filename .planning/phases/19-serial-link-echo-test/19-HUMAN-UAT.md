---
status: partial
phase: 19-serial-link-echo-test
source: [19-VERIFICATION.md]
started: 2026-03-31
updated: 2026-03-31
---

## Current Test

[awaiting human testing — user working remotely]

## Tests

### 1. Echo test na fizycznym hardware
expected: `python3 scripts/echo_test.py` zwraca PASS (exit 0) z output `sent=[AA 02 2D 00 F4 FF 80 A4] / recv=[AA 02 2D 00 F4 FF 80 A4] / PASS`
result: [pending]

### 2. Firmware upload na Arduino Leonardo
expected: `arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:leonardo src/arduino/aries_controller` — upload OK, brak bledow
result: [pending]

### 3. (Opcjonalnie) USB disconnect/reconnect resync
expected: Po odlaczeniu i ponownym podlaczeniu USB, echo_test.py nadal zwraca PASS — parser resyncuje na 0xAA
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
