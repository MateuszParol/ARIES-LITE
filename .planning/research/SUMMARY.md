# Project Research Summary

**Project:** ARIES-LITE v2.0 — Architektura Rozproszona (RPi4 Mozg + Arduino Leonardo Uklad Wykonawczy)
**Domain:** Distributed embedded face tracking — RPi4 (vision + serial TX) + Arduino Leonardo (PID + servo + HMI)
**Researched:** 2026-03-30
**Confidence:** HIGH (architecture and pitfalls from authoritative sources and project-specific empirical history)

## Executive Summary

ARIES-LITE v2.0 migrates from a Python monolith (single RPi4, gpiozero/pigpio servos, ~30 Hz PID) to a distributed two-node system: the RPi4 handles only vision (MediaPipe FaceDetector) and serial transmission, while an Arduino Leonardo runs dual-axis PID at 100+ Hz with MG-90S servos, LCD 1602 HMI, buzzer, and an abort button. The core motivation is deterministic real-time servo control: the Arduino loop achieves 10ms±1ms dT stability versus Python's 30ms with 10-30ms GIL/GC jitter. This is the same pattern used in industrial robotics (compute node + controller node) and validated by the SaraKIT MediaPipe/RPi reference implementation.

The recommended approach is a strict Brain-Muscle split: the RPi computes pixel error from MediaPipe bounding boxes and sends 8-byte binary frames (start byte + mode + int16 error_x + int16 error_y + uint8 face_size + XOR checksum) over USB Serial at 115200 baud. The Arduino receives frames via a non-blocking byte-state-machine parser, runs PID independently of the serial rate, and uses a millis()-based software watchdog (not hardware AVR WDT) to return to autonomous scan if the Pi goes silent. This architecture guarantees servo motion continues even when the Pi restarts or Python crashes.

The primary risks are: MediaPipe installation failing on Python 3.13 (stay on Bookworm + Python 3.11), Arduino Leonardo DTR-reset disrupting the USB connection on every Python reconnect (open serial with dtr=False), Linux USB CDC 16ms latency batching that disrupts timing (setserial low_latency required), and Arduino PID integral windup at servo limits (use QuickPID with iAwCondition anti-windup, not the default br3ttb PID library). The serial protocol frame format must be locked before any other implementation begins — both sides depend on it and changing it mid-implementation forces simultaneous changes to two code bodies.

---

## Key Findings

### Recommended Stack

The v2.0 stack replaces the Python-side servo control (gpiozero + pigpio) entirely. On the RPi4, the new dependencies are `mediapipe` (BlazeFace FaceDetector via Tasks API) and `pyserial`. The `picamera2` backend is retained unchanged; the AWB lock sequence (start + 2s sleep + capture_metadata + set_controls) is validated and must be carried into `pi_brain.py` verbatim. On the Arduino, the firmware uses the standard `Servo` library on D9/D10, `LiquidCrystal` in 4-bit mode on D2-D5/D11/D12, and `QuickPID` (replaces br3ttb PID) for anti-windup support.

A critical installation constraint: MediaPipe wheels are not published for Linux aarch64 on PyPI as of March 2026, and v1.8 research documented this as a blocker. The resolution is to use piwheels or a confirmed community wheel targeting Python 3.11. The project must stay on RPi OS Bookworm (Python 3.11) and must NOT upgrade to Trixie (Python 3.13). Installation must be verified via `import mediapipe` before writing any vision code.

**Core technologies:**
- `mediapipe` (Tasks API, FaceDetector, BlazeFace): vision — estimated 15-25 FPS on RPi4, lighter than Face Mesh (~4-5 FPS)
- `pyserial` 3.x: USB serial TX from Pi — fire-and-forget, no blocking ACK
- `picamera2` (system apt package): camera backend — YUV420/NV12 capture, AWB lock; requires `--system-site-packages` venv
- `QuickPID` (Arduino library): PID with iAwCondition anti-windup and derivative-on-measurement — replaces br3ttb PID_v1
- `Servo` (Arduino built-in): MG-90S PWM control on D9 (pan) / D10 (tilt)
- `LiquidCrystal` (Arduino built-in): LCD 1602 in 4-bit mode

**What is removed from requirements.txt:** `gpiozero`, `pigpio`, `dlib`, `face_recognition`. The Flask web server and MJPEG stream move to `legacy/` for v2.0 (re-addable as a v2.1 milestone).

---

### Expected Features

The protocol spec is the absolute first deliverable — it blocks all other work on both sides. Every other feature depends on the agreed 8-byte frame layout.

**Must have (table stakes — system non-functional without these):**
- Framed binary serial protocol (0xAA start byte, mode byte, int16 error_x, int16 error_y, uint8 face_size, XOR checksum, fixed 8 bytes) — gate for all other work
- MediaPipe FaceDetector + largest-face sticky selection + pixel error calculation (RPi)
- AWB warm-up + lock (2s sleep + capture_metadata + set_controls) — carried from validated v1.9 code
- Heartbeat TX from RPi at 200ms intervals when no face detected — keeps Arduino watchdog alive
- Graceful Python shutdown: serial.close() in try/finally
- Arduino non-blocking serial parser (byte-state-machine: WAIT_START → READ_PAYLOAD → VERIFY_XOR → DISPATCH)
- Arduino dual-axis PID at 100 Hz via millis() timing, QuickPID with anti-windup
- Arduino Servo on D9/D10, safe startup (smooth interpolation to center at 1 degree per 20ms in setup())
- Servo angle clamp (pan ±60°, tilt ±30°) enforced in Arduino before servo.write()
- Software watchdog (millis()-based, NOT AVR hardware WDT): return to SCAN if no valid frame for 2000ms
- `#define PAN_DIR / TILT_DIR` empirical sign calibration constants

**Should have (differentiators — system functional but incomplete without):**
- LCD 1602 showing current mode (SKANOWANIE / SLEDZENIE / BEZCZYNNOSC) — physical HMI proving state machine
- Buzzer beep on TRACKING entry and TARGET_LOST transition — audio confirmation of state changes
- Abort button D7 (INPUT_PULLUP, debounce 20ms) — physical safety override
- Face size field in serial frame (uint8, enables LCD Row 1 diagnostic)
- IIR low-pass filter on error input in Arduino — add only if PID oscillates from MediaPipe detection jitter

**Defer (v2.1+):**
- Flask web UI re-integration (adds CPU load competing with MediaPipe; put in legacy/ for v2.0)
- Face identity database / target selection (requires dlib back on RPi; contradicts lean vision strategy)
- systemd auto-start service (operational concern, after functional v2.0 validated)
- Runtime PID tuning over serial (out of scope; reflash with updated #define constants instead)
- Bidirectional serial with Arduino ACK (doubles protocol complexity for zero functional gain)

---

### Architecture Approach

The system is organized as two independent execution contexts connected by a unidirectional serial link. The RPi4 runs a minimal 2-thread Python process: a daemon thread captures Picamera2 YUV420/NV12 frames, and the main thread runs MediaPipe detection, error calculation, and serial TX. The Arduino runs a single-threaded deterministic loop: parse serial (non-blocking), run PID tick at 100 Hz via millis() guard, update LCD at 5 Hz, handle button debounce. The serial link is fire-and-forget from the Pi side; Arduino holds last-known error values between frames and runs PID independently. If serial goes silent, the software watchdog transitions Arduino to autonomous SCAN after 2000ms.

**Major components:**
1. `Picamera2Stream` (RPi daemon thread) — YUV420/NV12 capture, AWB lock, shared frame buffer with threading.Lock
2. `MediaPipe FaceDetector + ErrorCalculator` (RPi main thread) — BlazeFace detection, largest-face selection, pixel error to int16
3. `SerialSender` (RPi main thread) — 8-byte binary frame encoding, XOR checksum, pyserial.write (non-blocking, <0.1ms per frame)
4. `SerialParser` (Arduino) — byte state machine, XOR verify, updates shared volatile state (error_x, error_y, tryb)
5. `PIDController` (Arduino, 100 Hz) — QuickPID dual-axis, iAwCondition anti-windup, dOnMeas derivative mode, millis() timing
6. `ServoDriver` (Arduino) — Servo.write(angle+90) for pan D9 / tilt D10, angle clamp before write
7. `WatchdogTimer` (Arduino) — millis()-based, NOT hardware AVR WDT (documented Leonardo/Caterina bootloader bug)
8. `LCD1602 + BuzzerButton` (Arduino, throttled to 5 Hz) — LiquidCrystal update, tone() on state transitions, D7 abort

---

### Critical Pitfalls

1. **MediaPipe not installable on Python 3.13** — Verify `python3 --version` on the RPi before writing any code. Must be 3.11 (Bookworm). Use `--system-site-packages` venv for picamera2 access. Fail fast in Phase 1 before any vision code is written.

2. **Arduino Leonardo DTR reset on serial.open()** — pyserial default behavior triggers bootloader reset on Leonardo via DTR toggle. Open with `ser.dtr = False` before `ser.open()` and add a 2s sleep before first TX. Add reconnection loop on SerialException in pi_brain.py. Address in Phase 2 protocol implementation, not as an afterthought.

3. **Linux USB CDC 16ms latency timer** — Default kernel USB polling batches serial data in 16ms windows. At 100 Hz PID (10ms cycle), Pi packets arrive in bursts, potentially causing spurious watchdog fires. Run `setserial /dev/ttyACM0 low_latency` at startup. Document as a required step. Measure latency early in Phase 2.

4. **Arduino PID integral windup at servo limits** — The default br3ttb PID library does not prevent integral accumulation past output limits. Use QuickPID with `iAwCondition` and `dOnMeas`. Also reduce I gain 3x from v1.8 values (Python 30 Hz → Arduino 100 Hz = 3x stronger integral action for the same Ki starting value of 0.001 → use 0.0003). Address in Phase 3 firmware design, not during gain tuning.

5. **AVR hardware WDT locks Leonardo bootloader** — `wdt_enable()` on Leonardo creates an infinite reset loop that prevents USB reprogramming (documented 32u4/Caterina bug). Use millis()-based software watchdog exclusively. Never call `wdt_enable()` in v2.0 firmware.

6. **Serial frame sync loss on Pi reconnect** — Arduino serial buffer may contain partial frame tail from a prior session. The 0xAA start byte allows parser re-sync: discard bytes until 0xAA, then read exactly 7 more bytes and verify XOR. Test by unplugging and re-plugging USB during operation in Phase 2.

7. **Servo direction undefined on new Arduino mount** — v1.7 empirical sign convention (TILT_DIR = -1) was validated for gpiozero/pigpio hardware path, not Arduino Servo library. Run a direction calibration routine as the first integration test in Phase 4, before enabling closed-loop PID.

8. **LCD blocking at PID rate** — LiquidCrystal `lcd.clear()` takes ~1500µs. Calling it in the 10ms PID loop consumes 15% of the PID budget and causes servo update jitter. Update LCD at maximum 5 Hz with millis() guard; never call `lcd.clear()` in the high-rate path. Address in Phase 5 HMI code.

---

## Implications for Roadmap

Based on the dependency graph from FEATURES.md and the build order from ARCHITECTURE.md, a 6-phase structure is recommended. The serial protocol is a hard gate for all other work. Arduino firmware phases are ordered to allow hardware testing at each stage without requiring the full Pi vision stack.

### Phase 1: Environment + Protocol Specification
**Rationale:** Two hard prerequisites before any code can be written: MediaPipe must be confirmed installable on the target RPi, and the 8-byte frame format must be fully specified and locked. Every other component on both sides depends on the agreed frame layout.
**Delivers:** Verified MediaPipe import on RPi4, documented binary protocol spec (byte layout, field widths, XOR formula), project structure (`src/arduino/aries_controller/`, `src/vision/pi_brain.py`, `legacy/`)
**Addresses:** Foundation for all table-stakes features; framed protocol is their shared prerequisite
**Avoids:** Pitfall 1 (MediaPipe Python 3.13 — fail fast here), Pitfall 6 (frame sync loss — spec locked before implementation)
**Research flag:** Standard patterns. Protocol design is covered by Eli Bendersky framing article and ARCHITECTURE.md Pattern 3.

### Phase 2: Serial Link — Pi Sender + Arduino Parser (Echo Test)
**Rationale:** Implement both ends of the serial link independently of vision and PID. Test with hardcoded values from the Pi and an Arduino Serial Monitor echo. Isolates the serial layer and validates DTR handling and latency before either vision or servo hardware is involved.
**Delivers:** `SerialSender` in pi_brain.py (dtr=False open, 2s delay, reconnection loop, low_latency mode), non-blocking byte state machine parser in aries_controller.ino, echo test confirming frame round-trip
**Uses:** pyserial, Arduino Serial, XOR checksum
**Avoids:** Pitfall 2 (DTR reset), Pitfall 3 (16ms USB latency), Pitfall 6 (frame sync re-sync on reconnect)
**Research flag:** Standard patterns. No additional research needed.

### Phase 3: Arduino Firmware — Safe Startup + PID + Servo
**Rationale:** With a working serial parser, inject hardcoded error values from the Pi and validate Arduino PID against live servos. Isolates the firmware layer from MediaPipe. Anti-windup configuration is a firmware architecture decision that must be made here, not during gain tuning.
**Delivers:** QuickPID dual-axis with iAwCondition + dOnMeas, millis()-throttled PID loop at 100 Hz, safe startup (smooth interpolation to center in setup()), servo angle clamp, millis()-based software watchdog (NOT AVR WDT), `#define PAN_DIR / TILT_DIR` with calibration routine
**Implements:** PIDController + ServoDriver + WatchdogTimer components
**Avoids:** Pitfall 4 (integral windup — architecture decision here), Pitfall 5 (AVR WDT bootloader lock), Pitfall 7 (servo direction — calibration routine before any PID test)
**Research flag:** Standard patterns. QuickPID is well-documented. Safe startup pattern validated in v1.7.

### Phase 4: RPi Vision — MediaPipe + Error Calculation + Serial TX
**Rationale:** With the Arduino firmware accepting and acting on serial frames, implement the RPi vision pipeline and connect end-to-end. First integration test: run direction calibration before enabling closed-loop PID.
**Delivers:** `pi_brain.py` with Picamera2Stream, MediaPipe FaceDetector Tasks API (VIDEO mode), largest-face sticky selection, AWB lock sequence (start + 2s sleep + capture_metadata + set_controls), int16 error calculation, heartbeat TX at 200ms, graceful SIGINT shutdown
**Avoids:** Pitfall 1 (MediaPipe install — verified in Phase 1), Pitfall 7 (direction — calibration before closed-loop PID)
**Research flag:** MEDIUM confidence on MediaPipe FPS. 15-25 FPS is an estimate from face_landmarker benchmarks. Measure empirically at the start of this phase. If FPS < 10, reduce resolution to 240x180.

### Phase 5: Arduino HMI — LCD + Buzzer + Button
**Rationale:** After end-to-end tracking is validated, add the HMI layer. These are independent of PID correctness and should not be in the critical path for functional validation.
**Delivers:** LCD 1602 showing SKANOWANIE/SLEDZENIE/BEZCZYNNOSC (Row 0), diagnostic data (Row 1), buzzer tone() on state transitions, D7 abort button with 20ms debounce
**Implements:** LCD1602 + BuzzerButton component
**Avoids:** Pitfall 8 (LCD blocking PID loop — millis() guard at 200ms, no lcd.clear() in high-rate path)
**Research flag:** Standard patterns. LiquidCrystal library well-documented.

### Phase 6: Watchdog Validation + Stability Testing
**Rationale:** Final phase validates the hardware safety net and system stability under fault conditions. Tests include: Pi crash → Arduino autonomously scans after 2000ms → Pi restarts → tracking resumes.
**Delivers:** Confirmed watchdog behavior on deliberate Pi shutdown, latency measurements confirming serial timing, empirical PID gain re-tuning if needed (starting from v1.8 values with I reduced 3x for 100 Hz rate: Ki=0.0003), optional IIR error low-pass if detection jitter causes oscillation
**Avoids:** All pitfalls — this phase stress-tests the mitigations installed in Phases 2-4
**Research flag:** No additional research needed. Tests are empirical.

---

### Phase Ordering Rationale

- Protocol spec before any code: the 8-byte frame layout is shared state between two code bodies. Defining it first prevents the most expensive rework scenario (mid-implementation protocol change requiring simultaneous edits to pi_brain.py and aries_controller.ino).
- Serial link tested in isolation (Phase 2) before adding vision complexity (Phase 4) or servo hardware complexity (Phase 3): single-variable failure modes during debugging.
- PID firmware (Phase 3) before Pi vision (Phase 4): lets Phase 3 use hardcoded test values, keeping servo hardware debugging independent of MediaPipe FPS variability.
- HMI (Phase 5) after tracking validated (Phase 4): LCD and buzzer add no functional capability to the tracking system and should not be in the critical path.
- Watchdog testing last (Phase 6): requires the full system to be functional before fault conditions can be injected meaningfully.

### Research Flags

Phases needing deeper research or empirical measurement during planning/execution:
- **Phase 4 (MediaPipe FPS):** 15-25 FPS is an estimate. Measure at the start of Phase 4. Decision point: if FPS < 10, reduce resolution to 240x180 or investigate hardware acceleration.
- **Phase 1 (MediaPipe install):** Confirm piwheels provides a compatible aarch64 wheel for Python 3.11 on the actual RPi OS version before any Phase 2+ work proceeds.

Phases with standard patterns (skip additional research):
- **Phase 1 (Protocol Spec):** Binary framing with start byte + XOR checksum is canonical. Covered by ARCHITECTURE.md Pattern 3.
- **Phase 2 (Serial Link):** dtr=False and low_latency are documented, tested patterns. ASCII protocol and blocking ACK explicitly ruled out.
- **Phase 3 (Arduino Firmware):** QuickPID documentation is comprehensive. millis()-based watchdog pattern is from Memfault best practices. Smooth startup validated from v1.7.
- **Phase 5 (HMI):** LiquidCrystal 4-bit mode and tone() are standard Arduino patterns.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Python side (pyserial, picamera2, AWB sequence) is HIGH — official docs and empirically validated in v1.7/v1.9. MediaPipe FPS estimate is MEDIUM — interpolated from face_landmarker benchmarks, requires empirical confirmation. QuickPID is HIGH — well-documented. |
| Features | HIGH | Feature set derived directly from PROJECT.md architectural decisions (locked) and validated against reference implementations (SaraKIT, PyImageSearch). Dependency graph is internally consistent. |
| Architecture | HIGH | Brain-Muscle split pattern validated by industrial robotics (ROS), SaraKIT reference, and theoretical analysis of Python GIL jitter vs. Arduino determinism. Frame format is a design decision — implementation will validate it. |
| Pitfalls | HIGH (serial/Arduino) / MEDIUM (MediaPipe) | Arduino Leonardo DTR reset, AVR WDT bootloader lock, and Linux USB 16ms latency are documented in official issues and forums with specific reproduction steps. MediaPipe aarch64 install status is MEDIUM — wheel availability changes between releases. |

**Overall confidence:** HIGH for architecture decisions. MEDIUM for MediaPipe FPS and install path — requires early empirical validation.

### Gaps to Address

- **MediaPipe aarch64 wheel status:** Confirm pip install succeeds on the actual RPi4 as the first action in Phase 1. STACK.md v1.8 section documents this as blocked on Python 3.13; the v2.0 research section references confirmed 10-15 FPS. Depends on OS version. Fail fast rather than assuming.
- **MediaPipe FPS at 320x240:** If measured FPS is below 10, the Pi TX rate drops below 10 Hz. The 200ms heartbeat provides a safety buffer for the 2000ms watchdog, but slower vision means fewer tracking frames. Measure in Phase 4 before committing to watchdog timing values.
- **Servo direction on new Arduino mount:** `TILT_DIR = -1` was validated for gpiozero/pigpio. Direction sign through Arduino Servo library may differ. Treat as empirically undefined until Phase 3 calibration routine runs.
- **Serial low_latency persistence:** `setserial low_latency` does not persist across USB reconnects. Decide whether to add it to a startup script, udev rule, or pi_brain.py init code during Phase 2 implementation.

---

## Sources

### Primary (HIGH confidence)
- `PROJECT.md` — v2.0 architecture decisions (distributed RPi4 + Arduino Leonardo, protocol, components) — project source of truth
- `CLAUDE.md` — v1.x validated decisions (smooth_move_to, AWB lock sequence, servo limits, PID gains P=0.05 I=0.001 D=0.005)
- [MediaPipe Face Detector Python API — Google AI Edge](https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector/python) — Tasks API, bounding box format
- [Framing in Serial Communications — Eli Bendersky](https://eli.thegreenplace.net/2009/08/12/framing-in-serial-communications/) — start byte + checksum framing pattern
- [Firmware Watchdog Best Practices — Interrupt/Memfault](https://interrupt.memfault.com/blog/firmware-watchdog-best-practices) — software watchdog vs. hardware WDT
- [PySerial API docs](https://pyserial.readthedocs.io/en/latest/pyserial_api.html) — dtr=False, non-blocking read

### Secondary (MEDIUM confidence)
- [MediaPipe for Raspberry Pi — CNX Software (2023)](https://www.cnx-software.com/2023/08/21/mediapipe-for-raspberry-pi-released-no-code-low-code-on-device-machine-learning-solutions/) — RPi4 FaceDetector FPS context
- [SaraKIT Face Tracking MediaPipe RPi — GitHub](https://github.com/SaraEye/SaraKIT-Face-Tracking-MediaPipe-Raspberry-Pi-64bit) — reference implementation (different HW, validates approach)
- [Arduino Forum: Serial Port WatchDog](https://forum.arduino.cc/t/creating-a-serial-port-watchdog-with-arduino/468929) — millis()-based watchdog pattern
- [Arduino Forum: Pan-tilt PID servo control](https://forum.arduino.cc/t/pan-tilt-servo-control-using-pid-for-face-tracking-webcam/1131405) — integration patterns
- [Simple and Robust Arduino Serial Communication — Medium/@araffin](https://medium.com/@araffin/simple-and-robust-computer-arduino-serial-communication-f91b95596788) — fire-and-forget protocol design
- [Raspberry Pi Arduino Serial Communication — The Robotics Back-End](https://roboticsbackend.com/raspberry-pi-arduino-serial-communication/) — baud rate, buffer, ACK patterns
- raspberrypi/picamera2 GitHub issues #312, #592, #825 — ColourGains behavior, AWB lock sequence validation

### Tertiary (LOW confidence / needs validation)
- MediaPipe FPS estimate (15-25 FPS for FaceDetector on RPi4) — interpolated from face_landmarker measurements; requires empirical verification in Phase 4
- piwheels MediaPipe aarch64 availability — wheel availability changes between releases; must be verified at project start

---

*Research completed: 2026-03-30*
*Ready for roadmap: yes*
