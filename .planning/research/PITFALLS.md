# Pitfalls Research — v2.0 Architektura Rozproszona

**Domain:** Distributed RPi4 (vision/brain) + Arduino Leonardo (PID/HMI) face tracking system — migrating from monolithic Python PID to distributed USB Serial architecture.
**Researched:** 2026-03-30
**Confidence:** HIGH (serial/Arduino pitfalls from direct forum/issue analysis) / MEDIUM (MediaPipe-specific RPi4 integration) / HIGH (project-specific — builds on v1.7/v1.9 known failures)

**Scope:** v2.0 milestone only — adding USB Serial protocol, Arduino PID firmware, MediaPipe vision, LCD HMI, and watchdog to an existing working system. The legacy monolith (v1.8) is preserved in `legacy/`. The pitfalls below are *addition and migration* failures, not general embedded pitfalls. Every pitfall maps to a specific v2.0 risk.

---

## Critical Pitfalls

### Pitfall 1: MediaPipe Does Not Install on Python 3.13 (RPi OS Trixie / System Default)

**What goes wrong:**
`pip install mediapipe` on Raspberry Pi OS Trixie (Debian 13, Python 3.13) fails with "no matching distribution found" or ABI mismatch error. MediaPipe officially supports Python 3.9–3.12 only. Python 3.13 introduces pybind11 ABI incompatibilities that prevent pre-built wheels from loading and building from source fails at the Bazel step.

The project currently runs Python 3.13.5 (per `STACK.md`). If the RPi is updated to Trixie or the active Python version is 3.13, MediaPipe installation will silently fail or produce wheels that segfault on import.

**Why it happens:**
MediaPipe pre-built wheels are compiled against specific Python ABI tags. The piwheels project provides `mediapipe` wheels for RPi, but only up to Python 3.12. Developers often `pip install mediapipe` without checking the active Python version first.

**How to avoid:**
1. Verify the active Python version on the RPi before starting v2.0: `python3 --version`. If it shows 3.13, MediaPipe will not install.
2. RPi OS Bookworm (Debian 12) ships Python 3.11. Stay on Bookworm for v2.0. Do not `apt upgrade` to Trixie.
3. If Python 3.13 is present, create a venv targeting 3.11 explicitly: `python3.11 -m venv venv --system-site-packages`. Verify: `python3 -c "import mediapipe; print(mediapipe.__version__)"`.
4. Always use `--system-site-packages` to retain access to `python3-picamera2` (installed via apt, not pip).

**Warning signs:**
- `pip install mediapipe` completes but `import mediapipe` raises `ImportError` or `Segmentation fault`
- `pip install mediapipe` fails with `No matching distribution found for mediapipe`
- `python3 --version` returns `3.13.x` on the RPi

**Phase to address:**
Phase 1 (Environment Setup / Pi Brain bootstrap) — MediaPipe installation must be verified as the first action before writing any vision code. Fail fast here rather than discovering it after writing `pi_brain.py`.

---

### Pitfall 2: Arduino Leonardo Serial Port Disappears When Python Opens a New Connection (DTR Reset)

**What goes wrong:**
When `pyserial` opens `/dev/ttyACM0`, it toggles the DTR line. On Arduino Leonardo (ATmega32U4 with native USB CDC), toggling DTR at 1200 baud triggers the bootloader reset. Even at 115200 baud, pyserial's default behavior sets DTR=True on open, which causes Leonardo to reset and re-enumerate as a new USB device — dropping the connection immediately.

The symptom: `pi_brain.py` opens the serial port, immediately loses the connection with `OSError: [Errno 5] Input/output error` or the port disappears from `/dev/ttyACM0` for 2–3 seconds, then reappears. The first packet sent is lost and the Arduino's firmware state is reset.

**Why it happens:**
Arduino Leonardo uses hardware-implemented USB CDC, unlike Uno (which uses a separate FTDI/CH340 chip). The 1200-baud DTR trick is built into the bootloader. pyserial's default DTR behavior triggers this on every reconnection from the Python side.

**How to avoid:**
Open the serial port with DTR disabled:
```python
ser = serial.Serial()
ser.port = "/dev/ttyACM0"
ser.baudrate = 115200
ser.dtr = False   # prevent reset-on-open
ser.open()
time.sleep(2.0)   # wait for Arduino to enumerate if it did reset
ser.reset_input_buffer()
```
Alternatively: `serial.Serial("/dev/ttyACM0", 115200, dsrdtr=False)`.

After opening, add a 2-second delay before sending the first packet — Arduino takes ~1.5s to re-initialize USB CDC after a physical reset.

Additionally, add a reconnection loop in `pi_brain.py` that re-opens the port on `SerialException`, since Leonardo may temporarily lose `/dev/ttyACM0` during OS USB suspend or after a programming upload.

**Warning signs:**
- `dmesg` shows `cdc_acm 1-1:1.0: ttyACM0: USB ACM device` appearing/disappearing repeatedly
- First `ser.read()` after open returns empty or raises `OSError`
- Arduino HUD/LCD shows reboot (RESET state) seconds after Pi connects

**Phase to address:**
Phase 2 (Serial Protocol) — DTR handling must be in the initial `SerialManager` implementation. Do not assume "just open the port."

---

### Pitfall 3: USB Serial Latency Is 16ms by Default on Linux — Kills 100 Hz PID Feedback Loop

**What goes wrong:**
Linux USB CDC ACM serial ports have a default latency timer of ~16ms. This means even at 115200 baud with tiny packets, the OS will not deliver incoming data to the application until 16ms have elapsed. For a 100 Hz PID loop on Arduino, the Pi's feedback acknowledgment (or the Pi's error packets arriving at Arduino) will arrive in batches with 16ms gaps rather than at 10ms intervals. This destroys the real-time feel of the distributed system and may cause the watchdog to fire spuriously.

**Why it happens:**
The Linux USB subsystem batches CDC ACM data transfers. The kernel latency timer (default 16ms) controls how often the USB host polls for new data. This is a well-known Linux USB serial issue — the pyserial maintainers added `low_latency` flag support in 2017 specifically for this reason.

**How to avoid:**
Set low-latency mode on the serial port via `setserial` or programmatically:
```bash
# One-time command (must repeat after each USB reconnect)
setserial /dev/ttyACM0 low_latency
```
Or in Python via pyserial (Linux only):
```python
import fcntl, termios, struct
ser = serial.Serial("/dev/ttyACM0", 115200)
# Set ASYNC_LOW_LATENCY flag
TIOCSSERIAL = 0x541F
buf = struct.pack('2H8I2H', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x2000)  # ASYNC_LOW_LATENCY = 0x2000
fcntl.ioctl(ser.fd, TIOCSSERIAL, buf)
```
For v2.0, the simpler path: add `setserial /dev/ttyACM0 low_latency` to the startup script or systemd unit, and document it as a required step.

Additionally: Arduino sends only when there is new error data (face detected). Pi does not need to poll — it reads in a background thread and the 16ms latency only affects the Pi→Arduino direction for commands, not the real-time PID loop (which runs autonomously on Arduino anyway).

**Warning signs:**
- Serial data arrives in bursts of ~6 packets every 16ms instead of continuously at 100 Hz
- `pi_brain.py` read loop shows timestamps clustered in 16ms windows
- Watchdog on Arduino fires even when Pi is actively sending, because Pi packets arrive in bursts with >15ms gaps

**Phase to address:**
Phase 2 (Serial Protocol) — measure actual round-trip latency early in protocol testing. If bursting is observed, add `setserial low_latency` to startup procedure.

---

### Pitfall 4: Arduino PID Integral Windup When Servo Is at Physical Limit

**What goes wrong:**
When the Arduino PID runs at 100+ Hz and the servo is at its physical limit (face at extreme edge of frame), the integral term accumulates while the output is clamped. When the face returns to center, the accumulated integral causes the servo to overshoot significantly — often swinging to the opposite limit. For a face tracking system, this produces oscillation: servo sweeps left-right repeatedly rather than settling on the target.

The br3ttb Arduino PID library does not enable anti-windup by default in older versions. Even with `SetOutputLimits()`, the internal integral sum continues growing beyond the output limits, and the clamped output just hides the windup until the setpoint changes.

**Why it happens:**
Anti-windup is not default behavior in the standard Arduino PID library. Developers add `SetOutputLimits(-limit, +limit)` thinking this prevents windup, but `SetOutputLimits` only clamps the *output*, not the integral accumulator. The windup still occurs internally.

**How to avoid:**
Use the QuickPID library (replaces br3ttb PID) which enables anti-windup by default via the `iAwCondition` mode:
```cpp
#include <QuickPID.h>
QuickPID panPID(&pan_input, &pan_output, &pan_setpoint);
panPID.SetOutputLimits(-PAN_LIMIT, PAN_LIMIT);
panPID.SetAntiWindupMode(QuickPID::iAwCondition);  // default — best for servos
panPID.SetMode(QuickPID::Control::automatic);
```

Alternatively with br3ttb PID: manually implement conditional integration — only add to the integral when the output is not saturated. This requires patching the library or using a wrapper.

Also configure derivative-on-measurement (not derivative-on-error) to prevent derivative kick when the setpoint changes abruptly (new face detection, tracking loss and re-acquisition):
```cpp
panPID.SetProportionalMode(QuickPID::pOnError);
panPID.SetDerivativeMode(QuickPID::dOnMeas);  // derivative on measurement — no kick
```

Starting PID gains from the empirically validated v1.8 values (P=0.05, I=0.001, D=0.005) is correct for initial tuning, but note that Arduino runs at 100 Hz while Python ran at ~30 Hz. The effective integral action is 3x stronger at 100 Hz for the same `I` gain — reduce `I` by 3x as the starting point: `I_arduino = 0.0003`.

**Warning signs:**
- Servo oscillates back and forth around center with increasing amplitude after face is centered
- After face moves to frame edge and returns to center, servo overshoots to opposite edge
- `panPID.GetPterm()` is small but `GetIterm()` is large despite face being centered
- PID output stays at maximum for several seconds after face re-enters center region

**Phase to address:**
Phase 3 (Arduino Firmware — PID) — anti-windup configuration is a firmware design decision, not a tuning parameter. Address at firmware architecture level before any gain tuning.

---

### Pitfall 5: Serial Protocol Frame Sync Loss — Arduino Gets Partial Packet on Pi Reconnect

**What goes wrong:**
If the Pi restarts, crashes, or the serial connection drops mid-transmission, the Arduino may have partially received a frame. On reconnect, the Arduino's serial buffer contains the tail of the old packet concatenated with the start of the new packet. If the protocol uses `readline()` / newline delimiters, this produces a garbled line that fails parsing — and the parser may silently drop it or misinterpret the error values as valid, causing a brief servo jump.

More dangerous: if the protocol uses binary framing without a sync byte, Arduino's `Serial.read()` gets out of phase with the packet boundaries and all subsequent packets are misinterpreted until the buffer is manually flushed.

**Why it happens:**
Serial communication has no implicit session concept. When a Python process re-opens `/dev/ttyACM0`, the Arduino's hardware UART buffer still contains whatever was there before. Arduino's `Serial.available()` will show bytes from before the reconnect.

**How to avoid:**
Use a text protocol with newline delimiter and a sync/heartbeat design:
```
SCAN\n
TRACK,ex,ey,sz\n
PING\n
```
Each line is self-contained. Arduino uses `Serial.readStringUntil('\n')` with a timeout. On parse failure (malformed tokens, wrong field count), Arduino discards the line and waits for the next `\n`. Partial packets from a prior session produce at most one malformed line, then the protocol self-heals.

On the Pi side: after opening the port, send `PING\n` and wait for `OK\n` before sending tracking data. This drains stale bytes from Arduino's buffer and confirms the firmware is responsive.

Additionally, define what Arduino does on parse failure: log to Serial (for Pi to monitor), keep the last valid command active (or revert to SCAN), never apply partial/corrupt error values to the PID.

**Warning signs:**
- Servo makes a brief unexpected jump immediately after Pi reconnects
- Arduino Serial debug shows malformed tokens (non-numeric where number expected)
- Tracking appears correct for most packets but has intermittent single-frame jumps
- `Serial.parseInt()` returns 0 for fields that should be non-zero (parseInt returns 0 on parse failure)

**Phase to address:**
Phase 2 (Serial Protocol) — frame sync resilience must be in the protocol design specification before either Pi or Arduino code is written. Test by unplugging and re-plugging the USB cable during operation.

---

### Pitfall 6: Arduino Watchdog Timer Causes Bootloader Lock (32u4-Specific)

**What goes wrong:**
Enabling the hardware watchdog timer (`wdt_enable(WDTO_2S)`) on Arduino Leonardo can cause a permanent reboot loop that makes the board impossible to reprogram via USB. The sequence: WDT fires → Arduino resets → bootloader starts (Caterina, ~8 seconds window for upload) → main sketch starts immediately → WDT fires again before sketch can execute `wdt_disable()` in `setup()` → infinite reset loop. The USB port disappears and the board appears "bricked."

This is a documented 32u4/Caterina bootloader interaction that does not affect Uno (Optiboot handles it cleanly).

**Why it happens:**
The Caterina bootloader on Leonardo does not call `wdt_disable()` at the start of the bootloader. When the WDT fires and the board resets, the WDT is still enabled with the short timeout. The bootloader runs for milliseconds, then the WDT fires again before the bootloader can enter the 8-second upload window.

**How to avoid:**
The correct and safe pattern for Leonardo WDT:
```cpp
#include <avr/wdt.h>

void setup() {
  // Disable WDT IMMEDIATELY as first line of setup()
  // This catches the case where we rebooted due to WDT
  MCUSR &= ~(1 << WDRF);  // clear WDT reset flag
  wdt_disable();

  // ... all other initialization ...
  Serial.begin(115200);
  // ... wait for serial ...

  // Enable WDT only AFTER everything is initialized
  // Use at least 2 seconds — never less than 1s on Leonardo
  wdt_enable(WDTO_4S);
}

void loop() {
  wdt_reset();  // pet the watchdog every iteration
  // ... rest of loop ...
}
```

Use `WDTO_4S` (4 seconds), not `WDTO_1S` or `WDTO_2S`. The 4-second window allows the Pi to restart and re-establish communication without triggering the watchdog during normal operation interruptions (Pi reboot takes ~25 seconds, so watchdog should trigger a return-to-SCAN, not a hardware reset).

Implement the watchdog in firmware as a software timeout counter, not hardware WDT: count milliseconds since last valid serial packet; if > 3000ms, transition to SCAN mode. This provides watchdog behavior without the hardware bootloader risk.

**Warning signs:**
- Arduino becomes unresponsive to upload after enabling WDT in sketch
- `dmesg` shows ttyACM0 appearing for ~100ms then disappearing repeatedly
- Arduino IDE upload fails with "no device found on /dev/ttyACM0"

**Phase to address:**
Phase 3 (Arduino Firmware) — implement watchdog as a software timeout counter in the firmware's main loop. Avoid hardware WDT (`wdt_enable()`) entirely unless comfortable with the bootloader risk. Document the decision.

---

### Pitfall 7: Servo Direction Wrong on New Arduino Mount — Requires Re-Verification

**What goes wrong:**
The v1.7 validated servo direction convention (`pan+=right, tilt+=down`, `korekta_tilt = -pid_tilt`) was established for the RPi/gpiozero/pigpio hardware path. In v2.0, servo control moves to `Arduino.Servo` library via `servo.write(angle)` — a completely different control path. The angle→direction mapping depends on: (a) servo physical orientation in the bracket, (b) how the Servo library maps `write(0)` to `write(180)` in terms of pulse width direction, and (c) whether the Arduino PID's setpoint convention (0 = center = 90° for a servo, or 0 = center = 0°) matches the Pi's error sign convention.

There is no guarantee the v1.7 sign convention survives the architecture migration.

**Why it happens:**
The Servo library `write(angle)` maps angle 0–180 to 1000–2000µs pulse width. If the servo is physically mounted with the shaft facing the opposite direction compared to the v1.7 mount, `write(90)` is still center but `write(91)` moves the opposite physical direction.

**How to avoid:**
Treat servo direction as empirically undefined on the new Arduino mount. Add a calibration routine to the Arduino firmware:
```
When Serial receives "CAL_PAN_PLUS", write pan servo to 100 (from 90 center) and log.
When Serial receives "CAL_PAN_MINUS", write pan servo to 80 and log.
```
From the Pi, send these calibration commands and observe physical movement direction. Determine the correct sign mapping before any PID test. The error sign convention on the Pi side (`blad_x = face_cx - frame_cx`, positive = face is right of center → servo should move right) must match the Arduino PID's correction direction.

Also: the MG90S on Arduino should use `servo.write(degrees)` with 0–180 range, not `servo.writeMicroseconds()`, unless pulse width calibration is needed for the new servos. Verify center position at `write(90)` before testing.

**Warning signs:**
- Servo moves away from face instead of toward it during TRACKING
- Tracking oscillates: servo chases face to limit, face re-centers, servo goes to opposite limit
- Pan converges correctly but tilt diverges (or vice versa) — one axis sign is wrong

**Phase to address:**
Phase 3 (Arduino Firmware) and Phase 4 (Integration Test) — always run direction verification as the first integration test before enabling PID in closed-loop mode.

---

### Pitfall 8: LCD Updates Block the Arduino Main Loop — Servo Jitter at PID Frequency

**What goes wrong:**
The LiquidCrystal library's `lcd.print()` and `lcd.setCursor()` use blocking `delayMicroseconds()` calls for LCD timing. On a 4-bit LCD 1602, writing one character takes ~37µs and clearing the display takes ~1500µs. If the Arduino main loop calls `lcd.clear()` and then prints two lines every iteration at 100 Hz (10ms intervals), the LCD operations consume 1500µs + 74µs per character × 32 characters = 4488µs ≈ 4.5ms per update — nearly half of the 10ms PID budget.

This delay directly adds jitter to the servo PWM update rate. The Servo library on Leonardo uses Timer4 hardware interrupts for PWM, so the servo signals themselves are not blocked. However, the PID computation and the `servo.write()` call are delayed by the LCD blocking time, making the effective PID rate drop from 100 Hz to ~67 Hz and introducing irregular spacing between updates.

**Why it happens:**
Developers write `lcd.clear(); lcd.setCursor(0,0); lcd.print(...)` in the same loop as `pid.Compute()` and `servo.write()` without considering that LCD operations are not instantaneous.

**How to avoid:**
Update the LCD at a much lower rate than the PID loop. Use a non-blocking timer pattern:
```cpp
unsigned long lastLCDUpdate = 0;
const unsigned long LCD_UPDATE_INTERVAL = 200;  // 5 Hz — sufficient for status display

void loop() {
  wdt_reset();
  processSerial();      // parse incoming Pi packet
  runPID();             // PID compute + servo.write()

  // LCD only at 5 Hz — not every loop iteration
  if (millis() - lastLCDUpdate >= LCD_UPDATE_INTERVAL) {
    updateLCD();
    lastLCDUpdate = millis();
  }
}
```

Never call `lcd.clear()` inside the high-rate loop — `clear()` has the longest blocking time. Instead, only update the LCD fields that changed by rewriting specific cursor positions.

**Warning signs:**
- Servo exhibits 5 Hz jitter (matching LCD update rate if LCD is called every loop)
- `Serial.println(millis())` shows loop iterations with irregular ~4ms gaps in otherwise 10ms loop
- Servo motion appears smooth during SCAN but jittery during TRACKING (when LCD prints error values every tick)

**Phase to address:**
Phase 3 (Arduino Firmware) — LCD update rate separation is a firmware architecture decision. Implement the `millis()`-based timer from the start; do not add it as a fix after observing jitter.

---

### Pitfall 9: pyserial readline() Blocks Forever Without a Timeout — Pi Brain Hangs

**What goes wrong:**
`serial.readline()` with `timeout=None` (pyserial default) blocks indefinitely waiting for a `\n` character. If the Arduino firmware is stuck in a WDT reset loop, rebooting, or the USB cable is unplugged, `readline()` in the Pi's receive thread never returns. The Pi brain's main loop hangs, face detection stops, and there is no way to recover without killing the process.

This is especially dangerous during startup: `pi_brain.py` calls `readline()` waiting for the Arduino handshake `OK\n`, but if Arduino takes >2 seconds to enumerate (due to Leonardo USB re-enumeration), the call blocks forever.

**Why it happens:**
pyserial's default timeout is `None` (blocking mode). Developers who are used to Arduino's `Serial.readStringUntil()` (which has its own timeout) assume pyserial behaves similarly.

**How to avoid:**
Always set a timeout when opening the serial port:
```python
ser = serial.Serial("/dev/ttyACM0", 115200, timeout=1.0)  # 1-second read timeout
```
With `timeout=1.0`, `readline()` returns an empty bytes object `b""` after 1 second if no newline arrives. The receive loop must handle empty responses gracefully:
```python
line = ser.readline().decode("utf-8", errors="ignore").strip()
if not line:
    # timeout — no data from Arduino
    handle_arduino_silence()
    continue
```
Design the receive loop to be non-blocking: use `ser.in_waiting` to check if bytes are available before reading, or run the serial receive in a dedicated daemon thread so main vision loop continues regardless of serial state.

**Warning signs:**
- `pi_brain.py` starts but never reaches "connection established" log message
- Process hangs on startup with no output after "opening serial port..."
- CPU usage is 0% but the process is alive (blocked in system call)
- `strace -p <pid>` shows process blocked on `read()` syscall

**Phase to address:**
Phase 2 (Serial Protocol) — timeout configuration is a baseline requirement for the `SerialManager` class. Test with Arduino disconnected to verify graceful degradation.

---

### Pitfall 10: AWB Blue/Green Tint Recurs With MediaPipe — New Camera Pipeline, Old Problem

**What goes wrong:**
The v1.7/v1.9 AWB fix (Picamera2 warm-up + ColourGains lock) was validated for the DNN/HAAR vision path. MediaPipe in v2.0 requires frames as RGB numpy arrays (not BGR). The conversion step changes: instead of `cv2.cvtColor(frame, cv2.COLOR_YUV420p2BGR)` (test tracker) or OpenCV VideoCapture BGR output (main app), `pi_brain.py` must provide RGB to MediaPipe.

If the YUV420→RGB conversion uses `COLOR_YUV420p2BGR` and then `cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)`, the double conversion adds processing cost and may produce incorrect colors if the intermediate BGR step has a non-neutral white balance. Alternatively, using `COLOR_YUV420p2RGB` directly skips one conversion but may be affected by the same ISP AWB issues.

More importantly: if `pi_brain.py` uses the Picamera2 `main` stream instead of `lores` for MediaPipe input, the default SRGGB10 (10-bit Bayer) raw format requires explicit ISP processing. Using the wrong stream format with MediaPipe produces a frame that looks like noise.

**Why it happens:**
MediaPipe's `FaceDetector.detect()` expects RGB. Developers port the YUV420→BGR pipeline from the test tracker and forget the MediaPipe RGB requirement, getting blue-shifted detections or no detections.

**How to avoid:**
Configure Picamera2 to provide a `main` stream in RGB888 format directly for MediaPipe, eliminating YUV conversion:
```python
config = picam2.create_preview_configuration(
    main={"size": (640, 480), "format": "RGB888"},
    controls={"ColourGains": AWB_FALLBACK_GAINS}
)
```
`picam2.capture_array("main")` then returns an RGB numpy array compatible with MediaPipe without any conversion.

The v1.9 AWB fix (warm-up + ColourGains lock + `AwbEnable: False`) remains valid and must be carried over to `pi_brain.py`. Do not skip the AWB lock because "MediaPipe doesn't need accurate color for face detection" — the MJPEG stream and any future HUD display will show the tint, and consistent AWB makes frame-to-frame comparison more reliable.

**Warning signs:**
- MediaPipe detections have correct bounding boxes but face landmarks are slightly off-color (blue faces in debug view)
- Frame 1 from Picamera2 appears heavily blue/green before AWB warmup completes
- MediaPipe `FaceDetector.detect()` returns `detections=[]` despite a visible face (wrong color format — BGRA or YUV passed as RGB)

**Phase to address:**
Phase 1 (Pi Brain — MediaPipe vision) — camera format configuration is the first decision. Prefer `RGB888` main stream over YUV+conversion. Re-apply the v1.9 AWB fix in the new `pi_brain.py` camera init.

---

### Pitfall 11: MediaPipe Face Detection Confidence Threshold Too Permissive — False Triggers Under Mixed Lighting

**What goes wrong:**
MediaPipe `FaceDetector` default `min_detection_confidence=0.5` is permissive for a face tracking system. On RPi4 under fluorescent or backlit conditions, MediaPipe detects false positives in reflective surfaces, posters, and bright windows at confidence 0.5–0.7. These false positives cause the system to transition from SCAN to TRACK on non-face objects, sending incorrect error values to Arduino, causing unexpected servo movement.

The v1.6/v1.7 system used a streak filter (3 consecutive HAAR detections required) to prevent this. MediaPipe returns a single-frame result with no built-in streak mechanism.

**Why it happens:**
MediaPipe's face detection model is highly accurate but designed for general use cases. In a robotic tracking application where false positive tracking is physically observable (servo moves toward wrong target), the cost of a false positive is higher than in a photo application. The default threshold is tuned for recall over precision.

**How to avoid:**
Use a higher confidence threshold for the tracking use case: `min_detection_confidence=0.75` as the starting point. Additionally, reimplement the streak filter concept: require N consecutive detections (N=3) of a face in roughly the same location (within 50px of bounding box center) before transitioning to TRACK mode. This prevents single-frame false positives from triggering servo movement.

For "sticky tracking" (largest face wins), implement: if multiple faces detected, choose the one with the largest bounding box area. If the largest face switches to a different face in consecutive frames, require 2 frames of agreement before accepting the new tracking target.

**Warning signs:**
- Arduino enters TRACK mode briefly when no person is in frame (servo moves toward background)
- System tracks a poster or monitor in the background instead of the nearest person
- Single-frame TRACK transitions that immediately return to SCAN (streaking false positive)

**Phase to address:**
Phase 1 (Pi Brain — vision logic) — confidence threshold and streak filter are pi_brain.py parameters, not Arduino parameters. Address in the vision layer before integration testing.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `Serial.readStringUntil('\n')` on Arduino with no timeout | Simple parsing | Arduino blocks if `\n` never arrives (Pi crash, partial packet) | Never — always set `setTimeout()` before readStringUntil |
| Hardcoding `/dev/ttyACM0` in Pi brain | Simple | Fails when ttyACM0 is ttyACM1 (e.g., another USB device present) | Only in early prototype — add configurable port in config.py |
| Sending full TRACK packets every frame (30 Hz) | Simple Pi code | 30 Hz × packet size = unnecessary serial throughput; bursts when MediaPipe drops frames | Better: send only on new MediaPipe detection; otherwise send PING heartbeat at 5 Hz |
| Hardware WDT with short timeout | Autonomous recovery | Leonardo bootloader lock (permanent bricking risk) | Never — use software timeout counter instead |
| LCD `clear()` every loop iteration | Always shows fresh state | 1.5ms blocking overhead per clear → PID jitter | Never in PID loop — use cursor repositioning at 5 Hz instead |
| PID I gain from Python simple_pid as-is on Arduino 100 Hz | Preserves validated gains | 3× stronger integral at 100 Hz vs 30 Hz — may cause oscillation | Only as starting point — expect I gain to need 3× reduction |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| pyserial + Leonardo | `serial.Serial("/dev/ttyACM0", 115200)` default DTR reset | Open with `dtr=False`, wait 2s, `reset_input_buffer()` before first packet |
| pyserial readline | `timeout=None` (blocks forever) | Always `timeout=1.0`; handle empty `b""` response in receive loop |
| MediaPipe + Picamera2 | Passing BGR frame or YUV frame to `FaceDetector.detect()` | Configure Picamera2 `main` stream as `RGB888`; pass directly to MediaPipe |
| MediaPipe + venv | `pip install mediapipe` fails on Python 3.13 | Verify Python ≤3.12 before install; use `--system-site-packages` venv for picamera2 access |
| Arduino PID library | `SetOutputLimits()` used as anti-windup | Use QuickPID with `iAwCondition`; or implement conditional integration manually |
| Arduino Servo + LCD | LiquidCrystal operations in PID loop | Update LCD at 5 Hz max using `millis()` timer; never `lcd.clear()` in main loop |
| Arduino WDT | `wdt_enable(WDTO_2S)` on Leonardo | Use software timeout counter (`millis()` since last valid packet) instead of hardware WDT |
| Serial protocol | Arduino `Serial.parseInt()` on malformed input | `parseInt()` returns 0 silently; use explicit field count validation, discard malformed lines |
| USB serial latency | Pi reads at full speed but data arrives in 16ms bursts | `setserial /dev/ttyACM0 low_latency` in startup script; or design protocol tolerant of bursty delivery |
| Servo direction | Assuming v1.7 sign convention carries to Arduino mount | Verify empirically: CAL_PAN_PLUS command → observe physical movement direction before enabling PID |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| MediaPipe full-resolution frame on RPi4 | <5 FPS, Pi CPU at 100%, Arduino starved of updates | Use 640x480 `main` stream; MediaPipe face detection is fast on this size | Breaks at 1280x720+ on RPi4 |
| Serial TX on every MediaPipe frame regardless of detection | Serial buffer fills when MediaPipe drops frames | Send TRACK packet only on valid detection; send PING at 5 Hz when no face | Serial buffer overflow when Pi processes slowly |
| Arduino `Serial.print()` debug in PID loop | PID timing jitter, loop rate drops | All debug prints gated behind `#define DEBUG` compile flag; disable for production | Any `Serial.print()` in 100 Hz loop adds ~100µs overhead |
| Picamera2 `main` stream at 1080p for vision | 200ms+ MediaPipe latency | Use 640x480 for vision; full resolution only if MJPEG stream to Flask is needed separately | >720p breaks real-time on RPi4 |
| pyserial in Pi main loop (blocking) | Vision loop blocked waiting for serial | Serial receive in dedicated daemon thread; use `queue.Queue` to pass data to vision loop | Any blocking serial call in vision loop stalls face detection |

---

## "Looks Done But Isn't" Checklist

- [ ] **MediaPipe install**: `python3 -c "import mediapipe; print(mediapipe.__version__)"` succeeds — not just `pip install` completion
- [ ] **Serial connection**: Pi opens port without Arduino resetting — verify by NOT seeing Arduino LCD reinitialize on Pi connect
- [ ] **Serial timeout**: Disconnect USB while pi_brain.py runs — confirm process recovers gracefully (not hung)
- [ ] **Serial frame sync**: Kill and restart pi_brain.py while Arduino is tracking — confirm no servo jump on reconnect
- [ ] **PID anti-windup**: Hold face at frame edge for 5 seconds, then center — confirm no overshoot beyond center
- [ ] **Arduino WDT safety**: Confirm `wdt_disable()` is the first line of `setup()` before `Serial.begin()`
- [ ] **LCD non-blocking**: Measure Arduino loop time with `micros()` — confirm no 1500µs spikes from `lcd.clear()`
- [ ] **Servo direction verification**: CAL_PAN_PLUS command moves pan servo right (facing camera) before PID enabled
- [ ] **AWB carry-over**: `pi_brain.py` camera init includes warm-up + ColourGains lock from v1.9 fix
- [ ] **MediaPipe RGB format**: `pi_brain.py` passes RGB array to FaceDetector — not BGR, not YUV
- [ ] **USB latency**: `setserial /dev/ttyACM0 low_latency` applied — verify with latency measurement script
- [ ] **Python version**: `python3 --version` on RPi shows 3.11.x or 3.12.x — not 3.13

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| MediaPipe won't install (Python 3.13) | MEDIUM | Create venv with `python3.11` explicitly; or stay on Bookworm (Python 3.11 default) |
| Arduino bricked by WDT (bootloader loop) | HIGH | Physical reset button press during upload window; replace Caterina with Optiboot if bricked permanently |
| Leonardo resets on Pi serial open | LOW | Add `dtr=False` to `serial.Serial()` constructor; add 2s post-open delay |
| Serial blocking (readline hangs) | LOW | Add `timeout=1.0` to Serial constructor; redesign receive loop as non-blocking thread |
| PID windup causing oscillation | MEDIUM | Switch to QuickPID with `iAwCondition`; reduce I gain by 3×; add output dead zone ±5° |
| Servo direction inverted | LOW | Add sign inversion flag in Arduino firmware config constants; empirically verify and set |
| LCD jitter in PID loop | LOW | Move all LCD calls to 5 Hz section gated by `millis()` timer |
| AWB tint with MediaPipe RGB888 | LOW | Apply v1.9 warm-up + ColourGains lock in pi_brain.py camera init; verify with `capture_metadata()` |
| Serial frame desync on reconnect | LOW | Add PING/OK handshake after port open; clear Arduino input buffer with flush |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| MediaPipe Python 3.13 incompatibility | Phase 1: Environment Setup | `import mediapipe` succeeds on RPi before writing pi_brain.py |
| Leonardo DTR reset on serial open | Phase 2: Serial Protocol | Pi connects without triggering Arduino reboot (LCD does not flash) |
| USB serial 16ms latency | Phase 2: Serial Protocol | Latency measurement script shows <2ms inter-packet gap after low_latency set |
| Serial readline blocking | Phase 2: Serial Protocol | Disconnect USB during run — pi_brain.py recovers within 2 seconds |
| Serial frame desync on reconnect | Phase 2: Serial Protocol | Kill and restart Pi process 5 times — no servo jumps observed |
| Arduino PID integral windup | Phase 3: Arduino Firmware | Face at edge 5s, returns to center — no overshoot beyond ±10° |
| Arduino WDT bootloader lock | Phase 3: Arduino Firmware | Firmware uploaded successfully 5 times after WDT enabled in sketch |
| LCD blocking PID loop | Phase 3: Arduino Firmware | Loop time measured with `micros()` — no spikes >500µs in 100 Hz operation |
| Servo direction wrong on new mount | Phase 4: Integration Calibration | CAL_PAN_PLUS/MINUS commands match expected physical direction before PID enabled |
| AWB tint recurs in pi_brain.py | Phase 1: Pi Brain camera init | Frame 1 shows neutral color; ColourGains lock verified with `capture_metadata()` |
| MediaPipe false positives | Phase 1: Pi Brain vision logic | 0 false TRACK transitions in 2-minute test with no person in frame |
| MediaPipe BGR/YUV format error | Phase 1: Pi Brain vision logic | `FaceDetector.detect()` returns correct bounding boxes; not empty |

---

## Sources

### PRIMARY (HIGH confidence — official documentation and issue trackers)
- [MediaPipe Python 3.13 issue #6159](https://github.com/google-ai-edge/mediapipe/issues/6159) — confirmed no Python 3.13 wheels; Bazel/pybind11 ABI incompatibility
- [MediaPipe + Picamera2 issue #755](https://github.com/raspberrypi/picamera2/issues/755) — `--system-site-packages` venv required; shebang conflicts with MediaPipe
- [Arduino Leonardo WDT bootloader issue #6077](https://github.com/arduino/Arduino/issues/6077) — confirmed 32u4/Caterina WDT bootloader lock pattern
- [pyserial DTR issue #124](https://github.com/pyserial/pyserial/issues/124) — DTR toggles on port open by default; set `dtr=False` before open
- [Arduino USB serial logging freeze issue #5797](https://github.com/arduino/Arduino/issues/5797) — serial output buffer fills if host does not read; Leonardo-specific behavior
- [QuickPID library](https://github.com/Dlloydev/QuickPID) — anti-windup `iAwCondition` mode; derivative-on-measurement; Arduino-optimized PID
- [Brett Beauregard PID anti-windup](http://brettbeauregard.com/blog/2011/04/improving-the-beginners-pid-reset-windup/) — standard reference for Arduino PID anti-windup patterns
- [pyserial low_latency PR #2102](https://github.com/serialport/node-serialport/pull/2102) — ASYNC_LOW_LATENCY flag; Linux USB CDC ACM 16ms default latency confirmed

### SECONDARY (MEDIUM confidence — community forums and RPi project docs)
- [Arduino Forum: Leonardo comport disappears](https://forum.arduino.cc/t/leonardo-comport-disappears/1031387) — USB re-enumeration on Leonardo; port transiently disappears after programming
- [Arduino Forum: Slow RPi4 → Arduino Mega serial](https://forum.arduino.cc/t/very-slow-serial-communication-raspberry-pi-4-arduino-mega/680162) — 2-second delays at default settings; low_latency resolves
- [Arduino Forum: servo jitter with I2C](https://forum.arduino.cc/t/servo-jittering-when-using-i2c/475789) — LiquidCrystal 4-bit mode blocking calls cause servo jitter
- [RPi Forums: MediaPipe Bookworm only](https://forums.raspberrypi.com/viewtopic.php?t=384248) — Bookworm (Debian 12) required; Trixie not supported
- [Picamera2 issue #825](https://github.com/raspberrypi/picamera2/issues/825) — `ColourGains` + `AwbEnable` sequencing; version-dependent behavior

### PROJECT HISTORY (HIGH confidence — empirically validated in prior milestones)
- v1.7 key decision: `tilt negation = -pid_tilt` confirmed empirically on physical mount — must re-verify on Arduino mount
- v1.7 known issue: AWB blue tint from cold start; ColourGains lock after 2s warm-up resolves
- v1.9 known issue: `ColourGains=(1.0,1.0)` produces green tint; fallback must use sensor-specific values
- v1.8 PID gains: P=0.05, I=0.001, D=0.005 validated at ~30 Hz Python loop rate; I gain must be scaled for 100 Hz Arduino

---
*Pitfalls research for: v2.0 Architektura Rozproszona — RPi4 (MediaPipe) + Arduino Leonardo (PID+HMI) via USB Serial*
*Researched: 2026-03-30*
