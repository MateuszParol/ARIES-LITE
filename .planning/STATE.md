---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Migracja na Uno R4 + DataLogger
status: roadmap_ready
stopped_at: Roadmap v2.1 created — 4 phases (24-27), ready for plan-phase
last_updated: "2026-04-01"
last_activity: 2026-04-01
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-01)

**Core value:** Rozproszona architektura — RPi4 (wizja) + Arduino Uno R4 WiFi (PID + HMI + DataLogger) polaczone USB Serial
**Current focus:** v2.1 Phase 24 — Migracja Pinow i Kompilacja Bazowa

## Current Position

Phase: 24 (Not started)
Plan: —
Status: Roadmap ready — awaiting plan-phase 24
Last activity: 2026-04-01 — Roadmap v2.1 created (4 phases, 18 requirements mapped)

Progress: [░░░░░░░░░░] 0%

## Phase Map (v2.1)

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 24 | Migracja Pinow i Kompilacja Bazowa | MIG-03,04,05,06,07,08,09 | Not started |
| 25 | RTC DS1307 Izolowana Integracja | RTC-01,02,03 + INT-07 | Not started |
| 26 | SD Card + DataLogger CSV | LOG-01,02,03,04,05 | Not started |
| 27 | Pelna Integracja DataLogger z MaszynaStanow | INT-06, INT-08 | Not started |

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
- [v2.1]: dtostrf() zastapione snprintf() — ARM Renesas RA4M1 nie ma dtostrf
- [v2.1]: Keep-file-open + flush-every-50-rows — nie close() w petli PID
- [v2.1]: Fuzja Soft Start (MIG-08) z Faza 24 — jeden krok kompilacji + hardware verify bez nowych peryferiow

### Blockers/Concerns

- Orientacja serw: PAN_DIR / TILT_DIR wymaga empirycznej kalibracji na nowym montazu Uno R4
- SD write latency: typowe < 1ms, worst-case 200-300ms na FAT32 sector boundary — wymaga empirycznego benchmarku w Fazie 26
- Shield header contact: A4/A5 moga tracic kontakt I2C — potrebne cynowanie przed Faza 25
- Active buzzer na D8: jesli aktywny (nie pasywny) moze przekroczyc 8mA limit Uno R4 — sprawdzic typ przed Faza 24

### Pending Todos

- Zweryfikowac typ buzzera (aktywny vs pasywny) przed uruchomieniem Fazy 24

## Session Continuity

Last session: 2026-04-01
Stopped at: Roadmap v2.1 created — ready for /gsd:plan-phase 24
Resume file: None
