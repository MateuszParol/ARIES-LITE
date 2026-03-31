# Requirements: ARIES-LITE v2.0

**Defined:** 2026-03-30
**Core Value:** Rozproszona architektura — RPi4 (wizja) + Arduino Leonardo (PID + HMI) polaczone USB Serial dla plynnego sledzenia twarzy

## v2.0 Requirements

Requirements for distributed architecture milestone. Each maps to roadmap phases.

### Environment (ENV)

- [x] **ENV-01**: Python 3.12 venv na RPi4 (przez pyenv — Trixie nie ma 3.11) z zainstalowanym MediaPipe (weryfikacja empiryczna)
- [x] **ENV-02**: Arduino IDE/arduino-cli z bibliotekami QuickPID, Servo, LiquidCrystal gotowe do kompilacji firmware

### Serial Protocol (SER)

- [x] **SER-01**: Specyfikacja ramki binarnej (8 bajtow: start marker 0xAA + tryb + blad X/Y + rozmiar twarzy + checksum XOR)
- [x] **SER-02**: Arduino parser state-machine (non-blocking, WAIT_START → READ_PAYLOAD → VERIFY_CHECKSUM → DISPATCH)
- [x] **SER-03**: RPi nadajnik pyserial z dtr=False, timeout, low_latency na /dev/ttyACM0 @ 115200 baud
- [x] **SER-04**: Heartbeat TX z RPi co 200ms — Arduino rozpoznaje utrate komunikacji
- [x] **SER-05**: Echo test — RPi wysyla ramke, Arduino potwierdza odczyt poprawny (walidacja end-to-end)

### Arduino Firmware (ARD)

- [x] **ARD-01**: QuickPID dual-axis (pan + tilt) z anti-windup, deterministyczny loop 100Hz via millis()
- [x] **ARD-02**: Servo safe startup — plynny ruch do 90/90 przy starcie (nie skok)
- [x] **ARD-03**: Software watchdog (millis()) — powrot do trybu SCAN gdy brak ramek >500ms
- [x] **ARD-04**: Konfigurowalny kierunek serw (PAN_INVERT / TILT_INVERT define) dla empirycznej kalibracji
- [x] **ARD-05**: Maszyna stanow: IDLE → SCAN → TRACK z przejsciami sterowanymi przez ramki z RPi
- [x] **ARD-06**: Skanowanie sinusoidalne w trybie SCAN (autonomiczne, bez ramek z RPi)

### RPi Vision (VIS)

- [x] **VIS-01**: MediaPipe Face Detection (BlazeFace, bbox only) na Picamera2 stream 320x240
- [x] **VIS-02**: Sticky tracking — priorytet dla najwiekszej twarzy (bbox area), stabilne sledzenie przy wielu twarzach
- [x] **VIS-03**: Obliczanie bledu X/Y wzgledem srodka klatki (znormalizowane do zakresu ramki)
- [x] **VIS-04**: AWB fix dla sensora IMX219 — poprawne kolory bez blue/green tint
- [x] **VIS-05**: Wysylanie ramek binarnych do Arduino przez SerialInterface (OOP)
- [x] **VIS-06**: Heartbeat TX co 200ms (nawet gdy brak detekcji twarzy)
- [x] **VIS-07**: Graceful shutdown — zamkniecie kamery, portu serial, czysty exit

### HMI (HMI)

- [x] **HMI-01**: LCD 1602 wyswietla tryb (SCAN/TRACK/IDLE) i blad X/Y — update max 5Hz (nie w petli PID!)
- [x] **HMI-02**: Buzzer (D8) krotki dzwiek przy przejsciu do TRACK ("Target Lock")
- [x] **HMI-03**: Przycisk akcji (D7, INPUT_PULLUP) — "Abort Track" przywraca tryb SCAN
- [x] **HMI-04**: LCD bootscreen z nazwa systemu przy starcie Arduino

### Migracja (MIG)

- [x] **MIG-01**: Stary kod monolitu przeniesiony do katalogu legacy/ jako referencja
- [x] **MIG-02**: Nowa struktura katalogow: src/arduino/ (firmware), src/vision/ (pi brain)

### Integracja (INT)

- [x] **INT-01**: End-to-end tracking — twarz wykryta na RPi → blad wyslany → Arduino PID koryguje serwa → kamera sledzi twarz
- [x] **INT-02**: Poprawna logika kierunkow (negative feedback) — twarz po prawej = ruch serwa w prawo
- [x] **INT-03**: Os pionowa (tilt) dziala poprawnie w obu trybach (SCAN i TRACK)
- [x] **INT-04**: Kod modularny OOP: klasy VisionManager, SerialInterface, ServoPID
- [x] **INT-05**: Wszystkie komentarze w kodzie w jezyku polskim

## v2.1 Requirements (Deferred)

### Rozszerzenia protokolu

- **SER-06**: ACK/NACK bidirectional feedback z Arduino do RPi
- **SER-07**: Dynamiczna zmiana baudrate

### Zaawansowany PID

- **ARD-07**: Adaptywny PID — gain scheduling wg rozmiaru twarzy (blizej = mniejsze gainy)
- **ARD-08**: Profil ruchu — acceleration/deceleration curves dla serw

### Zaawansowana wizja

- **VIS-08**: Face ID / re-identification across frames (persistent tracking)
- **VIS-09**: Multi-model fallback (MediaPipe → DNN → HAAR)

### Interfejs webowy

- **WEB-01**: Flask web UI z MJPEG stream i panelem sterowania (port z legacy/)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Hardware WDT na Arduino Leonardo | Caterina bootloader bug — ryzyko zbrickowania, uzywamy millis() watchdog |
| Face Mesh (468 landmarks) | 4-5 FPS na RPi4 — za wolne, bbox wystarczy do trackingu |
| Flask web UI w v2.0 | Konkuruje o CPU z MediaPipe, odlozone do v2.1 |
| dlib face recognition | Za wolny na RPi4 (~2 FPS), MediaPipe zastepuje |
| Binary protocol z ACK/NACK | Zbyt zlozony dla MVP, fire-and-forget wystarcza |
| Animacje LCD (custom chars) | Nie krytyczne, mozliwe w v2.1 |
| ROS integration | Overengineering dla projektu research/hobby |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENV-01 | Phase 18 | Complete |
| ENV-02 | Phase 18 | Complete |
| SER-01 | Phase 18 | Complete |
| MIG-01 | Phase 18 | Complete |
| MIG-02 | Phase 18 | Complete |
| SER-02 | Phase 19 | Complete |
| SER-03 | Phase 19 | Complete |
| SER-04 | Phase 19 | Complete |
| SER-05 | Phase 19 | Complete |
| ARD-01 | Phase 20 | Complete |
| ARD-02 | Phase 20 | Complete |
| ARD-03 | Phase 20 | Complete |
| ARD-04 | Phase 20 | Complete |
| ARD-05 | Phase 20 | Complete |
| ARD-06 | Phase 20 | Complete |
| VIS-01 | Phase 21 | Complete |
| VIS-02 | Phase 21 | Complete |
| VIS-03 | Phase 21 | Complete |
| VIS-04 | Phase 21 | Complete |
| VIS-05 | Phase 21 | Complete |
| VIS-06 | Phase 21 | Complete |
| VIS-07 | Phase 21 | Complete |
| HMI-01 | Phase 22 | Complete |
| HMI-02 | Phase 22 | Complete |
| HMI-03 | Phase 22 | Complete |
| HMI-04 | Phase 22 | Complete |
| INT-01 | Phase 23 | Complete |
| INT-02 | Phase 23 | Complete |
| INT-03 | Phase 23 | Complete |
| INT-04 | Phase 23 | Complete |
| INT-05 | Phase 23 | Complete |

**Coverage:**
- v2.0 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 — traceability mapped after roadmap creation*
