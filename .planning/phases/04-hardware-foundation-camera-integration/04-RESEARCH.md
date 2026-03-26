# Phase 4: Hardware Foundation & Camera Integration - Research

**Researched:** 2026-03-26
**Domain:** Picamera2 threaded capture, pigpio servo safe-start, graceful shutdown — RPi OS Bookworm 64-bit
**Confidence:** HIGH (project code directly readable; Picamera2 API confirmed MEDIUM via training knowledge — needs on-device verification)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Camera mock mode:**
- Picamera2 is **required** — if `from picamera2 import Picamera2` fails, print error and `sys.exit(1)`. No blank-frame mock mode.
- Servo mock mode remains **independent** — if pigpiod is not running, PanTiltSystem degrades to mock (existing hardware.py behavior). Camera + mock servos is a valid test configuration.
- Exit mechanism on missing Picamera2: Claude's discretion (logger error + sys.exit or RuntimeError).

**Frame preview:**
- Primary display: `cv2.imshow()` window for local monitor on RPi.
- **Headless fallback**: Try `cv2.imshow()` on first frame — if it throws (no DISPLAY), switch to headless log-only mode for the rest of the run. No CLI flag needed.
- Window size: **upscale to 640x480** (2x) for better visibility on desktop monitor.
- Headless logging granularity: Claude's discretion (periodic summary or state transitions only).

**Failure handling:**
- **Mid-run camera failure**: Retry camera re-initialization up to 3 times, then trigger clean shutdown. Handles transient Picamera2 errors.
- **No pigpiod**: Run with servo mock mode — camera pipeline still testable without hardware servos.
- **Startup**: If Picamera2 import fails → error and exit. If Picamera2 starts but first frame fails → retry logic applies.

**Capture threading:**
- **Lock-protected single frame** (`threading.Lock` + single `np.ndarray` variable) — matches existing VideoStream pattern in `camera.py`.
- **Lores stream**: `capture_array("lores")` at 320x240 BGR888 — lower latency, configured at Picamera2 init time.
- Capture runs in a **daemon thread** — dies with main process, consistent with project convention.

### Claude's Discretion
- Exact exit mechanism for missing Picamera2 (logger + sys.exit vs RuntimeError)
- Headless mode logging granularity (periodic summary vs state-change-only)
- Camera retry delay between attempts
- Thread sleep interval in capture loop

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HW-01 | System performs safe startup — servos move incrementally to neutral (0,0) via smooth_move_to before any loop begins | `smooth_move_to()` exists in `src/hardware.py` and is called in `MaszynaStanow.inicjalizuj()` — needs verification it is called BEFORE the main loop, and that shutdown also returns to neutral before detach |
| HW-02 | Picamera2 captures frames at 320x240 BGR888 via native libcamera on Bookworm 64-bit | Skeleton uses `create_video_configuration(lores={"size": (320,240), "format": "BGR888"})` + `capture_array("lores")` — correct pattern; needs mock mode removal per CONTEXT.md |
| HW-03 | System shuts down gracefully on Ctrl+C / SIGTERM — camera released, servos detached, no resource leaks | Signal handling wired in `run_test_tracker.py`; `zatrzymaj()` stops camera and calls `detach_servos()` — but is missing `smooth_move_to(0,0)` before detach (Pitfall 10) |
| HW-04 | Test tracker runs as standalone script (run_test_tracker.py) — no Flask, no modification to existing src/ files | Entry point exists at project root, imports only `src.modes.test_tracker`; no Flask imports present; `src/hardware.py` and `src/config.py` are read-only imports |
</phase_requirements>

---

## Summary

Phase 4 proves safe servo startup and Picamera2 frame delivery — the two prerequisites for all subsequent PID and vision work. The good news: a working skeleton already exists at `src/modes/test_tracker.py` and `run_test_tracker.py`. The structure, threading model, state machine outline, Picamera2 configuration, and signal handling are all present. Phase 4 is therefore a **targeted completion and correction** task, not a from-scratch build.

Four gaps exist between the skeleton and the locked CONTEXT.md decisions. First, the existing code has a Picamera2 mock mode (blank grey frames when Picamera2 is unavailable) — CONTEXT.md explicitly requires Picamera2 to be mandatory and exit via `sys.exit(1)` on import failure. Second, the preview window shows the native 320x240 frame; CONTEXT.md requires 2x upscale to 640x480 with headless fallback. Third, there is no camera retry logic on mid-run failure. Fourth, `zatrzymaj()` calls `detach_servos()` without first calling `smooth_move_to(0,0)`, which violates the brownout safety requirement (Pitfall 10 from PITFALLS.md).

The success criteria are all empirically verifiable on RPi4: no brownout on startup, FPS printed without error, clean Ctrl+C exit with no leftover libcamera process, and `git diff src/` showing zero changes.

**Primary recommendation:** Treat Phase 4 as four targeted fixes to an existing skeleton. Do not rewrite — patch the four gaps identified above, then run the four success-criteria checks sequentially.

---

## Discovery: Skeleton Code Already Exists

This is the most important finding for the planner. Both files targeted by Phase 4 are already present:

| File | Status | What Exists |
|------|--------|-------------|
| `run_test_tracker.py` | EXISTS — correct | Signal handlers (SIGINT/SIGTERM), `try/finally`, logging setup, calls `tracker.zatrzymaj()` |
| `src/modes/__init__.py` | EXISTS — correct | Empty file, package initialized |
| `src/modes/test_tracker.py` | EXISTS — skeleton, incomplete | `Picamera2Stream`, `DetekcjaTwarzy`, `MaszynaStanow`, `TestTracker` classes all present |

The planner MUST NOT plan tasks that create these files from scratch. Plans should patch specific gaps only.

---

## Gap Analysis: Skeleton vs CONTEXT.md Decisions

These are the four concrete deltas that Phase 4 must close:

### Gap 1: Mock camera mode must become hard exit (HW-02, HW-03)

**Current behavior in `test_tracker.py` lines 37-43:**
```python
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    logger.warning("picamera2 niedostępne. Tryb MOCK kamery (puste klatki).")
```

Then `Picamera2Stream.__init__` sets `self._mock_mode = not PICAMERA2_AVAILABLE` and `_petla_przechwytywania()` produces blank grey frames in mock mode.

**Required behavior (CONTEXT.md Locked Decision):** If `from picamera2 import Picamera2` fails → logger error + `sys.exit(1)`. No mock frames. No silent fallback.

**Fix scope:** Replace the `try/except ImportError` block at module level; remove `_mock_mode` branch from `Picamera2Stream`. Servo mock mode in `hardware.py` is independent and correct — do not touch it.

### Gap 2: Missing 2x upscale and headless fallback for cv2.imshow (HW-02)

**Current behavior:** `cv2.imshow("ARIES-LITE Test Tracker", klatka)` shows the raw 320x240 frame. No resize. No headless detection.

**Required behavior (CONTEXT.md Locked Decision):**
- Upscale frame to 640x480 before display: `cv2.resize(klatka, (640, 480), interpolation=cv2.INTER_NEAREST)`
- On first `cv2.imshow()` call: if it raises an exception → switch `self._headless = True` for the rest of the run
- In headless mode: skip `cv2.imshow()` and `cv2.waitKey()`; log at intervals (Claude's discretion on granularity)

**Fix scope:** Modify `TestTracker.uruchom()` loop — add resize before imshow, wrap first imshow in try/except, track `_headless` flag.

### Gap 3: Missing camera retry on mid-run failure (HW-03)

**Current behavior:** No retry. If `capture_array("lores")` raises during the capture thread, the exception propagates unhandled and the thread dies silently. Main loop continues reading `None` frames.

**Required behavior (CONTEXT.md Locked Decision):** Retry camera re-initialization up to 3 times on mid-run failure, then trigger clean shutdown.

**Fix scope:** Wrap `self._picam2.capture_array("lores")` in a try/except inside `_petla_przechwytywania()`. On exception: increment retry counter, attempt `stop()/close()` + re-init with `Picamera2()`, wait (delay at Claude's discretion). After 3 failures: set `self._running = False` and call back to stop the main loop.

### Gap 4: Missing smooth_move_to(0,0) before detach_servos() on shutdown (HW-01, HW-03)

**Current behavior in `TestTracker.zatrzymaj()` line 316-322:**
```python
def zatrzymaj(self) -> None:
    self._running = False
    self.kamera.stop()
    self.maszyna.hardware.detach_servos()   # <-- directly detaches, no return to neutral
    cv2.destroyAllWindows()
    logger.info("TestTracker zatrzymany — zasoby zwolnione.")
```

**Required behavior (PITFALLS.md Pitfall 10, CLAUDE.md):** Before `detach_servos()`, call `smooth_move_to(0, 0)` to return servos to neutral. Direct detach from an extreme angle causes the servo to fall to its mechanical stop — same brownout risk as Pitfall 1.

**Fix scope:** Add `self.maszyna.hardware.smooth_move_to(0, 0)` immediately before `self.maszyna.hardware.detach_servos()` in `zatrzymaj()`.

---

## Standard Stack

### Core (all already in requirements.txt)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| picamera2 | system pkg (≥0.3.x) | Picamera2 capture via native libcamera | Only correct camera API on RPi OS Bookworm 64-bit; V4L2 is unavailable for Pi Camera |
| opencv-python-headless | 4.8.1.78 (pinned) | cv2.imshow, cv2.resize, cv2.CascadeClassifier | Already validated in v1.5; headless avoids GUI deps |
| gpiozero | 2.0 | AngularServo for servo PWM | Used in PanTiltSystem — direct reuse, do not replace |
| pigpio | 1.78 | Hardware-level PWM via PiGPIOFactory | Only library providing true H-PWM on RPi4 BCM2711 |
| simple-pid | 2.0.0 | PID controllers for pan/tilt | Already in requirements.txt; API stable at 2.x |
| numpy | 1.26.0 | ndarray frame buffers | Transitive dep of cv2 and picamera2 |

**Installation note:** picamera2 must be installed as system package on the RPi4:
```bash
sudo apt install -y python3-picamera2
python3 -m venv venv --system-site-packages
source venv/bin/activate
```
A standard venv (without `--system-site-packages`) cannot find picamera2.

**OpenCV aarch64 caveat (LOW confidence — needs on-device verification):** The pinned `opencv-python-headless==4.8.1.78` may be armhf-only. If `import cv2` fails on Bookworm 64-bit, remove the version pin or install system OpenCV (`sudo apt install python3-opencv`).

### Reuse vs New

| Component | Decision | File |
|-----------|----------|------|
| `PanTiltSystem` | REUSE directly — no changes | `src/hardware.py` |
| `src.config` | REUSE directly — no changes | `src/config.py` |
| `VideoStream` | DO NOT USE — V4L2 incompatible with Bookworm | `src/camera.py` |
| `TrackerMachine` | DO NOT IMPORT — entangled with dlib | `src/tracker.py` |
| `HybridVision` | DO NOT IMPORT — entangled with CSRT + dlib | `src/vision.py` |

---

## Architecture Patterns

### Existing Project Structure (do not change)

```
src/
├── config.py            (EXISTING — unchanged, read-only import)
├── hardware.py          (EXISTING — unchanged, PanTiltSystem reused)
├── modes/
│   ├── __init__.py      (EXISTING — empty, already present)
│   └── test_tracker.py  (EXISTING skeleton — targeted patches only)
run_test_tracker.py      (EXISTING — correct, no changes needed)
```

### Pattern 1: Picamera2 lores stream with daemon capture thread

**What:** `create_video_configuration` with a `lores` sub-stream at 320x240 BGR888, captured in a background daemon thread. Main loop reads `latest_frame` without blocking on camera I/O.

**Already implemented** in `Picamera2Stream`. The pattern is correct — only the mock-mode removal is needed.

```python
# Source: ARCHITECTURE.md + existing src/modes/test_tracker.py
video_config = self._picam2.create_video_configuration(
    lores={"size": (self._width, self._height), "format": "BGR888"}
)
self._picam2.configure(video_config)
self._picam2.start()
# ... daemon thread calls self._picam2.capture_array("lores")
```

**Why lores stream:** Lower latency than `main` stream for real-time control loop; configured at init time so no per-frame conversion needed.

### Pattern 2: try/finally camera lifecycle (Picamera2 two-step teardown)

**What:** Picamera2 requires explicit `stop()` then `close()` — garbage collection is not reliable. The existing `Picamera2Stream.stop()` already has the correct pattern.

```python
# Source: PITFALLS.md Pitfall 2 + existing test_tracker.py lines 99-103
if self._picam2 is not None:
    try:
        self._picam2.stop()
    finally:
        self._picam2.close()
```

**Already correct** — no changes needed to this specific block.

### Pattern 3: Headless display detection via try/except on first frame

**What:** Do not check `DISPLAY` env var (unreliable on RPi). Instead, attempt `cv2.imshow()` on the first display cycle and catch the resulting `cv2.error` exception. Set `_headless = True` if it raises; skip display for all subsequent frames.

```python
# New code for TestTracker.uruchom()
if not self._headless:
    wyswietlana = cv2.resize(klatka, (640, 480), interpolation=cv2.INTER_NEAREST)
    try:
        cv2.imshow("ARIES-LITE Test Tracker", wyswietlana)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    except cv2.error:
        logger.info("Brak wyświetlacza — tryb headless (tylko logi)")
        self._headless = True
        cv2.destroyAllWindows()
```

**Why try/except not DISPLAY check:** CONTEXT.md explicitly chose try/catch over env var. Also: on some RPi setups with VNC, DISPLAY is set but cv2.imshow still fails.

### Pattern 4: Safe shutdown sequence (enforced order)

**What:** Specific ordering in `zatrzymaj()` prevents Pitfall 10 (servo falls on detach) and Pitfall 2 (camera lock):

```
1. self._running = False          # stop main loop
2. self.kamera.stop()             # stop capture thread, then picam2.stop() + picam2.close()
3. self.maszyna.hardware.smooth_move_to(0, 0)   # return to neutral BEFORE detach
4. self.maszyna.hardware.detach_servos()         # release PWM
5. cv2.destroyAllWindows()        # close display
```

**Currently missing step 3.** This is a required fix.

### Pattern 5: Camera retry on mid-run failure

**What:** Wrap `capture_array` in a retry loop inside `_petla_przechwytywania`. On exception: attempt up to 3 re-initializations before setting `_running = False`.

```python
# New code inside Picamera2Stream._petla_przechwytywania()
_retry_count = 0
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds (Claude's discretion)

while self._running:
    try:
        klatka = self._picam2.capture_array("lores")
        _retry_count = 0  # reset on success
    except Exception as e:
        _retry_count += 1
        logger.error(f"Błąd kamery ({_retry_count}/{MAX_RETRIES}): {e}")
        if _retry_count >= MAX_RETRIES:
            logger.error("Kamera niedostępna — zatrzymanie systemu")
            self._running = False
            break
        # Attempt re-init
        try:
            self._picam2.stop()
            self._picam2.close()
        except Exception:
            pass
        time.sleep(RETRY_DELAY)
        try:
            self._picam2 = Picamera2()
            video_config = self._picam2.create_video_configuration(
                lores={"size": (self._width, self._height), "format": "BGR888"}
            )
            self._picam2.configure(video_config)
            self._picam2.start()
            logger.info("Kamera ponownie uruchomiona po błędzie")
        except Exception as reinit_err:
            logger.error(f"Ponowna inicjalizacja nieudana: {reinit_err}")
        continue
    with self._lock:
        self._frame = klatka
    time.sleep(0.01)
```

### Anti-Patterns to Avoid

- **Picamera2 mock frames for missing picamera2 import:** CONTEXT.md explicitly forbids this. Fail fast with `sys.exit(1)`.
- **Calling `set_angles(0, 0)` directly in `__init__` or on cleanup:** Bypass of `smooth_move_to` causes brownout. Always use `smooth_move_to`.
- **`detach_servos()` without prior `smooth_move_to(0, 0)`:** Servo falls to mechanical stop (current spike risk). See Pitfall 10.
- **Importing `TrackerMachine` or `HybridVision`:** Brings in dlib/face_recognition as transitive deps. Phase 4 does not use vision or PID.
- **cv2.VideoCapture for Pi Camera on Bookworm:** V4L2 bridge is unavailable. Only Picamera2 works.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Servo safe startup | Custom PWM ramping | `PanTiltSystem.smooth_move_to()` in `src/hardware.py` | Already exists, tested, handles edge cases and soft limits |
| Camera lock on exit | Custom fd/socket cleanup | `picam2.stop()` + `picam2.close()` two-step | Picamera2 API owns the libcamera IPC lifecycle |
| Thread-safe frame sharing | `queue.Queue` or event system | `threading.Lock` + single `np.ndarray` (already in skeleton) | Simpler, lower overhead, already implemented in pattern matching `camera.py` |
| PID integral windup prevention | Custom clamping logic | `simple_pid` output_limits + `pid.reset()` on state transition | Already configured in `MaszynaStanow.__init__` |
| Headless detection | Checking `DISPLAY` env var or `os.environ` | `try/except cv2.error` on first `imshow` | More reliable across RPi display configurations; chosen by user in CONTEXT.md |

**Key insight:** Phase 4 has almost no net-new algorithmic code. The camera wrapper, threading model, and servo abstraction are all implemented. The value is in correctness of lifecycle management (startup safety, shutdown safety, retry resilience).

---

## Common Pitfalls

### Pitfall 1: Direct servo jump on startup (Brownout/Reboot) — CRITICAL

**What goes wrong:** Servo physically at extreme position at power-on; software state initialized to `pan_angle = 0.0`; calling `set_angles(0, 0)` directly moves the full delta in one PWM cycle → current spike → RPi4 under-voltage reboot.

**Why it happens:** No encoder feedback. `PanTiltSystem` tracks logical position, not physical.

**How to avoid:** `smooth_move_to(0, 0)` is called in `MaszynaStanow.inicjalizuj()` — verify this is the first hardware operation before the main loop. It IS correctly placed after `self.kamera.start()`.

**Warning signs:** RPi reboots 1-3 seconds after launch. Audible servo slam. `/var/log/syslog` shows `Under-voltage detected`.

**Confidence:** HIGH — documented in CLAUDE.md, confirmed in codebase.

### Pitfall 2: Camera not released — "Camera already in use" (next run fails)

**What goes wrong:** Picamera2 not stopped/closed on exit; libcamera IPC socket stays open; next run raises `RuntimeError: Camera is already in use`.

**How to avoid:** The existing `Picamera2Stream.stop()` already has correct `try/finally` teardown. The `zatrzymaj()` method calls `kamera.stop()` first. Signal handlers in `run_test_tracker.py` call `tracker.zatrzymaj()`. Pattern is correct.

**Recovery if it happens:** `sudo killall libcamera-vid` or `sudo systemctl restart` the camera service.

**Confidence:** MEDIUM — based on libcamera IPC behavior patterns.

### Pitfall 3: Missing smooth_move_to before detach_servos (Pitfall 10 from PITFALLS.md)

**What goes wrong:** `detach_servos()` drops PWM; servo falls under gravity to mechanical stop; if at an extreme angle, this causes current spike and potential ribbon cable stress.

**Where it is:** `TestTracker.zatrzymaj()` calls `detach_servos()` directly without prior `smooth_move_to(0,0)`. **This is a confirmed gap in the skeleton.**

**How to avoid:** Insert `self.maszyna.hardware.smooth_move_to(0, 0)` before `detach_servos()` in `zatrzymaj()`.

**Confidence:** HIGH — pattern documented in PITFALLS.md, directly observable in existing code.

### Pitfall 4: Picamera2 mock mode is currently present (violates CONTEXT.md)

**What goes wrong:** Current skeleton silently falls back to blank grey frames if picamera2 is missing. CONTEXT.md locked decision: no mock, hard exit.

**How to avoid:** Remove `_mock_mode` logic from `Picamera2Stream`. Replace the module-level `try/except ImportError` with a fail-fast block that logs and calls `sys.exit(1)`.

**Confidence:** HIGH — directly readable from existing code vs CONTEXT.md text.

### Pitfall 5: OpenCV aarch64 package compatibility

**What goes wrong:** `opencv-python-headless==4.8.1.78` was pinned for armhf; may not install on aarch64 Bookworm 64-bit.

**How to detect:** `import cv2` fails at launch on RPi4.

**How to avoid:** If import fails, remove version pin from requirements.txt or use `sudo apt install python3-opencv` and rely on system package.

**Confidence:** LOW — training data only; must verify on actual RPi4.

### Pitfall 6: capture_array format on specific firmware (XRGB vs BGR)

**What goes wrong:** On some RPi firmware versions, `capture_array("lores")` with `"BGR888"` config may return a 4-channel XBGR array instead of 3-channel BGR.

**How to detect:** `assert frame.ndim == 3 and frame.shape[2] == 3` at first frame; add a startup log of `frame.shape`.

**How to avoid:** Add shape assertion in `_petla_przechwytywania()` on first frame. If 4 channels detected, slice: `klatka = klatka[:, :, :3]`.

**Confidence:** MEDIUM — multiple community reports of firmware-dependent format variation.

---

## Code Examples

### Fail-Fast Picamera2 Import (replacing current mock fallback)

```python
# Zastąp obecny blok try/except na poziomie modułu
try:
    from picamera2 import Picamera2
except ImportError:
    import logging, sys
    logging.getLogger(__name__).error(
        "Nie można zaimportować picamera2. "
        "Zainstaluj: sudo apt install python3-picamera2 "
        "i uruchom venv z --system-site-packages"
    )
    sys.exit(1)
```

### Headless Detection (new code in TestTracker.uruchom())

```python
# W pętli while self._running:
if not self._headless:
    wyswietlana = cv2.resize(klatka, (640, 480), interpolation=cv2.INTER_NEAREST)
    try:
        cv2.imshow("ARIES-LITE Test Tracker", wyswietlana)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            logger.info("Klawisz 'q' — zatrzymanie.")
            break
    except cv2.error:
        logger.info("Brak wyświetlacza (cv2.error) — przełączam na tryb headless")
        self._headless = True
        cv2.destroyAllWindows()
```

### Correct Shutdown Order (fix for TestTracker.zatrzymaj())

```python
def zatrzymaj(self) -> None:
    """Cleanup: zatrzymanie pętli, powrót serw do neutralnej, zwolnienie kamery."""
    self._running = False
    self.kamera.stop()
    # OBOWIĄZKOWE: powrót do neutralnej przed detach (zapobiega brownout)
    self.maszyna.hardware.smooth_move_to(0, 0)
    self.maszyna.hardware.detach_servos()
    cv2.destroyAllWindows()
    logger.info("TestTracker zatrzymany — zasoby zwolnione.")
```

### First-frame Format Assertion

```python
# Na początku _petla_przechwytywania, po pierwszym capture:
klatka = self._picam2.capture_array("lores")
if not _format_zweryfikowany:
    logger.info(f"Format klatki: shape={klatka.shape}, dtype={klatka.dtype}")
    assert klatka.ndim == 3, f"Oczekiwano 3D array, otrzymano: {klatka.ndim}D"
    if klatka.shape[2] == 4:
        logger.warning("4-kanałowy format wykryty — przycinam do BGR")
        klatka = klatka[:, :, :3]
    _format_zweryfikowany = True
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `cv2.VideoCapture(0)` via V4L2 | `Picamera2.capture_array("lores")` via libcamera | RPi OS Bookworm (2023) | V4L2 bridge for Pi Camera removed; Picamera2 is the only supported path |
| `picamera` v1 | `picamera2` | RPi OS Bullseye → Bookworm | v1 deprecated; v2 is native libcamera |
| `RPi.GPIO` software PWM | `pigpio` hardware PWM via `gpiozero.PiGPIOFactory` | Proven in v1.5 | Eliminates jitter; requires `sudo pigpiod` daemon |

**Deprecated/outdated:**
- `cv2.VideoCapture(0)` for Pi Camera: does not work on Bookworm 64-bit without legacy camera stack
- `picamera` (v1): unsupported on Bookworm, raises ImportError
- `RPi.GPIO` PWM: software-timed, causes servo jitter at higher frequencies

---

## Open Questions

1. **Picamera2 import in venv with --system-site-packages**
   - What we know: Standard practice for Bookworm Picamera2 deployment; `apt install python3-picamera2` is documented
   - What's unclear: Whether the specific RPi4 target unit already has the system package installed; whether the existing venv was created with `--system-site-packages`
   - Recommendation: First task in Phase 4 execution must be: `python3 -c "from picamera2 import Picamera2; print('OK')"` inside the venv. If it fails, fix before writing code.

2. **capture_array("lores") format on target firmware**
   - What we know: `BGR888` should return HxWx3 uint8; there are reports of 4-channel XBGR on some firmware versions
   - What's unclear: Exact firmware version on target RPi4
   - Recommendation: Add shape/ndim assertion at startup, log it, and handle 4-channel case with a slice. Pre-emptive fix is trivial.

3. **Picamera2 + pigpio DMA coexistence**
   - What we know: Both use Linux DMA resources; no known conflict documented
   - What's unclear: Whether BCM2711 DMAHEAP allocation produces errors when both are active simultaneously
   - Recommendation: Run `dmesg | grep -i dma` after first combined camera+servo test. If DMAHEAP errors appear, report as a blocker — no workaround known.

4. **OpenCV aarch64 compatibility**
   - What we know: `opencv-python-headless==4.8.1.78` was pinned for armhf compatibility
   - What's unclear: Whether this version installs cleanly on aarch64 Bookworm
   - Recommendation: `python3 -c "import cv2; print(cv2.__version__)"` before first test run. If it fails, remove version pin from requirements.txt and re-install.

5. **smooth_move_to() blocking duration**
   - What we know: `smooth_move_to(0, 0)` at `step=1.0` with `delay=0.05` — if servos are at ±60° on startup, this takes up to 6 seconds per axis (worst case ~6s pan + 3s tilt but they run in parallel within the loop)
   - What's unclear: Whether blocking in `zatrzymaj()` during Ctrl+C handling causes the user to perceive a "hang" before exit
   - Recommendation: This is acceptable behavior; log "Powrót do pozycji neutralnej..." so the user knows it is intentional.

---

## Validation Architecture

> nyquist_validation key absent from .planning/config.json — treated as enabled. test_framework is "none" — validation is empirical (command output + visual inspection on RPi4).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None configured — empirical verification only |
| Config file | None |
| Quick run command | `python3 run_test_tracker.py` (on RPi4 with camera connected) |
| Full suite command | `scripts/validate-all.sh` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Verification Command / Method | Infrastructure |
|--------|----------|-----------|-------------------------------|----------------|
| HW-01 | Servos move incrementally to (0,0) before loop starts — no brownout | smoke | Run `python3 run_test_tracker.py`; observe no reboot, no `Under-voltage` in `dmesg` | No file needed — manual observation |
| HW-02 | Picamera2 captures BGR frames at 320x240; FPS visible in terminal or log | smoke | Run `python3 run_test_tracker.py`; observe window/log shows frames with FPS counter | No file needed — manual observation |
| HW-03 | Ctrl+C exits cleanly: camera released, servos at neutral, no leftover process | smoke | `python3 run_test_tracker.py` → Ctrl+C → `fuser /dev/video0` returns empty, `ps aux | grep libcamera` shows nothing | No file needed — manual command check |
| HW-04 | Entry point runs without Flask or src/ modification | static | `python3 -c "import run_test_tracker"` → no Flask import; `git diff src/` after execution shows no changes | No file needed — static check |

### Sampling Rate

- **Per task:** `python3 run_test_tracker.py` on RPi4 — observe 10 seconds of operation, verify no crash
- **Phase gate:** All four HW-0X success criteria TRUE before marking Phase 4 complete

### Wave 0 Gaps

None — no test files to create. All validation is empirical on-device. The planner should include a pre-task verification step confirming the RPi4 environment is ready:
- [ ] `python3 -c "from picamera2 import Picamera2; print('OK')"` — must succeed in venv
- [ ] `python3 -c "import cv2; print(cv2.__version__)"` — must succeed in venv
- [ ] `sudo pigpiod` — daemon running (or mock mode explicitly accepted)
- [ ] `libcamera-hello` — camera hardware responds (not locked by previous process)

---

## Sources

### Primary (HIGH confidence)
- `src/modes/test_tracker.py` — existing skeleton, all four gaps confirmed by direct inspection
- `run_test_tracker.py` — signal handling and entry point confirmed correct
- `src/hardware.py` — PanTiltSystem API: smooth_move_to, set_angles, detach_servos signatures
- `src/config.py` — all constants used by hardware layer
- `src/camera.py` — VideoStream threading pattern (reference for Picamera2Stream design)
- `.planning/phases/04-hardware-foundation-camera-integration/04-CONTEXT.md` — all locked decisions
- `CLAUDE.md` — brownout constraint, smooth_move_to requirement, hardware pin assignments
- `.planning/research/PITFALLS.md` — all 13 pitfalls including Pitfall 10 (detach before neutral)
- `.planning/research/ARCHITECTURE.md` — component boundaries, data flow, anti-patterns

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md` — Picamera2 API patterns (training data, August 2025 cutoff)
- Training data: Picamera2 `create_video_configuration`, `lores` stream, `capture_array("lores")`
- Training data: libcamera IPC socket lifecycle on Bookworm 64-bit

### Tertiary (LOW confidence — needs on-device verification)
- Exact format returned by `capture_array("lores")` with `BGR888` on specific RPi firmware
- Picamera2 + pigpio DMA coexistence on BCM2711
- `opencv-python-headless==4.8.1.78` compatibility with aarch64 Bookworm

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all deps already in requirements.txt and used in existing skeleton; only Picamera2-specific API is MEDIUM
- Architecture: HIGH — skeleton exists and has been read directly; gaps are confirmed by file diff, not inference
- Pitfalls: HIGH for Pitfalls 1-3 (codebase-grounded); MEDIUM for Picamera2-specific behaviors (training data)

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable domain — Picamera2 API changes infrequently; RPi Bookworm stack stable)
