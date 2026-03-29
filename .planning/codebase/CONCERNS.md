# Codebase Concerns

**Analysis Date:** 2026-03-29

## Critical Issues

**Race condition on CENTER command vs main_loop:**
- Issue: `handle_command()` in `web/server.py` line 109 spawns a daemon thread running `smooth_move_to(0, 0)` while `main_loop()` simultaneously calls `tracker.logic_tick()` which also calls `hardware.set_angles()`. Two threads fight over servo position with no synchronization.
- Files: `web/server.py` lines 106-109, `src/tracker.py` line 83, `src/hardware.py` lines 41-62
- Impact: Servo jitter, unpredictable position during CENTER command. Potential for hardware brownout if both threads issue rapid conflicting angle changes.
- Fix approach: Introduce a command queue consumed by `main_loop()` instead of spawning a separate thread. Add a lock to `PanTiltSystem.set_angles()` as a defensive measure.

**`generate_frames()` tight CPU spin loop:**
- Issue: `generate_frames()` in `web/server.py` lines 47-56 has a `while True` loop with `continue` when `shared_encoded_frame is None` -- no sleep, no wait. Burns 100% CPU on one core when no frame is available (during startup, camera failure, or slow processing).
- Files: `web/server.py` lines 47-56
- Impact: CPU starvation on RPi4, thermal issues, reduced performance for the vision pipeline that shares the same 4 cores.
- Fix approach: Add `time.sleep(0.01)` in the `continue` branch, or better, use `threading.Event` to signal new frame availability.

**`attach_servos()` is a no-op stub -- START after STOP is broken:**
- Issue: `attach_servos()` in `src/hardware.py` lines 96-98 is `pass`. After `detach_servos()` (STOP command at `web/server.py` line 114), servos cannot be reattached. The START command (line 111) sets state to SCANNING but servos remain detached -- `set_angles()` sends commands to detached pins, which silently fail.
- Files: `src/hardware.py` lines 96-98, `web/server.py` lines 111-114
- Impact: After STOP -> START sequence, the system appears to work (state updates, HUD shows SCANNING) but servos do not physically move. User must restart the entire application.
- Fix approach: Implement `attach_servos()` by reinitializing `AngularServo` instances, or track detach state and auto-reattach in `set_angles()`.

**`Picamera2` import calls `sys.exit(1)` at module level:**
- Issue: `src/modes/test_tracker.py` lines 41-49 call `sys.exit(1)` if `Picamera2` cannot be imported. This executes at import time, not at runtime.
- Files: `src/modes/test_tracker.py` lines 41-49
- Impact: Any code that imports `src.modes.test_tracker` on a non-RPi system (development laptop, CI) crashes the entire Python process. Prevents running any tests or linters that scan all modules.
- Fix approach: Raise `ImportError` instead of `sys.exit(1)`. Let the caller (`run_test_tracker.py`) decide how to handle missing Picamera2.

## Technical Debt

| Area | Description | Severity | Effort to Fix |
|------|-------------|----------|---------------|
| Hardcoded tolerance | Face recognition tolerance `0.55` hardcoded in `src/vision.py` line 116, not in `src/config.py`. Comment says "standardowo 0.6" but uses 0.55. | Low | 5 min |
| Duplicate PanTiltSystem | `TrackerMachine` (`src/tracker.py:17`) and `MaszynaStanow` (`src/modes/test_tracker.py:203`) each create their own `PanTiltSystem()`. No dependency injection. | Medium | 30 min |
| Duplicate HAAR loading | HAAR cascade loaded independently in `src/vision.py:22` and `src/modes/test_tracker.py:159-163` with different fallback logic. | Low | 15 min |
| Split config constants | `src/modes/test_tracker.py` lines 25-35 define `LORES_WIDTH`, `HAAR_MIN_NEIGHBORS`, `SCAN_AMPLITUDE`, `PID_OUTPUT_LIMIT` etc. as module globals separate from `src/config.py`. Two sources of truth. | Medium | 20 min |
| Global mutable state | `web/server.py` lines 23-28 use module-level globals (`stream`, `vision`, `tracker`, `shared_encoded_frame`) mutated across threads. | Medium | 1 hr |
| Duplicate state machines | `TrackerMachine` (`src/tracker.py`) and `MaszynaStanow` (`src/modes/test_tracker.py`) implement nearly identical PID+state logic independently. Bug fixes in one are not reflected in the other. | Medium | 2 hr |
| Mixed language API | `src/tracker.py` uses English (`logic_tick`, `start_pipeline`), `src/modes/test_tracker.py` uses Polish (`uruchom`, `zatrzymaj`, `wykryj`). Cognitive overhead. | Low | 1 hr |
| No linter/formatter | No `.flake8`, `ruff`, or `pyproject.toml` tool config. Code style varies between files. | Low | 15 min |
| Incomplete `.gitignore` | Missing `__pycache__/`, `*.pyc`, `venv/`, `tmp_faces/`, `*.egg-info`. Only ignores `.gsd/` and OS files. | Low | 5 min |
| PID integral not reset on TRACKING entry | `src/tracker.py` does not reset PID on SCANNING->TRACKING transition. Accumulated integral from scanning may cause initial overshoot. `MaszynaStanow` resets only on SCANNING entry (line 289). | Medium | 15 min |

## Security Concerns

**No authentication on Flask API:**
- Risk: Server binds to `0.0.0.0:5000` (`web/server.py` line 191), exposing all endpoints to the entire local network. Any device on the same WiFi can control servos, upload files, and view the camera feed.
- Files: `web/server.py` line 191, lines 68-89 (upload), lines 99-115 (command)
- Current mitigation: None.
- Recommendations: Add HTTP Basic Auth or a simple API key for command/upload endpoints. At minimum, restrict binding to localhost or add network-level access control.

**Unrestricted file upload (type, size, cleanup):**
- Risk: `/api/upload_target` accepts any file. `secure_filename()` prevents path traversal but does not validate file type, MIME type, or size. No `MAX_CONTENT_LENGTH` set in Flask config. Uploaded files in `tmp_faces/` are never cleaned up.
- Files: `web/server.py` lines 68-89, `src/config.py` line 33
- Current mitigation: `secure_filename()` only.
- Recommendations: Set `app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024`, validate extension against `{'jpg', 'jpeg', 'png'}`, delete previous target on new upload.

**No input validation on `/api/command`:**
- Risk: `request.json` at `web/server.py` line 104 is accessed without checking if content-type is JSON. Malformed requests cause unhandled exceptions (500 errors). No validation that `cmd` is one of the expected values.
- Files: `web/server.py` lines 99-115
- Recommendations: Add try/except around JSON parsing, validate `cmd` against allowlist.

**MJPEG stream in plaintext over WiFi:**
- Risk: Camera feed and all API traffic transmitted without encryption. Anyone on the network can passively view the camera stream.
- Files: `web/server.py` line 191
- Current mitigation: `debug=False` prevents debugger exposure.
- Recommendations: For sensitive deployments, add TLS via reverse proxy (nginx).

## Performance Concerns

**`VideoStream` camera thread holds lock during I/O:**
- Problem: `src/camera.py` lines 42-43 hold `_frame_lock` while calling `self.stream.read()`, which blocks on USB/CSI I/O (potentially 33ms at 30 FPS). During this time, `read()` (line 47) blocks waiting for the lock.
- Files: `src/camera.py` lines 37-48
- Cause: Lock granularity too coarse -- lock protects both I/O and assignment.
- Improvement: Read into local variable first, then acquire lock only for assignment: `grabbed, frame = self.stream.read(); with lock: self.frame = frame`.

**CSRT tracker overhead on RPi4:**
- Problem: `cv2.TrackerCSRT_create()` at `src/vision.py` line 57 is the heaviest OpenCV tracker. Each `tracker.update(frame)` costs 5-15ms on RPi4, consuming 15-45% of the 33ms frame budget.
- Files: `src/vision.py` line 57
- Improvement: Make tracker type configurable. KCF is ~3x faster. Comment on line 57 already acknowledges this.

**`main_loop()` fixed sleep ignores processing time:**
- Problem: `time.sleep(1/config.CAMERA_FPS)` at `web/server.py` line 170 adds a fixed 33ms sleep AFTER processing. If processing takes 20ms, the actual loop period is 53ms (~19 FPS instead of 30).
- Files: `web/server.py` line 170
- Improvement: Measure elapsed time and sleep only the remainder: `sleep(max(0, target_period - elapsed))`.

**Async dlib verification holds lock for entire 200-500ms encode+compare:**
- Problem: `src/vision.py` lines 103-123 hold `_async_lock` during the entire `face_encodings()` + `compare_faces()` operation (200-500ms on RPi4). `load_target_image()` (line 43) is blocked during this time.
- Files: `src/vision.py` lines 102-123
- Improvement: Copy `self.target_encoding` under lock, release, do expensive work, re-acquire only to write result.

**Camera capture thread has no rate limiting:**
- Problem: `VideoStream.update()` at `src/camera.py` lines 37-43 has no sleep between reads. If `stream.read()` returns immediately (buffered frame), this busy-loops at 100% CPU. Contrast: `Picamera2Stream` has `time.sleep(0.01)` at line 135.
- Files: `src/camera.py` lines 37-43

## Reliability Concerns

**No camera failure recovery in main app:**
- Issue: `VideoStream` in `src/camera.py` has zero retry logic. If `stream.read()` starts returning `(False, None)`, the camera thread silently continues reading `None` forever. `main_loop()` skips `None` frames but never attempts reinit.
- Files: `src/camera.py` lines 37-43, `web/server.py` lines 136-138
- Contrast: `Picamera2Stream` has proper retry logic with `CAMERA_MAX_RETRIES` and reinit (`src/modes/test_tracker.py` lines 107-131).
- Fix: Port the retry pattern from `Picamera2Stream` to `VideoStream`.

**`smooth_move_to()` can block indefinitely:**
- Issue: The `while` loop in `src/hardware.py` line 74 has no timeout or max iteration count. Floating-point precision edge cases could prevent convergence.
- Files: `src/hardware.py` lines 64-94
- Impact: During safe-start or CENTER command, entire system hangs.
- Fix: Add `max_steps = 300` guard or a wall-clock timeout (e.g., 10 seconds).

**Signal handler not thread-safe:**
- Issue: Signal handlers at `web/server.py` lines 186-187 call `shutdown()` which accesses global `tracker` and `stream` that may be mid-operation on other threads.
- Files: `web/server.py` lines 36-45, 186-187
- Fix: Set a flag in the handler; let main thread handle cleanup.

**Race condition in `_verifying_task_active` flag:**
- Issue: In `src/vision.py` lines 125-129, check-and-set of `_verifying_task_active` is not atomic. Two rapid calls can both see `False` and spawn duplicate verification threads.
- Files: `src/vision.py` lines 125-129
- Fix: Guard the flag check with `_async_lock`, or use `threading.Event`.

**No daemon thread watchdog:**
- Issue: All processing threads are daemons (`web/server.py` line 182). If `main_loop` crashes with an unhandled exception, Flask keeps serving but camera feed freezes and servos stop. No health check or restart mechanism.
- Files: `web/server.py` line 182
- Fix: Wrap `main_loop()` body in try/except with automatic restart or error state surfacing.

## Hardware-Specific Risks

**Brownout from direct servo jumps:**
- Risk: `set_angles()` moves servos instantly. Large deltas (e.g., SCANNING at -60 then face detected at +30) draw current spikes from MG-90S servos that can brownout RPi4.
- Files: `src/hardware.py` lines 41-62
- Current mitigation: PID output limits cap correction at +/-10 deg/tick. `smooth_move_to()` used at startup.
- Remaining risk: State transitions (SCANNING->TRACKING) bypass smooth movement. `handle_command('START')` at `web/server.py` line 111 does not call `smooth_move_to()`.

**Camera ribbon cable damage from excessive tilt:**
- Risk: Tilt limited to +/-30 degrees in `src/config.py` lines 20-21. If config is modified carelessly, wider angles could strain the ribbon cable.
- Files: `src/config.py` lines 20-21, `src/hardware.py` lines 49-50
- Current mitigation: Software clamping in `set_angles()`. No hardware hard stops documented.

**No thermal monitoring:**
- Risk: RPi4 running continuous OpenCV + dlib + Flask + PWM can reach thermal throttle (80-85C) in enclosed cases.
- Files: None -- no thermal monitoring exists.
- Recommendations: Add periodic `vcgencmd measure_temp` check; surface in `/api/state`.

**pigpiod failure silently enters mock mode:**
- Risk: If `pigpiod` daemon is not running, `PanTiltSystem` enters mock mode with only a log warning (`src/hardware.py` lines 27-36). No visible indicator in web UI. User may not realize servos are inactive.
- Files: `src/hardware.py` lines 5-11, 27-36
- Recommendations: Surface mock mode in `/api/state` response and display a warning banner in `web/templates/index.html`.

**No servo stall detection:**
- Risk: If a servo physically stalls (blocked), PID increases correction up to output limits (+/-10 deg/tick) indefinitely, drawing continuous current.
- Files: `src/tracker.py` lines 59-83, `src/hardware.py` lines 41-62
- Mitigation: PID output limits cap correction magnitude. No current monitoring available on standard RPi GPIO.

## Test Coverage Gaps

**No automated tests exist:**
- What's not tested: Everything. Zero test files in the entire repository.
- Risk: Any refactor (unifying camera backends, consolidating config, fixing race conditions) can silently break functionality. PID tuning, state machine transitions, vision pipeline -- all verified only by manual observation on physical hardware.
- Priority: High
- Recommended first tests:
  - `TrackerMachine` state transitions (`src/tracker.py`) -- pure logic, mockable hardware
  - `MaszynaStanow` state transitions (`src/modes/test_tracker.py`) -- pure logic
  - `PanTiltSystem` clamping and soft limits (`src/hardware.py`) -- runs in mock mode
  - `DetekcjaTwarzy` streak filter (`src/modes/test_tracker.py`) -- needs only numpy array input
  - `HybridVision.process_frame()` with mocked HAAR results (`src/vision.py`)

## Dependencies at Risk

**face_recognition / dlib maintenance status:**
- Risk: `face_recognition==1.3.0` (last release 2022) is in maintenance mode with no active development. `dlib==19.24.2` compiles from source on RPi4 (1-2 hours) and may fail with newer compilers or ARM toolchains.
- Files: `requirements.txt`
- Impact: Future Raspberry Pi OS upgrades may break dlib compilation.
- Migration plan: Consider `insightface` or `mediapipe` for face recognition -- better ARM support and active maintenance.

**Incomplete `.gitignore`:**
- Risk: `.gitignore` only covers `.gsd/` state files and OS artifacts. Missing: `__pycache__/`, `*.pyc`, `venv/`, `tmp_faces/`, `*.egg-info`, `*.so`, `.env`. Python bytecode and uploaded face images can be accidentally committed.
- Files: `.gitignore`
- Fix: Add standard Python gitignore entries plus project-specific exclusions.

## Recommendations

**Priority 1 -- Fix before next deployment:**
1. Fix `generate_frames()` CPU spin -- add sleep or event wait (`web/server.py` line 52)
2. Implement `attach_servos()` or auto-reattach logic (`src/hardware.py` line 96)
3. Fix CENTER command race condition -- use command queue (`web/server.py` line 109)
4. Replace `sys.exit(1)` with `ImportError` in test_tracker Picamera2 import (`src/modes/test_tracker.py` line 49)

**Priority 2 -- Address soon:**
5. Add camera failure recovery to `VideoStream` (`src/camera.py`)
6. Fix `VideoStream` lock scope -- do not hold lock during camera I/O (`src/camera.py` lines 42-43)
7. Add file upload validation -- size limit, extension allowlist, cleanup (`web/server.py`)
8. Add timeout to `smooth_move_to()` (`src/hardware.py` line 74)
9. Consolidate all config constants into `src/config.py`

**Priority 3 -- Improve quality:**
10. Add unit tests for state machines and hardware clamping
11. Update `.gitignore` with Python standard entries and `tmp_faces/`
12. Fix `main_loop()` sleep to account for processing time (`web/server.py` line 170)
13. Surface mock mode and system health in `/api/state` and web UI
14. Add input validation on `/api/command` endpoint

**Priority 4 -- Long-term:**
15. Add basic auth to Flask endpoints
16. Evaluate dlib replacement for better ARM support
17. Add thermal monitoring
18. Unify camera backends behind a common ABC
19. Unify duplicate state machines into single configurable class

---

*Concerns audit: 2026-03-29*
