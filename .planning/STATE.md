---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: Debugging & Optimization
status: "Awaiting `/gsd:plan-phase 6`"
stopped_at: "Completed 06-01-PLAN.md (checkpoint: awaiting hardware verify)"
last_updated: "2026-03-27T15:18:41.149Z"
last_activity: 2026-03-27 — Roadmap v1.7 created (Phases 6-8)
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 5
  completed_plans: 3
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-27)

**Core value:** Naprawić krytyczne bugi w test_tracker.py — tilt, runaway camera, AWB, logika stanów
**Current focus:** Ready to plan Phase 6

## Current Position

Phase: Phase 6 (not started)
Plan: —
Status: Awaiting `/gsd:plan-phase 6`
Last activity: 2026-03-27 — Roadmap v1.7 created (Phases 6-8)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (v1.7)
- Average duration: —
- Total execution time: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

- v1.7 scope: surgical bug fixes in test_tracker.py only — no architectural changes
- Phase order: DIAG+AWB first (observability + visual baseline), PID sign second (highest impact), scan logic last (requires working tracking to verify)
- Montaż standardowy potwierdzony: pan+ = prawo, tilt+ = dół
- TRACKING stan stabilny — tilt nie rusza z powodu brakującej negacji (snap do soft-limitu w 2-3 klatkach)
- Tilt fix is 1 character: `korekta_tilt = -self.pid_tilt(blad_tilt)` in `MaszynaStanow._sledz()`
- AWB fix: `set_controls({"ColourGains": gains})` MUST follow `picam2.start()` + `time.sleep(2.0)` — controls before start() are silently ignored
- PID reset: `_przejdz_do()` already calls reset — no change needed, only verification
- Streak reset: move from SCANNING entry to TARGET_LOST entry in `TestTracker.uruchom()`
- Do NOT add `AwbEnable: False` alongside `ColourGains` — causes ISP sequencing conflict
- Do NOT change `cv2.COLOR_YUV420p2BGR` constant — correct for Picamera2 I420 output
- Do NOT change Kp/Ki/Kd values — sign bug mimics gain problem but is distinct
- [z v1.6] Picamera2 over OpenCV VideoCapture — Bookworm native libcamera
- [z v1.6] HAAR_MIN_SIZE=(80,80), sample_time=0.033 na PID
- [z v1.6] TARGET_LOST two-tick pattern: widoczny w HUD na jedną klatkę
- [Phase 06]: Clamp WARNING fires before mock_mode check — active in both modes
- [Phase 06]: AWB lock: set_controls ColourGains after start()+sleep(2.0); AwbEnable omitted (ISP conflict)

### Blockers/Concerns

- AWB fallback gains (2.5, 1.9) may need empirical adjustment for specific indoor lighting
- simple_pid version: verify `pip show simple-pid` on device — need >=2.0.0 for reliable anti-windup
- SCAN-01 (phase offset for scan continuity) deferred by research — implement only if servo jerk confirmed visible after Phase 7 fixes

### Pending Todos

- Verify `pip show simple-pid` version on RPi4 device before Phase 7
- Read back `capture_metadata()["ColourGains"]` after warm-up in Phase 6 to tune fallback if needed

## Session Continuity

Last session: 2026-03-27T14:52:15.078Z
Stopped at: Completed 06-01-PLAN.md (checkpoint: awaiting hardware verify)
Resume file: None
