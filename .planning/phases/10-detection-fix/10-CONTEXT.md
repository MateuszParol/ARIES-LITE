# Phase 10: Detection Fix - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Tuning parametrow HAAR cascade w test_tracker.py — zmiana minSize i minNeighbors zeby detekcja dzialala w realnych warunkach (40-100cm, odchylenie glowy do ±30°). Zero zmian w architekturze detekcji, zero zmian w vision.py (main app).

</domain>

<decisions>
## Implementation Decisions

### Parametry HAAR
- **D-01:** `HAAR_MIN_SIZE = (40, 40)` — zmiana z (80,80). Pozwala na detekcje twarzy od 40cm do ~100cm przy FOV kamery RPi
- **D-02:** `HAAR_MIN_NEIGHBORS = 4` — zmiana z 8. Blizej default OpenCV (3), ale wciaz filtruje szum. Streak filter zapewnia dodatkowa filtracje

### Streak Filter
- **D-03:** `STREAK_REQUIRED = 3` — bez zmian. Research potwierdza ze 3 kolejne klatki (~100ms przy 30fps) to wystarczajacy filtr false positives nawet przy bardziej permisywnych parametrach HAAR

### Scope
- **D-04:** Zmiany TYLKO w `src/modes/test_tracker.py` — vision.py (main app) ma inna architekture (CSRT + dlib verification) i nie jest objeta ta faza
- **D-05:** Nie wyciagac parametrow do config.py — test tracker i main app maja rozne potrzeby, wspolne stale bylyby mylace

### Claude's Discretion
- scaleFactor: jesli 1.1 wymaga korekty przy nowych parametrach, Claude moze dostosowac
- Dodatkowe logging przy zmianie parametrow — Claude zdecyduje czy potrzebne

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Detection
- `src/modes/test_tracker.py` — `HAAR_MIN_NEIGHBORS` (linia 27), `HAAR_MIN_SIZE` (linia 28), `DetekcjaTwarzy.wykryj()` (linia 184+), `STREAK_REQUIRED` (linia 29)
- `.planning/research/PITFALLS.md` — root cause analysis: HAAR zbyt restrykcyjne parametry na 320x240

### Kontekst (nie modyfikowac)
- `src/vision.py` — main app HAAR params (minNeighbors=5, minSize=(60,60)) — NIE RUSZAC w tej fazie

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DetekcjaTwarzy` klasa — gotowy wrapper na HAAR z streak filterem, wystarczy zmienic stale
- `_rysuj_hud()` — juz rysuje zielone prostokaty z detekcji (Phase 9 dodala [MOCK] overlay)

### Established Patterns
- Stale HAAR na poczatku pliku test_tracker.py — proste do zmiany
- `detectMultiScale()` z named params — czytelne, latwe do modyfikacji
- Streak filter jako osobna warstwa nad HAAR — pozwala na permisywne HAAR bez false positives

### Integration Points
- Zmiana 2 stalych w test_tracker.py: `HAAR_MIN_NEIGHBORS` i `HAAR_MIN_SIZE`
- Brak zmian w interfejsach — `wykryj()` zwraca ten sam format bbox

</code_context>

<specifics>
## Specific Ideas

- Root cause z PITFALLS.md: "80px minimum = twarz musi zajmowac 25% szerokosci klatki" — to dlatego detekcja dzialala tylko z 30cm
- minNeighbors=8 to 2.5x wyzej niz default OpenCV — niemal eliminuje wszystkie nie-idealne detekcje
- Po tej zmianie: green rectangles powinny pojawiac sie na HUD przy normalnym uzyciu

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-detection-fix*
*Context gathered: 2026-03-29*
