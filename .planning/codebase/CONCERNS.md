# CONCERNS.md — Code Quality & Risk Analysis

> Generated: 2026-03-18

## Critical Issues

### 1. Missing `logger` import in server.py
- **File**: `web/server.py:78`
- **Impact**: `handle_command()` references `logger` but it's never defined/imported at module level
- **Severity**: Runtime crash on `/api/command` with `cmd=CENTER`

### 2. No graceful shutdown
- **Impact**: Daemon threads die abruptly, no servo detach, no camera release on SIGINT
- **Risk**: Servo left in powered state, potential hardware wear

### 3. No authentication on API endpoints
- **Impact**: Anyone on the network can control servos, upload images
- **Risk**: Unauthorized access in shared network environments

## Moderate Issues

### 4. Global state in server.py
- Module-level globals (`stream`, `vision`, `tracker`) initialized late
- Flask routes can be called before `start_server_and_logic()` completes init
- Race condition window between Flask start and logic thread start

### 5. VideoStream.read() has no lock
- `self.frame` written by camera thread, read by logic thread without synchronization
- On CPython GIL provides some protection, but not guaranteed for numpy arrays

### 6. CSRT tracker tolerance
- `face_cascade.detectMultiScale` returns first face, not largest
- Comment says "Wez pierwsza/najwieksza" but code takes `faces[0]` without sorting by area

### 7. Blocking smooth_move_to in Flask route
- `handle_command('CENTER')` calls `smooth_move_to(0,0)` synchronously
- This blocks the Flask request thread for potentially seconds

## Minor Issues

### 8. Unused import
- `imutils` in requirements.txt but never imported in any source file

### 9. No input validation on API
- `/api/command` doesn't validate unknown commands
- No rate limiting on any endpoint

### 10. Hardcoded camera index
- `CAMERA_INDEX = 0` with no override mechanism (env var or CLI arg)

## Technical Debt
- No tests (see TESTING.md)
- No type hints consistency
- No code formatter
- adapters/ directory exists but is unused
- Old `.gsd/` artifacts should be migrated or removed
