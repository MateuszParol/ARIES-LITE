# Phase 25: RTC DS1307 Izolowana Integracja - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Integracja RTC DS1307 z DataLogger Shield na Arduino Uno R4 WiFi. DS1307 odczytuje poprawny czas, LCD bootscreen pokazuje HH:MM:SS, poprawna kolejnosc inicjalizacji Wire→RTC w setup(). Izolowana integracja — BEZ SD card, BEZ DataLogger, BEZ zmian w protokole binarnym.

Faza NIE obejmuje: SD card (Phase 26), DataLogger CSV (Phase 26-27), zmian w protokole 8B, zmian w logice PID/stanow.

</domain>

<decisions>
## Implementation Decisions

### Fizyczne podlaczenie I2C
- **D-01:** DataLogger Shield oficjalny z gold pinami — styki stabilne, cynowanie A4/A5 NIEPOTRZEBNE
- **D-02:** I2C scanner (Wire.beginTransmission(0x68)) jako PIERWSZY task — osobny sketch, potwierdzenie fizycznego polaczenia przed kodem RTClib
- **D-03:** Shield osadzony bezposrednio na Arduino (nie kable jumper) — docelowa konfiguracja od poczatku

### Wyswietlanie czasu na LCD
- **D-04:** Czas RTC TYLKO na bootscreen — format "v2.1  HH:MM:SS" w wierszu 0 lub czas w wierszu 1 bootscreena
- **D-05:** Normalny tryb LCD (lcd_krok) BEZ ZMIAN — wiersz 0: tryb+katy, wiersz 1: bledy Bx/By. Czas dostepny przez Serial.
- **D-06:** Jesli RTC niedostepny, bootscreen pokazuje "RTC: FAIL" zamiast czasu

### Fallback bez RTC
- **D-07:** BLOKADA STARTU — jesli rtc.begin() zwroci false LUB czas niepoprawny (rok < 2025), system NIE startuje
- **D-08:** Blokada: buzzer alarm (ciagly ton) + LCD wiersz 0: "RTC ERROR" + wiersz 1: "Sprawdz baterie"
- **D-09:** Petla while(true) z buzzer — wymaga fizycznego resetu Arduino po naprawie RTC

### Klasa RTC w strukturze OOP
- **D-10:** Nowa klasa ZegarRTC w aries_controller.ino — spolna z istniejacym OOP (ServoPID, HMI, MaszynaStanow)
- **D-11:** Metody: inicjalizuj() -> bool, odczytaj_czas() -> DateTime, czy_dostepny() -> bool
- **D-12:** HMI dostaje referencje do ZegarRTC — bootscreen uzywa odczytaj_czas() do wyswietlenia czasu
- **D-13:** DataLogger (Phase 26) tez dostanie referencje do ZegarRTC — interfejs gotowy

### Kolejnosc inicjalizacji w setup()
- **D-14:** Serial → pinMode(A0/A1) → HMI (bootscreen bez czasu) → Wire.begin() + ZegarRTC.inicjalizuj() → HMI aktualizuje bootscreen z czasem (lub "RTC FAIL" → blokada) → Soft Start → Serwa
- **D-15:** Wire.begin() PRZED rtc.begin() — wymagane przez RTClib (research potwierdza)

### Biblioteka RTC
- **D-16:** Adafruit RTClib 2.1.4 — NIE DS1307RTC (PaulStoffregen) — RTClib przetestowane na Renesas RA4M1 (research STACK.md)

### Claude's Discretion
- Format czasu na bootscreen (HH:MM:SS vs HH:MM vs pelna data)
- Czy rtc.adjust() wywolywac przy pierwszym uruchomieniu (czas z kompilacji)
- Nazewnictwo metod klasy ZegarRTC (polskie, spojne z reszta)
- Ile czasu wyswietlac bootscreen z czasem (obecne 2000ms vs dluzej)
- Walidacja czasu — co znaczy "niepoprawny" (rok < 2025? epoch 0?)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Firmware Arduino (baza do modyfikacji)
- `src/arduino/aries_controller/aries_controller.ino` — Firmware v2.1: 3 klasy OOP (HMI, ServoPID, MaszynaStanow), setup() z Soft Start, lcd_bootscreen(). Baza do dodania ZegarRTC.

### Research v2.1
- `.planning/research/STACK.md` — RTClib 2.1.4, Wire bundled, ArduinoCore-renesas >=1.4.1, kod przykladowy #include
- `.planning/research/PITFALLS.md` — Pitfall 2: I2C styki shielda (nie dotyczy gold pinow), kolejnosc Wire→RTC→SD, I2C scanner obowiazkowy
- `.planning/research/ARCHITECTURE.md` — Kolejnosc init (Wire→RTC→SD), timing PID vs SD

### Kontekst poprzednich faz
- `.planning/phases/24-migracja-pinow-i-kompilacja-bazowa/24-CONTEXT.md` — D-04: piny I2C A4/A5 zarezerwowane, D-08: struktura .ino vs .h/.cpp
- `.planning/phases/24-migracja-pinow-i-kompilacja-bazowa/24-01-SUMMARY.md` — Stan firmware po migracji v2.1

### Specyfikacje
- `.planning/REQUIREMENTS.md` — RTC-01, RTC-02, RTC-03, INT-07

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `HMI` klasa (linie 76-169): lcd_bootscreen() do modyfikacji — dodanie wyswietlania czasu. lcd_begin(), lcd_krok() bez zmian.
- `ServoPID` klasa: BEZ ZMIAN w tej fazie
- `MaszynaStanow` klasa: BEZ ZMIAN w tej fazie
- Pattern: globalna instancja z referencjami — `ZegarRTC zegar; HMI hmi(zegar);` lub `hmi.ustaw_zegar(zegar);`

### Established Patterns
- Klasy OOP z metodami inicjalizuj(), polskie nazewnictwo
- Konstruktor z lista inicjalizacyjna (HMI, ServoPID)
- millis() throttle dla cyklicznych operacji (PID 10ms, LCD 200ms)
- Globalny enum StanSystemu — ZegarRTC nie zalezy od stanu

### Integration Points
- setup() linia 452-476: dodanie Wire.begin() + zegar.inicjalizuj() miedzy hmi.inicjalizuj() a delay(500)
- HMI::lcd_bootscreen() linia 162-168: modyfikacja aby wyswietlac czas z ZegarRTC
- Nowy #include na poczatku: Wire.h, RTClib.h
- Nowa globalna instancja: ZegarRTC zegar;

</code_context>

<specifics>
## Specific Ideas

- Shield oficjalny z gold pinami — Pitfall 2 (cynowanie) nie dotyczy tego hardware
- Uzytkownik wyraznie chce BLOKADY STARTU bez RTC — nie graceful degradation
- Czas na LCD tylko bootscreen — minimalny wplyw na istniejacy kod lcd_krok()
- I2C scanner jako oddzielny sketch diagnostyczny — nie w firmware

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 25-rtc-ds1307-izolowana-integracja*
*Context gathered: 2026-04-01*
