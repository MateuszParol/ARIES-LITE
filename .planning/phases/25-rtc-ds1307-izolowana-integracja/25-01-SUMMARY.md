---
phase: 25-rtc-ds1307-izolowana-integracja
plan: 01
subsystem: arduino
tags: [arduino, i2c, rtclib, ds1307, wire, diagnostics]

# Dependency graph
requires:
  - phase: 24-migracja-pinow-i-kompilacja-bazowa
    provides: Uno R4 WiFi target skonfigurowany, arduino-cli gotowy do kompilacji
provides:
  - Diagnostyczny sketch I2C scanner gotowy do flashowania
  - RTClib 2.1.4 i Adafruit BusIO 1.17.4 zainstalowane przez arduino-cli
  - Potwierdzenie kompilacji na arduino:renesas_uno:unor4wifi
affects: [25-02, 26-sd-card-datalogger, firmware-rtc-integration]

# Tech tracking
tech-stack:
  added:
    - RTClib 2.1.4 (Adafruit) — biblioteka RTC DS1307/DS3231 dla Arduino
    - Adafruit BusIO 1.17.4 — abstrakcja I2C/SPI (dependencja RTClib)
  patterns:
    - Wire.begin() bez argumentu = master mode (Wire.begin(addr) = slave, Pitfall 5)
    - I2C scan loop Wire.beginTransmission(addr) + endTransmission() == 0

key-files:
  created:
    - src/arduino/i2c_scanner/i2c_scanner.ino
  modified: []

key-decisions:
  - "Wire.begin() BEZ argumentu — master mode, nie slave (per D-02/RESEARCH.md Pitfall 5)"
  - "I2C scanner jako PIERWSZY krok — weryfikacja fizyczna przed kodem RTClib (per D-02)"
  - "RTClib 2.1.4 (Adafruit) zamiast DS1307RTC (PaulStoffregen) — przetestowane na Renesas RA4M1 (per D-16)"

patterns-established:
  - "Pattern I2C scan: Wire.beginTransmission(addr) + endTransmission() zwraca 0 gdy urzadzenie odpowiada"
  - "Serial CDC wait: while (!Serial && millis() - start < 500) — 500ms timeout dla R4 WiFi ESP32-S3 bridge"

requirements-completed: [RTC-01, INT-07]

# Metrics
duration: 2min
completed: 2026-04-02
---

# Phase 25 Plan 01: RTC DS1307 I2C Scanner — Summary

**RTClib 2.1.4 + BusIO zainstalowane, diagnostyczny I2C scanner sketch skompilowany na arduino:renesas_uno:unor4wifi (22% flash), gotowy do weryfikacji 0x68 na fizycznym DataLogger Shield**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-02T16:50:25Z
- **Completed:** 2026-04-02T16:52:08Z
- **Tasks:** 1 of 2 (Task 2 = checkpoint:human-verify, wymaga fizycznego hardware)
- **Files modified:** 1

## Accomplishments
- RTClib 2.1.4 i Adafruit BusIO 1.17.4 zainstalowane przez arduino-cli (BusIO auto-installed jako dependencja)
- Diagnostyczny sketch i2c_scanner.ino stworzony — skanuje adresy 0x01-0x7F, format hex, blad jezeli brak urzadzen
- Kompilacja zero bledow na docelowym fqbn arduino:renesas_uno:unor4wifi (58076 B / 22% flash)
- Wire.begin() bez argumentu (master mode) — zgodnie z Pitfall 5 z RESEARCH.md

## Task Commits

1. **Task 1: Instalacja RTClib + BusIO i stworzenie I2C scanner sketch** - `ecfa085` (feat)

**Plan metadata:** (do uzupelnienia po Task 2)

## Files Created/Modified
- `src/arduino/i2c_scanner/i2c_scanner.ino` — diagnostyczny I2C scanner, Wire.h, scan 0x01-0x7F, output hex, oczekiwany 0x68

## Decisions Made
- Wire.begin() BEZ argumentu — per RESEARCH.md Pitfall 5, Wire.begin(addr) konfiguruje slave mode, nie master
- Serial CDC wait 500ms — R4 WiFi uzywa ESP32-S3 USB bridge, wymaga timeout zamiast nieskonczonej petli
- I2C scan jako pierwszy krok przed RTClib — weryfikacja fizyczna per D-02

## Deviations from Plan
None — plan wykonany dokladnie wg specyfikacji.

## Issues Encountered
Brak — biblioteki zainstalowane bez problemow, kompilacja przeszla za pierwszym razem.

## User Setup Required
**Task 2 wymaga fizycznej weryfikacji hardware:**
1. Podlacz Arduino Uno R4 WiFi z DataLogger Shield przez USB
2. Flash: `arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:renesas_uno:unor4wifi src/arduino/i2c_scanner/i2c_scanner.ino`
3. Serial Monitor: `arduino-cli monitor -p /dev/ttyACM0 --config baudrate=115200`
4. Oczekiwany wynik: "I2C znaleziony: 0x68"
5. Odpowiedz "0x68 OK" aby odblokować Phase 25 Plan 02

## Next Phase Readiness
- Biblioteki RTClib 2.1.4 gotowe do uzycia w firmware (Phase 25-02)
- I2C scanner gotowy do flashowania na fizycznym Arduino
- Po potwierdzeniu 0x68: gotowe do integracji klasy ZegarRTC w aries_controller.ino (Phase 25-02)

## Known Stubs
None — sketch jest kompletny i diagnostyczny, nie ma placheholderow.

---
*Phase: 25-rtc-ds1307-izolowana-integracja*
*Completed: 2026-04-02*
