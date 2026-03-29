# Roadmap: ARIES-LITE

## Milestones

- ✅ **v1.5.0 Stabilization & Hardening** — Phases 1-3 (shipped 2026-03-18)
- ✅ **v1.6 Test Tracker** — Phases 4-5 (shipped 2026-03-26)
- ✅ **v1.7 Debugging & Optimization** — Phases 6-8 (shipped 2026-03-29)
- 🚧 **v1.8 Critical Hardware Fix** — Phases 9-13 (in progress)

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

### 🚧 v1.8 Critical Hardware Fix (In Progress)

**Milestone Goal:** System dziala poprawnie na RPi4 — tilt reaguje, PID nie ucieka, obraz bez blue tint, detekcja twarzy jest responsywna.

- [x] **Phase 9: Diagnostics** - Mock mode indicator, PID component logging, AWB gains logging — zero risk, maximum observability before any hardware change (completed 2026-03-29)
- [x] **Phase 10: Detection Fix** - HAAR parameter tuning (minSize, minNeighbors) — root cause of frozen tilt and apparent PID failures (completed 2026-03-29)
- [x] **Phase 11: AWB Fix** - ColourGains at configure-time — neutral colors from frame 1 (completed 2026-03-29)
- [ ] **Phase 12: PID Validation** - Confirm tilt moves, no runaway, convergence — only after stable detection is verified
- [ ] **Phase 13: DNN Detector** - OpenCV DNN replacement for HAAR — conditional on HAAR tuning being insufficient

## Phase Details

### Phase 9: Diagnostics
**Goal**: Operator widzi stan hardware i dane PID/AWB w logach przed pierwszym uruchomieniem na RPi4
**Depends on**: Phase 8 (v1.7 shipped)
**Requirements**: DIAG-02, DIAG-03, DIAG-04
**Success Criteria** (what must be TRUE):
  1. HUD wyswietla etykiete `[MOCK]` gdy pigpiod nie jest aktywny — operator od razu wie ze serwa nie reaguja fizycznie
  2. Terminal loguje P, I, D components dla obu osi (pan i tilt) w kazdym ticku stanu TRACKING
  3. Terminal loguje rzeczywiste ColourGains z `capture_metadata()` po AWB warm-up — widoczne niezerowe wartosci R i B
**Plans**: 1 plan
Plans:
- [x] 09-01-PLAN.md — mock_mode property + [MOCK] HUD overlay + PID component logging + AWB gains re-read

### Phase 10: Detection Fix
**Goal**: HAAR cascade wykrywa twarze w realnych warunkach — zielone prostokaty widoczne na HUD przy normalnym uzytkowaniu
**Depends on**: Phase 9
**Requirements**: DET-01, DET-02
**Success Criteria** (what must be TRUE):
  1. Zielony prostokat pojawia sie na HUD przy odleglosci 40-100 cm od kamery
  2. Detekcja dziala przy odchyleniu glowy do ±30° od frontalnej pozycji — nie wymaga idealnego ustawienia
  3. Stan TRACKING jest utrzymywany przez co najmniej 3 sekundy bez przerwy po wejsciu
**Plans**: 1 plan
Plans:
- [x] 10-01-PLAN.md — HAAR_MIN_SIZE=(40,40) + HAAR_MIN_NEIGHBORS=4 + empiryczna weryfikacja na RPi4

### Phase 11: AWB Fix
**Goal**: Kamera renderuje naturalne kolory od pierwszej klatki — brak blue tint w kazdych warunkach oswietlenia
**Depends on**: Phase 9
**Requirements**: AWB-01, AWB-02
**Success Criteria** (what must be TRUE):
  1. Pierwsza klatka wideo nie ma blue tint — skora wyglada naturalnie juz przy starcie aplikacji
  2. Log ColourGains pokazuje niezerowe wartosci R i B (np. `(2.5, 1.9)`) potwierdzone z `capture_metadata()`
  3. ColourGains sa ustawione w `create_video_configuration()` — nie tylko po `start()`
**Plans**: 1 plan
Plans:
- [x] 11-01-PLAN.md — AWB configure-time lock + fallback guard + weryfikacja wizualna

### Phase 12: PID Validation
**Goal**: Oba serwomotory reaguja na ruch twarzy i konwerguja do srodka kadru bez ucieczki
**Depends on**: Phase 10
**Requirements**: PID-04, PID-05, PID-06
**Success Criteria** (what must be TRUE):
  1. Wartosc Tilt na HUD zmienia sie w trakcie stanu TRACKING — serwo tilt fizycznie przesuwa sie gdy twarz jest poza centrum
  2. Zadna os nie ucieka do limitu po wejsciu w TRACKING — ruch jest proporcjonalny do bledu, nie natychmiastowy
  3. Po 10+ klatkach stabilnej detekcji twarz jest wycentrowana w obu osiach — PID osiaga stan ustalony
**Plans**: 1 plan
Plans:
- [ ] 12-01-PLAN.md — --debug flag + empiryczna walidacja PID na RPi4

### Phase 13: DNN Detector
**Goal**: OpenCV DNN zastepuje HAAR jako glowny detektor gdy HAAR jest niewystarczajacy — lepsza dokladnosc przy akceptowalnym FPS
**Depends on**: Phase 10
**Requirements**: DET-03
**Success Criteria** (what must be TRUE):
  1. Detektor wykrywa twarz pod katem i przy czesciowym zaslonieniu gdzie HAAR zawiodl
  2. FPS nie spada ponizej 10 klatek/s przy DNN detekcji na RPi4 — system jest responsive
  3. Interfejs `wykryj()` jest zachowany — `MaszynaStanow` i `TestTracker` nie wymagaja zmian
**Plans**: TBD

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
| 9. Diagnostics | v1.8 | 1/1 | Complete   | 2026-03-29 |
| 10. Detection Fix | v1.8 | 1/1 | Complete    | 2026-03-29 |
| 11. AWB Fix | v1.8 | 1/1 | Complete    | 2026-03-29 |
| 12. PID Validation | v1.8 | 0/1 | Planned | - |
| 13. DNN Detector | v1.8 | 0/? | Not started | - |
