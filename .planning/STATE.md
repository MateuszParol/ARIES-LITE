---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Critical Hardware Fix
status: verifying
stopped_at: Completed 11-awb-fix 11-01-PLAN.md
last_updated: "2026-03-29T10:46:11.960Z"
last_activity: 2026-03-29
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 3
  completed_plans: 3
  percent: 62
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-29)

**Core value:** System dziala poprawnie na RPi4 — detekcja, PID, AWB, diagnostyka
**Current focus:** Phase 11 — awb-fix

## Current Position

Phase: 11 (awb-fix) — EXECUTING
Plan: 1 of 1
Status: Phase complete — ready for verification
Last activity: 2026-03-29

Progress: [████████░░░░░] 62% (8/13 phases complete across all milestones)

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v1.8)
- Previous milestone (v1.7): 4 plans

## Accumulated Context

### Decisions

- [v1.7]: Tilt negation (korekta_tilt = -pid_tilt) — empirycznie potwierdzone na RPi4
- [v1.7]: AWB lock via set_controls after start()+2s — dziala ale configure-time jest pewniejszy
- [v1.8 research]: ROOT CAUSE = HAAR minNeighbors=8 + minSize=(80,80) — prawie zero detekcji w praktyce
- [v1.8 research]: Mock mode niewidoczny w HUD — set_angles() aktualizuje software state zawsze
- [Phase 09-diagnostics]: logger.debug dla PID per-tick — nie zasmiecanie INFO streamu, DEBUG wymaga jawnego ustawienia
- [Phase 09-diagnostics]: Tolerancja 0.1 dla roznic AWB gains — ponizej to szum pomiaru, powyzej sugeruje silent failure
- [Phase 10-detection-fix]: HAAR_MIN_NEIGHBORS=4 i HAAR_MIN_SIZE=(40,40) — streak filter=3 filtruje false positives, zakres detekcji 40-100cm
- [Phase 11-awb-fix]: Configure-time ColourGains=(1.0,1.0) w create_video_configuration() — neutralne kolory od frame 0, zanim ISP zdazy narzucic AWB
- [Phase 11-awb-fix]: Fallback guard rozszerzony o (0.0, 0.0) check — Picamera2 zwraca (0.0,0.0) gdy AWB nadal liczy, nie tylko None

### Blockers/Concerns

- [Phase 12]: PID validation zalezy od stabilnej detekcji z Phase 10 — nie walidowac PID bez 10+ klatek TRACKING
- [Phase 13]: DNN warunkowe — HAAR wystarczajacy (DET-01, DET-02 spelnione), Phase 13 prawdopodobnie zbedna
- [AWB]: Fallback gains (2.5, 1.9) wymagaja kalibracji dla konkretnego srodowiska — odczytac z capture_metadata()

### Pending Todos

None.

## Session Continuity

Last session: 2026-03-29T10:46:11.867Z
Stopped at: Completed 11-awb-fix 11-01-PLAN.md
Resume file: None
