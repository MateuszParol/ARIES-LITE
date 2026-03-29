# Phase 9: Diagnostics - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Dodanie logów diagnostycznych i wskaźnika mock mode do test_tracker.py — zero zmian w logice sterowania, maksymalna widoczność stanu systemu przed jakąkolwiek sesją debugowania na hardware RPi4.

</domain>

<decisions>
## Implementation Decisions

### Mock Mode Indicator
- **D-01:** Czerwony tekst `[MOCK]` w rogu HUD overlay gdy `PanTiltSystem._mock_mode` jest True — operator widzi natychmiast bez czytania terminala
- **D-02:** HUD musi mieć dostęp do flagi `_mock_mode` z hardware.py — przekazać jako property lub parametr do `_rysuj_hud()`

### PID Component Logging
- **D-03:** Logowanie co tick w TRACKING — kompaktowy format jednolinijkowy: `PAN err=+12.3 P=1.2 I=0.1 D=-0.3 out=+1.0 | TILT err=-5.1 P=... out=...`
- **D-04:** Użyć `pid.components` z simple-pid (>= 2.0) — zwraca (P, I, D) tuple po każdym wywołaniu `pid(error)`
- **D-05:** Logowanie w `_sledz()` po obliczeniu korekty — pokazuje zarówno error jak i output PID dla obu osi

### AWB Diagnostyka
- **D-06:** Po `set_controls({"ColourGains": gains})` zrobić ponowny `capture_metadata()` i zweryfikować czy gains faktycznie się ustawiły — wykrywa silent failure
- **D-07:** Logować zarówno wymagane gains jak i potwierdzone gains z re-read — jeśli różne = AWB silent failure

### Claude's Discretion
- Log level: logger.debug() vs logger.info() dla PID per-tick — Claude wybierze odpowiedni poziom
- Pozycja [MOCK] tekstu na HUD — Claude wybierze optymalną pozycję i kolor

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Hardware / Mock Mode
- `src/hardware.py` — `PanTiltSystem._mock_mode`, `PIGPIO_AVAILABLE` flag, `set_angles()` z clamp logic
- `src/config.py` — stałe PID gains, servo limits

### Test Tracker / HUD
- `src/modes/test_tracker.py` — `_rysuj_hud()` (linia 363+), `_sledz()` (linia 262+), `Picamera2Stream.start()` (AWB warm-up linia 78+)

### Research
- `.planning/research/SUMMARY.md` — syntetyzowane wyniki researchu v1.8
- `.planning/research/PITFALLS.md` — mock mode invisible pitfall, detection root cause

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `hardware.py:_mock_mode` (bool) — już istnieje, trzeba tylko wyeksponować do HUD
- `simple-pid.components` property — (P, I, D) tuple dostępne po każdym `pid(error)` call
- `_rysuj_hud()` — istniejący renderer HUD z cv2.putText, łatwy do rozszerzenia
- AWB warm-up block w `Picamera2Stream.start()` linia 78-87 — tu dodać weryfikację gains

### Established Patterns
- Logging via `logger = logging.getLogger(__name__)` — standard Python logging
- HUD text via `cv2.putText()` z kolorami BGR
- `set_angles()` loguje WARNING przy clamp (DIAG-01 z v1.7)

### Integration Points
- `_rysuj_hud()` — dodać [MOCK] overlay (potrzebna flaga mock z hardware)
- `_sledz()` — dodać PID logging po liniach 275-276 (po obliczeniu korekty)
- `Picamera2Stream.start()` — dodać re-read metadata po set_controls (linia 85)
- `MaszynaStanow.__init__` lub `TestTracker` — przekazać mock_mode do HUD

</code_context>

<specifics>
## Specific Ideas

- Format PID log: `PAN err=+12.3 P=1.2 I=0.1 D=-0.3 out=+1.0 | TILT err=-5.1 P=... out=...`
- [MOCK] tekst w czerwonym kolorze na HUD — widoczny natychmiast
- AWB weryfikacja: porównanie wymaganych vs rzeczywistych gains po set_controls

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-diagnostics*
*Context gathered: 2026-03-29*
