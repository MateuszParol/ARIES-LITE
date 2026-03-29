# Phase 6: Diagnostics & Camera - Research

**Researched:** 2026-03-27
**Domain:** Python logging patterns, Picamera2 AWB API, servo soft-limit diagnostics
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Clamp logging (DIAG-01)**
- Log every clamp hit — no rate-limiting, no additional state
- Format: separate lines per axis — e.g.:
  - `WARNING: Clamp pan: 75.0 → 60.0 (limit)`
  - `WARNING: Clamp tilt: -35.0 → -30.0 (limit)`
- Log active always — regardless of mock/hardware mode
- Log only axes that were actually clamped (not both if only one exceeded the limit)

**AWB warm-up (CAM-01)**
- Warm-up lives in `Picamera2Stream.start()` — method blocks ~2s before returning
- Camera starts immediately and shows frames during wait (uncalibrated for first ~2s — acceptable)
- Two terminal messages:
  - INFO before: `"Czekam na stabilizację AWB (2s)..."`
  - INFO after: `"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})"` (with actual values)
- `set_controls({"ColourGains": gains})` called AFTER `picam2.start()` + `time.sleep(2.0)` — NOT before start

**Fallback ColourGains (CAM-02)**
- When `capture_metadata()["ColourGains"]` returns `None` — use fallback values
- Fallback as module constant at top of `test_tracker.py` alongside other constants:
  ```python
  AWB_FALLBACK_GAINS = (2.5, 1.9)  # (Red, Blue) — fallback gdy sensor nie zwróci gains
  ```
- Log: WARNING (not INFO) — `"ColourGains niedostępne, używam fallback (2.5, 1.9)"`
- Do NOT add `AwbEnable: False` to `set_controls()` — causes ISP sequencing conflict

### Claude's Discretion
- Exact order of operations inside `Picamera2Stream.start()` (start → sleep → metadata → set_controls vs other variants)
- Variable naming for gains values

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase boundaries.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DIAG-01 | `set_angles()` logs WARNING when value is clamped to soft-limit (pan ±60°, tilt ±30°) | Clamp detection pattern: compare raw input vs clamped output; logger.warning() already available in hardware.py |
| CAM-01 | Picamera2 performs 2s warm-up after start() and locks ColourGains — image without blue cast | Picamera2 AWB stabilization: `capture_metadata()["ColourGains"]` after `time.sleep(2.0)`, then `set_controls({"ColourGains": ...})` |
| CAM-02 | If ColourGains lock does not eliminate blue tint, verified YUV conversion format (NV12 vs planar) | YUV conversion already confirmed correct (`cv2.COLOR_YUV420p2BGR` for I420/planar); fallback gains pattern documented |
</phase_requirements>

---

## Summary

Phase 6 consists of two surgical, non-behavioral changes to existing code. DIAG-01 adds WARNING-level logging to `src/hardware.py:set_angles()` when input values are clamped to soft limits — purely additive, no logic change. CAM-01 and CAM-02 extend `Picamera2Stream.start()` in `src/modes/test_tracker.py` with a 2-second AWB warm-up that reads `ColourGains` from camera metadata and locks them via `set_controls()` — this blocks `start()` for ~2s but is transparent to callers.

Both changes touch a single method each. The existing logging infrastructure (`logger = logging.getLogger(__name__)`) is already in place in both files. The `capture_metadata()` Picamera2 API returns a dict with `"ColourGains"` key; this may be `None` on the first call if the ISP has not yet converged, making a fallback constant necessary.

The critical ordering constraint for AWB is: `picam2.start()` must run first, then `time.sleep(2.0)`, then `capture_metadata()`, then `set_controls({"ColourGains": gains})`. Setting controls before start() is silently ignored by Picamera2. The `AwbEnable: False` control must NOT accompany `ColourGains` because it causes an ISP pipeline sequencing conflict.

**Primary recommendation:** Implement clamp logging by comparing raw input to clamped output per-axis; implement AWB lock by inserting the 4-step sequence at the tail of `Picamera2Stream.start()` after the thread is launched.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `logging` | stdlib | WARNING/INFO log emission | Already used in project; `logger` instance exists in both files |
| `picamera2` | system apt package | `capture_metadata()` + `set_controls()` APIs | Only camera library for RPi OS Bookworm libcamera stack |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python `time` | stdlib | `time.sleep(2.0)` for AWB warm-up | Already imported in `test_tracker.py` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Fixed 2s sleep | Poll until gains stabilize | Polling adds complexity; 2s is sufficient per project decision |
| `AwbEnable: False` | Omit it | Including it causes ISP conflict — locked decision: do NOT add |

**Installation:** No new dependencies — stdlib logging and Picamera2 already present.

---

## Architecture Patterns

### Recommended Project Structure
No structural change. Both modifications are method-level edits within existing files:
```
src/
├── hardware.py          # DIAG-01: set_angles() gets clamp logging
└── modes/
    └── test_tracker.py  # CAM-01+CAM-02: Picamera2Stream.start() gets AWB warm-up
```

### Pattern 1: Per-Axis Clamp Detection (DIAG-01)

**What:** Compare raw input value to clamped output per axis; emit WARNING only for axes where clamping occurred.

**When to use:** Before assigning `self.pan_angle` / `self.tilt_angle` — detect clamp by comparing raw vs min/max result.

**Example:**
```python
# In set_angles() — before assigning self.pan_angle / self.tilt_angle
pan_clamped = max(config.PAN_LIMIT_MIN, min(config.PAN_LIMIT_MAX, pan))
tilt_clamped = max(config.TILT_LIMIT_MIN, min(config.TILT_LIMIT_MAX, tilt))

if pan_clamped != pan:
    logger.warning(f"Clamp pan: {pan:.1f} → {pan_clamped:.1f} (limit)")
if tilt_clamped != tilt:
    logger.warning(f"Clamp tilt: {tilt:.1f} → {tilt_clamped:.1f} (limit)")

self.pan_angle = pan_clamped
self.tilt_angle = tilt_clamped
```

**Why this order:** Clamp calculation first, compare, warn, then assign. The mock/hardware branch comes after — WARNING fires unconditionally before the hardware check.

### Pattern 2: AWB Warm-up Lock (CAM-01 + CAM-02)

**What:** After `picam2.start()` and a blocking 2-second sleep, read `ColourGains` from metadata, fall back to constant if None, then lock via `set_controls()`.

**When to use:** At the tail of `Picamera2Stream.start()`, after the capture thread is already running (so frames are being captured, ISP has time to converge).

**Exact operation order inside `Picamera2Stream.start()`:**
```python
# 1. Camera already started: self._picam2.start()
# 2. Thread already started: self._thread.start()
# 3. Then append:
logger.info("Czekam na stabilizację AWB (2s)...")
time.sleep(2.0)
metadata = self._picam2.capture_metadata()
gains = metadata.get("ColourGains")
if gains is None:
    logger.warning("ColourGains niedostępne, używam fallback (2.5, 1.9)")
    gains = AWB_FALLBACK_GAINS
self._picam2.set_controls({"ColourGains": gains})
r, b = gains
logger.info(f"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})")
```

**Variable naming (Claude's Discretion):** Use `gains` for the tuple from metadata/fallback; unpack to `r, b` only for the log message. This is minimal, consistent with project style.

### Anti-Patterns to Avoid

- **`set_controls()` before `start()`**: Silently ignored by Picamera2 ISP. Controls are only applied to a running camera. Confirmed in project accumulated context.
- **`AwbEnable: False` in `set_controls()`**: Causes ISP sequencing conflict. Locked decision: do NOT include it.
- **Rate-limiting clamp logs**: Decided against — every hit must be logged for full diagnostics traceability.
- **Logging both axes when only one clamped**: Log only the axis where `raw != clamped`.
- **Float comparison with `!=` for extreme precision**: Float equality works here because `pan_clamped` is directly `min(max(...))` of the same float — if no clamp occurred, result is the exact same float object value.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| AWB convergence detection | Custom gain stability polling loop | Fixed `time.sleep(2.0)` + single `capture_metadata()` | Polling adds state, complexity, and potential hang; 2s is sufficient and already a project decision |
| Custom clamp-detect utility | Separate clamp helper function | Inline comparison in `set_angles()` | Two lines inline; no abstraction needed for two axes |

**Key insight:** Both changes are under 10 lines each. The complexity lives in knowing the API constraints (ordering, no AwbEnable), not in the implementation itself.

---

## Common Pitfalls

### Pitfall 1: set_controls() Before start()
**What goes wrong:** `set_controls({"ColourGains": gains})` called during `configure()` or before `start()` — silently ignored, no error, camera runs with uncorrected AWB.
**Why it happens:** Picamera2 API accepts `set_controls()` at any point but only applies controls after the ISP pipeline is running.
**How to avoid:** Always call `set_controls()` after `picam2.start()` + warm-up sleep.
**Warning signs:** Blue tint persists despite code being present; no ISP error raised.

### Pitfall 2: AwbEnable: False Alongside ColourGains
**What goes wrong:** ISP sequencing conflict — `ColourGains` may not be applied correctly, or camera enters inconsistent AWB state.
**Why it happens:** Disabling AWB and simultaneously setting gains triggers a race in the ISP pipeline ordering.
**How to avoid:** Do NOT add `AwbEnable: False`. Locked project decision.
**Warning signs:** Unexpected color shift, image darker or oversaturated.

### Pitfall 3: capture_metadata() Returns None for ColourGains
**What goes wrong:** `gains = metadata["ColourGains"]` raises `KeyError`, or `metadata.get("ColourGains")` returns `None`, causing `set_controls({"ColourGains": None})` crash or no-op.
**Why it happens:** ISP may not have a valid gains estimate in the first metadata frame, or on some sensor initializations the key is present but value is None.
**How to avoid:** Use `metadata.get("ColourGains")`, check for None, apply `AWB_FALLBACK_GAINS` with WARNING log.
**Warning signs:** `TypeError` in `set_controls()`, or KeyError on `metadata["ColourGains"]`.

### Pitfall 4: Clamp Comparison Noise on Float Values
**What goes wrong:** Near-limit values (e.g., 60.0000001) trigger WARNING on every scan peak.
**Why it happens:** PID outputs floating point; sinusoidal scan computed as `SCAN_AMPLITUDE * math.sin(...)` — at peak `sin(π/2) = 1.0` gives exactly 45.0, which is within limits.
**How to avoid:** No special handling needed — `SCAN_AMPLITUDE = 45.0` stays well within `PAN_LIMIT_MAX = 60`. The WARNING is intentionally fired on every actual clamp hit (no rate limiting, per DIAG-01 decision). Runaway PID is the scenario that triggers these warnings, so high frequency is diagnostic signal, not noise.
**Warning signs:** Not a pitfall in normal operation; becomes signal when PID bug causes runaway (Phase 7 context).

### Pitfall 5: Thread Already Running Before AWB Sleep
**What goes wrong:** `start()` caller unblocks the capture thread before the AWB warm-up completes — frames delivered before `set_controls()` fires have blue tint.
**Why it happens:** Thread is started before the 2s sleep; this is intentional (frames are captured immediately, just uncalibrated).
**How to avoid:** Accept ~2s of blue-tinted frames at startup — project decision explicitly accepts this. The SUCCESS CRITERIA require neutral color "within 3 seconds", not from frame 0.
**Warning signs:** Not a bug. If blue tint persists beyond 3s, check that `set_controls()` actually executed.

---

## Code Examples

Verified patterns from existing codebase and Picamera2 API:

### DIAG-01: Clamp Detection and Logging
```python
# Source: src/hardware.py set_angles() — modification point at line 48-50
def set_angles(self, pan: float, tilt: float) -> None:
    pan_clamped = max(config.PAN_LIMIT_MIN, min(config.PAN_LIMIT_MAX, pan))
    tilt_clamped = max(config.TILT_LIMIT_MIN, min(config.TILT_LIMIT_MAX, tilt))

    if pan_clamped != pan:
        logger.warning(f"Clamp pan: {pan:.1f} → {pan_clamped:.1f} (limit)")
    if tilt_clamped != tilt:
        logger.warning(f"Clamp tilt: {tilt:.1f} → {tilt_clamped:.1f} (limit)")

    self.pan_angle = pan_clamped
    self.tilt_angle = tilt_clamped

    if not self._mock_mode and self.pan_servo and self.tilt_servo:
        self.pan_servo.angle = self.pan_angle
        self.tilt_servo.angle = self.tilt_angle
```

### CAM-01 + CAM-02: AWB Warm-up in Picamera2Stream.start()
```python
# Source: src/modes/test_tracker.py Picamera2Stream.start() — append after thread start

# Module constant (top of file, alongside other constants):
AWB_FALLBACK_GAINS = (2.5, 1.9)  # (Red, Blue) — fallback gdy sensor nie zwróci gains

# Inside start(), after self._thread.start():
logger.info("Czekam na stabilizację AWB (2s)...")
time.sleep(2.0)
metadata = self._picam2.capture_metadata()
gains = metadata.get("ColourGains")
if gains is None:
    logger.warning("ColourGains niedostępne, używam fallback (2.5, 1.9)")
    gains = AWB_FALLBACK_GAINS
self._picam2.set_controls({"ColourGains": gains})
r, b = gains
logger.info(f"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})")
```

### Existing Logging Pattern (reference, no change needed)
```python
# Source: src/hardware.py lines 13, 33, 35 — logger already defined
logger = logging.getLogger(__name__)
logger.warning("gpiozero / pigpio not found. Running in mock hardware mode.")
logger.info("Hardware servos with PiGPIO initialized successfully.")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Silent clamp saturation in set_angles() | WARNING log per clamped axis | Phase 6 | Servo limit hits become grep-able, traceable |
| Uncorrected blue tint from AWB re-convergence | ColourGains locked after 2s warm-up | Phase 6 | Skin tones appear neutral; AWB stable during operation |
| No fallback for None ColourGains | AWB_FALLBACK_GAINS = (2.5, 1.9) module constant | Phase 6 | No crash or blue tint on first run if ISP has no gains yet |

**Deprecated/outdated:**
- None — this phase adds new behavior, does not replace existing patterns.

---

## Open Questions

1. **AWB fallback gains accuracy for specific hardware**
   - What we know: (2.5, 1.9) are documented as reasonable defaults for RPi camera modules indoors
   - What's unclear: Exact gains depend on lighting conditions and sensor variant (v2 vs HQ vs v3)
   - Recommendation: Accept (2.5, 1.9) for Phase 6; read back actual locked gains in terminal after first run and note for calibration if needed. Fallback is only used if `ColourGains` returns None — on a working sensor with 2s warm-up, it should return valid values.

2. **float comparison for clamp detection on boundary values**
   - What we know: `pan_clamped != pan` uses Python float equality; works correctly when clamp fires because `min(60, 60.0001) = 60.0` which differs from `60.0001`
   - What's unclear: Theoretical float precision edge case if input is exactly `60.0` (no clamp needed, comparison returns `False` correctly)
   - Recommendation: No special handling needed. The pattern is correct.

---

## Validation Architecture

> `test_framework: "none"` in .planning/config.json. CLAUDE.md states: "There are no unit tests or linting tools configured. Verification is empirical (HTTP responses, visual confirmation, command output)." This is a Raspberry Pi hardware project — automated test execution is not applicable.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None — empirical verification only |
| Config file | None |
| Quick run command | `python3 run_test_tracker.py` (on RPi hardware) |
| Full suite command | `python3 run_test_tracker.py` (same — single entry point) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Verification Method | Notes |
|--------|----------|-----------|---------------------|-------|
| DIAG-01 | WARNING in terminal when set_angles() receives out-of-range value | manual-only | Trigger from test: set SCAN_AMPLITUDE > 60 temporarily or pass known OOB value; grep terminal for "Clamp pan" / "Clamp tilt" | No automated unit test framework present |
| CAM-01 | Blue tint gone within 3s, INFO logs appear for AWB steps | manual-only | Visual observation of live feed; confirm terminal shows "Czekam na stabilizację AWB" then "ColourGains zablokowane" | Requires RPi hardware with camera |
| CAM-02 | AWB_FALLBACK_GAINS applied without crash when metadata returns None | manual-only | Code path confirmed by review; simulate None by temporarily setting `gains = None` in test run or review fallback branch | Hardware test: normal run should log INFO gains; fallback only if ISP fails |

### Sampling Rate
- **Per task commit:** Run `python3 run_test_tracker.py` on RPi, observe terminal and video for 10s
- **Per wave merge:** Same — single run verifies all three requirements simultaneously
- **Phase gate:** All three SUCCESS CRITERIA confirmed visually before `/gsd:verify-work`

### Wave 0 Gaps
None — no test infrastructure needed. Verification is empirical per CLAUDE.md and project config.

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `src/hardware.py` lines 41-54 — existing `set_angles()` structure, `logger` instance at line 13
- Direct code inspection: `src/modes/test_tracker.py` lines 24-35 (module constants), 63-75 (`Picamera2Stream.start()`)
- Direct code inspection: `src/config.py` — `PAN_LIMIT_MIN/MAX = -60/60`, `TILT_LIMIT_MIN/MAX = -30/30`
- `.planning/STATE.md` accumulated context — "AWB fix: set_controls(...) MUST follow picam2.start() + time.sleep(2.0)", "Do NOT add AwbEnable: False"
- `.planning/phases/06-diagnostics-camera/06-CONTEXT.md` — all implementation decisions verbatim
- `CLAUDE.md` — "There are no unit tests or linting tools configured. Verification is empirical."

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` accumulated context: "Do NOT change cv2.COLOR_YUV420p2BGR constant — correct for Picamera2 I420 output" — confirms YUV conversion format (CAM-02) is already correct, no change needed
- `.planning/REQUIREMENTS.md` — `CAM-02` description: "If ColourGains lock does not eliminate blue tint, checked YUV conversion format (NV12 vs planar)" — research confirms YUV420p is planar I420, which is what Picamera2 lores stream outputs; conversion is correct

### Tertiary (LOW confidence)
- General Picamera2 knowledge: `capture_metadata()` returns dict with `"ColourGains"` key; may be None before ISP convergence. Not verified against current official docs in this session — but consistent with project decisions and confirmed by accumulated context in STATE.md.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — both changes use stdlib logging and existing Picamera2 instance; no new dependencies
- Architecture: HIGH — direct code inspection of modification points; exact line numbers verified
- Pitfalls: HIGH for ordering/AwbEnable (confirmed in accumulated project context); MEDIUM for fallback None edge case (known Picamera2 behavior, not reverified against current docs)

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable — Picamera2 API, Python logging stdlib, and hardware constraints are not fast-moving)
