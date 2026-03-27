# Roadmap: ARIES-LITE

## Milestones

- ✅ **v1.5.0 Stabilization & Hardening** — Phases 1-3 (shipped 2026-03-18)
- ✅ **v1.6 Test Tracker** — Phases 4-5 (shipped 2026-03-26)
- 🚧 **v1.7 Debugging & Optimization** — Phases 6-8 (in progress)

## Phases

<details>
<summary>✅ v1.5.0 Stabilization & Hardening (Phases 1-3) — SHIPPED 2026-03-18</summary>

- [x] Phase 1: Critical Bug Fixes & Code Correctness (1/1 plans) — completed 2026-03-18
- [x] Phase 2: Robustness & Reliability (1/1 plans) — completed 2026-03-18
- [x] Phase 3: Cleanup & Quality (1/1 plans) — completed 2026-03-18

</details>

<details>
<summary>✅ v1.6 Test Tracker (Phases 4-5) — SHIPPED 2026-03-26</summary>

- [x] **Phase 4: Hardware Foundation & Camera Integration** - Servo safe startup, Picamera2 frame capture, and graceful shutdown proven on real hardware (completed 2026-03-26)
- [x] **Phase 5: State Machine, Vision & PID Integration** - Complete SCANNING → TRACKING → TARGET_LOST control loop with face detection and HUD (completed 2026-03-26)

</details>

### 🚧 v1.7 Debugging & Optimization (In Progress)

**Milestone Goal:** Naprawić krytyczne bugi w test_tracker.py wykryte podczas testów na hardware RPi4 — tilt nie rusza, runaway camera (błąd znaku PID), blue tint AWB, logika przejść stanów.

- [ ] **Phase 6: Diagnostics & Camera** - Clamp logging in hardware.py and Picamera2 AWB warm-up lock — baseline visibility and correct color rendering before any motion tests
- [ ] **Phase 7: PID Sign Correctness** - Tilt axis sign fix and pan verification — control loop converges to face-centered position in both axes
- [ ] **Phase 8: Scanning Logic** - Scan phase continuity and streak reset timing — clean state transitions with no servo jerk or premature detection

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

### Phase 6: Diagnostics & Camera
**Goal**: Hardware clamping is observable in logs and the camera delivers neutral color rendering — every subsequent test can be trusted visually and every servo limit event is traceable
**Depends on**: Phase 5
**Requirements**: DIAG-01, CAM-01, CAM-02
**Success Criteria** (what must be TRUE):
  1. When `set_angles()` receives a value outside pan ±60° or tilt ±30°, a WARNING line appears in terminal output identifying the axis and the clamped value — no silent saturation
  2. After startup, the live video feed shows neutral skin tones within 3 seconds — no persistent blue cast across frames
  3. `capture_metadata()["ColourGains"]` returns a non-None tuple after the 2s warm-up and the gains are locked via `set_controls({"ColourGains": ...})` — AWB does not re-converge during operation
  4. If `ColourGains` from metadata is None, the fallback values (2.5, 1.9) are applied and the image remains plausible — no crash or uncorrected blue tint on first run
**Plans:** 1 plan
Plans:
- [ ] 06-01-PLAN.md — Clamp logging in hardware.py + AWB warm-up lock in Picamera2Stream.start()

### Phase 7: PID Sign Correctness
**Goal**: The tilt axis drives the camera toward the face and neither axis runs away — the control loop converges to a face-centered steady state in both pan and tilt
**Depends on**: Phase 6
**Requirements**: PID-01, PID-02, PID-03
**Success Criteria** (what must be TRUE):
  1. Holding a face below the frame center causes the HUD `Tilt:` value to increase and the camera to tilt downward until the face reaches vertical center — tilt does not snap to the soft limit
  2. Holding a face to the right of frame center causes the HUD `Pan:` value to increase and the camera to pan right until the face reaches horizontal center — pan direction is unchanged from v1.6 behavior
  3. After a TRACKING → SCANNING → TRACKING transition cycle, neither the pan nor tilt PID integral accumulates a jump — the first correction frame after re-entering TRACKING is proportional to the actual error, not inflated by a residual integral term
**Plans:** 1 plan
Plans:
- [ ] 06-01-PLAN.md — Clamp logging in hardware.py + AWB warm-up lock in Picamera2Stream.start()

### Phase 8: Scanning Logic
**Goal**: State transitions between SCANNING and TRACKING are clean — no servo jerk on scan resumption, no stale detection streak when re-entering SCANNING
**Depends on**: Phase 7
**Requirements**: SCAN-01, SCAN-02
**Success Criteria** (what must be TRUE):
  1. When a face is lost and the system returns from TRACKING to SCANNING, the pan servo resumes the sinusoidal sweep from its current position — no visible snap or step change in the first scan frame
  2. After entering TARGET_LOST state, the detection streak counter is reset to zero immediately — a face appearing within the TARGET_LOST window requires a full 3-consecutive-frame streak before TRACKING is re-entered, not fewer
**Plans:** 1 plan
Plans:
- [ ] 06-01-PLAN.md — Clamp logging in hardware.py + AWB warm-up lock in Picamera2Stream.start()

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Bug Fixes | v1.5 | 1/1 | Complete | 2026-03-18 |
| 2. Robustness | v1.5 | 1/1 | Complete | 2026-03-18 |
| 3. Cleanup | v1.5 | 1/1 | Complete | 2026-03-18 |
| 4. Hardware Foundation & Camera Integration | v1.6 | 1/1 | Complete | 2026-03-26 |
| 5. State Machine, Vision & PID Integration | v1.6 | 1/1 | Complete | 2026-03-26 |
| 6. Diagnostics & Camera | v1.7 | 0/? | Not started | - |
| 7. PID Sign Correctness | v1.7 | 0/? | Not started | - |
| 8. Scanning Logic | v1.7 | 0/? | Not started | - |
