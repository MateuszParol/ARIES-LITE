# Phase 15: PID Tracking Fix - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminacja agresywnej reakcji PID przy wejściu w stan SLEDZENIE — serwa nie uciekają do limitów kątowych, twarz centrowana w obu osiach w 1-3 sekundy. Zmiana polega na redukcji OUTPUT_LIMIT (5.0→3.0°/tick). Reset PID już zaimplementowany w Phase 14.

Faza NIE obejmuje: zmian gainów PID (KP/KI/KD), zmian w logice maszyny stanów, zmian protokołu binarnego 8B, zmian MediaPipe/detekcji, nowych funkcji HMI.

</domain>

<decisions>
## Implementation Decisions

### Strategia redukcji agresji PID
- **D-01:** Redukcja OUTPUT_LIMIT z 5.0 na 3.0°/tick — jedyna zmiana stałej. Gainy KP=2.0, KI=0.1, KD=0.5 pozostają bez zmian.
- **D-02:** Reset PID (`pid_reset()`) już istnieje w `_przejdz_do(SLEDZENIE)` (linia 705) — nie wymaga dodatkowej implementacji.

### Metoda weryfikacji
- **D-03:** Weryfikacja przez logi SD (CSV z DataLogger) + obserwacja wizualna. Logi sprawdzają: pan/tilt nie docierają do ±60/±30 w ciągu 2s od TRACKING, error_x/y maleją. Wizualnie: brak szarpnięcia serw.

### Podejście do strojenia
- **D-04:** Iteracyjne strojenie — max 2-3 iteracje. Start od OUTPUT_LIMIT=3.0, analiza logów SD między próbami. Jeśli 3.0 nie spełnia SC, dopuszczalna korekta (niższy limit lub ew. gainy jako fallback).

### Claude's Discretion
- Kolejność kroków w planie (zmiana stałej → kompilacja → upload → test → analiza logów)
- Kryterium akceptacji iteracji na podstawie logów CSV (próg konwergencji, definicja "brak CLAMP")
- Ewentualna korekta w drugiej/trzeciej iteracji jeśli 3.0 nie wystarczy

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Firmware Arduino
- `src/arduino/aries_controller/aries_controller.ino` — OUTPUT_LIMIT (linia 25), pid_krok() (linia 256-277), _przejdz_do() z pid_reset() (linia 694-708), PID gainy (linie 22-24)

### Protokół binarny
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja ramki 8B

### Kontekst wcześniejszych faz
- `.planning/phases/14-pid-sign-fix/14-CONTEXT.md` — D-01..D-09: kalibracja PAN_INVERT/TILT_INVERT, konwencja znaków error
- `.planning/phases/23-integracja-kalibracja/23-CONTEXT.md` — procedura kalibracji, zapis INVERT

### DataLogger (weryfikacja)
- Logi CSV na SD card: timestamp, stan, pan, tilt, error_x, error_y, face_size, latency_ms — źródło danych do weryfikacji SC

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DataLogger` (klasa w aries_controller.ino) — logowanie CSV co 10 klatek w SLEDZENIE, gotowe do analizy post-test
- `pid_reset()` w klasie ServoPID — już wywoływany przy przejściu do SLEDZENIE

### Established Patterns
- Stałe konfiguracyjne jako `#define` na początku .ino — OUTPUT_LIMIT, KP, KI, KD
- QuickPID z iAwCondition anti-windup + dOnMeas derivative mode
- Normalizacja error: piksel/POLOWA_RAMKI → zakres -1..+1

### Integration Points
- Jedyny punkt zmiany: `#define OUTPUT_LIMIT 5.0f` → `3.0f` w aries_controller.ino linia 25
- Kompilacja + upload na Uno R4 WiFi przez Arduino IDE/CLI

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-tilt-servo-fix*
*Context gathered: 2026-04-04*
