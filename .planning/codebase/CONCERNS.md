# Technical Concerns

**Analysis Date:** 2026-03-27

## Architecture Concerns

**Dual camera backends with no shared interface:**
- Issue: `src/camera.py` uses OpenCV `VideoCapture`, while `src/modes/test_tracker.py` uses `Picamera2Stream` -- two completely separate camera implementations with different APIs (`read()` vs `odczytaj()`, different init/cleanup patterns).
- Files: `src/camera.py`, `src/modes/test_tracker.py:51-140`
- Impact: Any camera-related fix must be applied twice. Adding a third backend (e.g., libcamera via OpenCV) requires yet another implementation. The two backends have vastly different error handling -- `Picamera2Stream` has retry logic with re-initialization (lines 96-119), while `VideoStream` has none.
- Fix approach: Extract a common `CameraBackend` ABC with `start()`, `read()`, `stop()` methods. Both implementations inherit from it. Logic loop code accepts the ABC.

**Duplicated state machine and PID logic:**
- Issue: `src/tracker.py` (`TrackerMachine`) and `src/modes/test_tracker.py` (`MaszynaStanow`) implement nearly identical state machines and PID tracking logic independently.
- Files: `src/tracker.py:59-83` vs `src/modes/test_tracker.py:249-268`
- Impact: Bug fixes or PID tuning changes in one are not reflected in the other. The two machines have subtly different state transitions (e.g., `MaszynaStanow` uses `STATE_TARGET_LOST` as a transient state; `TrackerMachine` does not).
- Fix approach: Unify into a single configurable state machine class, parameterized for whether dlib verification is used.

**Global mutable state in `web/server.py`:**
- Issue: `stream`, `vision`, `tracker`, `shared_encoded_frame` are module-level globals mutated across threads. Flask routes access these globals directly.
- Files: `web/server.py:23-28`
- Impact: Impossible to run multiple instances, difficult to test, hard to reason about initialization order. The `init_event` guard (line 28-33) only protects API routes, not `/video_feed` or `/`.
- Fix approach: Wrap shared state in a context class; pass to Flask via `app.config` or a Flask extension pattern.

## Code Quality Issues

**Face recognition tolerance hardcoded outside config:**
- Issue: `tolerance=0.55` is hardcoded in `src/vision.py:116` instead of being a constant in `src/config.py`.
- Files: `src/vision.py:116`, `src/config.py`
- Impact: Tuning face recognition sensitivity requires editing vision.py source code rather than the centralized config. The comment on line 115 says "standardowo tolerancja 0.6" but the actual value is 0.55 -- this discrepancy suggests ad-hoc tuning without documentation.
- Fix approach: Add `FACE_RECOGNITION_TOLERANCE = 0.55` to `src/config.py` and reference it in `vision.py`.

**Test tracker module-level constants shadow config:**
- Issue: `src/modes/test_tracker.py` defines its own `LORES_WIDTH`, `LORES_HEIGHT`, `HAAR_MIN_NEIGHBORS`, `HAAR_MIN_SIZE`, `PID_OUTPUT_LIMIT`, `SCAN_AMPLITUDE`, `SCAN_FREQUENCY` as module-level constants (lines 25-33) instead of using `src/config.py`.
- Files: `src/modes/test_tracker.py:25-33`, `src/config.py`
- Impact: Two sources of truth for system parameters. Changing PID output limits in one place does not affect the other. Camera resolution differs (320x240 vs 640x480) without clear documentation of why.
- Fix approach: Consolidate all tuning constants into `src/config.py` with clear section headers for each mode.

**Stub methods in hardware.py:**
- Issue: `attach_servos()` at `src/hardware.py:88-90` is a no-op stub with a `pass` body. Comment says "Opcjonalne jesli API to umozliwia".
- Files: `src/hardware.py:88-90`
- Impact: After calling `detach_servos()` (e.g., via STOP command at `web/server.py:114`), there is no way to reattach without re-instantiating `PanTiltSystem`. The START command at line 111 sets state to SCANNING but servos remain detached.
- Fix approach: Implement `attach_servos()` properly using gpiozero's API, or remove the method and handle re-initialization differently.

## Security Concerns

**No authentication on Flask API:**
- Risk: The server binds to `0.0.0.0:5000` (line 191 of `web/server.py`), exposing all endpoints to the entire local network. Any device on the same WiFi can control servos, upload arbitrary images, and view the camera feed.
- Files: `web/server.py:191`, `web/server.py:68-89` (upload), `web/server.py:99-115` (command)
- Current mitigation: None.
- Recommendations: Add at minimum HTTP Basic Auth or a simple API key. For the upload endpoint, add file size limits and stricter MIME type validation beyond `secure_filename()`.

**Unrestricted file upload:**
- Risk: `/api/upload_target` accepts any file. `secure_filename()` prevents path traversal but does not validate file type or size. An attacker could upload large files to exhaust disk space on the SD card.
- Files: `web/server.py:68-89`
- Current mitigation: `secure_filename()` only.
- Recommendations: Add `MAX_CONTENT_LENGTH` to Flask config. Validate MIME type (only accept image/jpeg, image/png). Delete old uploads.

**Flask debug mode disabled but no HTTPS:**
- Risk: Camera feed and all API traffic transmitted in plaintext over WiFi. Anyone on the network can sniff the MJPEG stream.
- Files: `web/server.py:191`
- Current mitigation: `debug=False` prevents debugger exposure.
- Recommendations: For sensitive deployments, add TLS via a reverse proxy (nginx) or use Flask-Talisman.

## Performance Risks

**`generate_frames()` busy-loops when no frame is available:**
- Problem: The MJPEG generator at `web/server.py:47-56` has `continue` when `shared_encoded_frame is None`, creating a tight busy loop with no sleep or wait mechanism.
- Files: `web/server.py:47-56`
- Cause: No `threading.Event` or `threading.Condition` to signal new frame availability.
- Improvement path: Use `threading.Event` set by `main_loop()` after encoding a frame; `generate_frames()` waits on it with a timeout. Alternatively, add `time.sleep(0.001)` as a minimal fix.

**Camera thread in `VideoStream` busy-loops:**
- Problem: `src/camera.py:37-43` -- the `update()` method has no sleep between frame reads. On a system where `stream.read()` returns immediately (cached frame), this consumes 100% of one CPU core.
- Files: `src/camera.py:37-43`
- Cause: No rate limiting in the capture loop. Contrast with `Picamera2Stream` which has `time.sleep(0.01)` at line 123.
- Improvement path: Add a small sleep (e.g., `time.sleep(0.001)`) or use `stream.grab()` + `stream.retrieve()` pattern which blocks on actual frame arrival.

**CSRT tracker is heavyweight for RPi4:**
- Problem: `cv2.TrackerCSRT_create()` at `src/vision.py:57` is the most CPU-intensive OpenCV tracker. Each `tracker.update(frame)` call costs 5-15ms on RPi4.
- Files: `src/vision.py:57`
- Cause: CSRT was chosen for accuracy, but comment acknowledges KCF as alternative.
- Improvement path: Make tracker type configurable in `src/config.py`. Consider KCF for scenarios where FPS matters more than tracking precision.

**Async dlib verification holds `_async_lock` for entire encode+compare cycle:**
- Problem: In `src/vision.py:103-123`, the `_async_lock` is held during the entire `face_recognition.face_encodings()` + `compare_faces()` operation (200-500ms on RPi4). During this time, `load_target_image()` (which also acquires `_async_lock` at line 43) is blocked.
- Files: `src/vision.py:102-123`
- Cause: Lock granularity is too coarse.
- Improvement path: Copy `self.target_encoding` under lock, then release lock before the expensive encoding/comparison, re-acquire only to write `self.target_verified`.

## Reliability Risks

**Race condition in `_verifying_task_active` flag:**
- Problem: In `src/vision.py:125-129`, the check `if not self._verifying_task_active` and the set `self._verifying_task_active = True` are not atomic. Two calls to `trigger_async_verification()` in rapid succession could both see `False` and start two concurrent verification threads.
- Files: `src/vision.py:125-129`
- Trigger: Fast HAAR detection re-initializing tracker on consecutive frames before the first verification thread acquires the lock.
- Workaround: In practice, the `_async_lock` inside `heavy_task` serializes them, but two threads are still spawned unnecessarily.
- Fix: Use the `_async_lock` to guard the flag check, or use `threading.Event` instead.

**No camera disconnect recovery in `VideoStream`:**
- Problem: `src/camera.py` has zero error handling for camera disconnection. If `stream.read()` starts returning `(False, None)`, the `grabbed` flag is set to False but nothing acts on it. The `main_loop` in `web/server.py:136` checks `frame is None` and sleeps, but never attempts re-initialization.
- Files: `src/camera.py:37-43`, `web/server.py:134-138`
- Contrast: `Picamera2Stream` in `src/modes/test_tracker.py:77-119` has proper retry logic with re-initialization.
- Fix: Port the retry pattern from `Picamera2Stream` to `VideoStream`, or unify backends.

**`smooth_move_to()` can block indefinitely:**
- Problem: `src/hardware.py:66` -- the `while` loop has no timeout or maximum iteration count. If due to floating-point precision `abs(self.pan_angle - target_pan) > step` never becomes False, the function loops forever.
- Files: `src/hardware.py:56-86`
- Trigger: Unlikely with current step=1.0 and integer targets, but possible with fractional targets.
- Fix: Add a maximum iteration count (e.g., `max_steps = 300`) as a safety valve.

**Signal handler calls `shutdown()` which is not thread-safe:**
- Problem: `web/server.py:186-187` -- signal handlers call `shutdown()` which accesses globals (`tracker`, `stream`) that may be in an inconsistent state. Signal handlers can fire at any point during execution.
- Files: `web/server.py:36-45`, `web/server.py:186-187`
- Fix: Set a shutdown flag in the signal handler; check the flag in the main loop. Or use `atexit` for cleanup.

**START command after STOP does not reattach servos:**
- Problem: The STOP command at `web/server.py:113-114` calls `detach_servos()`, but the START command at line 111 only changes state to SCANNING. The servos remain detached, so `set_angles()` calls in scanning/tracking are silently no-ops (angles update in software only).
- Files: `web/server.py:110-114`, `src/hardware.py:88-90`
- Fix: Implement `attach_servos()` and call it in the START handler.

**CENTER command race condition with main_loop:**
- Problem: At `web/server.py:108-109`, CENTER sets state to IDLE and spawns a thread for `smooth_move_to()`. Meanwhile, `main_loop` continues calling `tracker.logic_tick()`. If state changes from IDLE before smooth_move completes (e.g., user sends START), two threads control servos simultaneously.
- Files: `web/server.py:106-109`
- Fix: Add a "moving" flag that `logic_tick` respects, or queue commands to be processed by `main_loop`.

## Technical Debt

**No test suite:**
- Issue: Zero automated tests exist. Verification is purely empirical (manual observation, HTTP responses, screenshots).
- Impact: Regressions go undetected. Refactoring (e.g., unifying camera backends) is risky without a safety net.
- Fix approach: Start with unit tests for PID calculations and state machine transitions (pure logic, no hardware needed). Add integration tests with mocked camera frames.

**No linter or formatter configured:**
- Issue: No `.eslintrc`, `.flake8`, `pyproject.toml [tool.ruff]`, or similar configuration. Code style varies between files (Polish vs English function names, inconsistent spacing).
- Impact: Code review friction; inconsistency between `src/tracker.py` (English API) and `src/modes/test_tracker.py` (Polish API).
- Fix approach: Add `ruff` or `flake8` config. Run formatter once to normalize.

**`__pycache__` directories not in `.gitignore`:**
- Issue: Multiple `__pycache__` directories appear in `git status` as untracked. These should never be committed.
- Files: `src/__pycache__/`, `src/modes/__pycache__/`
- Fix approach: Add `__pycache__/` to `.gitignore`.

**Mixed language API surface:**
- Issue: `src/tracker.py` and `web/server.py` use English method names (`logic_tick`, `start_pipeline`). `src/modes/test_tracker.py` uses Polish names (`uruchom`, `zatrzymaj`, `odczytaj`, `wykryj`). `src/config.py` uses English constants with Polish comments.
- Impact: Cognitive overhead when navigating between modules. New contributors must understand both languages.
- Fix approach: Standardize on English for all public API names; keep Polish only in comments and log messages.

## Hardware/Platform Risks

**Servo brownout on direct jump at startup:**
- Risk: If `smooth_move_to()` is bypassed or fails, directly setting servo angles from an unknown position can draw enough current to brown out the RPi4, causing a reboot.
- Files: `src/hardware.py:41-54` (set_angles), `src/tracker.py:40` (smooth_move_to at startup)
- Current mitigation: `start_pipeline()` always calls `smooth_move_to()` first. But `handle_command('START')` at `web/server.py:111` does not call `smooth_move_to()`.
- Recommendations: Always call `smooth_move_to()` when transitioning from detached/idle to active.

**No hardware watchdog for servo stall:**
- Risk: If a servo physically stalls (blocked by obstacle), the PID controller will increase correction, potentially driving current beyond safe limits.
- Files: `src/tracker.py:59-83`, `src/hardware.py:41-54`
- Current mitigation: PID output limits cap correction at +/-10 degrees per tick. Servo angle soft limits in `set_angles()`.
- Recommendations: Add current monitoring if hardware supports it, or add a maximum angular velocity check.

**Picamera2 hard dependency in test_tracker:**
- Risk: `src/modes/test_tracker.py:41-48` calls `sys.exit(1)` if Picamera2 cannot be imported. This crashes the entire Python process, not just the test tracker module.
- Files: `src/modes/test_tracker.py:41-48`
- Impact: Importing `src.modes` on a non-RPi system (e.g., development laptop) kills the process.
- Fix approach: Use lazy import or raise `ImportError` instead of `sys.exit(1)`. Let the caller decide how to handle missing Picamera2.

**Mock mode silently degrades:**
- Risk: When `PIGPIO_AVAILABLE` is False, `PanTiltSystem` enters mock mode silently. All angle calculations proceed normally but no physical movement occurs. This is intentional for development, but in production on RPi4, a failed pigpio connection (e.g., daemon not started) results in a system that appears to work but does nothing.
- Files: `src/hardware.py:5-11`, `src/hardware.py:27-36`
- Current mitigation: Log warning at import time. Log message at `__init__`.
- Recommendations: Add a `/api/state` field indicating mock vs real hardware. Consider failing loudly in production mode.

---

*Concerns audit: 2026-03-27*
