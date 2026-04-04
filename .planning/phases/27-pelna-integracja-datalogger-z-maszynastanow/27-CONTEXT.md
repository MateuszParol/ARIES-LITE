# Phase 27: Pelna Integracja DataLogger z MaszynaStanow - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Integracja klasy DataLogger z MaszynaStanow: logowanie WSZYSTKICH zmian stanow (BEZCZYNNOSC/SKANOWANIE/SLEDZENIE) z RTC timestamp, uzupelnienie placeholderow face_size i latency_ms rzeczywistymi wartosciami, komenda serialowa do zrzutu ostatnich 10 wpisow bufora, weryfikacja E2E z RPi.

Faza NIE obejmuje: zmian w formacie CSV (zamkniety w Phase 26), zmian w protokole binarnym 8B, zmian w PID/servo/wizji RPi, zmian w ring buffer/rotacji dobowej.

</domain>

<decisions>
## Implementation Decisions

### Logowanie zmian stanow
- **D-01:** Logowac WSZYSTKIE przejscia stanow: BEZCZYNNOSC↔SKANOWANIE↔SLEDZENIE — pelny audit trail sesji
- **D-02:** Claude's Discretion na mechanizm powiadamiania DataLogger o zmianie stanu (bezposrednie wywolanie, flaga+poll, lub porownanie w loop). Wybrac najprostszy sposob spojny z istniejaca architektura OOP

### face_size i latency_ms
- **D-03:** Claude's Discretion na zrodlo face_size — ramka binarna 8B zawiera face_size jako uint8 (bajt 6). Udostepnic przez MaszynaStanow lub ServoPID i przekazac do logger.krok()
- **D-04:** Claude's Discretion na definicje latency_ms — czas petli loop(), czas reakcji PID, lub 0 jesli niemierzalne. Wybrac co daje najwiecej wartosci diagnostycznej

### Format wpisu zmiany stanu
- **D-05:** Claude's Discretion na format wiersza CSV dla zmiany stanu — ten sam format co telemetria (prosty parsing) lub dedykowany marker. Wybrac co latwiej parsowac w Python/pandas

### Weryfikacja E2E
- **D-06:** Komenda serialowa do zrzutu ostatnich 10 wpisow bufora DataLogger na Serial — umozliwia weryfikacje bez fizycznego dostepu do karty SD
- **D-07:** Komenda wyzwalana przez wyslanie znaku/sekwencji na Serial (np. bajt 'D' lub dedykowana ramka). Claude's Discretion na konkretny trigger

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Firmware Arduino (baza do modyfikacji)
- `src/arduino/aries_controller/aries_controller.ino` — Firmware v2.1 z DataLogger (Phase 26) i ZegarRTC (Phase 25). Klasy OOP: HMI, ServoPID, MaszynaStanow, ZegarRTC, DataLogger. Placeholdery face_size=0, latency_ms=0 w linii 757

### Kontekst Phase 26 (decyzje DataLogger)
- `.planning/phases/26-sd-card-datalogger-csv/26-CONTEXT.md` — D-01..D-11: format CSV, kolumny, ring buffer 50, logowanie co 10 klatek w SLEDZENIE, graceful degradation, rotacja dobowa

### Requirements
- `.planning/REQUIREMENTS.md` — INT-06 (DataLogger zintegrowany z MaszynaStanow), INT-08 (E2E firmware z DataLogger + RPi tracking)

### Research
- `.planning/research/ARCHITECTURE.md` — Timing Impact Analysis: 100Hz PID Loop, SD write latency
- `.planning/research/PITFALLS.md` — Timing SD write vs PID

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DataLogger` klasa (Phase 26): `inicjalizuj() -> bool`, `krok(stan, pan, tilt, bx, by, fs, latency)` — ring buffer 50, flush, rotacja dobowa. Juz wywolywany w loop() linia 755
- `MaszynaStanow`: `stan() -> StanSystemu`, `przetwarzaj_bajt()` — parser ramek binarnych, przejscia stanow. Przechowuje ostatni face_size w ramce
- `ZegarRTC`: `odczytaj_czas() -> DateTime`, `czy_dostepny() -> bool`
- Serial parser w loop(): `while (Serial.available())` — punkt integracji dla komendy zrzutu

### Established Patterns
- Klasy OOP z referencjami: `MaszynaStanow(serwa, hmi)`, `DataLogger(zegar)`
- Globalny enum `StanSystemu` (BEZCZYNNOSC=0, SKANOWANIE=1, SLEDZENIE=2)
- Throttle pattern: `millis()` delta (PID 10ms, LCD 200ms, logger co 10 klatek)
- Polskie nazewnictwo metod i zmiennych

### Integration Points
- `loop()` linia 755: `logger.krok()` z placeholderami `0, 0` — zastapic rzeczywistymi wartosciami
- `MaszynaStanow` przejscia stanow — dodac powiadamianie DataLogger
- Serial parser w `loop()` linia 733 — rozszerzyc o komende zrzutu bufora
- Globalna instancja `DataLogger logger(zegar)` linia 666 — moze potrzebowac dodatkowych referencji

</code_context>

<specifics>
## Specific Ideas

- Komenda serialowa zrzuca ostatnie 10 wpisow — lekkie, czytelne w terminalu RPi przez pyserial
- face_size juz jest w ramce binarnej 8B od RPi — trzeba go tylko wyciagnac z parsera MaszynaStanow i przekazac dalej
- Istniejacy logger.krok() juz filtruje stan!=SLEDZENIE — nowa metoda logowania zmian stanow musi dzialac NIEZALEZNIE od tego filtra

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 27-pelna-integracja-datalogger-z-maszynastanow*
*Context gathered: 2026-04-04*
