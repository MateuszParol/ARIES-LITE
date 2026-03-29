---
phase: 06-diagnostics-camera
plan: "01"
subsystem: hardware, camera
tags: [diagnostics, observability, awb, servo, clamp-logging]
dependency_graph:
  requires: []
  provides: [DIAG-01, CAM-01, CAM-02]
  affects: [src/hardware.py, src/modes/test_tracker.py]
tech_stack:
  added: []
  patterns: [per-axis WARNING logging, AWB warm-up lock via capture_metadata]
key_files:
  created: []
  modified:
    - src/hardware.py
    - src/modes/test_tracker.py
decisions:
  - "AwbEnable NOT added to set_controls — causes ISP sequencing conflict (locked)"
  - "ColourGains lock via set_controls() only after start() + sleep(2.0) — controls before start() silently ignored"
  - "Clamp WARNING fires in both mock and hardware modes — before the if not _mock_mode block"
  - "AWB fallback gains (2.5, 1.9) applied with WARNING when capture_metadata() returns None for ColourGains"
metrics:
  duration: ~10 min
  completed_date: "2026-03-27"
---

# Phase 6 Plan 1: Clamp Logging + AWB Warm-up Lock Summary

Surgical observability additions — per-axis servo clamp WARNING logging in hardware.py and AWB warm-up lock in test_tracker.py — establishing diagnostic baseline before Phase 7 motion tests.

## Tasks Completed

### Task 1: Clamp logging in set_angles() (DIAG-01)

Modified `src/hardware.py` `set_angles()` method to compute clamped values separately, then emit `logger.warning` for each axis that exceeds soft limits before assigning to `self.pan_angle` / `self.tilt_angle`.

- Warning format: `"Clamp pan: {raw:.1f} → {clamped:.1f} (limit)"` and `"Clamp tilt: ..."`
- Each axis checked independently (two separate `if` statements, not `if/elif`)
- Warning fires before the `if not self._mock_mode` block — active in both mock and hardware modes
- No rate-limiting: every clamped call is logged
- Commit: `ea5e41d`

### Task 2: AWB warm-up lock in Picamera2Stream.start() (CAM-01, CAM-02)

Two additions to `src/modes/test_tracker.py`:

1. Module constant added after `CAMERA_RETRY_DELAY`:
   ```python
   AWB_FALLBACK_GAINS = (2.5, 1.9)  # (Red, Blue) — fallback gdy sensor nie zwróci gains
   ```

2. AWB warm-up block appended to `Picamera2Stream.start()` after `self._thread.start()`:
   - `logger.info("Czekam na stabilizację AWB (2s)...")` then `time.sleep(2.0)`
   - `capture_metadata()` to read sensor's auto-computed gains
   - Fallback to `AWB_FALLBACK_GAINS` with `logger.warning` when `gains is None`
   - `set_controls({"ColourGains": gains})` to lock gains
   - `logger.info(f"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})")` confirmation
   - `AwbEnable` intentionally absent (ISP sequencing conflict)
- Commit: `fc9fd55`

## Hardware Verification (Task 3 — Checkpoint)

Awaiting hardware verification on RPi4. Success criteria:
- [ ] WARNING "Clamp pan/tilt" visible in terminal when servo exceeds limits
- [ ] INFO "Czekam na stabilizację AWB (2s)..." at startup
- [ ] INFO "ColourGains zablokowane: (R=X.XX, B=X.XX)" after warm-up
- [ ] Neutral skin tones within ~3 seconds of startup

Note: Actual `ColourGains` values from RPi sensor not yet captured (requires hardware run).
Note: Whether fallback `(2.5, 1.9)` was needed will be known after hardware verification.

## Deviations from Plan

None — plan executed exactly as written. All locked decisions honored.

## Self-Check: PASSED

- `src/hardware.py` — exists, modified, syntax valid
- `src/modes/test_tracker.py` — exists, modified, syntax valid
- Commit `ea5e41d` — present (Task 1)
- Commit `fc9fd55` — present (Task 2)
- `grep "logger.warning.*Clamp"` — returns 2 lines (pan + tilt)
- `grep "AWB_FALLBACK_GAINS"` — returns constant line
- `grep "AwbEnable"` — empty (correct)
