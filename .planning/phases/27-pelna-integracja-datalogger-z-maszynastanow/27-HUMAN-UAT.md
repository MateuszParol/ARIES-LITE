---
status: partial
phase: 27-pelna-integracja-datalogger-z-maszynastanow
source: [27-02-PLAN.md]
started: 2026-04-04T08:30:00Z
updated: 2026-04-04T08:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Komenda 'D' z karta SD wlozona
expected: `[DUMP] Ostatnie 10 wpisow DataLogger:` + wpisy CSV + `[DUMP] Koniec.`
result: [pending]

### 2. Sesja E2E z RPi — sledzenie twarzy
expected: Serwa sledzą twarz (SLEDZENIE), wracaja do skanu przy braku twarzy (SKANOWANIE), plynne przejscia
result: [pending]
note: Serwo tilt (Y) nie reagowalo przy pierwszej probie — wymaga diagnostyki

### 3. Analiza CSV z karty SD
expected: Plik LYYMMDD.CSV z wierszami: zmiany stanow (1->2, 2->1), face_size > 0 w SLEDZENIE, latency_ms ~30-50ms
result: [pending]

### 4. Plynnosc PID podczas logowania SD
expected: Brak widocznych szarpan/przerw serw przy zmianie stanu (flush SD nie blokuje PID)
result: [pending]

## Summary

total: 4
passed: 0
issues: 1
pending: 4
skipped: 0
blocked: 0

## Gaps

### 1. Serwo tilt (Y) nie reaguje podczas sledzenia
status: investigating
description: err_y stale ~-80 w logach pi_brain. Software wyglada poprawnie (parser ramki, PID, ustaw_serwa). Wymaga diagnostyki sprzetowej — pin D9, zasilanie, test skanowania Lissajous.
