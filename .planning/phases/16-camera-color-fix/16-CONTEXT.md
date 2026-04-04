# Phase 16: Tilt Scan Fix - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Weryfikacja i naprawa skanowania Lissajous 2D na firmware Arduino — potwierdzenie ze oba serwa (pan + tilt) oscyluja w stanie SKANOWANIE, oraz implementacja phase-offset continuity eliminujacej skok serw przy przejsciu SLEDZENIE→SKANOWANIE. Opcjonalne strojenie parametrow Lissajous jesli pokrycie FOV nieoptymalne.

Faza NIE obejmuje: zmian w kodzie RPi (brain.py, detector.py), zmian protokolu binarnego 8B, zmian PID gains, zmian HMI, zmian DataLogger.

**UWAGA:** Faza byla oryginalnie napisana dla `_skanuj()` w starym monolicie (test_tracker.py). W architekturze v2.0+ skanowanie jest autonomiczne na Arduino w `skan_krok()` (aries_controller.ino linia 282). Cel SC pozostaje ten sam, ale plik docelowy to firmware Arduino.

</domain>

<decisions>
## Implementation Decisions

### Zakres fazy
- **D-01:** Firmware juz implementuje Lissajous 2D (`skan_krok()` linia 282) z SCAN_AMP_PAN=70°, SCAN_AMP_TILT=25°, SCAN_FREQ_PAN=0.05 Hz, SCAN_FREQ_TILT=0.073 Hz. SC #1 (tilt oscyluje) i SC #2 (wzorzec Lissajous) wymagaja weryfikacji empirycznej na sprzecie — kod istnieje, ale nie potwierdzone na zywo.
- **D-02:** Glowna praca programistyczna to SC #3: phase-offset continuity — eliminacja skoku serw przy przejsciu SLEDZENIE→SKANOWANIE.
- **D-03:** Jesli SC #1/#2 nie dzialaja na sprzecie — debug firmware jako czesc fazy.
- **D-04:** Opcjonalne strojenie parametrow Lissajous jesli pokrycie FOV nieoptymalne (max 2-3 iteracje).

### Phase-offset continuity (SC #3)
- **D-05:** Metoda: obliczenie t_offset z aktualnej pozycji serwa przy przejsciu do SKANOWANIE. Zamiast `resetuj_czas_skanu()` (t=0 → sin(0)=0 → skok), oblicz t taki ze sin(2π*f*t) = aktualna_pozycja/amplituda (arcsin + uwzglednienie kwadrantu).
- **D-06:** Osobny t_offset dla kazdej osi — t_offset_pan i t_offset_tilt obliczane niezaleznie. Dokladniejsza kontynuacja, akceptowalne rozjechanie sie wzgledem oryginalnego wzorca.
- **D-07:** Implementacja w `resetuj_czas_skanu()` lub nowej metodzie w klasie SerwoSterowanie w firmware Arduino.

### Parametry Lissajous
- **D-08:** Obecne parametry (AMP_PAN=70°, AMP_TILT=25°, FREQ_PAN=0.05, FREQ_TILT=0.073) jako punkt startowy. Strojenie empiryczne jesli potrzebne.
- **D-09:** Claude's Discretion — priorytet strojenia (pokrycie FOV vs plynnosc ruchu) i konkretne korekty wartosci na podstawie charakterystyki serw MG-90S.

### Weryfikacja empiryczna
- **D-10:** Metoda weryfikacji: logi SD CSV (DataLogger juz loguje pan/tilt/stan co 10 klatek) + obserwacja wizualna.
- **D-11:** Prog akceptacji skoku: max 5° na obu osiach przy przejsciu TARGET_LOST→SKANOWANIE. Skok >5° = fail SC #3.
- **D-12:** SC #1: w logach CSV wartosc tilt zmienia sie w wierszach ze stanem SKANOWANIE. SC #2: pan i tilt nie sa w fazie (rozne czestotliwosci). SC #3: roznica miedzy ostatnim katem w SLEDZENIE a pierwszym w SKANOWANIE ≤5°.

### Claude's Discretion
- Priorytet strojenia parametrow Lissajous — pokrycie FOV vs plynnosc ruchu (D-09)
- Dokladna implementacja arcsin + kwadrant w firmware Arduino (ograniczenia float na AVR)
- Kolejnosc krokow w planie (weryfikacja → fix → strojenie)
- Kryterium konwergencji iteracji strojenia

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Firmware Arduino (plik docelowy)
- `src/arduino/aries_controller/aries_controller.ino` — `skan_krok()` (linia 282-290), `resetuj_czas_skanu()` (linia 307-310), `_przejdz_do()` z reset scan timer (linia 694-708), stale SCAN_* (linie 46-50), klasa SerwoSterowanie

### Kontekst wczesniejszych faz
- `.planning/phases/14-pid-sign-fix/14-CONTEXT.md` — kalibracja PAN_INVERT/TILT_INVERT, konwencja znakow error
- `.planning/phases/15-tilt-servo-fix/15-CONTEXT.md` — redukcja OUTPUT_LIMIT 5.0→3.0°/tick, metoda weryfikacji przez logi SD
- `.planning/phases/15.1-stabilizacja-petli-detekcji/15.1-CONTEXT.md` — StabilizatorStanow, histereza SLEDZENIE→SKANOWANIE (12 klatek)

### Protokol binarny
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja ramki 8B (tryb 1=SKANOWANIE)

### DataLogger (weryfikacja)
- Logi CSV na SD card: timestamp, stan, pan, tilt, error_x, error_y, face_size, latency_ms

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DataLogger` (klasa w aries_controller.ino) — logowanie CSV co 10 klatek, gotowe do analizy post-test
- `skan_krok()` — juz implementuje Lissajous 2D z constrain() bezpieczenstwa
- `ustaw_serwa()` — konwersja kat→Servo.write z clamp

### Established Patterns
- Stale jako `#define` na gorze pliku (SCAN_FREQ_PAN, SCAN_AMP_PAN, etc.)
- `_przejdz_do()` jako centralny punkt przejsc stanow z resetem PID i scan timer
- `constrain()` jako obrona w glab na kazdym set_angles

### Integration Points
- `resetuj_czas_skanu()` — jedyne miejsce wymagajace modyfikacji dla phase-offset continuity
- `_przejdz_do(SKANOWANIE)` — punkt wywolania resetu, tu trzeba przekazac aktualna pozycje serw
- `kat_pan` / `kat_tilt` — publiczne pola klasy SerwoSterowanie, dostepne przy przejsciu

</code_context>

<specifics>
## Specific Ideas

- Phase-offset: arcsin z aktualnej pozycji serwa — pamietac o ograniczeniach float na Arduino (brak double, ograniczona precyzja asin())
- Niezalezne t_offset dla pan i tilt — po phase-offset wzorzec Lissajous moze nie byc "idealny" ale kontynuacja jest plynna
- AMP_PAN=70° jest blisko limitu ±60° — constrain() juz to lapie, ale warto obserwowac czy nie clampuje za czesto

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-camera-color-fix*
*Context gathered: 2026-04-04*
