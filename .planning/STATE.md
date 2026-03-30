---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Architektura Rozproszona
status: defining_requirements
stopped_at: Milestone v2.0 started — defining requirements
last_updated: "2026-03-30"
last_activity: 2026-03-30 -- Milestone v2.0 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Rozproszona architektura — RPi4 (wizja) + Arduino Leonardo (PID + HMI) polaczone USB Serial
**Current focus:** Defining requirements for v2.0

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-30 — Milestone v2.0 started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 13 (v1.5-v1.8)
- Average duration: brak danych dla v2.0
- Total execution time: brak danych dla v2.0

## Accumulated Context

### Decisions

- [v1.7]: Montaz standardowy: pan+=prawo, tilt+=dol (wymaga re-weryfikacji na nowym montazu)
- [v1.7]: Tilt negation: korekta_tilt = -pid_tilt (PID przeniesiony na Arduino)
- [v1.8]: DNN res10_300x300 zastepuje HAAR (teraz MediaPipe zastepuje DNN)
- [v1.8]: PID gains (P=0.05, I=0.001, D=0.005) empirycznie zwalidowane (punkt startowy dla Arduino PID)
- [v2.0]: Architektura rozproszona — RPi4 + Arduino Leonardo via USB Serial 115200
- [v2.0]: MediaPipe Face Detection zamiast DNN — RPi odciazone przez Arduino
- [v2.0]: PID na Arduino (100+ Hz) zamiast Python (30 Hz)
- [v2.0]: Stary monolit zachowany w legacy/ jako referencja

### Blockers/Concerns

- Orientacja serw wymaga empirycznej kalibracji na nowym montazu Arduino
- MediaPipe moze wymagac dodatkowej instalacji na RPi4 (libcamera + mediapipe compatibility)

### Pending Todos

None.

## Session Continuity

Last session: 2026-03-30
Stopped at: Milestone v2.0 started — defining requirements
Resume file: None
