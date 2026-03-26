# Roadmap: ARIES-LITE

## Milestones

- ✅ **v1.5.0 Stabilization & Hardening** — Phases 1-3 (shipped 2026-03-18)
- 🚧 **v1.6 Test Tracker** — Phases 4-5 (in progress)

## Phases

<details>
<summary>✅ v1.5.0 Stabilization & Hardening (Phases 1-3) — SHIPPED 2026-03-18</summary>

- [x] Phase 1: Critical Bug Fixes & Code Correctness (1/1 plans) — completed 2026-03-18
- [x] Phase 2: Robustness & Reliability (1/1 plans) — completed 2026-03-18
- [x] Phase 3: Cleanup & Quality (1/1 plans) — completed 2026-03-18

</details>

### 🚧 v1.6 Test Tracker (In Progress)

**Milestone Goal:** Izolowany moduł testowy z czystą pętlą sterowania (Scan → Detect → PID Track → Target Lost), udowadniający płynne działanie hardware (pigpio + PID) z Picamera2 na RPi OS Bookworm.

- [x] **Phase 4: Hardware Foundation & Camera Integration** - Servo safe startup, Picamera2 frame capture, and graceful shutdown proven on real hardware (completed 2026-03-26)
- [x] **Phase 5: State Machine, Vision & PID Integration** - Complete SCANNING → TRACKING → TARGET_LOST control loop with face detection and HUD (completed 2026-03-26)

## Phase Details

### Phase 4: Hardware Foundation & Camera Integration
**Goal**: Servo hardware and Picamera2 camera backend are proven safe and functional on RPi OS Bookworm 64-bit — brownout cannot occur, camera cannot be left locked, and the system runs as a standalone script with no Flask dependency
**Depends on**: Nothing (first phase of v1.6)
**Requirements**: HW-01, HW-02, HW-03, HW-04
**Success Criteria** (what must be TRUE):
  1. Running `python3 run_test_tracker.py` moves servos incrementally to (0,0) before any loop starts — no brownout or under-voltage reboot occurs
  2. Picamera2 captures BGR frames at 320x240 and the terminal prints FPS without errors — no "Camera already in use" error on launch
  3. Pressing Ctrl+C exits cleanly: servos return to neutral, camera releases, process terminates — no leftover libcamera process requiring `sudo killall`
  4. The entry point `run_test_tracker.py` runs without importing Flask or modifying any file in `src/` (except reading `src/hardware.py` and `src/config.py`) — `git diff src/` shows no changes after execution
**Plans:** 1/1 plans complete
Plans:
- [x] 04-01-PLAN.md — Patch test_tracker.py skeleton: fail-fast Picamera2, 2x upscale + headless, camera retry, safe shutdown

### Phase 5: State Machine, Vision & PID Integration
**Goal**: The complete isolated test tracker is running — HAAR detects any face, PID drives servos to center it, sinusoidal scan resumes when face is lost, and the HUD makes every state transition empirically observable
**Depends on**: Phase 4
**Requirements**: VIS-01, VIS-02, VIS-03, CTL-01, CTL-02, CTL-03, CTL-04
**Success Criteria** (what must be TRUE):
  1. When a face is held in front of the camera for 3 consecutive frames, the state label on the HUD changes from SCANNING to TRACKING and servos begin following the face centroid
  2. When the face is removed, the HUD shows TARGET_LOST for approximately 2 seconds, then returns to SCANNING with the pan servo resuming sinusoidal sweep
  3. Moving a face left/right causes the pan servo to track in the correct direction; moving it up/down causes the tilt servo to track correctly — no sign inversion errors
  4. During SCANNING, the pan servo sweeps sinusoidally between ±45° without accumulating error on repeated TRACKING → SCANNING transitions — servo does not snap or overshoot on the first frame after a transition
  5. The HUD shows a green bounding box around the detected face, a state label, a center crosshair, and current servo angles — all update correctly at each state transition
**Plans:** 1/1 plans complete
Plans:
- [x] 05-01-PLAN.md — Patch 5 gaps in test_tracker.py (HAAR minSize, PID sample_time, streak reset, TARGET_LOST logic, FPS counter) + RPi4 hardware verification

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Bug Fixes | v1.5 | 1/1 | Complete | 2026-03-18 |
| 2. Robustness | v1.5 | 1/1 | Complete | 2026-03-18 |
| 3. Cleanup | v1.5 | 1/1 | Complete | 2026-03-18 |
| 4. Hardware Foundation & Camera Integration | v1.6 | 1/1 | Complete | 2026-03-26 |
| 5. State Machine, Vision & PID Integration | 1/1 | Complete   | 2026-03-26 | 2026-03-26 |
