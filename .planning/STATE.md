---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Migracja na Uno R4 + DataLogger
status: defining_requirements
stopped_at: Milestone v2.1 started — defining requirements
last_updated: "2026-04-01"
last_activity: 2026-04-01
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-01)

**Core value:** Rozproszona architektura — RPi4 (wizja) + Arduino Uno R4 WiFi (PID + HMI + DataLogger) polaczone USB Serial
**Current focus:** Defining requirements for v2.1

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-01 — Milestone v2.1 started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 20 (v1.5-v2.0)
- Average duration: brak danych dla v2.1
- Total execution time: brak danych dla v2.1

## Accumulated Context

### Decisions

- [v1.7]: Montaz standardowy: pan+=prawo, tilt+=dol (wymaga re-weryfikacji na nowym montazu Uno R4)
- [v1.7]: Tilt negation: korekta_tilt = -pid_tilt (PID przeniesiony na Arduino)
- [v1.8]: PID gains (P=0.05, I=0.001, D=0.005) — punkt startowy dla Arduino, I redukowac 3x (Ki=0.0003) dla 100 Hz
- [v2.0]: Architektura rozproszona — RPi4 + Arduino via USB Serial 115200
- [v2.0]: QuickPID zamiast br3ttb PID — iAwCondition anti-windup, dOnMeas derivative mode
- [v2.0]: NIE uzywac AVR hardware WDT — millis() watchdog zamiast wdt_enable()
- [v2.0]: Protokol binarny 8B zamkniety: 0xAA + mode(uint8) + error_x/y(int16 LE) + face_size(uint8) + XOR checksum(1-6 bez start)
- [v2.1]: Migracja Leonardo -> Uno R4 WiFi (rozwiazuje USB blocker)
- [v2.1]: Nowa mapa pinow: LCD(A0,A1,D2-D5), Serwa(D6,D9), Buzzer(D8), Przycisk(D7), SD(D10-D13), I2C(A4,A5)
- [v2.1]: DataLogger Shield V1.0 — RTC DS1307 + SD card logging CSV

### Blockers/Concerns

- Orientacja serw: PAN_DIR / TILT_DIR wymaga empirycznej kalibracji na nowym montazu Uno R4
- QuickPID kompatybilnosc z Uno R4 (Renesas RA4M1) — zweryfikowac kompilacje
- SD.h + RTClib.h koegzystencja z QuickPID/Servo/LiquidCrystal — sprawdzic RAM/Flash na Uno R4

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-01
Stopped at: Milestone v2.1 started — defining requirements
Resume file: None
