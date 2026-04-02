# Phase 25: RTC DS1307 Izolowana Integracja - Context

**Gathered:** 2026-04-02 (updated)
**Status:** Ready for planning
**Target hardware:** Arduino Uno R4 WiFi (firmware v2.1 zaflashowany w Phase 28)

<domain>
## Phase Boundary

Integracja RTC DS1307 z DataLogger Shield na Arduino Uno R4 WiFi (firmware v2.1 juz zaflashowany w Phase 28). DS1307 odczytuje poprawny czas, LCD bootscreen pokazuje HH:MM:SS, poprawna kolejnosc inicjalizacji Wire→RTC w setup(). Izolowana integracja — BEZ SD card, BEZ DataLogger, BEZ zmian w protokole binarnym.

Target: Uno R4 WiFi z ArduinoCore-renesas 1.5.3 (Wire.h bundled, I2C na A4/A5 SDA/SCL). Kompilacja i flash przez arduino-cli na RPi4.

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

### Fallback bez RTC (NON-BLOCKING — zmiana z 2026-04-02)
- **D-07:** NON-BLOCKING ostrzezenie — jesli rtc.begin() zwroci false LUB czas niepoprawny (rok < 2025), system STARTUJE normalnie po krotkim ostrzezeniu
- **D-08:** Ostrzezenie: buzzer krotki alarm (3x beep, tone 2kHz/150ms) + LCD wiersz 0: "RTC: FAIL" + wiersz 1: "Sprawdz baterie" przez ~2s, potem kontynuacja setup()
- **D-09:** System kontynuuje bez RTC timestamps — serwa, PID, tracking dzialaja normalnie. BEZ while(true), BEZ blokady startu.

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
- **D-17:** Instalacja przez arduino-cli na RPi4: `arduino-cli lib install "RTClib@2.1.4"` (Adafruit BusIO zainstaluje sie jako zaleznosc)

### Claude's Discretion
- Format czasu na bootscreen (HH:MM:SS vs HH:MM vs pelna data)
- Czy rtc.adjust() wywolywac przy pierwszym uruchomieniu (czas z kompilacji)
- Nazewnictwo metod klasy ZegarRTC (polskie, spojne z reszta)
- Ile czasu wyswietlac bootscreen z czasem (obecne 2000ms vs dluzej)
- Walidacja czasu — co znaczy "niepoprawny" (rok < 2025? epoch 0?)
- Flash/compile workflow: arduino-cli na RPi4 (identyczny z Phase 28)

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

### Phase 28 (flash na R4 WiFi)
- `.planning/phases/28-kompletny-szkic-arduino-ino/28-RESEARCH.md` — Srodowisko arduino-cli, FQBN, port, pitfalls ESP32-S3 bridge
- `.planning/phases/28-kompletny-szkic-arduino-ino/28-01-SUMMARY.md` — Wynik flash firmware v2.1 na R4 WiFi

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
- Flash/compile: `arduino-cli compile/upload --fqbn arduino:renesas_uno:unor4wifi --port /dev/ttyACM0` (identyczny workflow z Phase 28)
- Wire.h bundled z ArduinoCore-renesas 1.5.3 — nie trzeba instalowac osobno

</code_context>

<specifics>
## Specific Ideas

- Shield oficjalny z gold pinami — Pitfall 2 (cynowanie) nie dotyczy tego hardware
- Fallback RTC: NON-BLOCKING ostrzezenie (zmiana z blokady na 2026-04-02) — krotki alarm + kontynuacja
- Czas na LCD tylko bootscreen — minimalny wplyw na istniejacy kod lcd_krok()
- I2C scanner jako oddzielny sketch diagnostyczny — nie w firmware
- Firmware v2.1 juz zaflashowany na R4 WiFi w Phase 28 — ta faza modyfikuje i re-flashuje

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 25-rtc-ds1307-izolowana-integracja*
*Context gathered: 2026-04-01, updated 2026-04-02 (R4 WiFi target + non-blocking RTC)*
