# Testing Patterns

**Analysis Date:** 2026-03-29

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
2. **GSD validation scripts** in `scripts/` — validate GSD methodology files (workflows, skills, templates), not application code

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

## Testability Assessment

**Easily testable (no hardware needed):**

| Component | File | What to test |
|-----------|------|-------------|
| PanTiltSystem (mock) | `src/hardware.py` | Angle clamping, smooth_move math, mock mode activation |
| TrackerMachine | `src/tracker.py` | State transitions, PID direction, scan pattern |
| MaszynaStanow | `src/modes/test_tracker.py` | State transitions, PID, sinusoidal scan |
| DetekcjaTwarzy | `src/modes/test_tracker.py` | Streak filter logic (with mocked cv2 cascade) |
| Config constants | `src/config.py` | Limits sensibility, state name uniqueness |
| Flask endpoints | `web/server.py` | API responses, 503 guard, upload validation |

**Testable with mocking:**

| Component | File | What to mock |
|-----------|------|-------------|
| HybridVision | `src/vision.py` | `cv2.CascadeClassifier`, `face_recognition`, `cv2.TrackerCSRT_create` |
| VideoStream | `src/camera.py` | `cv2.VideoCapture` |

**Not testable automatically:**
- Physical servo movement (requires hardware observation)
- Actual camera feed quality (requires RPi + camera module)
- End-to-end latency (requires full hardware chain)

## Barriers to Automated Testing

1. **No test framework installed** — needs pytest added to `requirements.txt`
2. **Global state in `web/server.py`** — module-level globals (`stream`, `vision`, `tracker`) prevent clean test isolation. Each test would need to reset these globals or the module needs refactoring to use dependency injection.
3. **No dependency injection** — `TrackerMachine.__init__()` creates `PanTiltSystem()` directly. To unit test the state machine without hardware concerns, inject the hardware dependency.
4. **Threading complexity** — `trigger_async_verification()` spawns daemon threads. Testing async verification requires either mocking the thread or using `threading.Event` synchronization.
5. **Camera dependency** — `VideoStream` opens `cv2.VideoCapture` in `__init__`. Needs mock or lazy initialization for testing.

## Recommended Testing Strategy

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

## Example Test Patterns

**TrackerMachine state machine** (`src/tracker.py`) — best candidate for first tests:
```python
def test_tracker_transitions_to_scanning_after_timeout():
    tracker = TrackerMachine()
    tracker.start_pipeline()
    assert tracker.state == "SCANNING"

    # Simulate target found
    tracker.logic_tick(bbox=(100, 100, 50, 50), w=640, h=480, is_target=True)
    assert tracker.state == "TRACKING"

    # After timeout with no bbox
    import time; time.sleep(config.TIME_TO_LOST_SEC + 0.1)
    tracker.logic_tick(bbox=None, w=640, h=480, is_target=False)
    assert tracker.state == "SCANNING"
```

**Hardware angle clamping** (`src/hardware.py`):
```python
def test_set_angles_clamps_to_limits():
    hw = PanTiltSystem()  # Mock mode on non-RPi
    hw.set_angles(999, -999)
    assert hw.pan_angle == config.PAN_LIMIT_MAX   # 60
    assert hw.tilt_angle == config.TILT_LIMIT_MIN  # -30
```

**DetekcjaTwarzy streak filter** (`src/modes/test_tracker.py`):
```python
def test_streak_filter_requires_consecutive_detections(mocker):
    detekcja = DetekcjaTwarzy()
    fake_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    mock_detect = mocker.patch.object(detekcja._klasyfikator, 'detectMultiScale')

    # First two detections return None (streak < STREAK_REQUIRED)
    mock_detect.return_value = np.array([[50, 50, 80, 80]])
    assert detekcja.wykryj(fake_frame) is None  # streak=1
    assert detekcja.wykryj(fake_frame) is None  # streak=2
    assert detekcja.wykryj(fake_frame) is not None  # streak=3, passes filter
```

**Flask API guard** (`web/server.py`):
```python
def test_state_endpoint_returns_503_before_init():
    from web.server import app
    client = app.test_client()
    response = client.get('/api/state')
    assert response.status_code == 503
```

**Vision target loading** (`src/vision.py`):
```python
def test_load_target_returns_false_for_missing_file(tmp_path):
    vision = HybridVision()
    assert vision.load_target_image(str(tmp_path / "nonexistent.jpg")) is False
```

## What to Mock

**Mock these:**
- `cv2.VideoCapture` and frame reads for camera tests
- `face_recognition.face_encodings` and `face_recognition.compare_faces` for vision tests
- `cv2.CascadeClassifier.detectMultiScale` for detection tests
- `PanTiltSystem` (or use its built-in mock mode) for tracker tests
- `threading.Thread` starts for async verification tests

**Do NOT mock these — test real behavior:**
- `src/config.py` constants — test with real values
- PID controller math (`simple_pid.PID`) — test actual behavior
- State machine transitions in `TrackerMachine` / `MaszynaStanow` — test real logic
- Angle clamping in `PanTiltSystem` — test real math

## Coverage

**Requirements:** None enforced. No coverage tool configured.

**Recommended setup:**
```bash
pip install pytest pytest-cov pytest-mock
pytest --cov=src --cov-report=term-missing
```

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

*Testing analysis: 2026-03-29*
