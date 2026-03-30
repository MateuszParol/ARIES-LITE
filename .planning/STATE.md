---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Architektura Rozproszona
status: ready_to_plan
stopped_at: Roadmap v2.0 created — 6 phases (18-23), 31 requirements mapped
last_updated: "2026-03-30"
last_activity: 2026-03-30 -- Roadmap v2.0 written, ready to plan Phase 18
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Rozproszona architektura — RPi4 (wizja) + Arduino Leonardo (PID + HMI) polaczone USB Serial
**Current focus:** Phase 18 — Srodowisko + Protokol + Migracja

## Current Position

Phase: 18 of 23 (Srodowisko + Protokol + Migracja)
Plan: — (nie zaplanowane)
Status: Ready to plan
Last activity: 2026-03-30 — Roadmap v2.0 utworzony, 31 wymagan zmapowanych do 6 faz

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

### Blockers/Concerns

- MediaPipe aarch64 wheel: weryfikacja pip install na konkretnej wersji RPi OS wymagana w Fazie 18 (fail fast)
- Orientacja serw: PAN_DIR / TILT_DIR wymaga empirycznej kalibracji na nowym montazu Arduino w Fazie 20
- setserial low_latency nie persystuje przez USB reconnect — zdecydowac gdzie ustawiac (udev / startup script)

### Pending Todos

None.

## Session Continuity

Last session: 2026-03-30
Stopped at: Roadmap v2.0 written — 6 phases (18-23), 31/31 requirements mapped
Resume file: None
