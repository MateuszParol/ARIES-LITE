# Requirements: ARIES-LITE

**Defined:** 2026-03-29
**Core Value:** System dziala poprawnie na RPi4 — detekcja, PID, AWB, diagnostyka

## v1.8 Requirements

Wymagania dla milestone Critical Hardware Fix. Naprawa bugow persystujacych po v1.7 + ulepszenie detekcji.

### Diagnostyka

- [x] **DIAG-02**: HUD wyswietla indykator mock mode gdy pigpiod nie jest aktywny — operator widzi ze serwa sa w trybie symulacji
- [x] **DIAG-03**: Konsola loguje PID error i output (P, I, D components) dla obu osi w kazdym ticku TRACKING — wartosci widoczne w terminalu
- [x] **DIAG-04**: Konsola loguje ColourGains z capture_metadata() po AWB warm-up — operator widzi rzeczywiste gains z sensora

### Detekcja

- [x] **DET-01**: HAAR cascade wykrywa twarz z minSize=(40,40) i minNeighbors=4-5 na 320x240 — detekcja na odleglosc 40-100cm
- [x] **DET-02**: System wykrywa twarz pod katem do ±30° (nie tylko idealnie frontalnie) — zielony prostokat na HUD
- [ ] **DET-03**: OpenCV DNN detector (res10 lub YuNet) zastepuje HAAR jako glowny detektor — lepsza dokladnosc przy akceptowalnym FPS (>10)

### Kamera (AWB)

- [x] **AWB-01**: ColourGains sa ustawione na etapie create_video_configuration() — neutralne kolory od pierwszej klatki
- [x] **AWB-02**: Obraz nie ma blue tint — skora wyglada naturalnie w normalnym oswietleniu wewnetrznym

### PID/Sterowanie

- [ ] **PID-04**: Wartosc Tilt na HUD zmienia sie w TRACKING — PID output dociera do set_angles() i serwo tilt reaguje fizycznie
- [ ] **PID-05**: Zaden z osi nie ucieka (runaway) po wejsciu w TRACKING — sprzezenie zwrotne jest negatywne na obu osiach
- [ ] **PID-06**: Po stabilnej detekcji (10+ klatek) kamera centruje twarz w obu osiach — PID konwerguje do stanu ustalonego

## Future Requirements

### Scan Continuity (warunkowe)

- **SCAN-03**: Phase offset sinusoidy uzywa czasu relatywnego zamiast absolutnego — gladkie wznowienie skanu

## Out of Scope

| Feature | Reason |
|---------|--------|
| MediaPipe Face Detection | Brak wheela aarch64 na PyPI dla RPi4 Bookworm 64-bit |
| Kalman filter | PID jest locked decision — nie zmieniamy |
| Flask / MJPEG streaming | Test tracker jest standalone — bez web interface |
| dlib identity recognition | Obscures debugging — test tracker tracks any face |
| Zmiana Kp/Ki/Kd gains | Najpierw diagnostyka — nie zmieniamy gains bez danych z logow |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DIAG-02 | Phase 9 | Complete |
| DIAG-03 | Phase 9 | Complete |
| DIAG-04 | Phase 9 | Complete |
| DET-01 | Phase 10 | Complete |
| DET-02 | Phase 10 | Complete |
| AWB-01 | Phase 11 | Complete |
| AWB-02 | Phase 11 | Complete |
| PID-04 | Phase 12 | Pending |
| PID-05 | Phase 12 | Pending |
| PID-06 | Phase 12 | Pending |
| DET-03 | Phase 13 | Pending |

**Coverage:**
- v1.8 requirements: 11 total
- Mapped: 11/11 ✓
- Unmapped: 0

---
*Requirements defined: 2026-03-29*
*Traceability updated: 2026-03-29 (roadmap created)*
