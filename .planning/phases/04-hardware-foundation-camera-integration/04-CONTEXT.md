# Phase 4: Hardware Foundation & Camera Integration - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove safe startup and Picamera2 frame delivery on RPi OS Bookworm 64-bit. Servos move incrementally to neutral, camera captures BGR888 frames at 320x240, clean shutdown on Ctrl+C/SIGTERM, standalone entry point with no Flask dependency. No vision, no PID, no state machine logic — those belong in Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Camera mock mode
- Picamera2 is **required** — if `from picamera2 import Picamera2` fails, print error and `sys.exit(1)`. No blank-frame mock mode.
- Servo mock mode remains **independent** — if pigpiod is not running, PanTiltSystem degrades to mock (existing hardware.py behavior). Camera + mock servos is a valid test configuration.
- Exit mechanism on missing Picamera2: Claude's discretion (logger error + sys.exit or RuntimeError).

### Frame preview
- Primary display: `cv2.imshow()` window for local monitor on RPi.
- **Headless fallback**: Try `cv2.imshow()` on first frame — if it throws (no DISPLAY), switch to headless log-only mode for the rest of the run. No CLI flag needed.
- Window size: **upscale to 640x480** (2x) for better visibility on desktop monitor.
- Headless logging granularity: Claude's discretion (periodic summary or state transitions only).

### Failure handling
- **Mid-run camera failure**: Retry camera re-initialization up to 3 times, then trigger clean shutdown. Handles transient Picamera2 errors.
- **No pigpiod**: Run with servo mock mode — camera pipeline still testable without hardware servos.
- **Startup**: If Picamera2 import fails → error and exit. If Picamera2 starts but first frame fails → retry logic applies.

### Capture threading
- **Lock-protected single frame** (`threading.Lock` + single `np.ndarray` variable) — matches existing VideoStream pattern in `camera.py`.
- **Lores stream**: `capture_array("lores")` at 320x240 BGR888 — lower latency, configured at Picamera2 init time.
- Capture runs in a **daemon thread** — dies with main process, consistent with project convention.

### Claude's Discretion
- Exact exit mechanism for missing Picamera2 (logger + sys.exit vs RuntimeError)
- Headless mode logging granularity (periodic summary vs state-change-only)
- Camera retry delay between attempts
- Thread sleep interval in capture loop

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Hardware abstraction (reuse)
- `src/hardware.py` — PanTiltSystem class: smooth_move_to, set_angles, detach_servos, mock mode pattern
- `src/config.py` — PID gains, servo limits (PAN ±60°, TILT ±30°), SERVO_STEP, TIME_TO_LOST_SEC, state constants

### Existing camera pattern (reference, not reuse)
- `src/camera.py` — VideoStream: threaded capture with lock, read() interface. Reference for threading pattern, but Picamera2 replaces cv2.VideoCapture.

### Research
- `.planning/research/SUMMARY.md` — Stack recommendations, pitfalls, architecture approach
- `.planning/research/ARCHITECTURE.md` — Picamera2 integration patterns, async capture design
- `.planning/research/PITFALLS.md` — Brownout risk, camera lock, BGR/RGB format issues

### Project constraints
- `CLAUDE.md` — Brownout warning, servo startup constraint, architecture overview
- `.planning/PROJECT.md` — v1.6 scope, hardware constraints, isolation requirement

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PanTiltSystem` (src/hardware.py): Direct reuse — smooth_move_to(0,0) for safe start, set_angles() for control, detach_servos() for cleanup. Mock mode built-in.
- `src/config.py`: All servo limits, PID gains, state name constants. Import directly.

### Established Patterns
- **Mock mode**: `try/except ImportError` at module level → boolean flag → conditional behavior. Used in hardware.py for pigpio.
- **Thread safety**: `threading.Lock()` for shared frame data. Used in camera.py and vision.py.
- **Daemon threads**: All background threads are daemon=True. Process exit kills them.
- **Polish comments**: All docstrings and comments in Polish. Variable names mix English/Polish.

### Integration Points
- `src/modes/__init__.py` — New package for test tracker module.
- `run_test_tracker.py` — Project root entry point. Does NOT import from main.py or web/.
- Import path: `from src.hardware import PanTiltSystem` and `from src import config`.

</code_context>

<specifics>
## Specific Ideas

- Upscale preview to 640x480 for better visibility — user explicitly chose 2x over native 320x240
- Headless detection via try/catch on cv2.imshow, not DISPLAY env var check
- Camera retry (3 attempts) before giving up on mid-run failures

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-hardware-foundation-camera-integration*
*Context gathered: 2026-03-26*
