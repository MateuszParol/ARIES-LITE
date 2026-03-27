---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: Debugging & Optimization
status: planning
stopped_at: Defining requirements
last_updated: "2026-03-27"
last_activity: 2026-03-27 — Milestone v1.7 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-27)

**Core value:** Naprawić krytyczne bugi w test_tracker.py — tilt, runaway camera, AWB, logika stanów
**Current focus:** Defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-27 — Milestone v1.7 started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (v1.7)
- Average duration: —
- Total execution time: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

- v1.7 scope: debugging & optimization test_tracker.py (nie nowe funkcje)
- Montaż standardowy potwierdzony: pan+ = prawo, tilt+ = dół
- TRACKING stan stabilny — tilt po prostu się nie rusza (nie flickeruje)
- Podejrzenie: brak negacji znaku tilt w _sledz() powoduje ruch w złym kierunku (snap do limitu)
- [z v1.6] Picamera2 over OpenCV VideoCapture — Bookworm native libcamera
- [z v1.6] Face detection only — no identity recognition, HAAR any-face
- [z v1.6] HAAR_MIN_SIZE=(80,80), sample_time=0.033 na PID
- [z v1.6] TARGET_LOST two-tick pattern: widoczny w HUD na jedną klatkę

### Blockers/Concerns

- Analiza znaku PID wymaga weryfikacji z biblioteką simple_pid (setpoint=0, error = setpoint - input)
- AWB fix wymaga testów na żywym hardware z sensorem IMX219

### Pending Todos

None yet.

## Session Continuity

Last session: 2026-03-27
Stopped at: Defining requirements for v1.7
Resume file: None
