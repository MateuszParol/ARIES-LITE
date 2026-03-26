# Requirements: ARIES-LITE

**Defined:** 2026-03-26
**Core Value:** Prove hardware+PID control loop works smoothly with Picamera2 on RPi OS Bookworm 64-bit

## v1.6 Requirements

Requirements for Test Tracker milestone. Each maps to roadmap phases.

### Hardware

- [x] **HW-01**: System performs safe startup — servos move incrementally to neutral (0,0) via smooth_move_to before any loop begins
- [x] **HW-02**: Picamera2 captures frames at 320x240 BGR888 via native libcamera on Bookworm 64-bit
- [x] **HW-03**: System shuts down gracefully on Ctrl+C / SIGTERM — camera released, servos detached, no resource leaks
- [x] **HW-04**: Test tracker runs as standalone script (run_test_tracker.py) — no Flask, no modification to existing src/ files

### Vision

- [ ] **VIS-01**: HAAR cascade detects any face in grayscale frame (no identity recognition)
- [ ] **VIS-02**: Detection streak filter requires 3 consecutive frames before triggering TRACKING transition
- [ ] **VIS-03**: HUD overlay shows face bounding box (green), state label, center crosshair, and servo angles

### Control

- [ ] **CTL-01**: State machine cycles: SCANNING → TRACKING → TARGET_LOST → SCANNING
- [ ] **CTL-02**: Dual-axis PID (pan + tilt) drives servos from face centroid error, with reset on SCANNING entry
- [ ] **CTL-03**: SCANNING state sweeps sinusoidally (±45° pan, 0.1 Hz)
- [ ] **CTL-04**: TARGET_LOST triggers after 2 seconds without face detection, returns to SCANNING

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Identity

- **ID-01**: System recognizes specific target person via dlib face encoding
- **ID-02**: System distinguishes target from non-target faces

### Operations

- **OPS-01**: System runs as systemd service with auto-restart
- **OPS-02**: System provides MJPEG stream via Flask web interface

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| dlib identity recognition | Obscures PID behavior; test tracker tracks any face |
| CSRT/KCF visual tracker | Adds indirection; direct HAAR→PID is cleaner for proof |
| Flask / MJPEG streaming | Standalone terminal script; no web interface needed |
| Multi-face priority logic | Complexity that obscures proof; largest face by area suffices |
| IDLE state | Test runs until Ctrl+C; SCANNING is the resting state |
| Kalman filter | PID is the proven choice (locked architectural decision) |
| Persistent config / YAML | Overkill for test module; constants at top of file |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HW-01 | Phase 4 | Complete |
| HW-02 | Phase 4 | Complete |
| HW-03 | Phase 4 | Complete |
| HW-04 | Phase 4 | Complete |
| VIS-01 | Phase 5 | Pending |
| VIS-02 | Phase 5 | Pending |
| VIS-03 | Phase 5 | Pending |
| CTL-01 | Phase 5 | Pending |
| CTL-02 | Phase 5 | Pending |
| CTL-03 | Phase 5 | Pending |
| CTL-04 | Phase 5 | Pending |

**Coverage:**
- v1.6 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---
*Requirements defined: 2026-03-26*
*Last updated: 2026-03-26 — traceability filled after roadmap creation*
