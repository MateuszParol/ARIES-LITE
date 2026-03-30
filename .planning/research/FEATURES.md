# Feature Research

**Domain:** Distributed embedded face tracking — RPi4 (vision) + Arduino (PID + HMI) via USB Serial
**Researched:** 2026-03-30
**Confidence:** MEDIUM-HIGH (architecture confirmed in PROJECT.md; ecosystem validated via web research)

---

## Context: What v2.0 Adds

v2.0 splits the v1.x monolith into two cooperating nodes:

- **Mozg (RPi4):** MediaPipe face detection, error calculation, serial TX
- **Uklad Wykonawczy (Arduino Leonardo):** Serial RX/parser, PID dual-axis at 100+ Hz, servo output, LCD 1602 HMI, buzzer feedback, hardware watchdog

The prior Python-level PID loop ran at ~30 Hz (OS-scheduled). The Arduino loop runs at a stable 100+ Hz using `millis()` timing in AVR firmware, decoupled from RPi Python GIL jitter. This is the core motivation for the split.

Features below are categorized for the v2.0 **distributed** layer only. Features already built in v1.x (HAAR/DNN detection, Picamera2 stream, Flask web UI, state machine, sinusoidal scan) are not re-listed unless the distributed architecture changes how they behave.

---

## Feature Landscape

### Table Stakes (Users Expect These)

These are non-negotiable for the distributed architecture to function. Without them, the system is either non-functional or unsafe.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| USB Serial link at 115200 baud | RPi4 and Arduino Leonardo communicate via `/dev/ttyACM0`; 115200 is the standard high-rate baud for real-time embedded control links | LOW | Confirmed: PROJECT.md pins this. `pyserial` on RPi, `Serial.begin(115200)` on Arduino. No alternatives needed. |
| Framed serial protocol (start byte + payload + checksum) | Raw ASCII or newline-delimited protocols silently lose frames under load; a framed binary protocol with checksum detects corruption | MEDIUM | Start byte `0xAA`, fixed payload length, XOR or CRC8 checksum. Both sides must agree on frame layout before any other feature works. This is the foundation. |
| Mode field in frame (SCAN / TRACK / IDLE) | Arduino must know whether to run PID or sinusoidal scan; RPi state machine controls mode transitions | LOW | One byte in payload. Arduino's behavior branches entirely on this field. Without it, Arduino cannot know what to do. |
| Error X / Error Y in frame (normalized float or int16) | PID setpoint is zero; error is the face displacement from frame center; Arduino needs this number to compute PID output | LOW | Two int16 values (pixels or normalized). Computed by RPi from MediaPipe bounding box centroid vs. frame center. |
| Arduino PID dual-axis at 100+ Hz | Core motivation for distributed architecture; hardware-rate servo updates produce smoother motion than Python-rate 30 Hz | MEDIUM | Use Brett Beauregard's `PID_v1` or `PID_v2` library (Arduino-native). `millis()` timing loop, `Kp/Ki/Kd` starting from v1.8-validated values (P=0.05, I=0.001, D=0.005 — will need re-tuning for degree-scaled error input). |
| Arduino Servo library on D9 (PAN) / D10 (TILT) | MG-90S servos require standard 50 Hz PWM; Arduino Servo library handles this correctly on Leonardo | LOW | Leonardo uses Timer 1 for Servo library by default. Two servos on D9 and D10 do not conflict. Attach at startup, detach on IDLE command. |
| Safe startup (smooth_move_to equivalent) | Direct servo jump from unknown position at power-on causes current spike and brownout; must interpolate to center | LOW | Arduino firmware: after `servo.attach()`, use a stepped loop moving toward center (1° per 20ms). Replicate the behavior already validated in v1.7 `smooth_move_to()`. |
| Watchdog: return to SCAN on communication timeout | If RPi crashes or Python script exits, Arduino must not hold last servo position indefinitely; autonomous recovery required | MEDIUM | Arduino-side timer: if no valid frame received in N ms (e.g., 500ms), transition to SCAN mode autonomously. This is the hardware safety net — required for unattended operation. |
| MediaPipe FaceDetector on RPi4 | Replaces DNN/HAAR; BlazeFace model achieves 10–15 FPS on RPi4 without accelerator (confirmed by benchmark research); lighter inference frees CPU for serial TX | MEDIUM | `mediapipe` pip package. Use `FaceDetector` with `LIVE_STREAM` mode for async processing. Returns normalized bounding box. Must convert to pixel error for serial TX. |
| Largest-face sticky tracking (one target) | System must lock onto a single face and not oscillate between multiple detections; "largest by bounding box area" is the standard heuristic for proximity | LOW | Filter `FaceDetectorResult.detections` by max bounding-box area. Carry last known target between frames (last-known-bbox pattern from v1.x). |
| Arduino firmware serial parser (non-blocking) | Arduino loop must parse incoming bytes without blocking the PID update cycle; blocking `Serial.readString()` destroys timing | MEDIUM | State-machine byte parser: `WAIT_START → READ_PAYLOAD → VERIFY_CHECKSUM → DISPATCH`. Never use `Serial.readString()` or `Serial.parseInt()` — both block until timeout. |
| Servo angle clamp (pan ±60°, tilt ±30°) | Hardware limits protect camera ribbon cable; must be enforced in Arduino firmware regardless of PID output | LOW | Clamp PID output before writing to servo. Same limits as v1.x `set_angles()`. |
| Graceful Python shutdown (serial close) | RPi script must close serial port cleanly on SIGINT/SIGTERM; otherwise `/dev/ttyACM0` stays locked | LOW | `try/finally` in `pi_brain.py`; call `ser.close()` in `finally` block. Pattern already used in v1.x signal handlers. |

### Differentiators (Competitive Advantage)

Features that provide meaningful capability beyond the basic functional requirement. Not blocking for MVP, but high value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| LCD 1602 status display (4-bit mode) | Physical HMI — visible system state without SSH or laptop; valuable in lab/demo context | MEDIUM | LCD lines: Row 0 = mode (`SKANOWANIE`, `SLEDZENIE`, `BEZCZYNNOSC`); Row 1 = diagnostic (pan angle, tilt angle, or face size). Use `LiquidCrystal` library. Update on state transition only — do not redraw every loop tick (LCD update takes ~2ms and pollutes timing). |
| Buzzer feedback on state transitions | Immediate audio confirmation of SCAN→TRACK and TRACK→LOST transitions; faster than reading LCD | LOW | D8 buzzer. Short beep (50ms) on TRACKING entry, double beep on TARGET_LOST. Use `tone()`/`noTone()`. Do not use `delay()` — schedule beep with `millis()` timer. |
| Abort button (D7): force return to SCAN | Physical "eject" for unwanted targets; ergonomic for demos and calibration | LOW | D7 as `INPUT_PULLUP`. Poll in Arduino loop; on LOW, transition to SCAN mode and reset PID. Debounce: require 20ms stable LOW before acting. |
| Face size (bounding box area) in serial frame | Lets Arduino know how close the face is; enables future proximity-based behavior (slow down at close range, alert at threshold) | LOW | Add one uint16 to serial frame: `face_size = bbox.width * bbox.height` (normalized, scaled to 0–1000). Arduino can display it on LCD Row 1 or log it without acting on it in v2.0. |
| Configurable servo direction per axis | New physical mount may reverse sign of pan or tilt; direction must be configurable without firmware rebuild | LOW | `#define PAN_INVERT 0` and `#define TILT_INVERT 1` at top of `.ino` file. Apply sign flip before servo write. Documented in CLAUDE.md: empirical calibration required on new mount. |
| AWB warm-up + lock for IMX219 on RPi | Prevents color cast (blue or green tint) confirmed in v1.7/v1.9; must be preserved in `pi_brain.py` | LOW | Copy the validated pattern from `test_tracker.py`: `start()` → sleep 2s → `capture_metadata()["ColourGains"]` → `set_controls(ColourGains)`. Already solved; just must not be forgotten in the rewrite. |
| Heartbeat frame from RPi (periodic TX even when no face) | Keeps watchdog timer alive on Arduino side; without heartbeat, Arduino times out and enters autonomous SCAN | LOW | RPi sends `mode=SCAN, error_x=0, error_y=0` frame at fixed interval (e.g., every 200ms) when no face detected. Watchdog timeout must be longer than this interval (e.g., 500ms). |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem natural to add but create disproportionate complexity or conflict with the architecture goals.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Bidirectional serial (Arduino → RPi feedback) | RPi could know actual servo angles for logging/display | Introduces ACK/NAK complexity; Arduino servo library does not provide position readback; adds parse state on RPi side; doubles protocol complexity for zero functional gain in v2.0 | RPi tracks estimated position by integrating sent corrections; display computed angle in Flask UI if needed |
| ASCII text serial protocol (`"TRACK:12,-5\n"`) | Human-readable; easier to debug with terminal | Larger frame size (10–20 bytes vs. 6–8 binary bytes); `atoi`/`sprintf` parsing in Arduino loop adds latency; newline framing fails if data contains newline byte; unreliable at 100 Hz TX rate | Fixed-width binary frame with start byte + checksum; use `socat` or simple Python logger to inspect frames during debug |
| PID tuning over serial at runtime | Adjust Kp/Ki/Kd without reflashing | Requires a separate command frame type, parser branch, EEPROM storage; adds edge cases (negative values, float encoding); out of scope for v2.0 | Recompile and flash with updated `#define` constants; Arduino flash cycle takes <10s with avrdude |
| MediaPipe Face Mesh (468 landmarks) | Richer face data, gaze estimation possible | Face Mesh runs at ~4–5 FPS on RPi4 vs. 10–15 FPS for FaceDetector; halves the command rate to Arduino; PID becomes jerky at 4 FPS input | Use FaceDetector (BlazeFace) which returns bounding box + 6 keypoints — sufficient for centroid error calculation |
| Multi-face priority tracking | Track the "most important" face among several | Requires face identification (dlib-level complexity) or arbitrary heuristics; two-face ambiguity causes PID oscillation between targets | Largest-face heuristic with sticky lock: once tracking starts, keep target until lost; only re-evaluate target selection on TARGET_LOST→SCANNING transition |
| Flask web UI retained in v2.0 | Live MJPEG stream useful for debugging | Flask requires a second thread and MJPEG encoding pipeline on RPi; adds CPU load that competes with MediaPipe and serial TX; increases startup complexity; v2.0 goal is lean brain script, not full server | Keep Flask in `legacy/` (v1.x monolit preserved). Optionally add a simple `/dev/ttyACM0` log viewer or SSH + `top` for v2.0 debugging. Flask can be re-added as a separate milestone. |
| Kalman filter on Arduino for servo smoothing | Smoother servo response to noisy detection input | Kalman state estimation requires 2×2 matrix operations per axis per tick at 100 Hz; AVR has no FPU; fixed-point Kalman is complex to implement and tune; PID derivative term already provides partial noise rejection | Tune PID `Kd` to damp detection noise; add a simple IIR low-pass on error input in Arduino: `filtered = alpha * error + (1-alpha) * prev_filtered` (integer arithmetic, no Kalman) |
| EEPROM persistence of PID gains | Survive reboot without reflashing | EEPROM has 100,000 write cycles; if gains are written every tuning session, lifespan is limited; adds write logic, verification, and corruption handling | Store gains as `#define` constants in firmware; reflash when changing gains. Gains are rarely changed after calibration. |

---

## Feature Dependencies

```
[Framed Serial Protocol]
    └──foundation for──> [Mode field in frame]
    └──foundation for──> [Error X/Y in frame]
    └──foundation for──> [Face size in frame]
    └──foundation for──> [Heartbeat frame]

[MediaPipe FaceDetector on RPi]
    └──produces──> [Error X/Y in frame]
    └──produces──> [Face size in frame]
    └──requires──> [AWB warm-up + lock for IMX219]

[Arduino Serial Parser (non-blocking)]
    └──consumes──> [Framed Serial Protocol]
    └──required by──> [Arduino PID dual-axis]
    └──required by──> [Watchdog timeout]

[Arduino PID dual-axis]
    └──requires──> [Arduino Serial Parser]
    └──requires──> [Arduino Servo library D9/D10]
    └──requires──> [Safe startup]
    └──requires──> [Servo angle clamp]

[Watchdog timeout]
    └──requires──> [Heartbeat frame]
    └──requires──> [Arduino Serial Parser]
    └──enables──> [Autonomous SCAN on RPi failure]

[LCD 1602 status display]
    └──requires──> [Mode field in frame] (to show mode)
    └──enhances──> [Buzzer feedback] (both are HMI)

[Abort button D7]
    └──independent of──> [LCD 1602]
    └──independent of──> [Serial protocol] (local Arduino input)
    └──enhances──> [Watchdog timeout] (both trigger SCAN transition)

[Largest-face sticky tracking]
    └──requires──> [MediaPipe FaceDetector]
    └──prerequisite for──> [Error X/Y in frame] (must select one face before computing error)
```

### Dependency Notes

- **Framed Serial Protocol must be defined first:** Every other feature on both sides depends on the agreed frame format. The protocol spec (byte layout, field widths, checksum algorithm) must be locked before writing either `pi_brain.py` or `aries_controller.ino`. Changing frame format mid-implementation forces changes on both sides simultaneously.

- **Arduino parser must be non-blocking before PID can run at 100 Hz:** A blocking serial read in the Arduino loop degrades PID update rate from 100 Hz to the worst-case serial timeout interval (default: 1000ms on Arduino). The byte-by-byte state-machine parser is required, not optional.

- **Heartbeat and watchdog are a pair:** Watchdog timeout (Arduino) and heartbeat TX (RPi) must be designed together. Watchdog timeout threshold (e.g., 500ms) must be at least 2x the heartbeat interval (e.g., 200ms) to avoid false watchdog triggers when MediaPipe skips a frame.

- **AWB lock is a dependency of MediaPipe pipeline:** If AWB is not locked, the IMX219 color channel response shifts during the first 2–3 seconds, making the first MediaPipe detections unreliable (face confidence drops under color cast). Warm-up must complete before detection loop starts.

- **Safe startup on Arduino must precede any PID activity:** If Arduino begins PID immediately after power-on without smooth startup, servo current spike can cause RPi USB power brownout, preventing serial link from establishing.

---

## MVP Definition

### Launch With (v2.0 core)

Minimum set to validate the distributed architecture end-to-end. All table stakes features.

- [ ] Framed serial protocol defined and documented (byte layout, field widths, checksum) — gate for all other work
- [ ] `pi_brain.py`: MediaPipe FaceDetector, AWB lock, largest-face selection, error calculation, serial TX, heartbeat, graceful shutdown
- [ ] `aries_controller.ino`: non-blocking serial parser, mode dispatch, PID dual-axis at 100+ Hz, Servo D9/D10, safe startup, servo angle clamp, watchdog timeout
- [ ] LCD 1602 shows current mode (SKANOWANIE / SLEDZENIE / BEZCZYNNOSC) — visual proof of state machine
- [ ] Buzzer beeps on TRACKING entry and TARGET_LOST — audio confirmation of transitions
- [ ] Abort button D7 returns to SCAN — physical safety override
- [ ] Configurable servo direction (`#define PAN_INVERT / TILT_INVERT`) — required because new mount orientation is unverified

### Add After Validation (v2.0 polish)

Features to add once end-to-end tracking works on hardware.

- [ ] Face size field in serial frame — add after base protocol validated; enables LCD Row 1 display
- [ ] PID gain empirical re-tuning on Arduino — after hardware assembled; starting point: v1.8 gains (P=0.05, I=0.001, D=0.005) with degree-scaled error normalization
- [ ] IIR low-pass filter on error input in Arduino — add if PID oscillates due to MediaPipe detection jitter (simpler than Kalman)
- [ ] LCD Row 1 diagnostic display (pan angle / face size) — after face_size field added to frame

### Future Consideration (v2.1+)

Features to defer until v2.0 is stable.

- [ ] Flask web UI re-integration — RPi resources freed after confirming MediaPipe + serial headroom; add as separate milestone
- [ ] Face database / target identity selection — requires dlib or face_recognition back on RPi; contradicts current MediaPipe-only vision strategy
- [ ] systemd service for auto-start — operational milestone after functional v2.0 validated
- [ ] Automated tests for serial protocol framing — after protocol is locked; regression-protect the frame spec

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Framed serial protocol spec | HIGH | LOW (design only) | P1 |
| MediaPipe FaceDetector + error TX | HIGH | MEDIUM | P1 |
| Arduino non-blocking serial parser | HIGH | MEDIUM | P1 |
| Arduino PID dual-axis 100+ Hz | HIGH | MEDIUM | P1 |
| Safe startup (servo interpolation) | HIGH | LOW | P1 |
| Watchdog + heartbeat pair | HIGH | MEDIUM | P1 |
| Servo angle clamp | HIGH | LOW | P1 |
| Graceful Python shutdown | HIGH | LOW | P1 |
| AWB warm-up + lock | HIGH | LOW (already validated) | P1 |
| Largest-face sticky tracking | HIGH | LOW | P1 |
| LCD 1602 mode display | MEDIUM | MEDIUM | P2 |
| Buzzer state feedback | MEDIUM | LOW | P2 |
| Abort button D7 | MEDIUM | LOW | P2 |
| Configurable servo direction | MEDIUM | LOW | P2 |
| Face size in frame | LOW | LOW | P2 |
| IIR low-pass on error | MEDIUM | LOW | P2 (after PID stability confirmed) |
| Flask UI re-integration | LOW | HIGH | P3 |
| EEPROM PID persistence | LOW | MEDIUM | P3 (explicitly an anti-feature for v2.0) |

**Priority key:**
- P1: Must have for v2.0 launch — system non-functional without these
- P2: Should have — system functional but incomplete without these
- P3: Nice to have — future consideration, do not plan in v2.0

---

## Competitor / Reference Architecture Analysis

| Feature | Pan-Tilt Face Tracker (PyImageSearch 2019) | SaraKIT MediaPipe RPi (2023) | ARIES-LITE v2.0 Approach |
|---------|----------------------------------------------|------------------------------|--------------------------|
| Vision model | HAAR cascade | MediaPipe Face Mesh (468 landmarks) | MediaPipe FaceDetector (BlazeFace, 6 landmarks) — lighter than Mesh |
| PID location | RPi Python (30 Hz) | RPi Python (30 Hz) | Arduino AVR (100+ Hz) — key differentiator |
| Servo backend | gpiozero AngularServo | Custom BLDC Gimbal motors | Arduino Servo library (MG-90S, standard 50 Hz PWM) |
| HMI | None | None | LCD 1602 + buzzer + abort button |
| Watchdog | None | None | Arduino-side timeout → autonomous SCAN |
| Heartbeat | None | None | RPi TX at 200ms interval |
| Serial protocol | N/A (single node) | N/A (single node) | Binary framed, checksum-verified |
| Face selection | Single detection | Largest face | Largest face + sticky lock |

Common pattern across all references: RPi does vision, Arduino/MCU does motor. ARIES-LITE v2.0 adds HMI and watchdog safety on top of this baseline, which are rare in hobby projects at this complexity level.

---

## Sources

- PROJECT.md: Architecture decisions locked (distributed RPi4 + Arduino Leonardo, USB Serial 115200, MediaPipe, PID 100+ Hz, LCD 1602, buzzer, button, watchdog)
- [Pan/tilt face tracking with RPi and OpenCV — PyImageSearch](https://pyimagesearch.com/2019/04/01/pan-tilt-face-tracking-with-a-raspberry-pi-and-opencv/)
- [Face detection guide for Python — MediaPipe / Google AI Edge](https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector/python)
- [MediaPipe for Raspberry Pi released — CNX Software (2023)](https://www.cnx-software.com/2023/08/21/mediapipe-for-raspberry-pi-released-no-code-low-code-on-device-machine-learning-solutions/) — confirms RPi4 FaceDetector at 10–15 FPS
- [SaraKIT Face Tracking MediaPipe RPi 64-bit — GitHub](https://github.com/SaraEye/SaraKIT-Face-Tracking-MediaPipe-Raspberry-Pi-64bit) — reference implementation (BLDC variant)
- [Simple and Robust Computer-Arduino Serial Communication — Medium/@araffin](https://medium.com/@araffin/simple-and-robust-computer-arduino-serial-communication-f91b95596788) — token semaphore anti-flood pattern
- [Raspberry Pi Arduino Serial Communication — The Robotics Back-End](https://roboticsbackend.com/raspberry-pi-arduino-serial-communication/) — baud rate, buffer, ACK patterns
- [Arduino Forum: Creating a Serial Port WatchDog](https://forum.arduino.cc/t/creating-a-serial-port-watchdog-with-arduino/468929) — watchdog timeout implementation pattern
- [Arduino Watchdog Timer Tutorial — microcontrollerslab.com](https://microcontrollerslab.com/arduino-watchdog-timer-tutorial/) — AVR watchdog prescaler and cli/sei usage
- [Framing in serial communications — Eli Bendersky](https://eli.thegreenplace.net/2009/08/12/framing-in-serial-communications/) — binary framing theory
- [Pan-tilt servo control using PID — Arduino Forum](https://forum.arduino.cc/t/pan-tilt-servo-control-using-pid-for-face-tracking-webcam/1131405) — PID + servo control integration pattern
- v1.8 validated PID gains: P=0.05, I=0.001, D=0.005 (`.planning/STATE.md` accumulated context)

---

*Feature research for: Distributed embedded face tracking — RPi4 + Arduino Leonardo (v2.0)*
*Researched: 2026-03-30*
