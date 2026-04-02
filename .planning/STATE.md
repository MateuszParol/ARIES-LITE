---
gsd_state_version: 1.0
milestone: v1.9
milestone_name: Stabilizacja Ruchu i Obrazu
status: verifying
stopped_at: Phase 26 context gathered
last_updated: "2026-04-02T17:56:21.442Z"
last_activity: 2026-04-02
progress:
  total_phases: 19
  completed_phases: 17
  total_plans: 27
  completed_plans: 26
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-01)

**Core value:** Rozproszona architektura — RPi4 (wizja) + Arduino Uno R4 WiFi (PID + HMI + DataLogger) polaczone USB Serial
**Current focus:** Phase 25 — rtc-ds1307-izolowana-integracja

## Current Position

Phase: 28
Plan: Not started
Status: Phase complete — ready for verification
Last activity: 2026-04-02

Progress: [░░░░░░░░░░] 0%

## Phase Map (v2.1)

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 24 | Migracja Pinow i Kompilacja Bazowa | MIG-03,04,05,06,07,08,09 | Complete |
| 28 | Flash firmware na Uno R4 WiFi | MIG-10 | Not started |
| 25 | RTC DS1307 Izolowana Integracja | RTC-01,02,03 + INT-07 | Not started |
| 26 | SD Card + DataLogger CSV | LOG-01,02,03,04,05 | Not started |
| 27 | Pelna Integracja DataLogger z MaszynaStanow | INT-06, INT-08 | Not started |

## Performance Metrics

**Velocity:**

- Total plans completed: 20 (v1.5-v2.0)
- Average duration: brak danych dla v2.1
- Total execution time: brak danych dla v2.1

## Accumulated Context

### Decisions

- [v1.7]: Montaz standardowy: pan+=prawo, tilt+=dol (wymaga re-weryfikacji na nowym montazu Uno R4)
- [v1.7]: Tilt negation: korekta_tilt = -pid_tilt (PID przeniesiony na Arduino)
- [v1.8]: PID gains (P=0.05, I=0.001, D=0.005) — punkt startowy dla Arduino, I redukowac 3x (Ki=0.0003) dla 100 Hz
- [v2.0]: Architektura rozproszona — RPi4 + Arduino via USB Serial 115200
- [v2.0]: QuickPID zamiast br3ttb PID — iAwCondition anti-windup, dOnMeas derivative mode
- [v2.0]: NIE uzywac AVR hardware WDT — millis() watchdog zamiast wdt_enable()
- [v2.0]: Protokol binarny 8B zamkniety: 0xAA + mode(uint8) + error_x/y(int16 LE) + face_size(uint8) + XOR checksum(1-6 bez start)
- [v2.1]: Migracja Leonardo -> Uno R4 WiFi (rozwiazuje USB blocker)
- [v2.1]: Nowa mapa pinow: LCD(A0,A1,D2-D5), Serwa(D6,D9), Buzzer(D8), Przycisk(D7), SD(D10-D13), I2C(A4,A5)
- [v2.1]: DataLogger Shield V1.0 — RTC DS1307 + SD card logging CSV
- [v2.1]: dtostrf() zastapione snprintf() — ARM Renesas RA4M1 nie ma dtostrf
- [v2.1]: Keep-file-open + flush-every-50-rows — nie close() w petli PID
- [v2.1]: Fuzja Soft Start (MIG-08) z Faza 24 — jeden krok kompilacji + hardware verify bez nowych peryferiow
- [Phase 24-migracja-pinow-i-kompilacja-bazowa]: snprintf z int cast zamiast dtostrf — ARM Renesas RA4M1 nie ma dtostrf
- [Phase 24-migracja-pinow-i-kompilacja-bazowa]: delay(500) Soft Start po hmi.inicjalizuj() ale przed serwa.inicjalizuj() — stabilizacja zasilacza 6V
- [Phase 24-migracja-pinow-i-kompilacja-bazowa]: Serial CDC wait 500ms zamiast 3000ms — R4 uzywa ESP32-S3 bridge nie natywnego USB CDC
- [Phase 24-migracja-pinow-i-kompilacja-bazowa]: Rampa Soft Start 1400->1500us zamiast 500->1500us — breadboard z zewnetrznym zasilaniem 6V wymaga lagodniejszej rampy PWM
- [Phase 24-migracja-pinow-i-kompilacja-bazowa]: Weryfikacja sprzetowa na Uno R3 jako proxy dla R4 WiFi — pinout identyczny D6/D9/A0/A1, wyniki wazne dla obu plyt
- [Phase 28-kompletny-szkic-arduino-ino]: Testy sprzetowe T1-T3 odroczone — brak zewnetrznego zasilacza 6V do serw MG-90S podczas sesji
- [Phase 28-kompletny-szkic-arduino-ino]: Testy T4-T6 DEFERRED — mediapipe wymaga Python 3.12, picamera2 wymaga Python 3.13, konflikt ABI uniemozliwia E2E testing na ARM64/aarch64
- [Phase 25-rtc-ds1307-izolowana-integracja]: Wire.begin() BEZ argumentu — master mode, nie slave (per D-02/RESEARCH.md Pitfall 5)
- [Phase 25-rtc-ds1307-izolowana-integracja]: RTClib 2.1.4 (Adafruit) zamiast DS1307RTC (PaulStoffregen) — przetestowane na Renesas RA4M1 (per D-16)
- [Phase Phase 25-rtc-ds1307-izolowana-integracja]: loop() skan co 5s zamiast jednorazowego setup() — Uno R4 WiFi ESP32-S3 bridge nie wysyla DTR reset do RA4M1
- [Phase 25]: ZegarRTC jako adapter RTClib z polskim interfejsem — oddziela logike RTC od kodu glownego
- [Phase 25]: HYBRID mode: ostrzezenie buzzer + LCD FAIL zamiast blokady — system startuje zawsze bez RTC
- [Phase 25]: Weryfikacja sprzetowa R4 WiFi bez Serial Monitor — ESP32-S3 bridge nie resetuje RA4M1 przy otwarciu portu szeregowego

### Blockers/Concerns

- Orientacja serw: PAN_DIR / TILT_DIR wymaga empirycznej kalibracji na nowym montazu Uno R4
- SD write latency: typowe < 1ms, worst-case 200-300ms na FAT32 sector boundary — wymaga empirycznego benchmarku w Fazie 26
- Shield header contact: A4/A5 moga tracic kontakt I2C — potrebne cynowanie przed Faza 25
- Active buzzer na D8: jesli aktywny (nie pasywny) moze przekroczyc 8mA limit Uno R4 — sprawdzic typ przed Faza 24
- CHECKPOINT 24-02 Task 2: Weryfikacja sprzetowa 5 testow na Uno R3 — uzytkownik musi potwierdzic LCD, Servo, Serial, Soft Start, Stabilnosc

### Roadmap Evolution

- Phase 28 added: Flash firmware na Uno R4 WiFi — wgranie i weryfikacja sprzetowa na docelowym hardware
- Phase 28 przesunięta przed Phase 25 — kolejność wykonania: 24→28→25→26→27 (swieze R4 wymaga firmware natychmiast)

### Pending Todos

- Zweryfikowac typ buzzera (aktywny vs pasywny) przed uruchomieniem Fazy 24

## Session Continuity

Last session: 2026-04-02T17:56:21.400Z
Stopped at: Phase 26 context gathered
Resume file: .planning/phases/26-sd-card-datalogger-csv/26-CONTEXT.md
