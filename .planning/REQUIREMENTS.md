# Requirements: ARIES-LITE v2.1

**Defined:** 2026-04-01
**Core Value:** Rozproszona architektura — RPi4 (wizja) + Arduino Uno R4 WiFi (PID + HMI + DataLogger) polaczone USB Serial dla plynnego sledzenia twarzy

## v2.1 Requirements

Requirements for Uno R4 WiFi migration + DataLogger Shield milestone. Each maps to roadmap phases.

### Migracja (MIG)

- [x] **MIG-03**: Firmware kompiluje sie pod Arduino Uno R4 WiFi (ArduinoCore-renesas >=1.4.1) bez bledow
- [x] **MIG-04**: Nowa mapa pinow: LCD(RS=A0,E=A1,D4=D2,D5=D3,D6=D4,D7=D5), Serwa(PAN=D6,TILT=D9), Buzzer=D8, Przycisk=D7
- [x] **MIG-05**: Servo library >=1.3.0 — brak jittera na serwach MG-90S przy PID 100Hz
- [x] **MIG-06**: dtostrf() zastapione snprintf() — kompatybilnosc ARM Renesas RA4M1
- [x] **MIG-07**: Usuniete specyfiki Leonardo (Caterina DTR=False, USB CDC workaroundy)
- [x] **MIG-08**: Soft Start 500ms w setup() — stabilizacja napiecia przed ruchem serw
- [x] **MIG-09**: QuickPID kompiluje sie i dziala poprawnie na 32-bit Renesas RA4M1

### RTC (RTC)

- [x] **RTC-01**: RTC DS1307 odczytuje poprawny czas po inicjalizacji Wire->RTC->SD
- [x] **RTC-02**: LCD bootscreen wyswietla jednorazowy snapshot czasu RTC (HH:MM:SS) przy starcie — Phase 25 scope: bootscreen only, aktualizacja co 1s odlozona (lcd_krok BEZ ZMIAN per D-05)
- [x] **RTC-03**: Timestamp z RTC uzywany w nazwach plikow CSV i wpisach logow

### Logowanie (LOG)

- [x] **LOG-01**: Zapis CSV na karte SD: timestamp, stan, pan, tilt, error_x, error_y, face_size, latency_ms
- [x] **LOG-02**: Daily file rotation — nowy plik LYYMMDD.CSV co dzien (FAT 8.3)
- [x] **LOG-03**: Ring buffer w RAM (flush co ~50 wpisow) — ochrona petli PID 100Hz
- [x] **LOG-04**: Graceful degradation — system dziala normalnie bez karty SD (logowanie wylaczone)
- [x] **LOG-05**: Empiryczny benchmark latencji zapisu SD na Uno R4 przed integracja z PID

### Integracja (INT)

- [ ] **INT-06**: Klasa DataLogger (OOP) zintegrowana z MaszynaStanow — logowanie zmian stanow
- [x] **INT-07**: Poprawna kolejnosc inicjalizacji w setup(): Wire.begin() -> rtc.begin() -> SD.begin()
- [ ] **INT-08**: End-to-end: firmware z DataLogger dziala na Uno R4 z pelnym trackingiem RPi

## v2.2 Requirements (Deferred)

### Asystent glosowy

- **M5S-01**: Integracja M5Stack Atom S3R — asystent glosowy polaczony z systemem sledzenia

### Czujnik odleglosci

- **TOF-01**: Czujnik ToF na I2C (A4/A5) — pomiar odleglosci do obiektu sledzenia

### Rozszerzenia protokolu

- **SER-06**: ACK/NACK bidirectional feedback z Arduino do RPi
- **SER-07**: Dynamiczna zmiana baudrate

### Zaawansowany PID

- **ARD-07**: Adaptywny PID — gain scheduling wg rozmiaru twarzy (blizej = mniejsze gainy)
- **ARD-08**: Profil ruchu — acceleration/deceleration curves dla serw

### Zaawansowana wizja

- **VIS-08**: Face ID / re-identification across frames (persistent tracking)
- **VIS-09**: Multi-model fallback (MediaPipe -> DNN -> HAAR)

### Interfejs webowy

- **WEB-01**: Flask web UI z MJPEG stream i panelem sterowania (port z legacy/)

## Out of Scope

| Feature | Reason |
|---------|--------|
| M5Stack Atom S3R | Zarezerwowane na przyszly milestone v2.2 |
| Czujnik ToF | Rezerwacja pinow I2C, integracja w v2.2 |
| Hardware WDT | Nie dotyczy Uno R4, millis() watchdog wystarczy |
| ACK/NACK bidirectional | Fire-and-forget wystarczy dla v2.1 |
| Flask web UI | Odlozone — konkuruje z MediaPipe o CPU |
| Face Mesh (468 landmarks) | 4-5 FPS na RPi4 — za wolne |
| Animacje LCD (custom chars) | Nie krytyczne, mozliwe w v2.2 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MIG-03 | Phase 24 | Complete |
| MIG-04 | Phase 24 | Complete |
| MIG-05 | Phase 24 | Complete |
| MIG-06 | Phase 24 | Complete |
| MIG-07 | Phase 24 | Complete |
| MIG-08 | Phase 24 | Complete |
| MIG-09 | Phase 24 | Complete |
| RTC-01 | Phase 25 | Complete |
| RTC-02 | Phase 25 | Complete |
| RTC-03 | Phase 25 | Complete |
| INT-07 | Phase 25 | Complete |
| LOG-01 | Phase 26 | Complete |
| LOG-02 | Phase 26 | Complete |
| LOG-03 | Phase 26 | Complete |
| LOG-04 | Phase 26 | Complete |
| LOG-05 | Phase 26 | Complete |
| INT-06 | Phase 27 | Pending |
| INT-08 | Phase 27 | Pending |

**Coverage:**
- v2.1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-04-01*
*Last updated: 2026-04-01 — RTC-02 scope narrowed to bootscreen-only for Phase 25 (checker revision)*
