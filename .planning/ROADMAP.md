# Roadmap: ARIES-LITE

## Milestones

- ✅ **v1.5.0 Stabilization & Hardening** — Phases 1-3 (shipped 2026-03-18)
- ✅ **v1.6 Test Tracker** — Phases 4-5 (shipped 2026-03-26)
- ✅ **v1.7 Debugging & Optimization** — Phases 6-8 (shipped 2026-03-29)
- ✅ **v1.8 Critical Hardware Fix** — Phases 9-13 (shipped 2026-03-29)
- 🚧 **v1.9 Stabilizacja Ruchu i Obrazu** — Phases 14-17 (in progress)
- 📋 **v2.0 Architektura Rozproszona** — Phases 18-23 (planned)

## Phases

<details>
<summary>✅ v1.5.0 Stabilization & Hardening (Phases 1-3) — SHIPPED 2026-03-18</summary>

- [x] Phase 1: Critical Bug Fixes & Code Correctness (1/1 plans) — completed 2026-03-18
- [x] Phase 2: Robustness & Reliability (1/1 plans) — completed 2026-03-18
- [x] Phase 3: Cleanup & Quality (1/1 plans) — completed 2026-03-18

</details>

<details>
<summary>✅ v1.6 Test Tracker (Phases 4-5) — SHIPPED 2026-03-26</summary>

- [x] **Phase 4: Hardware Foundation & Camera Integration** - Servo safe startup, Picamera2 frame capture, and graceful shutdown proven on real hardware (completed 2026-03-26)
- [x] **Phase 5: State Machine, Vision & PID Integration** - Complete SCANNING → TRACKING → TARGET_LOST control loop with face detection and HUD (completed 2026-03-26)

</details>

<details>
<summary>✅ v1.7 Debugging & Optimization (Phases 6-8) — SHIPPED 2026-03-29</summary>

- [x] **Phase 6: Diagnostics & Camera** - Clamp logging + AWB warm-up lock (completed 2026-03-27)
- [x] **Phase 7: PID Sign Correctness** - Tilt sign fix + hardware verification (completed 2026-03-27)
- [x] **Phase 8: Scanning Logic** - Phase offset + streak reset timing (completed 2026-03-27)

</details>

<details>
<summary>✅ v1.8 Critical Hardware Fix (Phases 9-13) — SHIPPED 2026-03-29</summary>

- [x] **Phase 9: Diagnostics** - Mock mode indicator, PID component logging, AWB gains logging (completed 2026-03-29)
- [x] **Phase 10: Detection Fix** - HAAR parameter tuning (minSize, minNeighbors) (completed 2026-03-29)
- [x] **Phase 11: AWB Fix** - ColourGains at configure-time — neutral colors from frame 1 (completed 2026-03-29)
- [x] **Phase 12: PID Validation** - Confirm tilt moves, no runaway, convergence (completed 2026-03-29)
- [x] **Phase 13: DNN Detector** - OpenCV DNN replacement for HAAR (completed 2026-03-29)

</details>

### 🚧 v1.9 Stabilizacja Ruchu i Obrazu (In Progress)

**Milestone Goal:** System skanuje plynnie w obu osiach, kamera oddaje prawidlowe kolory, a tracking nie powoduje ucieczki serw.

- [ ] **Phase 14: AWB/Color Fix** - Naprawa zielonej poswiaty: flaga cvtColor i fallback ColourGains
- [ ] **Phase 15: PID Tracking Fix** - Reset PID przy wejsciu w TRACKING + redukcja output limit
- [ ] **Phase 16: Tilt Scan Fix** - Sinusoida tilt w _skanuj() — Lissajous 2D z phase-offset continuity
- [ ] **Phase 17: Scan Smoothness** - DNN_SKIP_EVERY wzrost + opcjonalne EMA wygladzanie serw

### 📋 v2.0 Architektura Rozproszona (Planned)

**Milestone Goal:** Calkowita przebudowa na architekture rozproszona — RPi4 (MediaPipe wizja + serial TX) + Arduino Leonardo (PID 100 Hz + HMI) polaczone USB Serial 115200 baud.

- [x] **Phase 18: Srodowisko + Protokol + Migracja** - MediaPipe zweryfikowany na RPi4, binarny protokol 8-bajtowy specyfikacja zamknieta, stary kod w legacy/ (completed 2026-03-30)
- [x] **Phase 19: Serial Link + Echo Test** - SerialSender (RPi) + parser state-machine (Arduino) + end-to-end echo test (completed 2026-03-31)
- [ ] **Phase 20: Firmware Arduino PID + Servo** - QuickPID 100 Hz, safe startup, watchdog millis(), konfigurowalny kierunek serw, maszyna stanow, skan sinusoidalny
- [ ] **Phase 21: Wizja RPi MediaPipe** - pi_brain.py: MediaPipe FaceDetector, sticky tracking, blad X/Y, AWB fix, TX do Arduino, graceful shutdown
- [ ] **Phase 22: HMI LCD + Buzzer + Przycisk** - LCD 1602 status, buzzer na zmiane stanu, przycisk Abort Track
- [ ] **Phase 23: Integracja + Kalibracja** - End-to-end tracking, kalibracja kierunkow serw, modularnosc OOP, komentarze polskie

## Phase Details

### Phase 14: AWB/Color Fix
**Goal**: Kamera oddaje prawidlowe kolory od pierwszej klatki — brak zielonej poswiaty niezaleznie od sceny
**Depends on**: Phase 13 (v1.8 shipped)
**Requirements**: COL-01, COL-02, COL-03
**Success Criteria** (what must be TRUE):
  1. Obraz kamerowy nie ma zielonej poswiaty — skora wyglada naturalnie od pierwszej klatki po starcie
  2. Poruszanie kamera przed roznymi tlami nie zmienia dominujacego odcienia barwnego (kanal G nie jest staly)
  3. Log AWB warm-up pokazuje ColourGains z R > 1.4 i B > 1.4 — wartosci realistyczne dla IMX219
**Plans**: 1 plan

Plans:
- [ ] 14-01-PLAN.md — COLOR_YUV420p2BGR → COLOR_YUV420p2RGB + AWB_FALLBACK_GAINS (2.2, 1.8) + weryfikacja wizualna

### Phase 15: PID Tracking Fix
**Goal**: Przejscie w stan TRACKING nie powoduje natychmiastowej ucieczki serw do limitow
**Depends on**: Phase 14
**Requirements**: TRK-01, TRK-02, TRK-03
**Success Criteria** (what must be TRUE):
  1. Po wejsciu w TRACKING serwa nie docieraja do limitow katowych w ciagu pierwszych 2 sekund
  2. Twarz zostaje wycentrowana w obu osiach w ciagu 1-3 sekund od wejscia w TRACKING — widoczna konwergencja PID
  3. Brak ciaglych ostrzezen CLAMP w logach terminala po wejsciu w TRACKING
**Plans**: 2 plans

Plans:
- [ ] 15-01: pid_pan.reset() + pid_tilt.reset() na wejscie TRACKING + PID_OUTPUT_LIMIT 10.0 → 3.0

### Phase 16: Tilt Scan Fix
**Goal**: Skanowanie pokrywa obie osie — kamera przemieszcza sie w pionie i poziomie podczas stanu SCANNING
**Depends on**: Phase 15
**Requirements**: SCN-01, SCN-02, SCN-03
**Success Criteria** (what must be TRUE):
  1. Wartosc Tilt na HUD zmienia sie podczas stanu SCANNING — serwo tilt fizycznie oscyluje
  2. Sciezka skanowania tworzy wzorzec Lissajous — kamera pokrywa pole widzenia w obu osiach
  3. Powrot do stanu SCANNING po TARGET_LOST nie powoduje skoku serwa tilt — plynna kontynuacja z aktualnej pozycji
**Plans**: 2 plans

Plans:
- [ ] 16-01: SCAN_AMPLITUDE_TILT=15.0 + SCAN_FREQUENCY_TILT=0.07 w _skanuj() + phase-offset dla tilt

### Phase 17: Scan Smoothness
**Goal**: Ruch serw podczas skanowania jest plynny bez widocznych szarpan powodowanych przez DNN inference
**Depends on**: Phase 16
**Requirements**: SMT-01, SMT-02
**Success Criteria** (what must be TRUE):
  1. Skanowanie wizualnie wyglada na plynne — brak wyraznych szarpan widocznych golym okiem
  2. Petla sterowania wykonuje wywolania set_angles() w regularnych odstepach — FPS nie spada ponizej 10 podczas skanowania
**Plans**: 2 plans

Plans:
- [ ] 17-01: DNN_SKIP_EVERY 5 → 10 + empiryczna weryfikacja plynnosci na RPi4 (opcjonalnie EMA jesli niewystarczajace)

### Phase 18: Srodowisko + Protokol + Migracja
**Goal**: Srodowisko deweloperskie gotowe na obu wezlach, protokol binarny w pelni zspecyfikowany i zablokowany, stary monolit przeniesiony do legacy/
**Depends on**: Phase 17 (v1.9 shipped)
**Requirements**: ENV-01, ENV-02, SER-01, MIG-01, MIG-02
**Success Criteria** (what must be TRUE):
  1. `import mediapipe` dziala na RPi4 bez bledow — potwierdzony Python 3.12 + Trixie
  2. Arduino IDE / arduino-cli kompiluje szkielet firmware z QuickPID, Servo, LiquidCrystal bez bledow
  3. Plik specyfikacji protokolu opisuje wszystkie 8 bajtow ramki (start 0xAA, tryb, int16 error_x, int16 error_y, uint8 face_size, XOR checksum) — zamkniety przed jakimkolwiek kodem
  4. Katalogi src/arduino/ i src/vision/ istnieja w repo; stary kod dziala w legacy/ bez regresji
**Plans**: 2 plans

Plans:
- [x] 18-01-PLAN.md — Specyfikacja protokolu binarnego + migracja monolitu do legacy/ + nowa struktura src/
- [x] 18-02-PLAN.md — Python 3.12 venv z MediaPipe + arduino-cli z weryfikacja kompilacji

### Phase 19: Serial Link + Echo Test
**Goal**: Warstwa szeregowa dziala end-to-end — RPi wysyla poprawne ramki binarne, Arduino parsuje je bez bledow i potwierdza odczyt przez Serial Monitor
**Depends on**: Phase 18
**Requirements**: SER-02, SER-03, SER-04, SER-05
**Success Criteria** (what must be TRUE):
  1. Arduino Serial Monitor pokazuje poprawnie zdekodowane pola ramki dla kazdej ramki wyslanej przez RPi (tryb, error_x, error_y, face_size, checksum OK)
  2. RPi otwiera port /dev/ttyACM0 z dtr=False i low_latency — Arduino nie resetuje sie przy polaczeniu
  3. Heartbeat RPi (co 200ms) jest widoczny w parserze Arduino — log lub LED potwierdzajacy zywotnosc polaczenia
  4. Odlaczenie USB podczas dzialania i ponowne podlaczenie — parser Arduino resyncuje sie poprawnie na znaczniku 0xAA
**Plans**: 2 plans

### Phase 20: Firmware Arduino PID + Servo
**Goal**: Arduino steruje serwami w sposob deterministyczny — PID 100 Hz, bezpieczny startup, autonomiczny skan sinusoidalny, watchdog millis() zwraca do SCAN po utracie komunikacji
**Depends on**: Phase 19
**Requirements**: ARD-01, ARD-02, ARD-03, ARD-04, ARD-05, ARD-06
**Success Criteria** (what must be TRUE):
  1. Serwa plynnie docieraja do pozycji 90/90 przy starcie — brak skoku pradu na zasilaniu 6V
  2. Petla PID wykonuje sie co 10ms (±1ms) — mierzalne przez znaczniki Serial lub oscyloskop
  3. Przy braku ramek przez >500ms Arduino przechodzi autonomicznie do trybu SCAN — serwa zaczynaja skan sinusoidalny bez interwencji RPi
  4. Zmiana PAN_INVERT / TILT_INVERT w #define odwraca kierunek serwa — kalibracja empiryczna mozliwa bez przepisywania kodu
  5. Maszyna stanow przechodzi IDLE → SCAN → TRACK w odpowiedzi na ramki z RPi
**Plans**: 2 plans

### Phase 21: Wizja RPi MediaPipe
**Goal**: RPi4 wykrywa twarze przez MediaPipe, oblicza blad X/Y i wysyla ramki do Arduino w sposob ciagly — kamera sledzi twarz bez Flaska
**Depends on**: Phase 20
**Requirements**: VIS-01, VIS-02, VIS-03, VIS-04, VIS-05, VIS-06, VIS-07
**Success Criteria** (what must be TRUE):
  1. MediaPipe FaceDetector wykrywa twarz w kadrze Picamera2 320x240 — bbox widoczny w podglad/logu przy FPS >= 10
  2. Przy kilku twarzach w kadrze system sledzi konsekwentnie najwieksza (sticky selection) — brak migotania miedzy celami
  3. Obraz Picamera2 nie ma niebieskiej/zielonej poswiaty — AWB lock (start + 2s sleep + capture_metadata) dziala poprawnie
  4. pi_brain.py zamyka sie czysto na Ctrl+C — serial.close() i camera.stop() wywolane bez wyjatkow
  5. Heartbeat TX co 200ms nawet gdy brak detekcji twarzy — Arduino watchdog nie odpala sie przy wykrytej twarzy poza kadrem
**Plans**: 2 plans
**UI hint**: yes

### Phase 22: HMI LCD + Buzzer + Przycisk
**Goal**: Uzytkownik widzi stan systemu na LCD i slyszy potwierdzenie dzwiekowe przy zmianie stanu — fizyczny przycisk przywraca SCAN
**Depends on**: Phase 21
**Requirements**: HMI-01, HMI-02, HMI-03, HMI-04
**Success Criteria** (what must be TRUE):
  1. LCD Row 0 pokazuje aktualny tryb (SKANOWANIE / SLEDZENIE / BEZCZYNNOSC) — aktualizacja widoczna w ciagu 200ms od zmiany stanu
  2. Buzzer emituje krotki ton przy przejsciu do trybu SLEDZENIE — slyszalne z odleglosci 1m
  3. Wcisniecie przycisku D7 podczas SLEDZENIE przywraca tryb SKANOWANIE — reakcja w ciagu 50ms (debounce 20ms)
  4. LCD bootscreen z nazwa systemu widoczny przez pierwsze 2 sekundy po wlaczeniu Arduino
**Plans**: 2 plans

### Phase 23: Integracja + Kalibracja
**Goal**: System dziala end-to-end jako rozproszony tracker — twarz na RPi powoduje ruch serw przez Arduino PID, kierunki poprawne, kod modularny
**Depends on**: Phase 22
**Requirements**: INT-01, INT-02, INT-03, INT-04, INT-05
**Success Criteria** (what must be TRUE):
  1. Twarz wykryta na RPi powoduje ruch serw na Arduino w ciagu <100ms — latencja end-to-end mierzalna przez log timestamps
  2. Twarz po prawej stronie kadru = serwo pan przesuwa kamera w prawo (negative feedback poprawny) — brak ucieczki serw
  3. Os tilt dziala poprawnie w obu trybach: tilt oscyluje podczas SCAN, tilt sledzi twarz podczas TRACK
  4. Kod podzielony na klasy VisionManager, SerialInterface, ServoPID — kazda klasa w oddzielnym pliku bez cyklicznych importow
  5. Wszystkie komentarze, nazwy zmiennych i komunikaty w kodzie sa w jezyku polskim
**Plans**: 2 plans

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Bug Fixes | v1.5 | 1/1 | Complete | 2026-03-18 |
| 2. Robustness | v1.5 | 1/1 | Complete | 2026-03-18 |
| 3. Cleanup | v1.5 | 1/1 | Complete | 2026-03-18 |
| 4. Hardware Foundation | v1.6 | 1/1 | Complete | 2026-03-26 |
| 5. State Machine & PID | v1.6 | 1/1 | Complete | 2026-03-26 |
| 6. Diagnostics & Camera | v1.7 | 1/1 | Complete | 2026-03-27 |
| 7. PID Sign Correctness | v1.7 | 2/2 | Complete | 2026-03-27 |
| 8. Scanning Logic | v1.7 | 1/1 | Complete | 2026-03-27 |
| 9. Diagnostics | v1.8 | 1/1 | Complete | 2026-03-29 |
| 10. Detection Fix | v1.8 | 1/1 | Complete | 2026-03-29 |
| 11. AWB Fix | v1.8 | 1/1 | Complete | 2026-03-29 |
| 12. PID Validation | v1.8 | 1/1 | Complete | 2026-03-29 |
| 13. DNN Detector | v1.8 | 1/1 | Complete | 2026-03-29 |
| 14. AWB/Color Fix | v1.9 | 0/1 | Not started | - |
| 15. PID Tracking Fix | v1.9 | 0/1 | Not started | - |
| 16. Tilt Scan Fix | v1.9 | 0/1 | Not started | - |
| 17. Scan Smoothness | v1.9 | 0/1 | Not started | - |
| 18. Srodowisko + Protokol + Migracja | v2.0 | 2/2 | Complete    | 2026-03-30 |
| 19. Serial Link + Echo Test | v2.0 | 2/2 | Complete    | 2026-03-31 |
| 20. Firmware Arduino PID + Servo | v2.0 | 0/? | Not started | - |
| 21. Wizja RPi MediaPipe | v2.0 | 0/? | Not started | - |
| 22. HMI LCD + Buzzer + Przycisk | v2.0 | 0/? | Not started | - |
| 23. Integracja + Kalibracja | v2.0 | 0/? | Not started | - |
