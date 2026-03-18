# TESTING.md — Testing Analysis

> Generated: 2026-03-18

## Current State: NO AUTOMATED TESTS

The project has zero automated tests. No test framework is installed or configured.

## Verification Method
- **Empirical**: Manual HTTP requests, screenshots, command output
- **Validation scripts**: `scripts/validate-all.sh` and `scripts/validate-workflows.sh` (GSD workflow validation, not code tests)

## Testability Assessment

| Module | Testability | Notes |
|--------|------------|-------|
| config.py | Trivial | Pure constants, no logic to test |
| camera.py | Hard | Requires camera hardware or mock VideoCapture |
| vision.py | Medium | Can mock cv2/face_recognition, test logic flow |
| tracker.py | Good | State machine + PID are pure logic, mockable hardware |
| hardware.py | Medium | Already has mock mode, but no test harness |
| server.py | Medium | Flask test client possible, but globals complicate it |

## Barriers to Testing
1. **Hardware dependency**: Camera, servos, pigpio daemon
2. **Global state in server.py**: Module-level globals prevent clean test isolation
3. **No dependency injection**: Classes create their own dependencies (e.g., TrackerMachine creates PanTiltSystem)
4. **Threading**: Async verification, daemon threads hard to test deterministically

## Recommendations for Future Testing
- pytest + pytest-mock for unit tests
- Flask test client for API endpoint tests
- TrackerMachine state machine is the best candidate for first tests
- Mock PanTiltSystem already supports mock mode — leverage this
