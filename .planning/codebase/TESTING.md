# Testing Patterns

**Analysis Date:** 2026-03-27

## Test Framework

**Runner:**
- None configured. No pytest, unittest, or any test framework in `requirements.txt`.
- No `pyproject.toml`, `setup.cfg`, or `tox.ini` for test configuration.

**Assertion Library:**
- None

**Run Commands:**
```bash
# No automated test commands exist
# Manual validation only:
python3 main.py                  # Start full system, verify via browser at http://0.0.0.0:5000
python3 run_test_tracker.py      # Standalone hardware test (requires RPi4 + pigpiod + camera)
scripts/validate-all.sh          # GSD methodology validators (not code tests)
```

## Test File Organization

**Location:**
- No test files exist. No `tests/` directory. No `*_test.py` or `test_*.py` files.

**Closest to a "test":**
- `src/modes/test_tracker.py` + `run_test_tracker.py` — a standalone hardware integration test module, not an automated test. It runs the full camera-detection-PID pipeline without Flask/dlib, using Picamera2 directly. Requires physical hardware to execute.

## Current State

**Zero automated tests.** Verification is entirely empirical per GSD methodology rules in `PROJECT_RULES.md`:

| Change Type | Required Proof |
|-------------|----------------|
| API endpoint | curl/HTTP response |
| UI change | Screenshot |
| Build/compile | Command output |
| Config | Verification command |

**What exists:**
1. **Manual integration testing** via `run_test_tracker.py` — runs camera + HAAR + PID + servos in a loop with HUD display
2. **GSD validation scripts** in `scripts/` — validate GSD methodology files (workflows, skills, templates), not application code:
   - `scripts/validate-all.sh`: Master runner, calls all validators below
   - `scripts/validate-workflows.sh`: Checks `.agent/workflows/*.md` for frontmatter and `<process>` tags
   - `scripts/validate-skills.sh`: Checks `.agent/skills/*/SKILL.md` for frontmatter fields
   - `scripts/validate-templates.sh`: Checks `.gsd/templates/*.md` for title heading and minimum size

## Verification Methods

**Primary method: Empirical proof**
- Run the system on RPi4 hardware
- Observe servo movement, MJPEG stream, HUD overlay
- Capture screenshots or curl output as evidence
- Document in GSD state snapshots

**Hardware test module** (`run_test_tracker.py`):
```bash
# Requires: RPi4 + Picamera2 + pigpiod running + physical servos
sudo pigpiod
python3 run_test_tracker.py
# Displays OpenCV window with HUD, or runs headless with logging
# Press 'q' to quit
```
This tests: Picamera2 capture, HAAR face detection with streak filter, PID tracking, sinusoidal scanning, safe start sequence, graceful shutdown. Does NOT test: dlib face recognition, Flask API, target upload.

**Mock hardware mode:**
- `src/hardware.py` automatically enters mock mode when pigpio is unavailable
- Allows running the Flask server on non-RPi machines for UI development
- Servos are simulated (angles tracked in memory, no PWM output)

## Test Structure (for future implementation)

**Recommended framework:** pytest + pytest-mock

**Recommended test runner config** (to be created as `pyproject.toml`):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

**Recommended directory structure:**
```
tests/
├── conftest.py              # Shared fixtures (mock hardware, mock camera)
├── test_config.py           # Verify config constants are sensible
├── test_tracker.py          # TrackerMachine state machine logic
├── test_hardware.py         # PanTiltSystem in mock mode
├── test_vision.py           # HybridVision with mocked cv2/face_recognition
└── test_server.py           # Flask test client for API endpoints
```

## Mocking

**No mocking framework in use.** However, the codebase has built-in mock patterns:

**Hardware mock** (`src/hardware.py` lines 5-11, 25-39):
```python
try:
    from gpiozero import AngularServo
    from gpiozero.pins.pigpio import PiGPIOFactory
    PIGPIO_AVAILABLE = True
except ImportError:
    PIGPIO_AVAILABLE = False

# In PanTiltSystem.__init__:
self._mock_mode = not PIGPIO_AVAILABLE
```
`PanTiltSystem` already operates in mock mode without hardware. This is leverageable for testing — instantiate on any machine, verify angle calculations without servos.

**Headless display mock** (`src/modes/test_tracker.py` lines 331-344):
```python
try:
    cv2.imshow("ARIES-LITE Test Tracker", wyswietlana)
except cv2.error:
    self._headless = True
    cv2.destroyAllWindows()
```

**What to mock for unit tests:**
- `cv2.VideoCapture` and frame reads for camera tests
- `face_recognition.face_encodings` and `face_recognition.compare_faces` for vision tests
- `cv2.CascadeClassifier.detectMultiScale` for detection tests
- `PanTiltSystem` (or use its built-in mock mode) for tracker tests
- `threading.Thread` starts for async verification tests

**What NOT to mock:**
- `src/config.py` constants — test with real values
- PID controller math (`simple_pid.PID`) — test actual behavior
- State machine transitions in `TrackerMachine` / `MaszynaStanow` — test real logic

## Coverage

**Requirements:** None enforced. No coverage tool configured.

**Recommended setup:**
```bash
pip install pytest pytest-cov pytest-mock
pytest --cov=src --cov-report=term-missing
```

## Test Types

**Unit Tests (not yet implemented, highest priority):**

*TrackerMachine state machine* (`src/tracker.py`) — best candidate for first tests:
```python
# Example test pattern:
def test_tracker_transitions_to_scanning_after_timeout():
    tracker = TrackerMachine()
    tracker.start_pipeline()
    assert tracker.state == "SCANNING"

    # Simulate no target for TIME_TO_LOST_SEC
    tracker.logic_tick(bbox=(100, 100, 50, 50), w=640, h=480, is_target=True)
    assert tracker.state == "TRACKING"

    # After timeout with no bbox
    import time; time.sleep(config.TIME_TO_LOST_SEC + 0.1)
    tracker.logic_tick(bbox=None, w=640, h=480, is_target=False)
    assert tracker.state == "SCANNING"
```

*PID tracking direction* (`src/tracker.py`):
```python
def test_pid_moves_toward_target():
    tracker = TrackerMachine()
    tracker.start_pipeline()
    initial_pan = tracker.hardware.pan_angle
    # Target is to the right of center
    tracker.do_tracking(bbox=(400, 240, 50, 50), frame_w=640, frame_h=480)
    # Pan should move right (negative correction due to negation)
    assert tracker.hardware.pan_angle != initial_pan
```

*Hardware angle clamping* (`src/hardware.py`):
```python
def test_set_angles_clamps_to_limits():
    hw = PanTiltSystem()  # Mock mode on non-RPi
    hw.set_angles(999, -999)
    assert hw.pan_angle == config.PAN_LIMIT_MAX   # 60
    assert hw.tilt_angle == config.TILT_LIMIT_MIN  # -30
```

*Vision target loading* (`src/vision.py`) — requires mocking face_recognition:
```python
def test_load_target_returns_false_for_missing_file(tmp_path):
    vision = HybridVision()
    assert vision.load_target_image(str(tmp_path / "nonexistent.jpg")) is False
```

**Integration Tests (not yet implemented):**

*Flask API endpoints* (`web/server.py`) — use Flask test client:
```python
def test_state_endpoint_returns_503_before_init():
    from web.server import app
    client = app.test_client()
    response = client.get('/api/state')
    assert response.status_code == 503
```

**E2E Tests:**
- Not applicable for automated testing due to hardware dependency
- `run_test_tracker.py` serves as a manual E2E test
- Full system E2E requires RPi4 + camera + servos + pigpiod

## Barriers to Automated Testing

1. **No test framework installed** — needs pytest added to `requirements.txt`
2. **Global state in `web/server.py`** — module-level globals (`stream`, `vision`, `tracker`) prevent clean test isolation. Each test would need to reset these globals or the module needs refactoring to use dependency injection.
3. **No dependency injection** — `TrackerMachine.__init__()` creates `PanTiltSystem()` directly. To unit test the state machine without hardware concerns, inject the hardware dependency.
4. **Threading complexity** — `trigger_async_verification()` spawns daemon threads. Testing async verification requires either mocking the thread or using `threading.Event` synchronization.
5. **Camera dependency** — `VideoStream` opens `cv2.VideoCapture` in `__init__`. Needs mock or lazy initialization for testing.

## Validation Scripts

**`scripts/validate-all.sh`:**
- Master validation runner
- Calls: `validate-workflows.sh`, `validate-skills.sh`, `validate-templates.sh`
- Returns exit code 0 if all pass, 1 if any fail
- These validate GSD methodology files only, not application code

**`scripts/validate-workflows.sh`:**
- Checks `.agent/workflows/*.md` files
- Validates: frontmatter present (starts with `---`), `description:` field exists
- Warns if `<process>` tag missing

**`scripts/validate-skills.sh`:**
- Checks `.agent/skills/*/SKILL.md` files
- Validates: file exists, frontmatter present, `name:` and `description:` fields

**`scripts/validate-templates.sh`:**
- Checks `.gsd/templates/*.md` files
- Validates: title heading (`# `), `Last updated` marker, minimum 200 chars

**No application-level validation scripts exist.** No syntax check, import verification, or smoke test scripts.

## Priority Test Implementation Plan

**Phase 1 — Foundation (low effort, high value):**
1. Add `pytest` and `pytest-mock` to `requirements.txt`
2. Create `tests/conftest.py` with mock hardware fixture
3. Write `tests/test_hardware.py` — angle clamping, smooth_move, mock mode
4. Write `tests/test_config.py` — constants exist, limits are sensible

**Phase 2 — Core logic:**
5. Write `tests/test_tracker.py` — state machine transitions, PID direction
6. Write `tests/test_vision.py` — target loading, HAAR detection (mocked cv2)

**Phase 3 — API:**
7. Write `tests/test_server.py` — Flask test client for all endpoints
8. Add `pytest --cov` to a validation script

---

*Testing analysis: 2026-03-27*
