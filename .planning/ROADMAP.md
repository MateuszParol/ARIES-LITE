# Roadmap: ARIES-LITE

## Milestones

- ✅ **v1.5.0 Stabilization & Hardening** — Phases 1-3 (shipped 2026-03-18)
- ✅ **v1.6 Test Tracker** — Phases 4-5 (shipped 2026-03-26)
- ✅ **v1.7 Debugging & Optimization** — Phases 6-8 (shipped 2026-03-29)
- ✅ **v1.8 Critical Hardware Fix** — Phases 9-13 (shipped 2026-03-29)
- 🚧 **v1.9 Stabilizacja Ruchu i Obrazu** — Phases 14-17 (in progress)

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

## Phase Details

### Phase 14: AWB/Color Fix
**Goal**: Kamera oddaje prawidlowe kolory od pierwszej klatki — brak zielonej poswiaty niezaleznie od sceny
**Depends on**: Phase 13 (v1.8 shipped)
**Requirements**: COL-01, COL-02, COL-03
**Success Criteria** (what must be TRUE):
  1. Obraz kamerowy nie ma zielonej poswiaty — skora wyglada naturalnie od pierwszej klatki po starcie
  2. Poruszanie kamera przed roznymi tlami nie zmienia dominujacego odcienia barwnego (kanal G nie jest staly)
  3. Log AWB warm-up pokazuje ColourGains z R > 1.4 i B > 1.4 — wartosci realistyczne dla IMX219
**Plans**: TBD

Plans:
- [ ] 14-01: COLOR_YUV420p2BGR → COLOR_YUV420p2RGB + AWB_FALLBACK_GAINS (2.2, 1.8) + weryfikacja wizualna

### Phase 15: PID Tracking Fix
**Goal**: Przejscie w stan TRACKING nie powoduje natychmiastowej ucieczki serw do limitow
**Depends on**: Phase 14
**Requirements**: TRK-01, TRK-02, TRK-03
**Success Criteria** (what must be TRUE):
  1. Po wejsciu w TRACKING serwa nie docieraja do limitow katowych w ciagu pierwszych 2 sekund
  2. Twarz zostaje wycentrowana w obu osiach w ciagu 1-3 sekund od wejscia w TRACKING — widoczna konwergencja PID
  3. Brak ciaglych ostrzezen CLAMP w logach terminala po wejsciu w TRACKING
**Plans**: TBD

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
**Plans**: TBD

Plans:
- [ ] 16-01: SCAN_AMPLITUDE_TILT=15.0 + SCAN_FREQUENCY_TILT=0.07 w _skanuj() + phase-offset dla tilt

### Phase 17: Scan Smoothness
**Goal**: Ruch serw podczas skanowania jest plynny bez widocznych szarpan powodowanych przez DNN inference
**Depends on**: Phase 16
**Requirements**: SMT-01, SMT-02
**Success Criteria** (what must be TRUE):
  1. Skanowanie wizualnie wyglada na plynne — brak wyraznych szarpan widocznych golym okiem
  2. Petla sterowania wykonuje wywolania set_angles() w regularnych odstepach — FPS nie spada ponizej 10 podczas skanowania
**Plans**: TBD

Plans:
- [ ] 17-01: DNN_SKIP_EVERY 5 → 10 + empiryczna weryfikacja plynnosci na RPi4 (opcjonalnie EMA jesli niewystarczajace)

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
