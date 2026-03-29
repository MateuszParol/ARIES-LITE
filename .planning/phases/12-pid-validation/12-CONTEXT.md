# Phase 12: PID Validation - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Walidacja PID w test_tracker.py — potwierdzenie ze oba kontrolery PID (pan + tilt) obliczaja poprawne korekty i pan fizycznie reaguje na ruch twarzy. Dodanie flagi --debug do run_test_tracker.py. Naprawa bledow znaku/wiring jesli logi pokaza problem. Tilt freeze (serwo nie reaguje) to osobna faza — Phase 12 waliduje software path PID, nie hardware tilt.

</domain>

<decisions>
## Implementation Decisions

### Strategia walidacji
- **D-01:** Test empiryczny z logami — uruchom `python3 run_test_tracker.py --debug`, stoj przed kamera, obserwuj HUD + logi PID per-tick z Phase 9
- **D-02:** Istniejace logi PID per-tick (logger.debug) z Phase 9 sa wystarczajace — brak potrzeby dodatkowego logowania
- **D-03:** Dodac flag `--debug` do `run_test_tracker.py` — argument CLI ktory ustawia log level na DEBUG. Latwiejsze niz edycja kodu

### Reakcja na failure
- **D-04:** Jesli PID nie konwerguje — diagnoza + fix w tej fazie. Phase 12 to validation + fix jesli potrzebny
- **D-05:** Dopuszczalne naprawy: bledy znaku (brakujace minus), bledna os (pan zamiast tilt), brakujacy set_angles() call, bledny error calculation. Gains (Kp/Ki/Kd) nadal locked — bez zmian
- **D-06:** PID_OUTPUT_LIMIT, setpoint i inne parametry NIE sa w scope naprawy — tylko bledy znaku i wiring

### Scope tilt freeze
- **D-07:** Tilt freeze (HUD=0.0, serwo nie reaguje fizycznie) to OSOBNA FAZA — nie debugujemy hardware tilt w Phase 12
- **D-08:** PID-04 przechodzi jesli logi pokazuja blad_tilt != 0 i korekta_tilt != 0 — PID software path oblicza poprawnie, nawet jesli serwo fizycznie nie reaguje (to osobny bug)

### Claude's Discretion
- Format output flagi --debug (argparse vs sys.argv)
- Kolejnosc sprawdzen w walidacji

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### PID / Sterowanie
- `src/modes/test_tracker.py` — `MaszynaStanow.__init__()` (linia 215+), `_sledz()` (linia 277-305), PID diagnostyka per-tick (linie 298-305), `_przejdz_do()` (linia 309+)
- `src/config.py` — PID gains (PID_PAN_P/I/D, PID_TILT_P/I/D), STATE_TRACKING, STATE_SCANNING
- `src/hardware.py` — `PanTiltSystem.set_angles()`, pan_angle/tilt_angle properties, clamp WARNING logging

### Entry point
- `run_test_tracker.py` — entry point do dodania flagi --debug

### Kontekst (nie modyfikowac)
- `src/vision.py` — main app, NIE dotykac w tej fazie
- `src/tracker.py` — main app tracker, NIE dotykac w tej fazie

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- PID per-tick logging z Phase 9 (linie 298-305) — kompaktowy format `PAN err=... P=... I=... D=... out=... | TILT err=...`
- `set_angles()` clamp WARNING logging z v1.7 — wykrywa saturacje
- `_przejdz_do()` resetuje PID przy SCANNING — zapobiega wind-up carry-over

### Established Patterns
- `simple_pid.PID` z `pid.components` — zwraca (P, I, D) tuple
- Negacja obu osi: `korekta_pan = -pid_pan(blad_pan)`, `korekta_tilt = -pid_tilt(blad_tilt)`
- Error calculation: `blad_pan/tilt` jako roznica miedzy centrum kadru a centrum bbox

### Integration Points
- `run_test_tracker.py` — jedyny plik do dodania --debug (import argparse lub sys.argv)
- `src/modes/test_tracker.py` — ewentualne fixy bledow znaku w _sledz()

</code_context>

<specifics>
## Specific Ideas

- Phase 9 logi PID sa w logger.debug — bez --debug flag nie beda widoczne
- v1.7 potwierdzila tilt negation jako poprawna konwencje — nie zmieniac
- REQUIREMENTS Out of Scope: "Zmiana Kp/Ki/Kd gains — najpierw diagnostyka" — Phase 12 dostarcza te dane

</specifics>

<deferred>
## Deferred Ideas

- Tilt freeze fix (serwo tilt nie reaguje fizycznie) — osobna faza po Phase 12
- Tuning gains (Kp/Ki/Kd) — jesli Phase 12 pokaze ze gains sa nieoptymalne, to osobna faza z danymi z logow
- Automatyczny test konwergencji (parse logow, sprawdz czy error maleje) — potencjalna przyszla faza

</deferred>

---

*Phase: 12-pid-validation*
*Context gathered: 2026-03-29*
