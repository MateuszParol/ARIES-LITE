---
phase: 1
plan: 1
name: "Critical Bug Fixes & Code Correctness"
status: complete
---

# Summary: 01-01 Critical Bug Fixes

## What was built
Three critical bug fixes across core modules:

1. **Logger Fix (REQ-11)**: Added `logger = logging.getLogger(__name__)` at module level in `web/server.py` — CENTER command no longer crashes.

2. **HAAR Sort by Area (REQ-12)**: Added `faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)` in `src/vision.py` — largest face selected when multiple detected.

3. **Frame Lock (REQ-14)**: Added `threading.Lock()` to `src/camera.py` VideoStream — frame reads/writes synchronized between camera and logic threads.

## Key files
- **modified**: `web/server.py`, `src/vision.py`, `src/camera.py`

## Deviations
None.

## Self-Check: PASSED
- `grep "logger = logging.getLogger" web/server.py` — found at line 15
- `grep "sorted(faces" src/vision.py` — found
- `grep "_frame_lock" src/camera.py` — 3 matches
