---
gsd_state_version: 1.0
milestone: v1.9
milestone_name: Stabilizacja Ruchu i Obrazu
status: verifying
stopped_at: Checkpoint Task 3 — 18-02 awaiting user verification of mediapipe + arduino-cli
last_updated: "2026-03-30T19:00:34.084Z"
last_activity: 2026-03-30
progress:
  total_phases: 10
  completed_phases: 9
  total_plans: 11
  completed_plans: 10
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Rozproszona architektura — RPi4 (wizja) + Arduino Leonardo (PID + HMI) polaczone USB Serial
**Current focus:** Phase 18 — srodowisko-protokol-migracja

## Current Position

Phase: 18 (srodowisko-protokol-migracja) — EXECUTING
Plan: 2 of 2
Status: Phase complete — ready for verification
Last activity: 2026-03-30

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 13 (v1.5-v1.8)
- Average duration: brak danych dla v2.0
- Total execution time: brak danych dla v2.0

## Accumulated Context

### Decisions

- [v1.7]: Montaz standardowy: pan+=prawo, tilt+=dol (wymaga re-weryfikacji na nowym montazu Arduino)
- [v1.7]: Tilt negation: korekta_tilt = -pid_tilt (PID przeniesiony na Arduino)
- [v1.8]: PID gains (P=0.05, I=0.001, D=0.005) — punkt startowy dla Arduino, I redukowac 3x (Ki=0.0003) dla 100 Hz
- [v2.0]: Architektura rozproszona — RPi4 + Arduino Leonardo via USB Serial 115200
- [v2.0]: QuickPID zamiast br3ttb PID — iAwCondition anti-windup, dOnMeas derivative mode
- [v2.0]: NIE uzywac AVR hardware WDT — millis() watchdog zamiast wdt_enable() (Caterina bootloader bug)
- [Phase 18-srodowisko-protokol-migracja]: Protokol binarny 8B zamkniety: 0xAA + mode(uint8) + error_x/y(int16 LE) + face_size(uint8) + XOR checksum(1-6 bez start)
- [Phase 18-srodowisko-protokol-migracja]: Stary monolit w legacy/ via git mv — historia plikow zachowana przez git log --follow
- [Phase 18]: Servo i LiquidCrystal wymagaly osobnej instalacji przez arduino-cli lib install — nie sa builtin w arduino:avr 1.8.7
- [Phase 18]: picamera2 nie importuje sie w Python 3.12 venv — rozwiazanie odlozone do Phase 21

### Blockers/Concerns

- MediaPipe aarch64 wheel: weryfikacja pip install na konkretnej wersji RPi OS wymagana w Fazie 18 (fail fast)
- Orientacja serw: PAN_DIR / TILT_DIR wymaga empirycznej kalibracji na nowym montazu Arduino w Fazie 20
- setserial low_latency nie persystuje przez USB reconnect — zdecydowac gdzie ustawiac (udev / startup script)

### Pending Todos

None.

## Session Continuity

Last session: 2026-03-30T19:00:34.052Z
Stopped at: Checkpoint Task 3 — 18-02 awaiting user verification of mediapipe + arduino-cli
Resume file: None
