# Stack Research

**Domain:** Arduino Uno R4 WiFi firmware — DataLogger Shield integration (RTC DS1307 + SD card)
**Researched:** 2026-04-01
**Confidence:** HIGH (core libraries verified via official Arduino compatibility repo + community threads)

---

## Context: What Already Exists (DO NOT re-research)

The following are validated and locked from v2.0. Research below covers only what changes for v2.1.

| Component | Library | Status |
|-----------|---------|--------|
| Dual-axis PID 100 Hz | QuickPID 3.1.9 | Locked — compatible with 32-bit ARM (uses standard float arithmetic) |
| Servo MG-90S | Servo (arduino-libraries) | Needs version update — see below |
| LCD 1602 4-bit | LiquidCrystal (built-in) | Compatible — minor pin note below |
| State machine + HMI | Custom OOP (Polish) | No library changes needed |
| Binary protocol 8B | Serial (built-in) | Behavior change on R4 — see below |

---

## Recommended Stack — New Additions for v2.1

### Core Technologies (New/Changed)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| ArduinoCore-renesas | 1.4.1 (2025-03-10) | Board support package for Renesas RA4M1 | Official Arduino BSP — must be this version minimum; fixes Wire master/slave switch (issue #180, merged Nov 2023), Servo timer resolution (Servo 1.2.2 dependency) |
| Servo (arduino-libraries) | 1.3.0 (2024-11-06) | PWM servo control for MG-90S on D6, D9 | Pre-1.2.2 had 100 µs step resolution bug on R4 causing servo jitter (issue #113); 1.3.0 is current and includes KurtE's timer fix |
| RTClib (Adafruit) | 2.1.4 (2024-04-09) | DS1307 RTC read/write via I2C | Arduino official compatibility matrix: PASS (compile + hardware). Supports DS1307 via `RTC_DS1307` class. Wire.h backed. |
| SD (Arduino built-in) | bundled with ArduinoCore-renesas | SD card read/write via SPI D10-D13 | Arduino official compatibility matrix: PASS (compile + hardware). Use `SD.begin(10)` for CS=D10. Always call `dataFile.close()` after writes. |
| Wire (Arduino built-in) | bundled with ArduinoCore-renesas | I2C bus for DS1307 on A4/A5 | Issue #180 fixed in core 1.0.4+ — DS1307 now works in master-only mode. External pull-ups required (see Critical Notes). |

### Supporting Libraries (Unchanged from v2.0, verified compatible)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| QuickPID | 3.1.9 | Dual-axis PID control at 100 Hz | Standard float arithmetic — runs on 32-bit ARM without modification |
| LiquidCrystal (built-in) | bundled | LCD 1602 4-bit parallel mode | A0/A1 used as digital output (RS, E) — functional but see A0/A1 note |
| SPI (built-in) | bundled with ArduinoCore-renesas | SPI bus for SD card | Use `SPI.beginTransaction()` / `endTransaction()` explicitly when sharing bus |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Arduino IDE 2.x | Compilation + upload | Board: "Arduino UNO R4 WiFi" from Boards Manager (ArduinoCore-renesas 1.4.1) |
| Arduino Library Manager | Install RTClib, update Servo | Search: "RTClib" → Adafruit; "Servo" → arduino-libraries (must be 1.3.0+) |
| Serial Monitor 115200 baud | Debugging over USB | Use `Serial` (USB-C) for debug; same object as pi_brain.py reads |

---

## Installation

```cpp
// Arduino IDE — Library Manager installs
// 1. Boards Manager: "Arduino UNO R4 Boards" → version 1.4.1
// 2. Library Manager: "RTClib by Adafruit" → 2.1.4
// 3. Library Manager: "Servo by Arduino" → 1.3.0  (update if older!)
// SD and Wire are bundled — no separate install

// Sketch includes for new features
#include <Wire.h>        // I2C — required by RTClib
#include <RTClib.h>      // DS1307 RTC
#include <SPI.h>         // SPI bus — required by SD
#include <SD.h>          // SD card (CS=D10)
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Adafruit RTClib 2.1.4 | DS1307RTC (PaulStoffregen) | Never for this project — DS1307RTC is AVR-only, not tested on R4 |
| Arduino built-in SD.h | SdFat (greiman) | If CSV write performance becomes a bottleneck (unlikely at 10-frame logging interval); SdFat is more efficient but adds complexity |
| Wire (hardware I2C) | Software I2C | Never — software I2C has no advantage on R4; hardware Wire works with proper pull-ups |
| Servo 1.3.0 | PWMServo | PWMServo not recommended for R4; requires timer configuration not supported in standard Arduino framework |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Servo library < 1.2.2 | PWM resolution bug: only 10 discrete steps (~100 µs increments) on R4, causes servo jitter; affects MG-90S control quality | Servo 1.3.0 from Library Manager |
| DS1307RTC (PaulStoffregen) | Targets AVR register-level TimeLib, not tested on Renesas RA4M1 | Adafruit RTClib 2.1.4 |
| Wire as I2C slave | ArduinoCore-renesas issue #180 — switching between master/slave modes was broken; fixed in core 1.0.4+ but using as master-only is safest | Wire.begin() without address (master only) |
| SoftwareSerial at 115200 baud | R4 SoftwareSerial only supports single instance; unreliable at 115200 baud | Hardware Serial1 on D0/D1 if needed; but this project uses USB Serial only |
| WiFi / Bluetooth features of R4 | Not needed in v2.1; enabling WiFi draws burst current on 3.3V rail, risks brownout | Leave WiFi unconfigured; do not include WiFiS3.h |

---

## Arduino Uno R4 WiFi vs Leonardo (ATmega32U4) — Migration Differences

This is the core of v2.1. Every difference below requires action in firmware.

### USB Serial (CRITICAL)

| Aspect | Leonardo (ATmega32U4) | Uno R4 WiFi (RA4M1 + ESP32-S3) |
|--------|----------------------|--------------------------------|
| USB hardware | Native USB CDC on MCU | ESP32-S3 bridges USB to RA4M1 via UART |
| DTR signal | Exposed to sketch via `Serial.dtr()` | NOT implemented — DTR/RTS not forwarded |
| Serial object | `Serial` = USB CDC | `Serial` = USB-C (same name, different implementation) |
| Serial1 | D0/D1 UART | D0/D1 UART (same behavior) |
| 1200-baud reset trick | Present (bootloader entry) | Not applicable |
| Caterina bootloader | Yes — required `DTR=False` workaround in pyserial | No — standard DFU; pyserial does not need DTR trick |
| Startup delay | Script needed `time.sleep(2)` after reset | No reset on connect; `Serial` available immediately |

**Action for v2.1:** Remove any `DTR=False` / `time.sleep()` logic from `pi_brain.py`. On R4, `Serial` over USB-C works identically to any standard serial port — open at 115200, read/write normally. No special handshake needed.

### I2C (Wire) — Pull-ups

| Aspect | Leonardo / Uno R3 | Uno R4 WiFi |
|--------|------------------|------------|
| On-board pull-ups on A4/A5 | Present (built-in ~10 KΩ) | NOT mounted — footprints exist but unpopulated |
| Consequence | I2C devices work without external resistors | I2C devices may fail or produce garbage without external pull-ups |

**Action for v2.1:** The DataLogger Shield V1.0 includes its own I2C pull-up resistors (2.2 KΩ on SDA/SCL) on the shield PCB. When the shield is seated, these pull-ups are present — no additional wiring needed. Verify shield pull-ups are present before debugging I2C failures. If I2C fails, add external 4.7 KΩ resistors from A4 (SDA) to 5V and A5 (SCL) to 5V as a fallback.

### SPI Performance

| Aspect | Uno R3 (ATmega328P) | Uno R4 WiFi (RA4M1) |
|--------|--------------------|--------------------|
| Max SPI clock | 8 MHz | 24 MHz theoretical |
| Practical SD card speed | ~4 MHz reliable | ~5 MHz practical max before instability |
| Inter-transfer gap | < 2 µs | ~11 µs (FSP library reconfigures SPI each transfer) |
| Impact on CSV logging | N/A baseline | Slower, but sufficient for 10-frame + state-change log rate |

**Action for v2.1:** Use `SD.begin(10)` with default speed (SPISettings 4 MHz, MSBFIRST, SPI_MODE0). Do not attempt to maximize SPI clock — stability matters more than speed for CSV logging.

### GPIO Current Limits

| Aspect | Uno R3 | Uno R4 WiFi |
|--------|--------|------------|
| Per-pin max current | 40 mA | 8 mA |
| Total GPIO budget | 200 mA | 60 mA |
| Buzzer driver | Direct drive possible | Use transistor or ensure passive buzzer < 8 mA |

**Action for v2.1:** Verify buzzer current draw on D8. Passive buzzers driven by PWM are typically < 5 mA — acceptable. Active buzzers can draw up to 30 mA — requires NPN transistor driver on D8.

### Analog Pins A0/A1 as Digital Output (LCD RS, E)

| Aspect | R3 | R4 WiFi |
|--------|-----|---------|
| A0 special function | ADC only | DAC output (12-bit) + ADC |
| A1 special function | ADC only | Op-amp non-inverting input + capacitive touch |
| Use as digital OUTPUT | Yes, fully supported | Yes — `pinMode(A0, OUTPUT); digitalWrite(A0, HIGH)` works |
| Risk | None | No conflict when used as digital output (DAC/op-amp disabled by default) |

**Action for v2.1:** LiquidCrystal with RS=A0, E=A1 is functional. The DAC and op-amp are inactive by default. Use `pinMode(A0, OUTPUT)` and `pinMode(A1, OUTPUT)` explicitly in setup() before `LiquidCrystal.begin()`.

### 32-bit vs 8-bit Arithmetic

| Aspect | Leonardo (8-bit AVR) | R4 WiFi (32-bit ARM Cortex-M4) |
|--------|---------------------|-------------------------------|
| `int` size | 16-bit | 32-bit |
| `long` size | 32-bit | 32-bit |
| float arithmetic | Software (slow) | Hardware FPU (fast) |
| millis() overflow | 49.7 days at 32-bit | Same — RA4M1 millis() is 32-bit |

**Action for v2.1:** No arithmetic changes expected. QuickPID uses `float` — benefits from hardware FPU on RA4M1. `millis()` watchdog logic unchanged. Review any `int` variables used for timing — on R4 they are 32-bit, which is fine (same or wider than Leonardo).

---

## Stack Patterns by Variant

**SD card file naming (daily rotation):**
```cpp
// RTClib DateTime object + SD.h filename construction
DateTime now = rtc.now();
char filename[16];
snprintf(filename, sizeof(filename), "log_%04d%02d%02d.csv",
         now.year(), now.month(), now.day());
SD.open(filename, FILE_WRITE);
// ALWAYS close after write:
dataFile.close();
```

**I2C initialization order:**
```cpp
Wire.begin();       // Must call before RTClib — master-only mode
RTC_DS1307 rtc;
rtc.begin();        // DS1307 at 0x68
```

**SPI bus management (single device, no sharing needed):**
```cpp
// SD.h manages CS (D10) internally
// No SPI.beginTransaction() needed unless a second SPI device is added
SD.begin(10);  // CS=D10
```

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| ArduinoCore-renesas 1.4.1 | Servo 1.3.0 | Servo timer fix requires renesas core 1.0.4+; 1.4.1 confirmed |
| ArduinoCore-renesas 1.4.1 | RTClib 2.1.4 | Wire master/slave issue fixed in core 1.0.4 (PR #191) |
| ArduinoCore-renesas 1.4.1 | SD (bundled) | SD compile+hardware PASS per official compatibility matrix |
| RTClib 2.1.4 | Wire (built-in) | RTClib uses Wire internally; call Wire.begin() before rtc.begin() |
| QuickPID 3.1.9 | RA4M1 32-bit | Pure C++ float arithmetic — no AVR-specific code; compatible |
| LiquidCrystal (built-in) | RA4M1 | Parallel 4-bit mode — no I2C involved; no compatibility issues |

---

## Sources

- https://github.com/arduino/uno-r4-library-compatibility — Official Arduino compatibility matrix; SD PASS, RTClib PASS (HIGH confidence)
- https://github.com/arduino/ArduinoCore-renesas/issues/180 — DS1307 Wire master-only fix, merged 2023-11-16 as PR #191 (HIGH confidence)
- https://github.com/arduino/ArduinoCore-renesas/releases/tag/1.4.1 — Latest core release 2025-03-10 (HIGH confidence)
- https://github.com/arduino-libraries/Servo/releases — Servo 1.3.0 (2024-11-06), 1.2.2 (2024-06-27) PWM timer fix for R4 (HIGH confidence)
- https://github.com/adafruit/RTClib — RTClib 2.1.4 release 2024-04-09 (HIGH confidence)
- https://lastminuteengineers.com/arduino-uno-r4-wifi-pinout-reference/ — Pin assignment reference for R4 WiFi including current limits, DAC/op-amp, I2C pull-ups (MEDIUM confidence)
- https://forum.arduino.cc/t/serial1-serial-differences-and-how-to/1325960 — Serial vs Serial1 clarification on R4 (MEDIUM confidence)
- https://forum.arduino.cc/t/data-logging-shield-for-r4-minima/1272770 — DataLogger shield RTC I2C issues on R4; shield pull-ups provide fix (MEDIUM confidence)
- https://forum.arduino.cc/t/arduino-uno-r4-spi-with-sd-card/1328547 — SD card `close()` requirement, SPI transaction management on R4 (MEDIUM confidence)
- https://github.com/arduino/ArduinoCore-renesas/issues/28 — SPI performance regression on R4 vs R3 (~11 µs inter-transfer gap) (MEDIUM confidence)
- https://forum.arduino.cc/t/trouble-with-servos-on-r4-wifi/1151749 — Servo PWM resolution bug pre-1.2.2, confirmed fixed (MEDIUM confidence)

---

*Stack research for: Arduino Uno R4 WiFi firmware migration — DataLogger Shield (DS1307 + SD)*
*Researched: 2026-04-01*
