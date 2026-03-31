# Phase 20: Firmware Arduino PID + Servo - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Arduino Leonardo steruje serwami MG-90S deterministycznie: QuickPID dual-axis 100 Hz, bezpieczny startup z rampa writeMicroseconds(), watchdog millis() przywracajacy skan przy utracie komunikacji, maszyna stanow IDLE/SCAN/TRACK sterowana ramkami z RPi, autonomiczny skan sinusoidalny Lissajous 2D.

Faza NIE obejmuje: MediaPipe, pi_brain.py, LCD, buzzer, przycisk (HMI w Phase 22). Faza rozbudowuje firmware z Phase 19 (parser + echo) o logike sterowania.

</domain>

<decisions>
## Implementation Decisions

### PID tuning + mapowanie
- **D-01:** Normalizacja bledu do -1.0..+1.0 po stronie Arduino: `error_norm = (float)error_px / 160.0f`. PID operuje na znormalizowanym bledzie — przenoszalne miedzy rozdzielczosciami.
- **D-02:** Poczatkowe gainy konserwatywne: Kp=2.0, Ki=0.1, Kd=0.5. Output limit +/-5.0 stopni/tick. Kalibracja empiryczna w Phase 23.
- **D-03:** QuickPID z anti-windup. Dual-axis (osobne instancje pan i tilt). Loop PID co 10ms via millis() (deterministyczny, nie delay()).

### Safe startup + serwa
- **D-04:** Safe startup przez Servo.writeMicroseconds() z rampa. Startuj od 500us (lub min), inkrementuj do 1500us (centrum = 90 stopni) w ciagu 1000ms. Minimalne obciazenie zasilacza 6V.
- **D-05:** Servo.attach() na pinach PAN=D9, TILT=D10. Attach PRZED rampa — writeMicroseconds() wymaga attach.

### Maszyna stanow + watchdog
- **D-06:** Stan po power-on: IDLE. Arduino czeka na pierwsza ramke z RPi. Serwa w pozycji 90/90 po safe startup, nic sie nie rusza samo.
- **D-07:** Watchdog timeout 500ms (millis()). Po timeout bez ramek Arduino przechodzi do stanu wybranego przez Claude (SCAN lub IDLE — Claude's Discretion). Kazda poprawna ramka resetuje timer watchdog.
- **D-08:** Dispatcher ramek — Claude's Discretion: czy tryb z ramki bezposrednio ustawia stan, czy przejscia sa warunkowe. Obie opcje akceptowalne.

### Skan sinusoidalny
- **D-09:** Skan Lissajous 2D — obie osie skanuja jednoczesnie z roznymi czestotliwosciami.
- **D-10:** Amplitudy: PAN = 70 stopni (zwiekszony z legacy 45), TILT = 25 stopni. Zapewnia szerokie pokrycie pola widzenia.
- **D-11:** Czestotliwosci — Claude's Discretion. Irracjonalny stosunek PAN/TILT dla pelnego pokrycia Lissajous. Legacy: PAN=0.05, TILT=0.07 jako punkt odniesienia.

### PAN/TILT sign convention
- **D-12:** Claude's Discretion — strategia znakow (negacja pan error vs PAN_INVERT). ARD-04 wymaga konfigurowalnego kierunku przez #define PAN_INVERT / TILT_INVERT.

### PID setpoint
- **D-13:** Claude's Discretion — staly setpoint 0.0 (error=0 = centrum) lub inny. Protokol wysyla error wzgledem centrum klatki.

### Claude's Discretion
- Strategia znakow PID (negacja vs INVERT define) — D-12
- Watchdog target state (SCAN vs IDLE) — D-07
- Dispatcher logic (bezposredni vs warunkowy) — D-08
- Czestotliwosci skanowania — D-11
- PID setpoint — D-13
- Wewnetrzna organizacja kodu w .ino (funkcje, nazwy zmiennych, komentarze)
- Kolejnosc inicjalizacji w setup() (parser, serwa, PID, watchdog)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Protokol binarny
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja ramki 8B, przyklady referencyjne Python + Arduino C, parametry transmisji

### Research z Phase 18
- `.planning/research/ARCHITECTURE.md` — Wzorzec Brain-Muscle, data flow, serial protocol patterns
- `.planning/research/PITFALLS.md` — Leonardo DTR reset, USB CDC latency, MG-90S current spikes
- `.planning/research/STACK.md` — QuickPID API, Servo library, arduino-cli versioning

### Firmware z Phase 19
- `src/arduino/aries_controller/aries_controller.ino` — Aktualny firmware: parser state-machine + echo. Phase 20 rozbudowuje ten plik.

### Codebase
- `.planning/codebase/INTEGRATIONS.md` — Hardware interfaces (piny, zasilanie)
- `.planning/codebase/STRUCTURE.md` — Aktualna struktura katalogow

### Project
- `.planning/PROJECT.md` — Hardware spec (piny Arduino: PAN=D9, TILT=D10, LCD, Buzzer=D8, Button=D7), zasilanie 6V
- `.planning/REQUIREMENTS.md` — ARD-01 do ARD-06 mapped to this phase

### Legacy reference
- `legacy/src/hardware.py` — smooth_move_to() pattern, set_angles() z clamp, PID output limit
- `legacy/src/modes/test_tracker.py` — Skan sinusoidalny (SCAN_AMPLITUDE, SCAN_FREQUENCY), maszyna stanow, PID sign convention

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/arduino/aries_controller/aries_controller.ino` — Parser state-machine z Phase 19. Rozbudowywany o PID, serwa, maszyne stanow. Zachowac #include (QuickPID, Servo, LiquidCrystal) i istniejacy parser.
- `legacy/src/hardware.py` — Wzorzec smooth_move_to() jako referencja dla safe startup (D-04)
- `legacy/src/modes/test_tracker.py` — Skan sinusoidalny, maszyna stanow, PID sign convention jako referencja

### Established Patterns
- Polish-language naming w nowszym kodzie (przetwarzaj_bajt, ramka_buf, stan_parsera) — kontynuowac w Phase 20
- State-machine enum pattern (StanParsera) — rozszerzyc o StanSystemu (IDLE/SCAN/TRACK)
- Non-blocking bajt-po-bajcie w loop() — zachowac, dodac PID millis() tick

### Integration Points
- `przetwarzaj_bajt()` — po echo dodac dispatch do maszyny stanow (ekstrakcja mode, error_x/y, face_size)
- `loop()` — dodac PID tick co 10ms obok parsera serial
- Servo.attach(D9) / Servo.attach(D10) — nowe w setup()
- QuickPID instancje — nowe globalne zmienne

</code_context>

<specifics>
## Specific Ideas

- PAN amplituda skanowania 70 stopni (uzytkownik: "45 stopni bylo za waskim obszarem") — wieksza niz legacy
- TILT amplituda 25 stopni — blizsza limitowi mechanicznemu 30 stopni
- Konserwatywne gainy PID (Kp=2.0) — priorytet brak overshootu nad szybkoscia reakcji
- writeMicroseconds() rampa 1000ms zamiast prostego Servo.write(90) — bezpieczenstwo pradu

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-firmware-arduino-pid-servo*
*Context gathered: 2026-03-31*
