# Phase 28: Flash firmware na Uno R4 WiFi - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Wgranie istniejacego firmware v2.1 (z Phase 24) na swieze Arduino Uno R4 WiFi i pelna weryfikacja sprzetowa — LCD bootscreen, serwa Soft Start + skan, serial z RPi (pelny E2E tracking twarzy), buzzer, przycisk, stabilnosc zasilania (5x power cycle). Firmware juz sportowany i skompilowany w Phase 24. Ta faza nie modyfikuje firmware — tylko flashuje i weryfikuje na docelowym hardware.

</domain>

<decisions>
## Implementation Decisions

### Metoda flashowania
- **D-01:** arduino-cli na RPi4 (nie Arduino IDE). RPi4 ma monitor + klawiature — wizualna weryfikacja LCD/serw mozliwa.
- **D-02:** Instalacja ArduinoCore-renesas od zera — RPi4 nie ma jeszcze zainstalowanego srodowiska Arduino. Plan musi zawierac kroki instalacji arduino-cli + core + bibliotek.
- **D-03:** Board FQBN: `arduino:renesas_uno:unor4wifi` — Claude zweryfikuje poprawny identyfikator w research.

### Procedura testow
- **D-04:** Testy izolowane po kolei, od pasywnych do aktywnych: 1) LCD bootscreen, 2) Serwa Soft Start + sweep, 3) Buzzer ton, 4) Przycisk D7, 5) Serial E2E z RPi (pelny tracking twarzy), 6) Stabilnosc 5x power cycle.
- **D-05:** Checkpoint w planie po kazdym tescie — uzytkownik wpisuje PASS/FAIL, Claude kontynuuje lub debuguje. Wzorzec identyczny z Phase 24.
- **D-06:** Test serial obejmuje PELNY E2E tracking: uruchomienie pi_brain.py, wykrycie twarzy, sledzenie serwami. Najsilniejszy dowod poprawnosci.

### Awarie i rollback
- **D-07:** Debug in-place na R4 — nie rollback na R3. Diagnoza: polaczenia, piny, Serial output.
- **D-08:** Pojedyncze egzemplarze komponentow (serwa, LCD, kable) — plan testow musi byc ostrozny. Pasywne testy (LCD) najpierw, aktywne (serwa) pozniej. Unikac agresywnych ruchow serw przy pierwszym uruchomieniu.

### Konfiguracja RPi
- **D-09:** pi_brain.py dzialal E2E z Uno R3 w Phase 24. Cel: identyczne zachowanie z R4 WiFi. R4 juz polaczone do RPi4 przez USB.
- **D-10:** Claude's Discretion — DTR behavior R4 WiFi (ESP32-S3 bridge) vs Leonardo. Researcher zbada czy pi_brain.py wymaga zmian ustawien serial (dtr=False, port path). Phase 24 decyzja D-06 usunela CDC workaround Leonardo.

### Claude's Discretion
- Dokladna metoda instalacji arduino-cli na RPi4 ARM64 (apt vs curl)
- Biblioteki do zainstalowania przez arduino-cli (QuickPID, Servo, LiquidCrystal)
- Czy /dev/ttyACM0 jest stabilny na R4 WiFi czy trzeba udev rules
- Kolejnosc pasywna/aktywna w testach serw — minimalny zakres ruchu przy pierwszym sweep
- Timeout i retry strategy jesli flash sie nie powiedzie

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Firmware Arduino (do flashowania)
- `src/arduino/aries_controller/aries_controller.ino` — Pelny firmware v2.1: 3 klasy OOP (HMI, ServoPID, MaszynaStanow), sportowany na R4 w Phase 24. To jest plik do wgrania.

### Kontekst Phase 24 (baza)
- `.planning/phases/24-migracja-pinow-i-kompilacja-bazowa/24-CONTEXT.md` — Decyzje migracji: mapa pinow, Soft Start, dtostrf, Serial startup. Firmware juz skompilowany.

### Protokol binarny
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja ramki 8B (bez zmian)

### Pi Brain (strona RPi)
- `src/vision/pi_brain.py` — Skrypt wizji RPi: MediaPipe + serial TX do Arduino. E2E testowany z R3.

### Research v2.1
- `.planning/research/PITFALLS.md` — Znane problemy: Servo jitter, Serial CDC, shield I2C kontakt
- `.planning/research/SUMMARY.md` — Synteza ustalen migracji

### Mapa pinow (LOCKED)
- `.planning/PROJECT.md` sekcja "Current Milestone: v2.1" — Kompletna mapa pinow hardware

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `aries_controller.ino` — Pelny firmware gotowy do flashowania. Nie wymaga modyfikacji (chyba ze testy wykazal problem R4-specific).
- `pi_brain.py` — Skrypt wizji RPi przetestowany z R3. Powinien dzialac z R4 bez zmian (do weryfikacji DTR).

### Established Patterns
- Phase 24 checkpoint pattern: CHECKPOINT w planie z listia testow, uzytkownik potwierdza PASS/FAIL
- Polskie nazewnictwo konsekwentne w firmware i pi_brain.py
- millis() throttle dla PID (10ms) i LCD (200ms)

### Integration Points
- USB /dev/ttyACM0 — punkt polaczenia RPi ↔ Arduino. R4 WiFi uzywa ESP32-S3 bridge (nie natywne CDC jak Leonardo)
- Zasilacz 6V — zewnetrzne zasilanie serw MG-90S. Soft Start 500ms chroni przed brownout.
- Breadboard — wszystkie polaczenia na plytce stykowej (ryzyko mechaniczne)

</code_context>

<specifics>
## Specific Ideas

- Uzytkownik ma RPi4 z monitorem i klawiatura — moze obserwowac LCD i serwa bezposrednio
- R4 WiFi juz fizycznie podlaczone do RPi4 przez USB
- Pojedyncze egzemplarze komponentow — plan musi byc ostrozny, brak zapasowych serw/LCD
- Phase 24 testowala na R3 jako proxy — teraz czas na docelowy R4

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 28-kompletny-szkic-arduino-ino*
*Context gathered: 2026-04-02*
