# Phase 11: AWB Fix - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Naprawa AWB w test_tracker.py — neutralne kolory od pierwszej klatki. ColourGains w create_video_configuration() jako primary lock, re-lock po warm-up z wartosciami sensora. Obsluga bledow gdy sensor zwraca None lub (0.0, 0.0).

</domain>

<decisions>
## Implementation Decisions

### Strategia AWB Lock
- **D-01:** Dwa etapy ustawiania ColourGains:
  - Etap 1 (configure-time): Fallback gains w `create_video_configuration(controls={"ColourGains": AWB_FALLBACK_GAINS})` — neutralne kolory od frame 1, przed startem ISP
  - Etap 2 (post-start): Po 2s warm-up, `capture_metadata()` + `set_controls()` z rzeczywistymi gains sensora — re-lock z auto-AWB converged values
- **D-02:** Istniejacy re-read z Phase 9 (D-06) pozostaje — weryfikacja czy gains sie ustawily po set_controls

### Wartosci Fallback
- **D-03:** `AWB_FALLBACK_GAINS = (1.0, 1.0)` — neutralne, bez wzmocnienia. Minimalna ingerencja w kolory, eliminuje blue tint. Odkomentowac i uzyc w create_video_configuration()
- **D-04:** Fallback (0.0, 0.0) NIGDY nie uzywac — Picamera2 interpretuje jako "re-enable AWB"

### Obsluga Bledow
- **D-05:** Gdy `capture_metadata()["ColourGains"]` zwraca `None`: uzyj fallback `(1.0, 1.0)`, zaloguj WARNING. Nie crashuj, nie retry
- **D-06:** Gdy `capture_metadata()["ColourGains"]` zwraca `(0.0, 0.0)`: traktuj jak None — uzyj fallback, zaloguj WARNING ("AWB still running, using fallback")
- **D-07:** Odkomentowac fallback guard w `start()` (linie 82-84) — przywrocic obsluge None z nowa wartoscia (1.0, 1.0)

### Claude's Discretion
- Czas warm-up (2s) — Claude moze dostosowac jesli research wskazuje inna wartosc
- Kolejnosc logow — Claude zdecyduje o formacie komunikatow

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### AWB / Picamera2
- `src/modes/test_tracker.py` — `Picamera2Stream.start()` (linia 64+), `create_video_configuration()` (linia 67), AWB warm-up block (linia 78-101), `AWB_FALLBACK_GAINS` (linia 35, wykomentowane)
- `.planning/research/PITFALLS.md` — Pitfall 3 (AWB ColourGains API sequencing), Pitfall 6 (fallback gains values)

### Kontekst (nie modyfikowac)
- `src/vision.py` — main app, NIE dotykac w tej fazie

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AWB_FALLBACK_GAINS` stala (linia 35) — wykomentowana, trzeba odkomentowac i ustawic na (1.0, 1.0)
- `create_video_configuration()` (linia 67) — juz istnieje, trzeba dodac `controls` parametr
- AWB re-read block (linia 89-101) — Phase 9 dodala weryfikacje, zostaje bez zmian

### Established Patterns
- `set_controls({"ColourGains": gains})` — istniejacy pattern ustawiania gains
- `capture_metadata().get("ColourGains")` — istniejacy pattern odczytu gains
- Logging via `logger.info/warning` — standardowy Python logging

### Integration Points
- `create_video_configuration()` linia 67 — dodac `controls={"ColourGains": AWB_FALLBACK_GAINS}`
- `start()` linia 82-84 — odkomentowac fallback guard z nowa wartoscia
- Dodac guard na `(0.0, 0.0)` obok None check

</code_context>

<specifics>
## Specific Ideas

- Research PITFALLS.md: "pass ColourGains in controls dict of create_video_configuration() — guarantees first frame has correct colors"
- (0.0, 0.0) = re-enable AWB w Picamera2 — musi byc explicite filtrowane
- Verifier Phase 10 zauwazyl: wykomentowany fallback = crash risk gdy None

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-awb-fix*
*Context gathered: 2026-03-29*
