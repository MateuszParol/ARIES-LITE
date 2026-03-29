# Requirements: ARIES-LITE

**Defined:** 2026-03-29
**Core Value:** System skanuje plynnie w obu osiach, prawidlowe kolory, tracking bez ucieczki serw

## v1.9 Requirements

Requirements for milestone v1.9 Stabilizacja Ruchu i Obrazu.

### Kolory (AWB/Color)

- [ ] **COL-01**: Kamera oddaje prawidlowe kolory od pierwszej klatki (brak zielonej poswiaty)
- [ ] **COL-02**: Konwersja YUV→RGB uzywa prawidlowej flagi OpenCV (nie BGR swap)
- [ ] **COL-03**: AWB fallback gains odpowiadaja rzeczywistym wartosciom IMX219 (nie 1.0, 1.0)

### Tracking (PID)

- [ ] **TRK-01**: Serwa nie uciekaja do limitu po wejsciu w TRACKING
- [ ] **TRK-02**: PID reset() wykonywany przy przejsciu do TRACKING (czysty accumulator)
- [ ] **TRK-03**: PID output limit ogranicza maksymalna korekta per-tick do bezpiecznej wartosci

### Skanowanie (Scan)

- [ ] **SCN-01**: Tilt porusza sie podczas skanowania (sinusoida, nie staly 0.0)
- [ ] **SCN-02**: Skanowanie pokrywa obie osie (Lissajous pattern — pan + tilt)
- [ ] **SCN-03**: Phase offset zachowany przy powrocie do SCANNING (brak skoku serw)

### Plynnosc (Smoothness)

- [ ] **SMT-01**: Ruch serw podczas skanowania jest plynny (brak widocznego szarpania)
- [ ] **SMT-02**: DNN inference nie blokuje petli sterowania na tyle by powodowac klatkowanie

## Future Requirements

Deferred to future milestones.

### Kalibracja

- **KAL-01**: MG90S pulse width calibration w hardware.py (min_pulse_width, max_pulse_width)
- **KAL-02**: AWB gains odczytane z capture_metadata() per-srodowisko

## Out of Scope

| Feature | Reason |
|---------|--------|
| PID gain retuning (P/I/D) | v1.8 Phase 12 zwalidowal gains empirycznie — nie zmieniac |
| Servo interpolation thread | Zbyt zlozone; DNN_SKIP_EVERY + EMA wystarczy na ten milestone |
| Multi-face tracking | Osobny milestone (features) |
| Main app (server.py) fixes | v1.9 dotyczy wylacznie test trackera |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COL-01 | Phase 14 | Pending |
| COL-02 | Phase 14 | Pending |
| COL-03 | Phase 14 | Pending |
| TRK-01 | Phase 15 | Pending |
| TRK-02 | Phase 15 | Pending |
| TRK-03 | Phase 15 | Pending |
| SCN-01 | Phase 16 | Pending |
| SCN-02 | Phase 16 | Pending |
| SCN-03 | Phase 16 | Pending |
| SMT-01 | Phase 17 | Pending |
| SMT-02 | Phase 17 | Pending |

**Coverage:**
- v1.9 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-29*
*Last updated: 2026-03-29 — traceability uzupelniona po roadmap v1.9*
