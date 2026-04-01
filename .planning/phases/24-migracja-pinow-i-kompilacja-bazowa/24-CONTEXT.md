# Phase 24: Migracja Pinow i Kompilacja Bazowa - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Port firmware OOP (HMI, ServoPID, MaszynaStanow — 496 linii w jednym .ino) z Arduino Leonardo (ATmega32U4) na Arduino Uno R4 WiFi (Renesas RA4M1 32-bit). Zmiana mapy pinow, usuniecie specyfik Leonardo (CDC USB wait), Soft Start 500ms + rampa, zamiana dtostrf() na ARM-kompatybilny zamiennik, weryfikacja kompilacji QuickPID na 32-bit. Protokol binarny 8B BEZ ZMIAN.

Faza NIE obejmuje: RTC DS1307, SD card, DataLogger (Phase 25-27), zmian w pi_brain.py (protokol bez zmian), zmian w logice PID/state machine.

</domain>

<decisions>
## Implementation Decisions

### Mapa pinow (LOCKED — nie zmieniac)
- **D-01:** LCD 1602: RS=A0, E=A1, D4=D2, D5=D3, D6=D4, D7=D5
- **D-02:** Serwa MG-90S: PAN=D6, TILT=D9
- **D-03:** Buzzer=D8 (OUTPUT), Przycisk=D7 (INPUT_PULLUP)
- **D-04:** ZAREZERWOWANE — SD: D10-D13 (SPI), I2C: A4-A5 (nie uzywac w tej fazie)

### Soft Start
- **D-05:** delay(500) na poczatku setup() PRZED inicjalizacja serw — stabilizacja napiecia zasilacza 6V. Nastepnie istniejaca rampa writeMicroseconds(500→1500) w 1000ms. Lacznie ~1.5s do pelnej gotowosci.

### Serial startup (Leonardo → R4)
- **D-06:** Claude's Discretion — usunac lub skrocic blok `while(!Serial && timeout)`. R4 WiFi ma ESP32-S3 bridge, nie natywne USB CDC. Research zweryfikuje zachowanie Serial na R4.

### dtostrf zamiennik
- **D-07:** Claude's Discretion — zamienic dtostrf(kat_pan, 4, 0, pan_buf) i dtostrf(kat_tilt, 4, 0, tilt_buf) w lcd_krok() na ARM-kompatybilny zamiennik. Opcje: snprintf z int cast lub snprintf z %.0f. Precision=0 w oryginale upraszcza zamiane.

### Struktura plikow firmware
- **D-08:** Claude's Discretion — zachowac jeden .ino lub rozdzielnic na .h/.cpp (HMI.h, ServoPID.h, MaszynaStanow.h). Uwzglednic ze Fazy 25-27 dodadza RTC, SD, DataLogger (rosnacy rozmiar kodu).

### Weryfikacja kompatybilnosci
- **D-09:** QuickPID musi kompilowac sie na Arduino Uno R4 WiFi (Renesas RA4M1). Zweryfikowac parametry enum (iAwMode, pMode, dMode) — moga sie roznic na 32-bit.
- **D-10:** Servo library >= 1.3.0 wymagana — znany bug jittera na R4 w wersjach < 1.2.2. Zweryfikowac plynnosc sweep na D6/D9.
- **D-11:** LiquidCrystal na pinach analogowych (A0, A1) — wymaga jawnego pinMode(A0, OUTPUT) w setup() (DAC domyslnie wylaczony, ale lepiej explicit).

### Wersjonowanie
- **D-12:** Zmiana bootscreen LCD: "ARIES-LITE v2.1" (z v2.0). Zaktualizowac tez komentarz naglowkowy w pliku .ino.

### Claude's Discretion
- Serial startup behavior na R4 — D-06
- dtostrf zamiennik (snprintf int cast vs %.0f) — D-07
- Struktura plikow (.ino vs .h/.cpp split) — D-08
- Kolejnosc zmian w migracji (piny najpierw, potem Soft Start, potem dtostrf)
- Czy tone() na D8 wymaga innego timera na R4 (Renesas vs AVR Timer3)
- Wewnetrzne nazwy zmiennych — zachowac obecne polskie

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Firmware Arduino (baza do migracji)
- `src/arduino/aries_controller/aries_controller.ino` — Pelny firmware 496 linii: 3 klasy OOP (HMI, ServoPID, MaszynaStanow), parser serial, PID 100Hz, LCD, buzzer, przycisk. Baza do portu.

### Protokol binarny
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja ramki 8B (bez zmian w tej fazie)

### Research v2.1
- `.planning/research/STACK.md` — Wersje bibliotek, ArduinoCore-renesas >=1.4.1, Servo >=1.3.0
- `.planning/research/PITFALLS.md` — dtostrf, Servo jitter, Serial CDC, shield I2C kontakt
- `.planning/research/ARCHITECTURE.md` — Kolejnosc init (Wire→RTC→SD), timing PID vs SD
- `.planning/research/SUMMARY.md` — Synteza ustalen

### Kontekst poprzednich faz
- `.planning/phases/20-firmware-arduino-pid-servo/20-CONTEXT.md` — Decyzje PID, safe startup, scan Lissajous
- `.planning/phases/22-hmi-lcd-buzzer-przycisk/22-CONTEXT.md` — Decyzje LCD, buzzer, przycisk
- `.planning/phases/23-integracja-kalibracja/23-CONTEXT.md` — Decyzje OOP, polonizacja, kalibracja

### Mapa pinow (LOCKED)
- `.planning/PROJECT.md` sekcja "Current Milestone: v2.1" — Kompletna mapa pinow hardware

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `HMI` klasa (linie 76-169): LCD bootscreen, lcd_krok(), buzzer_beep(), przycisk_krok() — wymaga tylko zmiany pin defines
- `ServoPID` klasa (linie 175-309): PID dual-axis, safe start rampa, skan Lissajous — wymaga zmiany PAN_PIN/TILT_PIN
- `MaszynaStanow` klasa (linie 315-440): Parser serial, watchdog, dispatch — BEZ ZMIAN (protokol ten sam)
- `setup()` i `loop()` (linie 452-495): Glowna petla — Serial CDC wait do zmiany, reszta prawie bez zmian

### Established Patterns
- Polskie nazewnictwo konsekwentne (zmienne, komentarze, enum values)
- millis() throttle dla PID (10ms) i LCD (200ms)
- Globalne instancje z referencjami: `ServoPID serwa; HMI hmi; MaszynaStanow maszyna(serwa, hmi);`
- QuickPID enum kwalifikacja: `QuickPID::iAwMode::iAwCondition` (pelna sciezka)
- constrain() zamiast warunkow if — bezpieczny clamp

### Integration Points
- Pin defines (linie 21-56) — centralny punkt zmiany, wszystkie #define w jednym bloku
- setup() linia 453-460 — Serial.begin + CDC wait (do zmiany)
- ServoPID::_bezpieczny_start() linia 278 — Soft Start delay() dodac PRZED rampa
- HMI::lcd_krok() linie 110-111 — dtostrf() zamiana
- HMI::lcd_bootscreen() linia 164 — wersja "v2.0" → "v2.1"

</code_context>

<specifics>
## Specific Ideas

- Uzytkownik wyraznie zadeklarowal: "500ms opoznienia aby ustabilizowac napiecie przed ruchem serw" — to delay(500) PRZED rampa, nie zamiana rampy
- Mapa pinow jest KLUCZOWA i NIE PODLEGA ZMIANIE — uzytkownik podkreslil to wielokrotnie
- Testy na Uno R3 (8-bit) przed przejsciem na R4 (32-bit) — uzytkownik wymienil to jako strategie

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-migracja-pinow-i-kompilacja-bazowa*
*Context gathered: 2026-04-01*
