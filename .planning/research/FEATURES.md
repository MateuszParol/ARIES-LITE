# Feature Research

**Domain:** RPi4 autonomous face tracking — hardware bug fixes (v1.8)
**Researched:** 2026-03-29
**Confidence:** HIGH (direct code audit + confirmed symptom list from STATE.md)

---

## Context: This Is Still a Bug-Fix Milestone

v1.8 goal is to repair four confirmed hardware defects that persist despite v1.7
code changes. The symptom set from STATE.md:

1. TILT frozen at 0.0 in HUD — PID output not reaching servo
2. PAN runaway immediately on TRACKING entry — correction amplifies error
3. Blue tint from first frame — AWB lock not executing or wrong gains applied
4. HAAR detection too restrictive — requires near-perfect frontal position

The v1.7 FEATURES.md documented fixes that were mathematically correct but did not
resolve symptoms on actual hardware. v1.8 research focuses on why those fixes did
not work and what a hardware-verified solution requires.

---

## Feature Landscape

### Table Stakes (Must-Fix for v1.8 to Ship)

Features the system must have for the hardware to be usable. Missing any of these
means the tracker is non-functional on RPi4.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Tilt axis physically moves during TRACKING | Two-axis tracking is the product's core value | LOW | v1.7 fix applied negation but HUD still shows 0.0. Need to trace whether (a) mock mode is silently active, (b) pigpiod is not running, (c) tilt servo pin assignment is wrong, or (d) correction value is computed but then overwritten. Add debug log to confirm `set_angles()` receives non-zero tilt. |
| PAN converges to face center without runaway | Tracker must center face — not slam to limit | LOW | Runaway immediately on TRACKING entry suggests sign error or that `pan_angle` starts at an extreme and PID compounds it. Log `blad_pan`, `korekta_pan`, `nowy_pan` on each tick to identify where divergence starts. |
| Camera renders correct colors (no blue tint) | Usable image is prerequisite for visual inspection and face detection quality | LOW | AWB lock code exists in `Picamera2Stream.start()` and logs gains. STATE.md says "brak logu ColourGains" — meaning either the log never fires (exception swallowed before that line) or gains are captured but wrong. Must confirm `ColourGains` log fires before declaring AWB fixed. |
| Face detection triggers on real faces at 50–80 cm | Detector must find faces in actual operating conditions | MEDIUM | At 320x240 a face at 60 cm occupies roughly 40–60 px width. Current `minSize=(80,80)` rejects all such detections. Minimum fix: lower `minSize` to `(40,40)` and `minNeighbors` from 8 to 5. Verify streak filter still suppresses false positives. |

### Differentiators (High Value for This Diagnostic Milestone)

Not strictly required for hardware to function, but essential for confirming the
fixes actually work. All are low complexity.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-tick PID diagnostic logging (error, raw output, correction) | Exposes sign error vs. mock mode vs. hardware write issue without deploying to hardware repeatedly | LOW | Add `logger.debug()` after each PID call in `_sledz()`. Format: `PAN err={blad_pan:.1f} pid={raw:.2f} korekt={korekta_pan:.2f} → pan={nowy_pan:.1f}`. Same for tilt. This separates "PID not computing" from "hardware not moving". |
| ColourGains log at startup confirming actual R/B values | Proves AWB lock code path executed successfully | LOW | Already coded (`logger.info(f"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})")`) but apparently not firing. Add a log line immediately after `capture_metadata()` call before the None check, to confirm metadata was received at all. |
| Mock-mode status log at PanTiltSystem startup | Confirms whether servo commands go to real hardware or are silently dropped | LOW | `hardware.py` already logs mock mode. Add it to `set_angles()` too on first call: `logger.info(f"set_angles called: mock={self._mock_mode}")`. Eliminates the common RPi diagnostic failure where pigpiod is not running and all movements are silently no-ops. |
| HUD bbox dimension display (w x h pixels) | Confirms whether detected face size is above or below minSize threshold | LOW | Add `(bw)x(bh)` to the face rectangle label in `_rysuj_hud()`. One `cv2.putText` call. Immediately shows whether 80x80 threshold was the blocker or whether some faces do appear but are not detected. |

### Anti-Features (Do Not Add in v1.8)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| MediaPipe face detection | More robust at angles than HAAR | Requires separate install (mediapipe wheel for ARM), different API, adds 200-400 ms startup, not tested with YUV420 pipeline. Integration risk exceeds diagnostic value. | Tune HAAR parameters first (lower minNeighbors + minSize). If still insufficient after empirical test, consider OpenCV DNN as a closer swap. |
| OpenCV DNN SSD detector | Better accuracy at angles, works with same BGR pipeline | Adds `res10_300x300_ssd_iter_140000.caffemodel` (~10 MB) download, different bbox format (0–1 normalized), needs interface wrapper to match `wykryj()` return type. Medium risk. | Use only if HAAR tuning at (40,40)/5 is still insufficient. Document as Phase 2 option. |
| CSRT tracker between detections | Smoother PID input at low detection rate | CSRT is a main.py feature, not in test_tracker.py. Adding it to `TestTracker` introduces frame state that must be init/reset correctly. Not a fix — it is new scope. | Fix PID convergence first. CSRT adds value only after PID is verified working. |
| PID gain retuning | "Maybe gains are too high/low" | Gains (Kp=0.05, Ki=0.001, Kd=0.005) are from v1.7 validation. Sign error symptoms mimic gain problems. Do not change gains until sign convention is confirmed correct. | Fix sign/hardware path first. Retuning is a separate empirical phase after hardware is working. |
| Replacing AWB lock with hardcoded gains | Simpler, more predictable | Defeats purpose of adaptive AWB. Hardcoded values are environment-specific. | Fix the dynamic lock to actually execute. Log to confirm. |

---

## Feature Dependencies

```
[PID diagnostic logging]
    └──enables diagnosis of──> [Tilt axis fix]
    └──enables diagnosis of──> [PAN runaway fix]

[Mock-mode status log]
    └──prerequisite for──> [Tilt axis fix]
        (without knowing if mock mode is active, tilt=0 is ambiguous)

[Tilt axis fix]
    └──independent of──> [PAN runaway fix]
        (but both share same _sledz() method — fix together)

[ColourGains confirmation log]
    └──prerequisite for──> [AWB blue tint fix]
        (confirms fix actually executed, not skipped by exception)

[HAAR minSize tuning]
    └──independent of──> [PID fixes]
    └──enhanced by──> [HUD bbox dimension display]
        (confirms threshold was the actual blocker)

[OpenCV DNN detector] ──conflicts──> [DetekcjaTwarzy HAAR class interface]
    (wykryj() return type identical, but internal detection pipeline changes)
```

### Dependency Notes

- **Mock-mode log is prerequisite for tilt fix:** If pigpiod is not running, tilt
  commands are silently dropped in mock mode. The HUD reads `hardware.tilt_angle`
  which is updated even in mock mode. This means HUD can show non-zero tilt while
  the physical servo does not move. Log confirms which failure mode is active.

- **PID logging before hardware changes:** PID diagnostic logging costs zero
  hardware risk. It should be the first change applied and verified before any
  sign/path fixes, so the baseline behavior is documented.

- **AWB log before AWB fix:** The ColourGains confirmation log goes in before
  changing the sleep duration or gain capture code. Establishes whether the code
  path even executes.

- **Detection fix is independent:** HAAR tuning does not affect PID or AWB. Can
  be developed and tested in parallel. However, functional detection is needed to
  exercise the PID path — so detection should be confirmed working before PID
  runaway testing.

---

## MVP Definition

### Fix Now — v1.8 (all four required)

The four hardware defects are the entire stated goal of this milestone. They must
all ship together because a partially broken tracker has no value.

- [ ] Tilt axis physically moves — diagnose mock mode / sign / hardware path
- [ ] PAN converges without runaway — diagnose sign convention with logging
- [ ] AWB lock executes — confirm ColourGains log fires with correct values
- [ ] HAAR detects real faces — lower minSize to (40,40) and minNeighbors to 5

### Add as Diagnostic Support (same milestone, zero structural risk)

One-line additions that prove the fixes worked. Include in same phase as the fix.

- [ ] PID per-tick debug logging (error + output + correction + resulting angle)
- [ ] ColourGains confirmation log at metadata capture point (before None check)
- [ ] Mock-mode status log on first `set_angles()` call
- [ ] HUD bbox dimension display (w x h pixels next to face rectangle)

### Defer to Future Milestones

- [ ] OpenCV DNN face detector — only if HAAR tuning is empirically insufficient
- [ ] MediaPipe detector — v2+, separate dependency effort
- [ ] CSRT tracker in test module — after PID is confirmed working
- [ ] PID gain retuning — after hardware sign/path confirmed correct
- [ ] AwbMode preset selection (Indoor/Fluorescent) — only if dynamic lock still fails

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Tilt axis fix (mock mode / sign / path) | HIGH | LOW | P1 |
| PAN runaway fix (sign convention) | HIGH | LOW | P1 |
| AWB blue tint fix (lock execution) | HIGH | LOW | P1 |
| HAAR detection tuning (minSize/minNeighbors) | HIGH | LOW | P1 |
| PID diagnostic logging | HIGH (debugging) | LOW | P1 |
| ColourGains confirmation log | HIGH (debugging) | LOW | P1 |
| Mock-mode status log in set_angles | HIGH (debugging) | LOW | P1 |
| HUD bbox dimension display | MEDIUM | LOW | P2 |
| OpenCV DNN detector | MEDIUM | MEDIUM | P3 |
| CSRT tracker in test module | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for v1.8 launch
- P2: Should have, add when possible
- P3: Nice to have, future milestone

---

## Existing Code Constraints (RPi4-Specific)

These constraints must be respected by all fixes. No architectural changes allowed.

| Constraint | Location | Impact on v1.8 Fixes |
|------------|----------|----------------------|
| YUV420 capture thread is daemon — AWB set_controls must happen on main thread after start() | `Picamera2Stream.start()` lines 79–87 | AWB fix: the existing timing (2s sleep on main thread, then set_controls) is architecturally correct. If it fails, the failure is in exception handling or metadata availability, not the sequence. |
| `hardware.tilt_angle` updates even in mock mode | `hardware.py` `set_angles()` lines 49–58 | Tilt fix: HUD shows `hardware.tilt_angle` which is always updated. Angle=0.0 in HUD means `set_angles()` was never called with non-zero tilt, OR the correction was zero, OR mock mode silently dropped it. Must log at `set_angles()` call site. |
| HAAR operates on grayscale BGR→GRAY conversion | `DetekcjaTwarzy.wykryj()` line 174 | Detection fix: grayscale conversion is correct. Only `minNeighbors` and `minSize` parameters need adjustment. Do not change scaleFactor (1.1) — correct for small faces. |
| `PID_OUTPUT_LIMIT = 10.0` degrees/tick | `MaszynaStanow.__init__` | PID fix: with Kp=0.05 and max pixel error ~160px at 320x240, max PID output = 8 degrees/tick. Runaway cannot be caused by output limits alone — must be sign error compounding. |
| `TILT_LIMIT_MIN/MAX = ±30` degrees | `config.py` | Narrow tilt range. If sign error drives tilt to +30 on frame 1, all subsequent corrections clamp. This is why tilt appears frozen at a non-zero value — but STATE.md says frozen at 0.0, suggesting servo never received a command at all. |
| `simple_pid>=2.0.1` pinned, anti-windup via output_limits | `requirements.txt`, v1.7 decision | Do not change PID library. It is correct. The bug is in the sign convention of `blad_pan`/`blad_tilt` and `korekta_pan`/`korekta_tilt`. |

---

## Sign Convention Reference (v1.7 Validated, Must Verify on Hardware)

v1.7 established this reference (PROJECT.md "Key Decisions"):

```
HARDWARE (empirically confirmed in v1.7):
  pan_angle increases  → servo rotates RIGHT → face moves LEFT in frame
  tilt_angle increases → servo rotates DOWN  → face moves UP in frame

PIXEL ERRORS:
  blad_pan  = srodek_x - ramka_cx  (+ = face RIGHT of center)
  blad_tilt = srodek_y - ramka_cy  (+ = face BELOW center)

REQUIRED CORRECTION:
  face RIGHT  → pan_angle must INCREASE  → korekta_pan must be POSITIVE
  face BELOW  → tilt_angle must INCREASE → korekta_tilt must be POSITIVE

DERIVATION (simple_pid output = Kp * (setpoint - input) = -Kp * error):
  korekta_pan  = -pid_pan(blad_pan)   = +Kp*blad_pan  ✓  (currently in code)
  korekta_tilt = -pid_tilt(blad_tilt) = +Kp*blad_tilt ✓  (v1.7 fix applied)
```

The v1.7 fix (`korekta_tilt = -self.pid_tilt(blad_tilt)`) is in the code at line 276.
v1.8 question is: why does HUD still show tilt=0.0? The sign is now correct. Suspect:
- pigpiod not running → mock mode active → servo does not move (HUD still updates)
- OR tilt servo physically broken/disconnected
- OR `tilt_angle` resets to 0 somewhere else (search for `tilt_angle = 0`)

---

## Sources

- Direct code audit: `src/modes/test_tracker.py`, `src/hardware.py`, `src/config.py`
- Project state: `.planning/STATE.md` ("brak logu ColourGains", tilt frozen at 0.0)
- Project decisions: `.planning/PROJECT.md` ("Tilt negation: korekta_tilt = -pid_tilt — Good")
- v1.7 FEATURES.md (this file's previous version) — sign convention derivation, HIGH confidence
- Confidence: HIGH — analysis from code + confirmed symptom set, no speculation

---

*Feature research for: RPi4 face tracking — v1.8 Critical Hardware Fix*
*Researched: 2026-03-29*
