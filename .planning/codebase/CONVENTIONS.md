# CONVENTIONS.md — Code Conventions & Patterns

> Generated: 2026-03-18

## Language
- **Comments**: Polish language throughout
- **Variable names**: Mix of English (code) and Polish (comments/strings)
- **Logging messages**: Polish with some English technical terms
- **UI text**: Polish (button labels, status messages)

## Python Style
- **No type hints** on most functions (except vision.py which uses `typing`)
- **No docstring standard** — mix of Polish descriptions, some functions undocumented
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Imports**: Standard library first, then third-party, then local (`from . import config`)
- **No linter/formatter** configured (no pyproject.toml, setup.cfg, .flake8, etc.)

## Architecture Patterns
- **Configuration**: All constants centralized in `src/config.py` — no env vars, no .env file
- **Graceful degradation**: `PIGPIO_AVAILABLE` flag for mock hardware mode
- **Thread safety**: Explicit `threading.Lock()` for shared resources
- **State machine**: String-based states defined as constants in config.py
- **Error handling**: try/except with logging, no custom exception classes

## Flask Patterns
- **Global state**: Module-level globals (`stream`, `vision`, `tracker`) initialized in `start_server_and_logic()`
- **No blueprints**: All routes in single `server.py`
- **MJPEG streaming**: Generator-based `multipart/x-mixed-replace`
- **File upload**: `werkzeug.secure_filename` + direct filesystem save
- **JSON API**: `jsonify()` responses with Polish error messages

## Commit Convention
- `type(scope): description` format
- Types: feat, fix, docs, refactor, test, chore
- Scope typically references phase number: `feat(phase-1): ...`

## Missing Conventions
- No automated testing
- No CI/CD
- No code formatting tools
- No pre-commit hooks
- No dependency management beyond requirements.txt
