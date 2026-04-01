# Feature Research

**Domain:** Distributed embedded face tracking — Arduino Uno R4 WiFi firmware + DataLogger Shield (SD + RTC)
**Researched:** 2026-04-01
**Confidence:** MEDIUM (SD write timing specifics are LOW; protocol/RTC integration is MEDIUM-HIGH)

---

## Context: v2.1 Scope

v2.0 delivered the distributed architecture: Arduino Leonardo OOP firmware (ServoPID, MaszynaStanow, HMI), RPi brain (MediaPipe + serial TX), binary 8B protocol, and hardware watchdog. v2.0 was **code-complete but hardware-blocked** by the Leonardo USB enumeration bug.

v2.1 resolves the hardware blocker (swap Leonardo → Uno R4 WiFi) and adds the DataLogger Shield:
- **SD card logging**: CSV rows with timestamp, state, servo angles, PID errors, face_size, latency
- **RTC DS1307**: Real timestamps instead of `millis()` offsets
- **Pin map migration**: New Uno R4 pin assignments for all peripherals

Features listed below cover **only v2.1 additions**. v2.0 table stakes (binary 8B protocol, PID at 100 Hz, LCD, buzzer, abort button, watchdog, soft start) are inherited as working assumptions.

Critical constraint for every new feature: **the PID loop runs at 100 Hz (10ms tick). Any SD or RTC operation that blocks longer than 10ms disrupts tracking.** This constraint shapes every design choice below.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Non-negotiable for v2.1 to be functional. Missing these = milestone incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Pin map migration to Uno R4 WiFi | Leonardo pins for LCD, servos, buzzer, button are different from Uno R4 v2.1 target map; firmware will not compile correctly without this | LOW | New map: LCD(RS=A0, E=A1, D4=D2, D5=D3, D6=D4, D7=D5), Servos(PAN=D6, TILT=D9), Buzzer=D8, Button=D7. Lock pin map in `#define` constants at top of `.ino`. |
| Remove Leonardo-specific USB CDC handling | Leonardo used `Serial` = USB CDC (`Caterina` bootloader with DTR=false workaround). Uno R4 uses standard UART0 on USB via CH340/native USB — no DTR tricks needed | LOW | Delete any `while (!Serial) {}` loop with DTR guard. Uno R4 standard `Serial.begin(115200)` in `setup()` is sufficient. Confirm: RPi `pyserial` does not need DTR=false either. |
| SD card initialization at startup | `SD.begin(10)` with CS on D10; must succeed before any log write. If SD init fails, system must still operate (no SD = degrade gracefully, do not halt) | LOW | Call in `setup()` after Servo and LCD init. Log success/failure to LCD row 1 for 2 seconds. Set a boolean `sd_disponivel = false` on failure. |
| RTC DS1307 initialization and time read | `RTClib` (Adafruit) provides `RTC_DS1307` class; `rtc.begin()` + `rtc.isrunning()` check in `setup()`. If battery dead or not set, fallback to `millis()`-based offset | MEDIUM | **Known Uno R4 issue (RESOLVED):** DS1307 I2C access required exclusive `Wire.begin()` master role. Fixed in ArduinoCore-renesas PR #191 — update Arduino IDE / board package before flashing. Verify `Wire.begin()` is called once before `SD.begin()` to avoid SPI/I2C ordering conflict. |
| CSV row write on state transitions | Every SCAN→TRACK, TRACK→TARGET_LOST transition gets one CSV row. This covers all meaningful behavioral events without high-frequency writes | LOW | Trigger: state machine's `_przejdz_do()` method. Write immediately in state transition handler. One row per event. Row format below. |
| CSV row write every Nth TRACKING tick | Continuous telemetry during active tracking. Every 10th loop tick while in TRACKING state = 10 Hz logging rate (100 Hz / 10 = 10 Hz) | MEDIUM | Counter in `MaszynaStanow`. Increment on each TRACKING tick; write + reset counter at N=10. **Critical: write must complete before next PID tick or skip the write.** |
| CSV column header on file creation | First row of every new CSV file must be the column header so the file is self-documenting | LOW | Write header in the file-create code path, not on every open. Check: if `!SD.exists(filename)` → open + write header + first data row. If file exists → open in append mode. |
| Daily log file rotation (log_YYYYMMDD.csv) | Each day gets its own file. Prevents single monolithic file; enables per-day analysis | MEDIUM | Filename format `LYYMMDD.CSV` (8.3 FAT32 limit: 8 chars + 3 ext). At start of each `loop()` iteration, compare RTC date to stored `current_date`. On mismatch: close current file, open new file with today's name, write header. Note: FAT32 requires 8.3 filenames — `LYYYYMMDD` is 9 chars, must use `LYYMMDD` (7 chars, 2-digit year) or `LMMDD` with directory per year. |
| CSV row format (8 fields) | Defined in PROJECT.md: `timestamp, stan, pan, tilt, error_x, error_y, face_size, latency_ms` | LOW | `timestamp` = ISO-like string from RTC: `"2026-04-01T13:45:22"`. `stan` = state name string (`"TRACK"`/`"SCAN"`/`"IDLE"`). `pan`, `tilt` = current servo angles (int). `error_x`, `error_y` = last PID errors (int16). `face_size` = last face_size from serial frame (uint16). `latency_ms` = time since last valid serial frame (uint16). |
| SD card SPI pin reservation (D10-D13) | SPI bus must be free; no other shield or device may use D10-D13. DataLogger Shield occupies this bus permanently | LOW | Document in pin map. D13 (SCK) doubles as LED on Uno — shield conflicts with LED blinking. Do not use `digitalWrite(13, ...)` in firmware. |
| I2C pin reservation (A4/A5) | RTC DS1307 uses I2C. A4=SDA, A5=SCL. These pins must not be used as analog inputs or digital outputs | LOW | Comment in hardware init section. ToF sensor (future) also uses I2C — shield can share the bus with up to 8 I2C devices at different addresses. |

### Differentiators (Competitive Advantage)

Features that add meaningful capability beyond minimum functional requirements.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| SD write deferred via millis()-gated flag | PID loop sets a "pending write" flag at the Nth tick; actual SD write happens only if we have >= 8ms of headroom before next PID tick (i.e., `millis() % 10 < 8`). Prevents SD blocking from eating into servo update budget | MEDIUM | Pattern: `bool log_pending = false`. In PID tick: set flag. After PID + servo write: check flag + millis headroom. Write only if safe. If headroom exceeded, skip and set flag for next iteration. **LOW confidence this is reliable with standard `SD.h` — worst-case write is 200-300ms on FAT32 sector boundary, which will break PID regardless.** Mitigation: batch writes via in-RAM buffer (see next row). |
| In-RAM ring buffer for CSV rows | Accumulate 4-8 CSV rows in a fixed-size `char` array in RAM; flush to SD only when buffer is full or on state transition. Reduces SD write frequency from 10 Hz to ~1-2 Hz, dramatically reducing PID disruption probability | HIGH | Uno R4 WiFi (RA4M1) has 32KB RAM vs 8-bit Uno's 2KB — viable. Ring buffer of 8 rows x ~80 chars = 640 bytes. Flush on full or state change. Implement as a simple circular buffer, not a dynamic structure. Flag PID loop to skip if flush is in progress. **Risk: ring buffer flush (640 bytes to SD) may still block 20-40ms. Must test empirically.** |
| RTC time displayed on LCD row 1 during IDLE | When system is idle (no serial connection, no tracking), show current time `HH:MM:SS` on LCD row 1. Provides visual confirmation RTC is working without connecting serial monitor | LOW | In `MaszynaStanow` IDLE state handler: update LCD row 1 with `rtc.now()` formatted time, once per second (millis gated). Does not affect SCAN or TRACKING states where row 1 shows diagnostic data. |
| Fallback to millis() timestamp if RTC unavailable | If DS1307 is dead battery or unset (returns all zeros), use `millis()` elapsed time as `timestamp` field in CSV. Data is still useful for relative timing analysis | LOW | In RTC init: check `rtc.isrunning()`. If false: set `rtc_disponivel = false`. In log write: if `rtc_disponivel` use RTC time string; else write `"T+"` + millis() + `"ms"`. |
| SD card pre-format recommendation in docs | FAT32 formatted with official SD Formatter (sdcard.org) dramatically reduces worst-case write latency by pre-erasing blocks. Class 10 or UHS-I rated card recommended | LOW (docs only) | **MEDIUM confidence**: Community consensus is that card quality and format state directly affects worst-case latency. SanDisk or Samsung Class 10 recommended. 8GB is sufficient; larger cards are slower to format and offer no benefit. |
| Soft Start preservation on Uno R4 | 500ms interpolated ramp to center position at startup prevents brownout from servo current spike. Already implemented in v2.0 firmware; must survive pin map migration | LOW | Verify `smooth_move_to()` uses `delay()` (acceptable in `setup()`) or millis loop. Confirm D6/D9 servo pins re-attached correctly in new pin map before soft start runs. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| SD write inside PID ISR or timer interrupt | Seems elegant — log every PID tick from interrupt handler, keep main loop clean | SD library is **not interrupt-safe**. SPI transactions inside an ISR corrupt the SD state machine and hang the firmware. Timer3 + SD library conflicts are a documented failure mode on Arduino. | Log from main `loop()` only, using the millis-gated flag or ring buffer pattern. Never call SD.write from an ISR. |
| Synchronous `file.close()` after every row | Guarantees no data loss on power failure | `file.open()` takes ~140ms, `file.close()` takes ~75ms. Combined 215ms per write cycle destroys 100 Hz PID loop entirely (loop period = 10ms, write takes 21x a loop period). | Keep file open in append mode. Call `file.flush()` instead (much faster: ~7-8ms for the write operation itself). Accept that the last few seconds of data may be lost on unexpected power loss — this is a research logger, not a flight recorder. |
| Logging every PID tick (100 Hz / 100% duty) | Full-fidelity servo telemetry | At 100 Hz, SD write calls come every 10ms. Even Class 10 cards have typical 7-8ms writes with worst-case 200-300ms outliers on FAT32 sector boundaries. This will cause PID skips every ~256KB of written data. Servo will jerk visibly during those outlier writes. | Log every Nth tick (N=10 recommended = 10 Hz). For post-analysis, 10 Hz is sufficient to observe PID convergence. Research platform does not need sub-10ms telemetry. |
| Use Uno R4 WiFi built-in RTC instead of DS1307 | Uno R4 WiFi has onboard RTC with VRTC pin; no external chip needed | The DataLogger Shield **already includes DS1307** on its PCB. Routing around it to use the RA4M1 internal RTC requires custom code and loses the shield battery backup hardware. The DS1307 issue on R4 is **resolved** (ArduinoCore-renesas PR #191). | Use DS1307 via RTClib as designed. Only fall back to built-in RTC if DS1307 proves persistently unreliable in hardware testing. |
| Bidirectional SD logging (RPi reads SD over USB) | Central logging from RPi would consolidate all telemetry | Arduino SD library does not expose SD as a USB Mass Storage device; RPi cannot read it over the serial link. Implementing USB-MSC on Uno R4 is a separate complex project. | Log on SD standalone. Retrieve data by physically removing SD card and reading on PC. Or add a periodic Arduino → RPi serial frame with log data (high protocol complexity, out of scope). |
| Binary CSV format (raw bytes instead of ASCII) | Faster writes, smaller files | Incompatible with Excel / pandas direct import. The "CSV" in the milestone spec implies human-readable text. Performance gain is marginal for 10 Hz logging. | ASCII CSV with minimal formatting: no spaces around commas, integer values where possible (no float printf), fixed-width fields if padding needed. |
| WiFi data upload from Uno R4 (use the WiFi module) | Uno R4 WiFi has onboard ESP32-S3 WiFi coprocessor; could stream telemetry over network | WiFi + SD + RTC + PID simultaneously adds significant complexity. WiFi init time is >1s. ESP32 WiFi stack is a separate firmware on the coprocessor communicating via AT commands — adds another serial interface to manage. Out of scope for v2.1. | WiFi integration is a potential v2.2+ milestone. DataLogger shield handles local storage for v2.1. |

---

## Feature Dependencies

```
[Pin Map v2.1]
    └──prerequisite for──> [SD Initialization]
    └──prerequisite for──> [RTC DS1307 Init]
    └──prerequisite for──> [Servo Soft Start]
    └──prerequisite for──> [LCD Display]

[Remove Leonardo USB CDC]
    └──prerequisite for──> [Serial RX at 115200]
    └──prerequisite for──> [Binary 8B Protocol]

[RTC DS1307 Init]
    └──produces──> [Timestamp for CSV rows]
    └──enhances──> [LCD IDLE time display]
    └──fallback──> [millis() timestamp if RTC unavailable]

[SD Initialization]
    └──prerequisite for──> [CSV row write on state transition]
    └──prerequisite for──> [CSV row write every Nth tick]
    └──prerequisite for──> [Daily log file rotation]

[CSV row write on state transition]
    └──requires──> [SD Initialization]
    └──requires──> [RTC DS1307 Init] (or millis fallback)
    └──produces──> [Log file on SD card]

[CSV row write every Nth tick]
    └──requires──> [SD Initialization]
    └──requires──> [100Hz PID loop] (N=10 means 10Hz logging)
    └──CONFLICTS WITH──> [Synchronous close() per write]
    └──MITIGATED BY──> [In-RAM ring buffer]

[In-RAM ring buffer]
    └──requires──> [SD Initialization]
    └──enhances──> [CSV row write every Nth tick] (reduces SD access frequency)
    └──enables──> [PID loop integrity during logging]

[Daily log file rotation]
    └──requires──> [RTC DS1307 Init] (needs date to construct filename)
    └──requires──> [SD Initialization]
    └──requires──> [CSV column header on file creation]

[Soft Start 500ms]
    └──requires──> [Pin Map v2.1] (D6/D9 servo pins correct)
    └──prerequisite for──> [PID loop activation]
    └──prerequisite for──> [SD Initialization] (safe to run after servos stable)
```

### Dependency Notes

- **Pin map migration is the gate for everything**: SD CS is D10, but D10 was previously TILT servo in some Leonardo configs. Confirm new pin map does not double-assign any pin before writing a line of code.

- **Wire.begin() must precede SD.begin()**: On Uno R4, initializing SPI (SD) before I2C (Wire/DS1307) can cause I2C to become unreliable on some boards. Call `Wire.begin()` first in `setup()`, then `rtc.begin()`, then `SD.begin(10)`. This ordering workaround is documented in the Adafruit DataLogger shield forum thread.

- **SD write timing is the dominant risk for PID integrity**: The 100 Hz loop tick is 10ms. Standard `SD.h` write operations are typically 7-8ms for the actual write, but worst-case FAT32 sector boundary rewrites reach 200-300ms. Without a ring buffer or deferred write strategy, every sector boundary will cause a visible servo jerk. This is the highest-risk feature in the milestone.

- **RTC battery**: DS1307 uses CR1220 coin cell. If the shield ships without battery, RTC will not retain time after power loss. Initial time must be set via `rtc.adjust(DateTime(F(__DATE__), F(__TIME__)))` compiled-in from build time, or via a serial command. Document this in setup instructions.

- **FAT32 8.3 filename constraint**: SD library on Arduino only supports 8.3 filenames (8 chars name + 3 chars extension). `log_YYYYMMDD.csv` is 12 chars for the name — too long. Use `L` + `YYMMDD` = `LYYMMDD.CSV` (7-char name). Example: `L260401.CSV` for 2026-04-01.

---

## MVP Definition

### Launch With (v2.1 core)

Minimum set to validate Uno R4 + DataLogger integration.

- [ ] Pin map migration — compile and run on Uno R4 with all peripherals on new pins
- [ ] Leonardo USB CDC removal — serial link establishes without DTR workaround
- [ ] SD init with graceful degradation — system runs without SD card; LCD shows "SD BRAK" on failure
- [ ] RTC init with millis() fallback — system runs with dead/absent RTC battery; timestamps use millis offset
- [ ] CSV write on state transitions — SCAN↔TRACK transitions captured in log file
- [ ] CSV header on file creation — self-documenting log files
- [ ] Daily filename rotation (LYYMMDD.CSV) — log files split by date

### Add After Validation (v2.1 polish)

Features to add once SD+RTC initialization and basic writes work on hardware.

- [ ] CSV write every 10th TRACKING tick — continuous telemetry during tracking; validate PID loop not disrupted
- [ ] In-RAM ring buffer — add if empirical testing shows 10Hz direct writes disrupt PID; implement if needed
- [ ] RTC time on LCD row 1 during IDLE — cosmetic but useful for confirming RTC works

### Future Consideration (v2.2+)

- [ ] WiFi telemetry upload — leverage Uno R4 WiFi ESP32-S3; separate milestone
- [ ] ToF distance sensor (I2C) — I2C A4/A5 already reserved; add as separate v2.2 milestone
- [ ] SD card USB Mass Storage — read log files over USB without removing SD card; requires USB-MSC firmware complexity

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Pin map migration | HIGH | LOW | P1 |
| Remove Leonardo USB CDC | HIGH | LOW | P1 |
| SD initialization + graceful degrade | HIGH | LOW | P1 |
| RTC init + millis() fallback | HIGH | LOW | P1 |
| CSV write on state transitions | HIGH | LOW | P1 |
| CSV header on file creation | HIGH | LOW | P1 |
| Daily file rotation LYYMMDD.CSV | MEDIUM | MEDIUM | P1 |
| CSV write every 10th TRACKING tick | HIGH | MEDIUM | P2 |
| Millis-gated deferred write flag | HIGH | MEDIUM | P2 |
| In-RAM ring buffer for CSV rows | HIGH | HIGH | P2 (if PID disruption confirmed in testing) |
| RTC time on LCD row 1 (IDLE) | LOW | LOW | P2 |
| Soft start 500ms preservation | HIGH | LOW | P1 (inherited, verify not broken by pin change) |

**Priority key:**
- P1: Must have for v2.1 launch
- P2: Should have — add once P1 features validated on hardware
- P3: Future milestone

---

## SD Write Timing Impact on 100 Hz PID Loop

This section captures the key constraint analysis since it affects every logging design decision.

### The Problem

The PID loop tick interval is 10ms. SD card writes using the standard `SD.h` library are **blocking** — the entire Arduino sketch pauses during the write. Measured write times:

| Operation | Typical | Worst Case | Source Confidence |
|-----------|---------|------------|------------------|
| `file.write()` ~80 char row | 7-8ms | 200-300ms | MEDIUM (forum data, not Uno R4 specific) |
| `file.flush()` | ~7-8ms | 200-300ms | MEDIUM |
| `file.open()` | ~140ms | >200ms | MEDIUM |
| `file.close()` | ~75ms | >100ms | MEDIUM |

**Worst-case 200-300ms occurs when the FAT32 filesystem must rewrite sector allocation tables**, which happens roughly every 256KB of written data. At 10 Hz logging, 80-char rows, that is ~800 bytes/second, meaning a sector boundary event every ~320 seconds (~5 minutes of operation). During that event, the PID loop stalls for up to 300ms = 30 missed servo updates.

### Mitigation Strategy (Recommended)

1. **For state-transition rows** (low frequency): Direct write acceptable. One row per transition, transitions are rare (<1 Hz). Even a 200ms write is acceptable here because the face is already transitioning — the servo jerk from a 200ms PID pause is not worse than the TARGET_LOST handling itself.

2. **For every-Nth-tick rows** (10 Hz): Use millis-gated write. After PID calculation and servo write, check `millis() % 10 < 3` (write only in first 3ms of each 10ms window). If timing is tight, skip and defer. This prevents writes from overlapping into the next PID tick *in the common case* but does not protect against FAT32 sector boundary events.

3. **If testing shows visible servo disruption**: Implement in-RAM ring buffer (8 rows x ~80 chars = 640 bytes). Flush buffer to SD only outside of PID windows, or accept one 20-40ms stall per flush cycle. Ring buffer makes sector boundary events happen at controlled times (flush boundaries) rather than random write calls.

4. **Card selection**: Use SanDisk or Samsung Class 10 / UHS-I cards pre-formatted with official SD Formatter tool. This reduces (but does not eliminate) worst-case latency.

### What to Verify on Hardware

- Measure actual write time with `millis()` bracketing around `file.write()` + `file.flush()`
- Observe servo motion during a 5-minute TRACKING session — look for periodic jerks
- If jerks observed, measure their interval (should correlate with 256KB boundary timing)
- Decide on ring buffer implementation based on empirical data

---

## Sources

- PROJECT.md v2.1 milestone spec (pin map, feature list, hardware components)
- [Arduino DataLogger Shield V1.0 pinout — Botland](https://botland.store/arduino-shield-communication/8238-datalogger-shield-v10-rtc-ds1307-with-sd-card-reader-shield-for-arduino-iduino-st1046-5903351241205.html) — confirms D10 CS, D11-D13 SPI, A4/A5 I2C
- [Adafruit Data Logger Shield guide — Adafruit Learning System](https://learn.adafruit.com/adafruit-data-logger-shield/using-the-real-time-clock-3) — RTClib usage, Wire.begin() ordering
- [UNO R4 DS1307 I2C exclusive master issue — ArduinoCore-renesas GitHub #180](https://github.com/arduino/ArduinoCore-renesas/issues/180) — RESOLVED in PR #191
- [Arduino UNO R4 SPI with SD Card — Arduino Forum](https://forum.arduino.cc/t/arduino-uno-r4-spi-with-sd-card/1328547) — R4-specific SPI SD compatibility notes
- [Data logger shield and UNO R4 I2C conflict — Adafruit Forums](https://forums.adafruit.com/viewtopic.php?t=215319) — I2C+SPI ordering workaround
- [SD card writing causes timing issues — Arduino Forum](https://forum.arduino.cc/t/sd-card-writing-causes-timing-issues/620538) — write latency data
- [SD write time, max latency dependencies — Arduino Forum](https://forum.arduino.cc/t/sd-write-time-max-latency-depedencies/517159) — 200-300ms worst case
- [SD Card do I need to close after each write — Arduino Forum](https://forum.arduino.cc/t/sd-card-do-i-need-to-close-after-each-write/614994) — flush() vs close() tradeoff
- [Date as a file name YYYYMMDD.CSV — GarageBox](https://garagebox.org/arduino/61-date-as-a-file-name-yyyymmddcsv.html) — 8.3 filename construction from RTC date
- [How to make log rotate in SD card — Arduino Forum](https://forum.arduino.cc/t/how-to-makes-log-rotate-in-sd-card/893758) — daily rotation pattern
- [Cyclic Buffer for Data Logging on SD Card — Arduino Forum](https://forum.arduino.cc/t/cyclic-buffer-for-data-logging-on-sd-card/1275019) — ring buffer approach for high-rate logging
- [Data Logging to SD card at 5-10kHz — Arduino Forum](https://forum.arduino.cc/t/data-logging-to-sd-card-using-an-interrupt-at-5-10-khz/327792) — confirms SD writes cannot be called from ISR
- [Arduino SD Library Reference — arduino.cc](https://www.arduino.cc/en/Reference/SD) — official SD.h API

---

*Feature research for: Arduino Uno R4 WiFi + DataLogger Shield (SD CSV logging + RTC DS1307), v2.1 milestone*
*Researched: 2026-04-01*
