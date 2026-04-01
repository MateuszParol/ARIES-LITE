# Project Research Summary

**Project:** ARIES-LITE v2.1 — Migracja Arduino Leonardo → Uno R4 WiFi + DataLogger Shield
**Domain:** Distributed embedded face tracking — Arduino firmware migration (ATmega32U4 → Renesas RA4M1) + DataLogger Shield (RTC DS1307 + SD card) integration into 100 Hz real-time PID system
**Researched:** 2026-04-01
**Confidence:** HIGH (stack and pitfalls verified against official sources) / MEDIUM (SD write timing specifics require empirical validation)

---

## Executive Summary

v2.1 is a hardware migration milestone. The existing v2.0 firmware (OOP Arduino, binary 8B protocol, QuickPID 100 Hz, watchdog, HMI) is code-complete but was blocked by an Arduino Leonardo USB enumeration bug. The resolution is a board swap to Arduino Uno R4 WiFi (Renesas RA4M1), which requires a targeted pin map migration, removal of Leonardo-specific USB CDC workarounds, and one AVR-to-ARM code compatibility fix (`dtostrf` → `sprintf`). Simultaneously, the DataLogger Shield (DS1307 RTC + SD card) is being integrated to add timestamped CSV telemetry logging. Both changes are well-understood and fully documented in the Arduino ecosystem.

The central risk for v2.1 is the interaction between SD card blocking writes and the 100 Hz PID loop. Standard `SD.h` writes are blocking and can stall for 200–300 ms on FAT32 sector boundary events. Architecture research confirms that a keep-file-open + flush-every-N-rows pattern (N=50) keeps typical write latency at ~0.35 ms per CSV row, well within the 10 ms loop budget. The worst-case flush (~1–2 ms) also remains safe. The dangerous anti-patterns — `file.close()` per write or synchronous `SD.open()/close()` inside the PID loop — must be avoided entirely.

The recommended build order is sequential: pin migration and Servo library upgrade first (validates hardware without new peripherals), then soft start verification, then RTC DS1307 in isolation, then SD card + DataLogger CSV, then full integration with MaszynaStanow state transitions. This order isolates failure modes and ensures each layer is working before the next is added. Five specific pitfalls (Servo library version, DataLogger shield header contact, SD.begin() blocking, SD write latency, ESP32 USB bridge startup delay) have concrete prevention steps and must be addressed before reaching Phase 4 (SD integration).

---

## Key Findings

### Recommended Stack

The core change is the board package: **ArduinoCore-renesas 1.4.1** (2025-03-10) is the required minimum, as it includes the fix for DS1307 I2C Wire master-only mode (issue #180, PR #191) and is compatible with the Servo 1.3.0 PWM timer fix. All other libraries are either bundled (SD.h, Wire.h, SPI.h) or already locked from v2.0 (QuickPID 3.1.9, LiquidCrystal). The only library requiring a mandatory update is Servo: versions before 1.2.2 produce 100 µs step jitter on RA4M1 hardware, causing visible servo ticking that is unrelated to PID quality.

Uno R4 WiFi differs from Leonardo in three architecturally relevant ways: USB Serial is bridged through an ESP32-S3 coprocessor (no DTR trick needed, but 100–500 ms startup delay on first connect), GPIO current limits drop from 40 mA to 8 mA per pin (passive buzzers acceptable, active buzzers may need transistor), and I2C pull-ups are not populated on-board (DataLogger Shield V1.0 supplies its own 2.2 kΩ — sufficient).

**Core technologies:**
- **ArduinoCore-renesas 1.4.1**: Board support package — mandatory minimum for DS1307 I2C and Servo timer fixes
- **Servo 1.3.0**: PWM servo control — versions < 1.2.2 produce jitter on RA4M1; must update via Library Manager before any PID work
- **RTClib (Adafruit) 2.1.4**: DS1307 RTC access via I2C — officially PASS on Arduino R4 compatibility matrix
- **SD.h (bundled)**: FAT32 SD card read/write via SPI D10–D13 — officially PASS; keep file open, use flush not close
- **Wire.h (bundled)**: I2C for DS1307 — must call `Wire.begin()` before `rtc.begin()` and before `SD.begin()`
- **QuickPID 3.1.9** (locked from v2.0): runs without modification on 32-bit ARM; hardware FPU on RA4M1 is a performance bonus

### Expected Features

**Must have (table stakes — v2.1 launch blockers):**
- Pin map migration (LCD, servos, buzzer, button to new Uno R4 assignments: PAN=D6, TILT=D9, LCD on A0/A1/D2–D5, Buzzer=D8, Button=D7, SD_CS=D10)
- Remove Leonardo USB CDC handling (`while (!Serial)` without timeout, `dtr=False` in pi_brain.py) — blocks serial link
- SD initialization with graceful degradation (`sd_dostepne` flag) — system must run without SD card present
- RTC DS1307 initialization with millis() fallback — system must run with dead or absent RTC battery
- CSV write on state transitions (SCAN/TRACK/IDLE changes) — core telemetry requirement
- CSV column header on file creation — self-documenting log files
- Daily log file rotation as `LYYMMDD.CSV` (8.3 FAT32 filename constraint; `log_YYYYMMDD.csv` is too long)

**Should have (add after P1 validated on hardware):**
- CSV write every 10th TRACKING tick (10 Hz continuous telemetry)
- In-RAM ring buffer (8 rows x ~80 chars = 640 bytes, Uno R4 has 32 KB RAM) — implement only if empirical testing shows 10 Hz direct writes disrupt PID
- RTC time displayed on LCD Row 1 during IDLE state

**Defer (v2.2+):**
- WiFi telemetry upload (ESP32-S3 coprocessor available but adds substantial complexity and conflicts with v2.1 scope)
- ToF distance sensor over I2C (A4/A5 bus already reserved; separate milestone)
- SD card USB Mass Storage (requires USB-MSC firmware — separate project)

### Architecture Approach

The DataLogger integrates as a new component in the existing single-threaded loop, called after HMI tick. The keep-file-open + flush-every-N-writes pattern is the key architectural decision: the CSV file stays open from daily rotation until the next day's rotation or shutdown, with `flush()` every ~50 entries (~17 seconds). This limits worst-case power-loss data loss to 17 seconds of telemetry — acceptable for a research logger. `DataLogger::krok()` is called every loop iteration but performs SD IO only on the 10th TRACKING frame (~3 writes/second at 30 Hz input). `loguj_zmiane_stanu()` is called directly from `MaszynaStanow::_przejdz_do()` for immediate state transition capture. Timing analysis confirms the DataLogger write path (~0.35 ms typical, ~1–2 ms flush every 50 rows) does not disrupt the 10 ms PID period.

**Major components:**
1. **Pin map v2.1** — `#define` constants: PAN=D6, TILT=D9, SD_CS=D10, LCD on A0/A1/D2–D5, Buzzer=D8, Button=D7
2. **DataLogger class** (new) — SD init, RTC time cache (updated every 200 ms), CSV write, daily rotation, `sd_dostepne` guard
3. **MaszynaStanow** (modified) — holds DataLogger reference; calls `loguj_zmiane_stanu()` in `_przejdz_do()`
4. **HMI** (modified) — LCD Row 1 shows RTC time during IDLE, sourced from DataLogger cache
5. **setup() ordering** — `Wire.begin()` → `rtc.begin()` → `SD.begin(10)` → DataLogger init (strict order required on R4)

### Critical Pitfalls

1. **Servo library < 1.2.2 causes jitter on R4** — update to 1.3.0 via Library Manager before any PID test; verify with `Sweep` example showing smooth continuous motion
2. **DataLogger Shield header pins lose I2C contact when fully seated** — tin the A4/A5 stacking headers; run I2C scanner (must see 0x68) before writing any RTClib code
3. **SD.begin() blocks setup() when SD card is absent or wrong format** — always check return value and set `sd_dostepne = false` on failure; never block PID on SD init; system must boot without SD
4. **SD write latency stalls 100 Hz PID loop** — use keep-file-open + flush-every-50-rows pattern; measure `micros()` around `file.print()` before integrating into loop; never call `file.close()` inside loop
5. **`dtostrf()` does not exist on ARM/RA4M1** — replace every `dtostrf(v, w, p, buf)` with `snprintf(buf, sizeof(buf), "%w.pf", v)` before attempting compilation; the compile error blocks the entire build

---

## Implications for Roadmap

Based on research, the build order maps directly to 5 phases with clear dependency gates. Each phase has a binary verification condition before proceeding to the next.

### Phase 1: Migracja pinow i kompilacja bazowa

**Rationale:** Pin map migration is the prerequisite for every other phase. Serial communication cleanup (DTR removal, `dtostrf` fix) must also happen here because AVR-specific code produces compile errors that block all subsequent work. This phase has no new hardware — it only changes `#define` constants and removes dead code. It is the lowest-risk phase and produces the highest-leverage unblocking.

**Delivers:** Firmware that compiles under Arduino Uno R4 WiFi board target, runs all existing v2.0 features (LCD, servos, buzzer, abort button, watchdog, binary 8B protocol, QuickPID) with new pin assignments.

**Addresses:** Pin map migration (P1), Leonardo USB CDC removal (P1), Servo 1.3.0 update, `dtostrf` → `snprintf` replacement

**Avoids:** Servo jitter (confirm Servo >= 1.2.2), ESP32 USB bridge startup delay (add 500 ms timeout to `while (!Serial)`), `dtostrf` compile error (full-text search and replace), Leonardo Caterina-specific register code

**Verification:** `Sketch → Verify/Compile` zero errors; serial communicates with RPi (pi_brain.py connects without DTR workaround); LCD shows bootscreen; servos move smoothly via `Sweep` test (no jitter or ticking).

---

### Phase 2: Soft Start weryfikacja na R4

**Rationale:** Soft start (`smooth_move_to()` / `_bezpieczny_start()`) must be verified empirically on the new hardware before adding DataLogger. If the ramp causes brownout on the 6V servo supply with the new D6/D9 pin assignments, it must be fixed before any other feature is layered on top. This is a short empirical phase, not a code phase.

**Delivers:** Confirmed no-brownout servo startup on Uno R4 WiFi with v2.1 pin map; soft start duration confirmed (500 ms or 1000 ms).

**Addresses:** Soft start preservation (inherited P1 feature from v2.0)

**Avoids:** Servo current spike brownout during DataLogger integration testing (which would confound Phase 3/4 debugging)

**Verification:** Servo moves smoothly to center at boot; no reset loop; 6V supply stable; confirmed by absence of restart behavior during 5 repeated power cycles.

---

### Phase 3: RTC DS1307 izolowana integracja

**Rationale:** RTC is simpler than SD (I2C vs SPI; no blocking writes) and its output (timestamps, dates) is required by SD filename generation and every CSV row. Validating I2C in isolation catches the physical shield header contact problem before SD is involved. If I2C fails here, the diagnosis space is narrow: either header contact or Wire ordering.

**Delivers:** DS1307 returning correct time; LCD Row 1 showing `HH:MM:SS` updated every 200 ms; millis() fallback confirmed when RTC is not set or battery is absent.

**Uses:** RTClib 2.1.4, Wire.h from ArduinoCore-renesas 1.4.1

**Avoids:** Shield header contact failure (tin A4/A5 stacking pins before testing; I2C scanner verification at 0x68); Wire.begin() before rtc.begin() ordering; unset RTC (use `rtc.adjust(DateTime(F(__DATE__), F(__TIME__)))` at first flash)

**Verification:** LCD shows current year (2026); time continues after 30-second power interruption (CR1220 battery present and working); millis() fallback activates when battery removed.

---

### Phase 4: SD Card + DataLogger CSV (podstawowe logowanie)

**Rationale:** SD integration is the highest-risk phase due to blocking write latency. It is implemented after RTC is stable so daily filenames can be generated from real timestamps. This phase builds the DataLogger class with keep-file-open + flush-every-50-rows architecture and benchmarks actual write latency on the hardware before connecting to the PID loop.

**Delivers:** CSV files on SD card with correct 8.3 filename (`LYYMMDD.CSV`), header row, state-transition rows, and 10 Hz TRACKING telemetry rows. System operates normally without SD card (`sd_dostepne` guard active).

**Uses:** SD.h (bundled), DataLogger class, snprintf() for CSV row formatting (no dtostrf), `SD.begin(10)` with FAT32-formatted card

**Avoids:** SD.begin() blocking setup() without card; file.close() inside PID loop; FAT32 filename > 8.3 chars (`LYYMMDD.CSV` = 7+3, correct); SD.h with exFAT or NTFS formatted card; in-loop `String` allocation (use `char[80]` + snprintf)

**Verification:** 60-second TRACKING session; eject SD card; open CSV on PC; verify header, RTC timestamps, servo angles, state transitions present. Run without SD card — Arduino boots normally, Serial prints "SD fail", PID runs uninterrupted. Benchmark `micros()` around `file.print()` confirms < 1000 µs typical.

---

### Phase 5: Pelna integracja DataLogger z MaszynaStanow

**Rationale:** Passing DataLogger reference to MaszynaStanow and wiring `loguj_zmiane_stanu()` into `_przejdz_do()` is the final integration step. It is last because it requires all prior phases working independently and adds the cross-component dependency between the state machine and the logger.

**Delivers:** Complete telemetry: every SCAN/TRACK/IDLE state transition logged with RTC timestamp, plus 10 Hz continuous rows during TRACKING. Full v2.1 feature set operational.

**Addresses:** CSV write on state transitions (P1), daily rotation (P1), complete DataLogger integration

**Verification:** Full session with RPi sending face detections; extract SD card; verify CSV shows state transitions correlated with known events (manual face cover/uncover test); no PID disruption observable during logging.

---

### Phase Ordering Rationale

- **Phase 1 is the gate for all others:** Pin map errors cause compile failures; Serial cleanup and `dtostrf` fix are zero-cost if done first but catastrophic if left for later when two systems are under test simultaneously.
- **Phase 2 before DataLogger hardware:** Brownout at boot produces unstable test results that confound Phase 3 and Phase 4 debugging.
- **RTC before SD (Phase 3 before Phase 4):** Daily filename requires RTC date; I2C is simpler to debug without SPI conflicts; header contact failure diagnosis is cleaner in isolation.
- **SD standalone before MaszynaStanow integration (Phase 4 before Phase 5):** DataLogger must be stable and benchmarked in isolation before adding the state machine reference dependency.
- **In-RAM ring buffer deferred:** Architecture analysis shows keep-file-open + flush-every-50 is sufficient for ~3 writes/second (10 Hz TRACKING ticks). Ring buffer should only be implemented if Phase 4 empirical benchmarking reveals PID disruption.

### Research Flags

Phases needing empirical measurement (cannot be confirmed from docs alone):
- **Phase 2:** Soft start brownout risk is hardware-dependent (specific 6V supply, new D6/D9 assignments). Cannot be confirmed without hardware test.
- **Phase 4:** SD write latency with specific DataLogger Shield V1.0 hardware and SD card. Research provides typical values (0.35 ms write, 1–2 ms flush) confirmed by forum data, but worst-case 200–300 ms is only triggered by FAT32 sector boundaries. Measure with `micros()` bracketing on actual hardware before declaring Phase 4 complete.

Phases with well-documented patterns (standard execution, no additional research needed):
- **Phase 1:** Pure define changes + compile; documented migration path is complete and all fixes are confirmed merged.
- **Phase 3:** RTClib + Wire integration is fully documented; ArduinoCore-renesas fix is merged and confirmed.
- **Phase 5:** Reference passing and callback wiring is standard OOP Arduino pattern.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core library versions verified against official Arduino compatibility matrix and GitHub release notes; all fixes confirmed merged in specific PRs with dates |
| Features | MEDIUM-HIGH | Protocol/RTC integration is MEDIUM-HIGH (official docs, confirmed hardware tests reported in forum threads); SD write timing specifics are MEDIUM (forum data, not Uno R4 specific benchmarks — requires Phase 4 empirical validation) |
| Architecture | HIGH | Timing analysis based on multiple confirmed forum benchmarks; component separation validated against existing codebase structure; keep-file-open pattern confirmed as correct approach by multiple independent sources |
| Pitfalls | HIGH | All 5 critical pitfalls traced to specific GitHub issues and forum threads with confirmed reproduction steps and fix verification; physical shield header contact issue confirmed by multiple independent Adafruit forum reports |

**Overall confidence:** HIGH for migration correctness and architecture decisions. MEDIUM for SD write performance under 100 Hz load — requires empirical validation in Phase 4 before concluding that no ring buffer is needed.

### Gaps to Address

- **SD write latency on actual Uno R4 + DataLogger V1.0 hardware:** Research shows typical 0.35 ms, worst-case 200–300 ms. The 200–300 ms case must be triggered and measured on real hardware during Phase 4. If it disrupts PID, the in-RAM ring buffer (640 bytes, flush every ~17 seconds) should be activated. Decision deferred to Phase 4 empirical benchmarking.
- **DS1307 battery absent at first boot:** CR1220 may not be pre-installed in all DataLogger Shield variants. Time must be set via `rtc.adjust(DateTime(F(__DATE__), F(__TIME__)))` at first flash. This should be in Phase 3 setup instructions.
- **Active buzzer current draw on D8:** Passive buzzers are typically < 5 mA (safe on R4's 8 mA per-pin limit); active buzzers can draw up to 30 mA (requires NPN transistor). Verify buzzer type before Phase 1 hardware test.

---

## Sources

### Primary (HIGH confidence)
- https://github.com/arduino/uno-r4-library-compatibility — Official Arduino compatibility matrix; SD PASS, RTClib PASS
- https://github.com/arduino/ArduinoCore-renesas/issues/180 — DS1307 Wire master-only fix, merged PR #191 (2023-11-16)
- https://github.com/arduino/ArduinoCore-renesas/releases/tag/1.4.1 — Latest core release 2025-03-10
- https://github.com/arduino-libraries/Servo/releases — Servo 1.3.0 (2024-11-06), 1.2.2 PWM timer fix for R4
- https://github.com/adafruit/RTClib — RTClib 2.1.4 release 2024-04-09

### Secondary (MEDIUM confidence)
- https://forum.arduino.cc/t/arduino-uno-r4-spi-with-sd-card/1328547 — SD card close() requirement, SPI R4 compatibility notes
- https://forum.arduino.cc/t/data-logging-shield-for-r4-minima/1272770 — DataLogger shield I2C issues on R4
- https://forum.arduino.cc/t/trouble-with-servos-on-r4-wifi/1151749 — Servo PWM resolution bug pre-1.2.2, confirmed fix
- https://forums.adafruit.com/viewtopic.php?t=215319 — DataLogger Shield Rev C header contact physical issue (multiple reports)
- https://forum.arduino.cc/t/sd-write-time-max-latency-depedencies/517159 — 200–300 ms worst-case write latency
- https://forum.arduino.cc/t/cyclic-buffer-for-data-logging-on-sd-card/1275019 — Ring buffer approach for high-rate logging
- https://lastminuteengineers.com/arduino-uno-r4-wifi-pinout-reference/ — Pin assignments, current limits, DAC/op-amp, I2C pull-ups

---

*Research completed: 2026-04-01*
*Ready for roadmap: yes*
