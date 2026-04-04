---
gsd_state_version: 1.0
milestone: v1.9
milestone_name: Stabilizacja Ruchu i Obrazu
status: executing
stopped_at: Phase 16 context gathered
last_updated: "2026-04-04T14:14:21.752Z"
last_activity: 2026-04-04
progress:
  total_phases: 24
  completed_phases: 20
  total_plans: 34
  completed_plans: 32
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-01)

**Core value:** Rozproszona architektura — RPi4 (wizja) + Arduino Uno R4 WiFi (PID + HMI + DataLogger) polaczone USB Serial
**Current focus:** Phase 15.1 — stabilizacja-petli-detekcji

## Current Position

Phase: 16
Plan: Not started
Status: Executing Phase 15.1
Last activity: 2026-04-04

Progress: [░░░░░░░░░░] 0%

## Phase Map (v2.1)

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 24 | Migracja Pinow i Kompilacja Bazowa | MIG-03,04,05,06,07,08,09 | Not started |
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
- [Phase 14-pid-sign-fix]: OPOZNIENIE_BOOT 4.0s -> 5.0s dla R4 WiFi: CDC enumeration + DataLogger/RTC init wymaga wiecej czasu niz legacy Leonardo
- [Phase 14-pid-sign-fix]: PAN_INVERT=+1 i TILT_INVERT=-1 — punkt wyjscia kalibracji empirycznej Plan 02
- [Phase 14-pid-sign-fix]: TILT_INVERT zmieniony z (-1) na (+1) — kalibracja empiryczna R4 WiFi v2.1.1 (Kroki 3,4 FAIL)

### Roadmap Evolution

- Phase 15.1 inserted after Phase 15: Stabilizacja petli detekcji — DNN skip-frames + histereza stanow SKANOWANIE/SLEDZENIE + resize okna imshow (URGENT) — 2026-04-04

### Blockers/Concerns

- Orientacja serw: PAN_DIR / TILT_DIR wymaga empirycznej kalibracji na nowym montazu Uno R4
- SD write latency: typowe < 1ms, worst-case 200-300ms na FAT32 sector boundary — wymaga empirycznego benchmarku w Fazie 26
- Shield header contact: A4/A5 moga tracic kontakt I2C — potrebne cynowanie przed Faza 25
- Active buzzer na D8: jesli aktywny (nie pasywny) moze przekroczyc 8mA limit Uno R4 — sprawdzic typ przed Faza 24
- CHECKPOINT 24-02 Task 2: Weryfikacja sprzetowa 5 testow na Uno R3 — uzytkownik musi potwierdzic LCD, Servo, Serial, Soft Start, Stabilnosc

### Pending Todos

- Zweryfikowac typ buzzera (aktywny vs pasywny) przed uruchomieniem Fazy 24

## Session Continuity

Last session: 2026-04-04T14:14:21.690Z
Stopped at: Phase 16 context gathered
Resume file: .planning/phases/16-camera-color-fix/16-CONTEXT.md
