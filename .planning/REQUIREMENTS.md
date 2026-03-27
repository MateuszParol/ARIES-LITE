# Requirements: ARIES-LITE

**Defined:** 2026-03-26
**Core Value:** Prove hardware+PID control loop works smoothly with Picamera2 on RPi OS Bookworm 64-bit

## v1.6 Requirements (Completed)

<details>
<summary>All 11 requirements completed — click to expand</summary>

### Hardware

- [x] **HW-01**: System performs safe startup — servos move incrementally to neutral (0,0) via smooth_move_to before any loop begins
- [x] **HW-02**: Picamera2 captures frames at 320x240 BGR888 via native libcamera on Bookworm 64-bit
- [x] **HW-03**: System shuts down gracefully on Ctrl+C / SIGTERM — camera released, servos detached, no resource leaks
- [x] **HW-04**: Test tracker runs as standalone script (run_test_tracker.py) — no Flask, no modification to existing src/ files

### Vision

- [x] **VIS-01**: HAAR cascade detects any face in grayscale frame (no identity recognition)
- [x] **VIS-02**: Detection streak filter requires 3 consecutive frames before triggering TRACKING transition
- [x] **VIS-03**: HUD overlay shows face bounding box (green), state label, center crosshair, and servo angles

### Control

- [x] **CTL-01**: State machine cycles: SCANNING → TRACKING → TARGET_LOST → SCANNING
- [x] **CTL-02**: Dual-axis PID (pan + tilt) drives servos from face centroid error, with reset on SCANNING entry
- [x] **CTL-03**: SCANNING state sweeps sinusoidally (±45° pan, 0.1 Hz)
- [x] **CTL-04**: TARGET_LOST triggers after 2 seconds without face detection, returns to SCANNING

</details>

## v1.7 Requirements

Wymagania dla milestone Debugging & Optimization. Naprawy krytycznych bugów wykrytych na hardware RPi4.

### PID Control

- [x] **PID-01**: Korekta tilt jest negowana (-pid_tilt) — kamera podąża za twarzą w pionie w poprawnym kierunku
- [x] **PID-02**: Korekta pan zachowuje istniejącą negację — weryfikacja że oś X nadal działa poprawnie po zmianach
- [x] **PID-03**: Oba PID resetowane (integral+derivative) przy wejściu w SCANNING — brak skoku po zmianie stanu

### Camera (AWB)

- [x] **CAM-01**: Picamera2 wykonuje 2s warm-up po start() i lockuje ColourGains — obraz bez niebieskiej dominanty
- [x] **CAM-02**: Jeśli ColourGains lock nie eliminuje blue tint, sprawdzony format konwersji YUV (NV12 vs planar)

### Scanning

- [x] **SCAN-01**: Powrót z TRACKING do SCANNING nie powoduje skoku serwa — sinusoida startuje od aktualnej pozycji (phase offset)
- [x] **SCAN-02**: Streak filter resetowany przy wejściu w TARGET_LOST (nie czeka do SCANNING)

### Diagnostyka

- [x] **DIAG-01**: set_angles() loguje ostrzeżenie gdy wartość jest clampowana do soft-limitu (pan ±60°, tilt ±30°)

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
| Zmiana stałych PID (Kp/Ki/Kd) | Obecne wartości nie były problemem — bug to znak, nie gain |
| Refaktoring architektury test_tracker | Minimalne zmiany — chirurgiczne fixy, nie przebudowa |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HW-01 | Phase 4 | Complete |
| HW-02 | Phase 4 | Complete |
| HW-03 | Phase 4 | Complete |
| HW-04 | Phase 4 | Complete |
| VIS-01 | Phase 5 | Complete |
| VIS-02 | Phase 5 | Complete |
| VIS-03 | Phase 5 | Complete |
| CTL-01 | Phase 5 | Complete |
| CTL-02 | Phase 5 | Complete |
| CTL-03 | Phase 5 | Complete |
| CTL-04 | Phase 5 | Complete |
| PID-01 | Phase 7 | Complete |
| PID-02 | Phase 7 | Complete |
| PID-03 | Phase 7 | Complete |
| CAM-01 | Phase 6 | Complete |
| CAM-02 | Phase 6 | Complete |
| SCAN-01 | Phase 8 | Complete |
| SCAN-02 | Phase 8 | Complete |
| DIAG-01 | Phase 6 | Complete |

**Coverage:**
- v1.6 requirements: 11 total (all complete)
- v1.7 requirements: 8 total (all pending)
- Unmapped: 0 (all 8 v1.7 requirements mapped to Phases 6-8)

---
*Requirements defined: 2026-03-26*
*Last updated: 2026-03-27 — v1.7 traceability filled (Phases 6-8)*
