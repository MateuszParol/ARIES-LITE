# Phase 1 Plan: Critical Bug Fixes & Code Correctness

**Status**: EXECUTED
**Requirements**: REQ-11, REQ-12, REQ-14

## Wave 1 (all independent)

### Task 1: Add missing logger to server.py (REQ-11)
- **File**: `web/server.py`
- **Bug**: `handle_command()` references `logger` but no module-level logger exists — crashes on CENTER command
- **Fix**: Added `import logging` and `logger = logging.getLogger(__name__)` at module level (line 15)
- **Verification**: `grep -n "logger = logging.getLogger" web/server.py` returns line 15

### Task 2: Sort HAAR detections by area (REQ-12)
- **File**: `src/vision.py`
- **Bug**: `process_frame()` takes `faces[0]` (first detection) instead of largest; comment says "pierwsza/najwieksza" but no sorting
- **Fix**: Added `faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)` before `faces[0]`
- **Verification**: `grep "sorted(faces" src/vision.py` finds the sort line

### Task 3: Add frame lock to VideoStream (REQ-14)
- **File**: `src/camera.py`
- **Bug**: `self.frame` written by camera thread, read by logic thread with no synchronization — potential frame tearing
- **Fix**: Added `self._frame_lock = threading.Lock()` in `__init__`, wrapped write in `update()` and read in `read()` with lock
- **Verification**: `grep "_frame_lock" src/camera.py` returns 3 matches (init, update, read)
