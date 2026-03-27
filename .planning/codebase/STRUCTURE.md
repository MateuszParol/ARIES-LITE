# Codebase Structure

**Analysis Date:** 2026-03-27

## Directory Layout

```
ARIES-LITE/
├── main.py                     # Entry point: full system (Flask + vision + PID)
├── run_test_tracker.py         # Entry point: standalone test tracker (no Flask, no dlib)
├── requirements.txt            # Python dependencies (10 pinned packages)
├── VERSION                     # Version string file ("1.1")
├── CLAUDE.md                   # AI coding assistant instructions
├── PROJECT_RULES.md            # GSD methodology rules
├── GSD-STYLE.md                # GSD style guide
├── CHANGELOG.md                # Release changelog
├── LICENSE                     # License file
├── README.md                   # Project documentation
├── model_capabilities.yaml     # Model capability definitions
├── src/                        # Core application modules
│   ├── __init__.py             # Package exports: VideoStream, HybridVision, TrackerMachine, PanTiltSystem, config
│   ├── config.py               # All tuning constants (PID, servo limits, camera, states)
│   ├── camera.py               # VideoStream — async OpenCV frame capture (used by full system)
│   ├── vision.py               # HybridVision — HAAR + CSRT + async dlib verification
│   ├── tracker.py              # TrackerMachine — state machine + PID control
│   ├── hardware.py             # PanTiltSystem — servo abstraction with mock mode
│   └── modes/                  # Standalone operational modes
│       ├── __init__.py         # Exports: TestTracker
│       └── test_tracker.py     # Self-contained test mode (Picamera2 + HAAR + PID, ~394 lines)
├── web/                        # Flask web interface
│   ├── server.py               # Flask app, routes, MJPEG stream, main_loop orchestration
│   └── templates/
│       └── index.html          # Single-page mobile-first UI (vanilla HTML/CSS/JS, Polish)
├── scripts/                    # Validation and utility scripts
│   ├── validate-all.sh         # Master validation runner
│   ├── validate-workflows.sh   # GSD workflow validation
│   ├── validate-skills.sh      # Agent skill validation
│   ├── validate-templates.sh   # Template validation
│   ├── search_repo.sh          # Repository search utility
│   ├── setup_search.sh         # Search setup
│   └── *.ps1                   # Windows PowerShell equivalents of above
├── docs/                       # Documentation
│   ├── runbook.md              # Operations runbook
│   ├── model-selection-playbook.md
│   └── token-optimization-guide.md
├── .planning/                  # GSD planning artifacts (codebase analysis, phase plans)
├── .agent/                     # Agent configuration
│   ├── skills/                 # Agent skill definitions (codebase-mapper, debugger, executor, etc.)
│   └── workflows/              # GSD workflow definitions
├── .claude/                    # Claude Code local settings
└── .gemini/                    # Gemini configuration
```

## Directory Purposes

**`src/`:**
- Purpose: All core application logic -- camera, vision, control, hardware
- Contains: 5 Python modules + 1 sub-package (`modes/`)
- Key files: `config.py` (constants), `vision.py` (heaviest logic), `tracker.py` (state machine)
- Import pattern: Modules import from siblings via relative imports (`from . import config`, `from .hardware import PanTiltSystem`)

**`src/modes/`:**
- Purpose: Self-contained operational modes that can run independently of the full system
- Contains: `test_tracker.py` -- a standalone module with its own camera class (`Picamera2Stream`), detection class (`DetekcjaTwarzy`), and state machine (`MaszynaStanow`)
- Key design: Imports only `src.config` and `src.hardware` from the parent package; does NOT use `src/camera.py`, `src/vision.py`, or `src/tracker.py`
- Pattern for adding new modes: create a new file here with its own orchestrator class

**`web/`:**
- Purpose: HTTP interface layer -- Flask server and HTML templates
- Contains: `server.py` (routes + orchestration), `templates/index.html` (single-page UI)
- Note: `web/` is NOT a Python package (no `__init__.py`). It is imported via `from web.server import start_server_and_logic` which works because the project root is in `sys.path`.

**`scripts/`:**
- Purpose: Shell/PowerShell validation and utility scripts for GSD workflow
- Contains: Paired `.sh` / `.ps1` scripts
- Not imported by Python code; run manually

**`docs/`:**
- Purpose: Operational documentation
- Contains: Runbook, AI model selection guide, token optimization guide

## Module Boundaries

**Import Rules (strict downward flow, no cycles):**
- `src/config.py` imports nothing from the project (leaf dependency)
- `src/hardware.py` imports only `src/config`
- `src/camera.py` imports only `src/config`
- `src/vision.py` imports nothing from `src/` (uses OpenCV, face_recognition, threading directly)
- `src/tracker.py` imports `src/config` and `src/hardware` (creates its own PanTiltSystem instance)
- `src/modes/test_tracker.py` imports `src/config` and `src/hardware` (creates its own PanTiltSystem)
- `web/server.py` imports `src/camera`, `src/vision`, `src/tracker`, `src/config` (top-level orchestrator)

**Dependency graph:**
```
web/server.py
  ├── src/camera.py      -> src/config.py
  ├── src/vision.py      -> (no src imports)
  └── src/tracker.py     -> src/hardware.py -> src/config.py

run_test_tracker.py
  └── src/modes/test_tracker.py -> src/hardware.py -> src/config.py
```

## Key Files

**Entry Points:**
- `main.py`: Full system entry -- calls `web/server.py:start_server_and_logic()`
- `run_test_tracker.py`: Test tracker entry -- instantiates `src/modes/test_tracker.py:TestTracker`, registers signal handlers

**Configuration:**
- `src/config.py`: All runtime constants (PID gains, servo limits, camera settings, state name strings, file paths)
- `requirements.txt`: Python package dependencies with pinned versions

**Core Logic:**
- `src/vision.py`: HybridVision class -- HAAR detection, CSRT tracking, async dlib verification (~130 lines)
- `src/tracker.py`: TrackerMachine class -- state machine with PID-driven servo control (~114 lines)
- `src/hardware.py`: PanTiltSystem class -- gpiozero/pigpio servo driver with mock fallback (~97 lines)
- `src/camera.py`: VideoStream class -- threaded OpenCV VideoCapture wrapper (~55 lines)
- `src/modes/test_tracker.py`: Complete standalone test system -- 4 classes (Picamera2Stream, DetekcjaTwarzy, MaszynaStanow, TestTracker), largest file (~394 lines)

**Web Layer:**
- `web/server.py`: Flask routes (5 endpoints), MJPEG generator, main_loop, start/shutdown orchestration (~194 lines)
- `web/templates/index.html`: Mobile-first single-page UI with inline CSS/JS -- MJPEG stream viewer, status badge, control buttons, target face upload form (~222 lines)

## Configuration Files

- `src/config.py`: Application constants (not a config file, but a Python module with all tunables)
- `requirements.txt`: `pip install -r requirements.txt` -- 10 packages pinned
- `VERSION`: Plain text version string
- `model_capabilities.yaml`: AI model capability definitions for GSD tooling
- `.gitignore`: Ignores `__pycache__/`, `venv/`, `tmp_faces/`, `.env`

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `test_tracker.py`, `hardware.py`)
- Web templates: `lowercase.html`
- Scripts: `kebab-case.sh` / `kebab-case.ps1`
- Root configs: PascalCase or UPPER (e.g., `CLAUDE.md`, `VERSION`, `README.md`)

**Directories:**
- All lowercase, short names: `src/`, `web/`, `docs/`, `scripts/`
- Sub-packages: `src/modes/`

**Code naming (mixed Polish/English codebase):**
- Full system modules (`src/*.py`): English class names (PascalCase), English method names (snake_case), Polish comments
- Test tracker (`src/modes/test_tracker.py`): Polish class names (`MaszynaStanow`, `DetekcjaTwarzy`), Polish method names (`uruchom`, `zatrzymaj`, `wykryj`), Polish comments
- Config constants: English UPPER_SNAKE_CASE everywhere

## Where to Add New Code

**New operational mode (like test_tracker):**
- Create: `src/modes/new_mode.py` with its own orchestrator class
- Export from: `src/modes/__init__.py`
- Create entry point: `run_new_mode.py` in project root
- Can import: `src/config`, `src/hardware`
- Follow pattern: self-contained with own camera/detection classes if needed

**New vision algorithm or detector:**
- If used by full system: add to `src/vision.py` or create `src/new_vision.py`
- If standalone: create as a new mode in `src/modes/`

**New API endpoint:**
- Add route function to: `web/server.py`
- Guard with `require_init()` if it needs initialized system
- If it needs a new HTML page: add to `web/templates/`

**New hardware abstraction (e.g., new sensor, LED):**
- Create: `src/new_hardware.py`
- Follow pattern of `src/hardware.py` -- try/except import with mock fallback, `_mock_mode` flag

**New configuration constant:**
- Add to: `src/config.py` with English UPPER_SNAKE_CASE name and Polish comment

**New utility/helper:**
- For src modules: add to relevant module or create new file in `src/`
- For shell scripts: add `.sh` + `.ps1` pair to `scripts/`

**New dependency:**
- Add to: `requirements.txt` with pinned version (e.g., `package==X.Y.Z`)

## Generated/Temporary

**`tmp_faces/`:**
- Purpose: Uploaded target face images (via `/api/upload_target`)
- Created at: runtime by `os.makedirs()` in `web/server.py` (at import time)
- Default file: `target.jpg` auto-loaded if present
- Committed: No (in `.gitignore`)

**`__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes, by Python interpreter
- Committed: No (in `.gitignore`)

**`venv/`:**
- Purpose: Python virtual environment
- Generated: Yes, by `python3 -m venv venv`
- Committed: No (in `.gitignore`)

**`.planning/`:**
- Purpose: GSD planning documents and codebase analysis
- Generated: Yes (by planning/mapping tools)
- Committed: Yes

---

*Structure analysis: 2026-03-27*
