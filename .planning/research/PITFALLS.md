# Domain Pitfalls

**Domain:** Adding Picamera2-based isolated test tracker to existing RPi4 ARIES-LITE system
**Researched:** 2026-03-26
**Confidence:** MEDIUM — grounded in existing codebase analysis and training knowledge; web search unavailable for verification

---

## Critical Pitfalls

Mistakes that cause reboots, hardware damage, or require a full rewrite.

---

### Pitfall 1: Direct Servo Jump at Module Startup (Brownout/Reboot)

**What goes wrong:**
The test tracker initializes `PanTiltSystem`, reads `pan_angle = 0.0` and `tilt_angle = 0.0` as the logical starting position, then immediately sends a PWM command to move to (0, 0). If the servo is physically sitting at an extreme position (e.g., pan = +55° from a previous run), this triggers a hard mechanical jump that draws a current spike of 500–700 mA from the shared 5V/6V rail. The RPi4 under-voltage detector fires and reboots the board.

**Why it happens:**
`PanTiltSystem` tracks `pan_angle` and `tilt_angle` as software state, not as a reflection of the actual physical servo position. There is no encoder feedback. At startup, those values are initialised to `0.0` regardless of physical position. If the test tracker skips `smooth_move_to()` or calls `set_angles()` directly before the incremental ramp, the servo sees the full angular delta in a single PWM update cycle (~20 ms).

**Consequences:**
- RPi4 hard reboot during startup
- Camera ribbon cable stress if the jump is large on the tilt axis
- gpiozero/pigpio PWM state is undefined after unexpected reboot — next launch may re-enter the same failure

**Prevention:**
Always call `smooth_move_to(0, 0)` as the very first hardware operation in the test tracker, before any state machine transitions. Use the existing `delay=0.03` (30 ms between 1° steps). Do not call `set_angles()` directly from `__init__` or from any constructor path.

**Detection:**
- Board reboots ~1–3 seconds after test tracker launch
- Audible servo "slam" sound before reboot
- `/var/log/syslog` shows `Under-voltage detected`

**Phase note:** Must be addressed in Phase 1 (Safe Startup implementation). The existing `smooth_move_to()` in `src/hardware.py` is correct — the test tracker must call it unconditionally on first start.

---

### Pitfall 2: Picamera2 Not Released — "Camera already in use" on Subsequent Runs

**What goes wrong:**
The test tracker creates a `Picamera2` instance and calls `picam2.start()`. If the process exits without calling `picam2.stop()` and `picam2.close()`, the libcamera pipeline stays open at the kernel level. The next run immediately raises `RuntimeError: Camera is already in use` or hangs at `Picamera2.start()`. On Bookworm 64-bit, this is more common because libcamera's IPC uses a Unix socket that is not automatically released on process exit in some kernel versions.

**Why it happens:**
Unlike OpenCV's `VideoCapture.release()`, Picamera2 requires an explicit two-step teardown: `stop()` (stops the capture loop) then `close()` (releases the libcamera pipeline and the `/dev/video0` file descriptor). Raising an unhandled exception between `start()` and `stop()` skips the cleanup. Python's garbage collector does not reliably call `__del__` in daemon threads.

**Consequences:**
- Subsequent test runs fail immediately
- Requires `sudo killall libcamera-vid` or reboot to recover
- Makes iterative development extremely slow on real hardware

**Prevention:**
Wrap the entire camera lifecycle in a `try/finally` block:
```python
picam2 = Picamera2()
picam2.configure(...)
picam2.start()
try:
    run_loop(picam2)
finally:
    picam2.stop()
    picam2.close()
```
Additionally register a `signal.signal(signal.SIGINT, handler)` and `signal.signal(signal.SIGTERM, handler)` that set a stop event, so `KeyboardInterrupt` and systemd stop both trigger the `finally` block.

**Detection:**
- `RuntimeError: Camera is already in use` on second launch
- `lsof /dev/video0` shows the previous PID still holds the fd
- `ls /proc/<PID>/fd` after apparent process exit

**Phase note:** Must be addressed in Phase 1 (camera init) alongside graceful shutdown. Mirror the `stopped` flag pattern already used in `src/camera.py`.

---

### Pitfall 3: Picamera2 + OpenCV Frame Format Mismatch (BGR vs RGB)

**What goes wrong:**
`Picamera2.capture_array()` returns frames in **RGB** order by default (format `"RGB888"`). OpenCV functions — including `cv2.CascadeClassifier.detectMultiScale()` and `cv2.imshow()` — expect **BGR** order. Running HAAR detection on an RGB frame does not crash; it silently reduces detection accuracy because the cascade was trained on BGR images. Face bounding boxes may be missed or have higher false-negative rates.

**Why it happens:**
The existing `VideoStream` (OpenCV backend) produces BGR frames naturally. The new Picamera2 backend changes this contract. The difference is invisible unless explicitly checked — HAAR cascades are robust enough to still detect some faces, masking the problem during initial testing.

**Consequences:**
- Reduced face detection rate (false negatives increase)
- Subtle bug that is hard to diagnose — system appears to work but misses faces
- Any downstream component that receives frames and assumes BGR (e.g., `cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)`) produces incorrect grayscale

**Prevention:**
Explicitly configure Picamera2 to output BGR:
```python
config = picam2.create_preview_configuration(
    main={"format": "BGR888", "size": (640, 480)}
)
picam2.configure(config)
```
Or add a single conversion after every `capture_array()` call:
```python
frame = picam2.capture_array()
frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
```
The explicit format configuration is preferable — it is cheaper (no per-frame copy) and documents the contract.

**Detection:**
- Face detection works sometimes but misses obvious faces
- `frame.shape` is `(480, 640, 3)` — correct — but pixel channel ordering is wrong
- Add assertion: `assert picam2.camera_configuration()["main"]["format"] == "BGR888"`

**Phase note:** Phase 1 (camera init). Add a format sanity check to the test tracker's startup log output.

---

### Pitfall 4: Picamera2 and cv2.VideoCapture Both Opening Camera Simultaneously

**What goes wrong:**
The test tracker is isolated (`src/modes/test_tracker.py`) but runs in the same Python process as the Flask server that uses the existing `VideoStream` (OpenCV `cv2.VideoCapture`). If both are active simultaneously — or if the test tracker is started while the Flask server is running — both try to open `/dev/video0`. On Bookworm with libcamera, `cv2.VideoCapture(0)` uses the V4L2 libcamera bridge, which is the same pipeline Picamera2 uses. The second opener gets a blank stream or an error.

**Why it happens:**
On RPi OS Bookworm, `/dev/video0` is a V4L2-compat device backed by libcamera. Both Picamera2 and OpenCV's V4L2 backend attempt to acquire the same libcamera session. Unlike USB webcams, the Raspberry Pi camera module does not support multiple concurrent openers.

**Consequences:**
- Test tracker captures black frames silently
- Existing Flask MJPEG stream may drop to 0 FPS
- No exception raised — failure is silent and confusing

**Prevention:**
The test tracker must run as a standalone script (`python3 -m src.modes.test_tracker`) that does NOT import or start the Flask server. Document clearly in the module header that it is mutually exclusive with the main application. Add a runtime guard: check if port 5000 is bound before starting, and refuse to start if so.

**Detection:**
- All captured frames are black (numpy array of zeros)
- `v4l2-ctl --list-devices` shows device busy
- `fuser /dev/video0` shows two PIDs

**Phase note:** Phase 1 (isolation contract). Enforce via documentation and a startup check, not just convention.

---

## Moderate Pitfalls

---

### Pitfall 5: PID Integral Windup During Scanning State

**What goes wrong:**
The PID controllers (`pid_pan`, `pid_tilt`) accumulate integral error whenever there is a non-zero error signal. During the SCANNING state, no face is tracked but the PID objects still exist and may receive error values if `do_tracking()` is accidentally called, or if the integral is not reset when transitioning from TRACKING back to SCANNING. When a face is found after a scan, the wound-up integral causes a large initial correction overshoot — the servo snaps past the face position before settling.

**Why it happens:**
`simple_pid.PID` accumulates `_integral` continuously. The existing `TrackerMachine` uses `output_limits = (-10, 10)` which caps the *output* but not the internal integral accumulator. Windup occurs silently while the integrator accumulates beyond what the output limits would normally allow.

**Consequences:**
- Servo overshoots face position on first tracking tick after scan
- System oscillates around face center for 1–3 seconds before settling
- On MG-90S servos at 6V, oscillation can cause the servo to buzz/chatter

**Prevention:**
Call `pid_pan.reset()` and `pid_tilt.reset()` on every transition into SCANNING state. `simple_pid` also supports `auto_mode = False` to freeze the controller. Additionally, enable `simple_pid`'s built-in windup clamping:
```python
self.pid_pan = PID(..., output_limits=(-10, 10))
# simple_pid clamps integral automatically when output_limits is set
# but verify the version — older versions required explicit anti_windup flag
```
Verify the installed `simple_pid` version supports integral clamping by checking `pip show simple-pid`.

**Detection:**
- Servo makes a sharp initial move when target is first acquired after scanning
- Servo oscillates around center before stabilising
- Log `pid_pan._integral` value at transition point

**Phase note:** Phase 2 (PID loop). Test by covering the camera for 10+ seconds (to accumulate windup) then uncovering.

---

### Pitfall 6: PID Sample Time Mismatch with Frame Rate

**What goes wrong:**
`simple_pid.PID` uses a `sample_time` parameter (default: `None`, meaning "run every call"). If the control loop runs at variable frame rates — common when HAAR detection is slow on some frames — the derivative term `Kd * d(error)/dt` becomes unstable. A frame that takes 80 ms instead of the expected 33 ms (30 FPS) produces a derivative spike three times larger than expected, causing servo jitter.

**Why it happens:**
The existing PID gains `Kp=0.05, Kd=0.005` are tuned for approximately 30 FPS. The D term is computed as `Kd * (error - last_error) / dt`. When `dt` varies from 33 ms to 200 ms (heavy HAAR frame), the D term ratio changes 6x, producing erratic corrections.

**Consequences:**
- Servo jitter at irregular intervals
- System appears tuned correctly in tests but jitters during real use when HAAR takes longer
- MG-90S at 6V will audibly buzz during jitter events

**Prevention:**
Set `sample_time` on the PID controllers to match the target loop period:
```python
self.pid_pan = PID(..., sample_time=0.033)  # 30 FPS = 33ms
```
With `sample_time` set, `simple_pid` skips updates that arrive faster than `sample_time` and caps dt to a reasonable value. Alternatively, implement the control loop with a fixed-period `time.sleep()` and measure actual dt to log when frames are late.

**Detection:**
- Irregular servo twitches during otherwise stable tracking
- Log the time delta between `logic_tick()` calls — spikes above 100 ms indicate the problem

**Phase note:** Phase 2 (PID tuning). Set `sample_time` during initial implementation, not as a later fix.

---

### Pitfall 7: HAAR Cascade minNeighbors Too Low — False Detections Drive Servo Hunting

**What goes wrong:**
At `minNeighbors=5` (existing config), HAAR detection works well on a 640x480 frame in controlled lighting. In the test tracker context — where any face triggers immediate PID tracking — false detections on patterned backgrounds, hands, or low-light frames cause the servo to "hunt" toward phantom targets. Because the test tracker has no dlib identity verification, it tracks whatever HAAR reports.

**Why it happens:**
The existing `HybridVision` uses dlib async verification to confirm identity before entering full tracking. The test tracker (`test_tracker.py`) intentionally removes identity verification to simplify the control loop. Without that filter, every false HAAR positive drives the PID controller.

**Consequences:**
- Servo chases background patterns when no human is present
- State machine never reaches stable TRACKING — oscillates between TRACKING (phantom) and SCANNING
- PID integral accumulates against conflicting targets

**Prevention:**
Use `minNeighbors=8` (higher confidence threshold) and `minSize=(80, 80)` (ignore small detections) in the test tracker specifically. Also add a **detection streak filter**: require the same face region to be detected in N consecutive frames before transitioning from SCANNING to TRACKING. A streak of 3 frames eliminates almost all single-frame false positives.

**Detection:**
- Servo moves erratically when room is empty
- Log HAAR detection count per frame — healthy: 0–1 detections; hunting: >1 per frame

**Phase note:** Phase 2 (face detection integration). Tune `minNeighbors` and add streak filter before testing PID.

---

### Pitfall 8: MG-90S Servo PWM Pulse Width — gpiozero min/max_pulse_width Mismatch

**What goes wrong:**
`AngularServo` in gpiozero defaults to `min_pulse_width=1ms` and `max_pulse_width=2ms`. MG-90S servos technically accept 0.5 ms–2.5 ms, giving a full 180° range. With the 1–2 ms defaults, the effective range is ~90° (not the configured `min_angle=-90, max_angle=90`). The soft limits in `config.py` (pan ±60°, tilt ±30°) fall within this range, so the bug is hidden — but the servo may not reach commanded angles precisely, causing the PID to never fully zero the error.

**Why it happens:**
The existing `hardware.py` creates `AngularServo` with `min_angle=-90, max_angle=90` but does not explicitly set `min_pulse_width` and `max_pulse_width`. gpiozero maps angle to pulse width linearly between the defaults. If the actual servo calibration differs, the mapping is off.

**Consequences:**
- PID has a residual steady-state error it cannot eliminate
- `Ki` term winds up trying to correct the uncorrectable mechanical offset
- Pan/tilt does not center on face even with correct error calculation

**Prevention:**
Characterise the specific MG-90S units before PID tuning. Measure actual neutral pulse width with an oscilloscope or servo tester. For most MG-90S from reputable suppliers, `min_pulse_width=0.5ms, max_pulse_width=2.5ms` gives true ±90° range:
```python
AngularServo(pin, min_angle=-90, max_angle=90,
             min_pulse_width=0.0005, max_pulse_width=0.0025,
             pin_factory=factory)
```
Test center position independently: command `angle=0` and verify servo shaft is mechanically centred.

**Detection:**
- `set_angles(0, 0)` produces a measurably off-centre position
- PID settles with a visible face offset from frame center
- Residual error remains constant regardless of `Ki`

**Phase note:** Phase 1 (hardware init). Verify pulse width before writing any PID code.

---

### Pitfall 9: Scan Pattern Stale State After TRACKING → SCANNING Transition

**What goes wrong:**
`TrackerMachine.do_scan()` uses `scan_step_pan` and `scan_step_tilt` as directional accumulators. When tracking is lost and the state transitions back to SCANNING, the scan resumes from wherever `target_pan` and `target_tilt` were when tracking was last active. If tracking ended at pan=+55°, the scan immediately hits the limit, flips direction, and the tilt nudges — but the effective scan range is only the last ~5° before the limit, not the full ±60° sweep.

**Why it happens:**
There is no reset of `target_pan` / `target_tilt` on the TRACKING → SCANNING transition. The scan state is continuous, not re-initialized. This is acceptable for the main system (gradual recovery) but in the test tracker, which is intended to prove correct behaviour, it produces confusing partial-scan artefacts during testing.

**Consequences:**
- Scan pattern is asymmetric after tracking ends at an extreme
- System appears to not scan at all if target was lost at the pan limit
- Makes PID + scan integration harder to verify

**Prevention:**
On TRACKING → SCANNING transition, reset `target_pan = 0.0` and call `smooth_move_to(0, 0)` before resuming the scan. Alternatively, use a sine wave sweep (as mentioned in PROJECT.md goals) driven by `time.time()` instead of accumulated steps — a time-based sinusoid is immune to stale state:
```python
t = time.time() - self.scan_start_time
self.target_pan = PAN_LIMIT_MAX * math.sin(2 * math.pi * t / SCAN_PERIOD)
```

**Detection:**
- Servo barely moves after target is lost at an extreme angle
- Log `target_pan` and `target_tilt` at state transition point

**Phase note:** Phase 2 (state machine implementation). The sinusoidal scan is explicitly mentioned in the v1.6 goal — implement it from the start, not as a refactor.

---

## Minor Pitfalls

---

### Pitfall 10: `detach_servos()` Called Too Early — Servo Falls to Mechanical Stop

**What goes wrong:**
`PanTiltSystem.detach_servos()` removes the PWM signal from the servo pins. On MG-90S servos, this causes the servo to drop torque and fall under gravity to its mechanical stop (typically the extreme end of travel). If `detach_servos()` is called at module teardown without first moving to neutral, the servo snaps to the stop position — the same brownout risk as Pitfall 1, plus physical stress on the ribbon cable.

**Prevention:**
Always call `smooth_move_to(0, 0)` before `detach_servos()` in the cleanup sequence. The correct shutdown order: `stop capture loop` → `move to neutral` → `detach servos` → `close camera`.

**Phase note:** Phase 1 (graceful shutdown). Enforce via `finally` block ordering.

---

### Pitfall 11: Picamera2 `capture_array()` Blocking the Control Loop

**What goes wrong:**
`picam2.capture_array()` in synchronous mode blocks the calling thread until a frame is available from the camera sensor. At 30 FPS, this is ~33 ms. Combined with HAAR detection time (~40–80 ms on RPi4), the control loop tick rate drops to 8–12 FPS, making the PID derivative term unstable at gains tuned for 30 FPS.

**Prevention:**
Use Picamera2's continuous capture mode with a `deque(maxlen=1)` buffer, mirroring the existing `VideoStream` async pattern in `src/camera.py`. Configure:
```python
picam2.start()
# In a background thread:
frame = picam2.capture_array()
with lock:
    latest_frame = frame
```
The control loop reads from `latest_frame` without blocking on the camera, decoupling camera I/O latency from PID tick rate.

**Detection:**
- Measure time between `logic_tick()` calls — consistently above 50 ms indicates blocking capture
- FPS counter in the display overlay

**Phase note:** Phase 1 (camera architecture). Use the async capture pattern from the start — retrofitting it later requires restructuring the control loop.

---

### Pitfall 12: `simple_pid` Package Not Installed — Silent Import Error

**What goes wrong:**
`src/tracker.py` imports `from simple_pid import PID`. The test tracker depends on the same package. If the virtual environment on the RPi4 was set up before the `simple_pid` dependency was added to `requirements.txt`, the import fails at runtime with `ModuleNotFoundError`. This is a deployment-environment mismatch, not a code bug.

**Prevention:**
Verify `simple_pid` is in `requirements.txt` and confirm with `pip show simple-pid` on the RPi4 before testing. Add a version pin: the API is stable but `sample_time` behaviour changed between 1.x and 2.x.

**Phase note:** Pre-Phase 1 environment setup check.

---

### Pitfall 13: Tilt Sign Convention Inconsistency

**What goes wrong:**
In `TrackerMachine.do_tracking()`, the tilt correction sign differs from pan:
```python
pan_correction = -self.pid_pan(error_pan)   # negated
tilt_correction = self.pid_tilt(error_tilt) # not negated
```
This is intentional — camera geometry means pan and tilt require opposite sign conventions. However, the test tracker may re-implement this logic and get one axis backwards, causing the servo to actively move the target further from centre on one axis.

**Prevention:**
Copy the exact sign convention from `TrackerMachine.do_tracking()` into the test tracker. Document why each sign is what it is with a comment. Add a manual smoke test before PID tuning: move a face left in frame, verify servo pans left; move face up in frame, verify servo tilts up.

**Detection:**
- One axis tracks correctly, the other diverges continuously
- Face moves further from centre in one dimension over time

**Phase note:** Phase 2 (PID integration). Smoke test sign convention before any numerical tuning.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Phase 1: Camera init (Picamera2) | Camera not released on exit (Pitfall 2) | `try/finally` + signal handlers before any other code |
| Phase 1: Camera init (Picamera2) | Frame format RGB vs BGR (Pitfall 3) | Set `format="BGR888"` at configure time |
| Phase 1: Camera init (Picamera2) | Blocking `capture_array()` (Pitfall 11) | Async capture thread from day one |
| Phase 1: Hardware init | Brownout from servo jump (Pitfall 1) | `smooth_move_to(0,0)` is first operation |
| Phase 1: Hardware init | Wrong pulse width mapping (Pitfall 8) | Characterise servos and set explicit pulse widths |
| Phase 1: Isolation contract | Dual camera opener (Pitfall 4) | Run as standalone script; add startup guard |
| Phase 2: State machine | Stale scan state (Pitfall 9) | Sinusoidal scan using `time.time()` |
| Phase 2: Face detection | False detections hunting (Pitfall 7) | `minNeighbors=8`, detection streak filter |
| Phase 2: PID loop | Integral windup (Pitfall 5) | `pid.reset()` on TRACKING → SCANNING transition |
| Phase 2: PID loop | Variable-dt derivative spike (Pitfall 6) | Set `sample_time=0.033` on both PID objects |
| Phase 2: PID integration | Tilt sign error (Pitfall 13) | Smoke test sign convention before numerical tuning |
| Teardown/cleanup | Servo falls to mechanical stop (Pitfall 10) | Enforce cleanup order: neutral → detach → close camera |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Picamera2 resource cleanup (Pitfall 2) | MEDIUM | Based on known libcamera IPC behaviour; specific Bookworm kernel behaviour unverified via official docs |
| Brownout / servo jump (Pitfall 1) | HIGH | Explicitly documented in CLAUDE.md and PROJECT.md as known issue; confirmed in codebase |
| BGR/RGB format mismatch (Pitfall 3) | HIGH | Picamera2 default output format is RGB; confirmed in multiple community references |
| Dual camera opener conflict (Pitfall 4) | MEDIUM | Bookworm V4L2 libcamera bridge behaviour; pattern well-established in community |
| PID windup (Pitfall 5) | HIGH | Fundamental control theory; `simple_pid` integral accumulation is documented |
| PID sample_time / variable dt (Pitfall 6) | HIGH | Grounded in existing code and `simple_pid` documentation |
| HAAR false detections (Pitfall 7) | HIGH | Grounded in existing code — no dlib filter in test tracker by design |
| MG-90S pulse width (Pitfall 8) | MEDIUM | Common MG-90S behaviour; exact values depend on servo batch |
| Stale scan state (Pitfall 9) | HIGH | Directly observable from `TrackerMachine.do_scan()` logic |
| Tilt sign convention (Pitfall 13) | HIGH | Directly readable from `tracker.py` line 78 |

---

## Sources

- `src/hardware.py`, `src/tracker.py`, `src/camera.py`, `src/config.py`, `src/vision.py` — direct code analysis (HIGH confidence basis for code-grounded pitfalls)
- `CLAUDE.md` — documents brownout and smooth_move_to requirement explicitly
- `.planning/PROJECT.md` — documents v1.6 constraints and hardware setup
- `.planning/codebase/CONCERNS.md` — original risk analysis
- Training knowledge: Picamera2 resource management, libcamera on Bookworm, PID control theory, gpiozero AngularServo pulse width behaviour (MEDIUM confidence — training data, web search unavailable for verification)
