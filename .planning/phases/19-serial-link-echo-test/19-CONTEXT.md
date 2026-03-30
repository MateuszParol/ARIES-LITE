# Phase 19: Serial Link + Echo Test - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Warstwa komunikacji szeregowej RPi → Arduino dziala end-to-end. RPi buduje i wysyla poprawne ramki binarne 8B zgodnie z PROTOCOL_SPEC.md, Arduino parsuje je state-machine parserem i potwierdza odczyt przez echo identycznej ramki. Skrypt echo_test.py weryfikuje caly lancuch programowo.

Faza NIE obejmuje: PID, serw, LCD, buzzer, MediaPipe, pi_brain.py. Tylko serial link + weryfikacja.

</domain>

<decisions>
## Implementation Decisions

### Parser Arduino (state-machine)
- **D-01:** Parser zaimplementowany jako state-machine: WAIT_START → READ_PAYLOAD → VERIFY_CHECKSUM → DISPATCH. Non-blocking, bajt po bajcie w loop(). Zgodny z SER-02.
- **D-02:** Po poprawnym odbiorze ramki Arduino odsyla identyczna ramke 8B z powrotem (echo). RPi porownuje wyslane vs odebrane bajt po bajcie.
- **D-03:** Bledna checksum lub przerwana ramka = cichy drop + powrot do WAIT_START (resync). Brak echo — RPi wykrywa brak odpowiedzi przez timeout.

### Nadajnik RPi (SerialInterface)
- **D-04:** Klasa `SerialInterface` w `src/vision/serial_interface.py` — OOP wrapper na pyserial. Metody: open(), send_frame(), send_heartbeat(), close(). Zgodne z INT-04 (modularny OOP).
- **D-05:** low_latency ustawiane programowo (subprocess + setserial) przy kazdym open(). Nie wymaga sudo ani udev rules.
- **D-06:** Utrata portu USB = SerialException logowany jako warning + wyjatek podniesiony wyzej. Reconnect to odpowiedzialnosc wywolujacego (pi_brain.py w Phase 21). W Phase 19 echo test po prostu konczy sie.

### Echo test
- **D-07:** Skrypt jednorazowy `scripts/echo_test.py` — wysyla ramke, czyta echo, porownuje, drukuje PASS/FAIL + hex dump. Exit code 0/1.
- **D-08:** Scenariusz testowy: ramka TRACK z referencyjnego przykladu PROTOCOL_SPEC.md (mode=2, error_x=45, error_y=-12, face_size=128).
- **D-09:** Raport: sent=[hex], recv=[hex], PASS/FAIL. Minimalny, czytelny output.

### Heartbeat
- **D-10:** Heartbeat = normalna ramka 8B z mode=IDLE (0), error_x=0, error_y=0, face_size=0. Arduino traktuje kazda poprawna ramke jako dowod zywotnosci — zero specjalnej logiki.
- **D-11:** Metoda `send_heartbeat()` w SerialInterface — alias na send_frame(mode=0, 0, 0, 0). Timing co 200ms dopiero w pi_brain.py (Phase 21).

### Claude's Discretion
- Wewnetrzna implementacja state-machine parsera (nazwy stanow, zmienne pomocnicze)
- Dokladna struktura echo_test.py (argumenty CLI, timeout, ilosc powtorzen)
- Czy echo_test.py importuje SerialInterface czy ma wlasna logike serial (zalecane: importuje SerialInterface)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Protokol binarny
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja ramki 8B, przyklady referencyjne Python + Arduino C, parametry transmisji

### Research z Phase 18
- `.planning/research/ARCHITECTURE.md` — Wzorzec Brain-Muscle, data flow, serial protocol patterns
- `.planning/research/PITFALLS.md` — Leonardo DTR reset, USB CDC latency, setserial low_latency
- `.planning/research/STACK.md` — pyserial, QuickPID, arduino-cli versioning

### Codebase
- `.planning/codebase/INTEGRATIONS.md` — Hardware interfaces, camera backends, ML models
- `.planning/codebase/STRUCTURE.md` — Aktualna struktura katalogow

### Project
- `.planning/PROJECT.md` — Hardware spec (piny Arduino, baudrate 115200, /dev/ttyACM0)
- `.planning/REQUIREMENTS.md` — SER-02, SER-03, SER-04, SER-05 mapped to this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/arduino/aries_controller/aries_controller.ino` — Szkielet z #include (QuickPID, Servo, LiquidCrystal) i Serial.begin(115200). Parser state-machine bedzie dodany tutaj.
- `.planning/protocol/PROTOCOL_SPEC.md` — Referencyjny kod Python (build_frame) i Arduino C (parse_frame) do bezposredniego uzycia

### Established Patterns
- Polish-language naming w nowszym kodzie (wykryj(), odczytaj(), zatrzymaj()) — stosowac w nowych modulach
- try/except z logging.error() — nigdy re-raise w warstwie runtime, ale SerialInterface podnosi wyjatek (swiadoma decyzja D-06)
- Mock mode pattern z hardware.py (PIGPIO_AVAILABLE flag) — analogiczny wzorzec mozliwy dla serial port availability

### Integration Points
- `/dev/ttyACM0` @ 115200 baud — fizyczny port USB Serial RPi ↔ Arduino Leonardo
- `src/vision/serial_interface.py` — nowy modul, bedzie importowany przez pi_brain.py w Phase 21
- `src/arduino/aries_controller/aries_controller.ino` — firmware rozbudowywany w kolejnych fazach (PID w Phase 20, HMI w Phase 22)

</code_context>

<specifics>
## Specific Ideas

- Echo identycznej ramki 8B (nie tekst, nie payload) — najprostsza weryfikacja bajt-po-bajcie
- Heartbeat = normalna ramka IDLE — zero rozszerzania protokolu ponad spec 1.0
- echo_test.py powinien importowac SerialInterface (nie duplikowac logiki serial)
- Referencyjny przyklad z PROTOCOL_SPEC.md (mode=2, ex=45, ey=-12, fs=128) jako scenariusz testowy

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 19-serial-link-echo-test*
*Context gathered: 2026-03-30*
