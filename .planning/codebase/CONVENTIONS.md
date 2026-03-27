# Coding Conventions

**Analysis Date:** 2026-03-27

## Naming Patterns

**Files:**
- snake_case for all Python modules: `video_stream.py`, `test_tracker.py`
- Underscored prefixes for private methods within classes: `_async_lock`, `_mock_mode`, `_petla_przechwytywania`

**Functions:**
- snake_case for all functions and methods: `process_frame()`, `load_target_image()`, `smooth_move_to()`
- Polish-language function names in newer code (`src/modes/test_tracker.py`): `wykryj()`, `odczytaj()`, `zatrzymaj()`, `uruchom()`, `resetuj_streak()`, `_rysuj_hud()`, `_skanuj()`, `_sledz()`, `_przejdz_do()`
- English function names in older core modules (`src/vision.py`, `src/tracker.py`, `src/hardware.py`): `process_frame()`, `do_scan()`, `do_tracking()`, `logic_tick()`
- Private methods prefixed with underscore: `_petla_przechwytywania()`, `_rysuj_hud()`

**Variables:**
- Polish variable names in newer code: `klatka`, `szara`, `twarze`, `najw`, `srodek_x`, `blad_pan`, `korekta_pan`, `nowy_pan`, `ramka_cx`
- English variable names in older code: `frame`, `bbox`, `gray`, `faces`, `error_pan`, `pan_correction`
- Module-level constants in UPPER_SNAKE_CASE: `PID_PAN_P`, `CAMERA_WIDTH`, `STATE_SCANNING`, `LORES_WIDTH`, `STREAK_REQUIRED`
- Boolean flags use descriptive names: `is_tracking`, `target_verified`, `_verifying_task_active`, `_mock_mode`

**Classes:**
- PascalCase: `HybridVision`, `TrackerMachine`, `PanTiltSystem`, `VideoStream`
- Polish class names in newer code: `Picamera2Stream`, `DetekcjaTwarzy`, `MaszynaStanow`, `TestTracker`

**Convention for new code:** Follow the Polish naming pattern established in `src/modes/test_tracker.py` for user-facing names. Use English for standard programming concepts (PID, bbox, frame, thread). When unsure, use Polish.

## Code Style

**Formatting:**
- No automated formatter (no black, autopep8, yapf configured)
- 4-space indentation throughout
- No trailing whitespace enforcement
- Line length varies (no enforced limit), typically under 120 characters
- Blank lines between methods within classes (single blank line)
- Two blank lines between top-level definitions

**Linting:**
- No linter configured (no flake8, pylint, ruff, mypy)
- No `pyproject.toml`, `setup.cfg`, or `.flake8` files exist
- No pre-commit hooks

**Type Hints:**
- Used in `src/vision.py`: `def process_frame(self, frame: np.ndarray) -> Tuple[Optional[Tuple[int, int, int, int]], bool]:`
- Used in `src/tracker.py`: `def logic_tick(self, bbox: Optional[Tuple[int, int, int, int]], w: int, h: int, is_target: bool):`
- Used in `src/hardware.py`: `def set_angles(self, pan: float, tilt: float) -> None:`
- More thorough in `src/modes/test_tracker.py`: every method has return type annotations
- Convention: Use type hints from `typing` module (`Tuple`, `Optional`, `Generator`) for all new code

## Import Organization

**Order (observed consistently):**
1. Standard library imports (`time`, `os`, `threading`, `signal`, `math`, `sys`, `logging`)
2. Third-party imports (`cv2`, `numpy`, `flask`, `simple_pid`, `face_recognition`)
3. Local imports (`from src.camera import VideoStream`, `from . import config`)

**Path style:**
- Relative imports within `src/` package: `from . import config`, `from .hardware import PanTiltSystem`
- Absolute imports from entry points: `from src.camera import VideoStream`, `from src.modes.test_tracker import TestTracker`
- No path aliases configured

**Pattern example from `web/server.py`:**
```python
import time
import cv2
import threading
import signal
from typing import Generator
from flask import Flask, render_template, Response, request, jsonify
from werkzeug.utils import secure_filename
import os
import logging

from src.camera import VideoStream
from src.vision import HybridVision
from src.tracker import TrackerMachine
from src import config
```

## Error Handling

**Patterns:**
- try/except with `logging.error()` — never re-raise, always log and continue gracefully
- Pattern in `src/vision.py` line 50-53:
  ```python
  except Exception as e:
      logger.error(f"Blad przy ladowaniu wzorca: {e}")
      return False
  ```
- Hardware initialization falls back to mock mode on failure (`src/hardware.py` lines 28-39):
  ```python
  try:
      factory = PiGPIOFactory()
      self.pan_servo = AngularServo(...)
  except Exception as e:
      logger.error(f"Nie mozna uruchomic pigpio...: {e}")
      self._mock_mode = True
  ```
- Camera retry with counter in `src/modes/test_tracker.py` lines 95-119: retries up to `CAMERA_MAX_RETRIES` with delay, then stops

**No custom exceptions.** All error handling uses built-in `Exception` catches.

**Graceful degradation pattern:** Try hardware, fall back to mock/noop. Seen in:
- `src/hardware.py`: `PIGPIO_AVAILABLE` flag + `_mock_mode` attribute
- `src/modes/test_tracker.py`: `_headless` flag for display fallback

**Guard pattern for uninitialized state** in `web/server.py`:
```python
def require_init():
    if not init_event.is_set():
        return jsonify({"error": "System uruchamia sie..."}), 503
    return None
```
Use this pattern for any new API endpoint that depends on system initialization.

## Logging

**Framework:** Python standard `logging` module

**Setup pattern** (from `main.py`):
```python
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("MAIN")
```

**Enhanced setup** (from `run_test_tracker.py`):
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
```

**Per-module logger:** Every module creates its own logger at module scope:
```python
logger = logging.getLogger(__name__)
```

**Log messages are in Polish** with occasional English technical terms:
- `logger.info("Faza Safe-Start: Wyrownywanie polozenia")`
- `logger.error(f"Verify thread exception: {e}")`
- `logger.info("Hardware servos with PiGPIO initialized successfully.")`

**Convention for new code:** Use Polish log messages. Create module-level logger with `logging.getLogger(__name__)`. Use INFO for state transitions, ERROR for failures, WARNING for degraded operation.

## Comments

**Language:** Polish exclusively for inline comments and docstrings

**Docstring style:** Triple-quoted, single-paragraph Polish descriptions. No formal docstring format (no Sphinx, no Google style). Examples:
```python
def load_target_image(self, image_path: str) -> bool:
    """Laduje zdjecie by wyciagnac z niego DNA twarzy (encoding). Zwraca True jesli sie udalo."""
```

```python
class HybridVision:
    """
    Podejscie hybrydowe do sledzenia:
    1. Szybki detektor kaskadowy HAAR (szuka kazdej twarzy) ~30FPS na RPi
    2. Tracker CSRT (lub KCF)...
    3. Asynchronicznie odpytywane face_recognition...
    """
```

**Inline comments:** Polish, explaining *why* not *what*:
```python
# Obetnij wartości do zadeklarowanych bezpiecznych stref dla kamery RPi
# Przelicz przez PID (- bo odwracamy wektor bledu na kierunek skretu by go zniwelowac)
# Zawężono zakres dla bezpieczeństwa taśmy od kamery
```

**Param docs** (`:param` style) in `src/hardware.py`:
```python
:param pan: Docelowy kat X (horyzontalnie)
:param tilt: Docelowy kat Y (wertykalnie)
```

**Convention for new code:** Write docstrings in Polish. Use triple-quoted single paragraph for simple methods. Use numbered lists for complex algorithms. Add `:param` annotations for public methods with non-obvious parameters.

## Function Design

**Size:** Functions are small, typically 10-30 lines. Largest is `_petla_przechwytywania` at ~40 lines (camera retry logic).

**Parameters:** Use type hints. Default values for hardware config (`pan_pin: int = 12`). Named parameters for clarity (`delay=0.03`).

**Return values:**
- Tuples for multi-value returns: `Tuple[Optional[Tuple[int, int, int, int]], bool]`
- `bool` for success/failure: `load_target_image() -> bool`
- `Optional` for nullable returns: `odczytaj() -> Optional[np.ndarray]`
- `None` implicit return for void operations

## Module Design

**Exports:** Defined via `__all__` in `src/__init__.py` and `src/modes/__init__.py`:
```python
__all__ = ["VideoStream", "HybridVision", "TrackerMachine", "PanTiltSystem", "config"]
```

**Barrel files:** Both `src/__init__.py` and `src/modes/__init__.py` serve as barrel files.

**One class per file** pattern (mostly): `camera.py` has `VideoStream`, `vision.py` has `HybridVision`, `hardware.py` has `PanTiltSystem`. Exception: `src/modes/test_tracker.py` contains four classes (`Picamera2Stream`, `DetekcjaTwarzy`, `MaszynaStanow`, `TestTracker`) because they form a cohesive standalone module.

## Common Patterns

**Thread safety — Lock guards:**
```python
self._async_lock = threading.Lock()
# ...
with self._async_lock:
    self.target_encoding = encodings[0]
```
Every shared mutable state has a dedicated lock. Use `with` statement for lock acquisition.

**Daemon threads:**
```python
t = threading.Thread(target=heavy_task)
t.daemon = True
t.start()
```
All background threads are daemon threads so they die with the main process.

**Graceful hardware degradation:**
```python
try:
    from gpiozero import AngularServo
    PIGPIO_AVAILABLE = True
except ImportError:
    PIGPIO_AVAILABLE = False
```
Use module-level try/except for optional hardware imports. Set a boolean flag. Check flag in constructor.

**Signal handling for cleanup:**
```python
signal.signal(signal.SIGINT, lambda s, f: shutdown())
signal.signal(signal.SIGTERM, lambda s, f: shutdown())
```
Register signal handlers in the entry point. The handler calls a `shutdown()` or `zatrzymaj()` function that stops threads, releases camera, detaches servos.

**Configuration via centralized constants** (`src/config.py`):
- All tuning parameters live in `src/config.py`
- No environment variables, no `.env` files
- Import as `from . import config` then reference as `config.PID_PAN_P`

**State machine as string constants:**
```python
STATE_SAFE_START = "SAFE_START"
STATE_SCANNING = "SCANNING"
STATE_TRACKING = "TRACKING"
STATE_IDLE = "IDLE"
```
States are string constants in `src/config.py`. State transitions happen by direct assignment: `self.state = config.STATE_SCANNING`. No enum class is used.

**Flask module globals pattern** (`web/server.py`):
```python
stream = None
vision = None
tracker = None
# ... initialized in start_server_and_logic()
```
Globals are initialized once in the startup function. Protected by `init_event = threading.Event()` which gates API access via `require_init()`.

---

*Convention analysis: 2026-03-27*
