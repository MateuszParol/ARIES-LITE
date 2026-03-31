# Phase 23: Integracja + Kalibracja - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

System działa end-to-end jako rozproszony tracker: twarz wykryta na RPi (MediaPipe) → błąd X/Y wysłany przez serial 8B → Arduino PID koryguje serwa → kamera śledzi twarz. Kalibracja kierunków serw (PAN_INVERT/TILT_INVERT) potwierdzona empirycznie. Kod Arduino zrefaktoryzowany na klasy C++. Pełna polonizacja nazewnictwa w całym kodzie.

Faza NIE obejmuje: zmian w protokole 8B (LOCKED), zmian w MediaPipe/detekcji, Flask/web UI, nowych funkcji HMI.

</domain>

<decisions>
## Implementation Decisions

### Kalibracja kierunków serw
- **D-01:** Skrypt kalibracyjny Python na RPi (`scripts/kalibracja_serw.py`): wysyła sekwencję testową — error_x=+50 (symulacja twarzy po prawej) i użytkownik obserwuje czy serwo jedzie w prawo. Analogicznie error_y=+30 dla tilt. Deterministyczny, powtarzalny.
- **D-02:** Wynik kalibracji utrwalony jako `#define PAN_INVERT` i `#define TILT_INVERT` w firmware (obecny mechanizm z Phase 20). Zmiana wymaga rekompilacji — akceptowalne, bo kalibracja jednorazowa.

### Modularność OOP (INT-04)
- **D-03:** RPi: zachowaj obecne nazwy klas — MozgRPi (= VisionManager), SerialInterface, WykrywaczTwarzy, KameraRPi. Nazwy polskie spójne z konwencją nowego kodu. INT-04 opisuje odpowiedzialności, nie wymusza angielskich nazw.
- **D-04:** Arduino: refaktoryzacja .ino na klasy C++ w tym samym pliku. Wyodrębnij: ServoPID (pid_tick, gainy, anti-windup), MaszynaStanow (przejścia, dispatch), HMI (LCD, buzzer, przycisk). Globalne zmienne zastąpione polami klas.

### Weryfikacja end-to-end (INT-01, INT-02, INT-03)
- **D-05:** Claude's Discretion — metoda pomiaru latencji <100ms. Researcher zbada: logi timestamps (RPi time.monotonic() vs Arduino millis()), round-trip skrypt, lub inna metoda. Kryterium: mierzalny dowód per INT-01.
- **D-06:** Claude's Discretion — scenariusz testowy E2E. Researcher oceni możliwości automatyzacji na hardware. Musi pokryć: INT-01 (tracking działa), INT-02 (negative feedback poprawny), INT-03 (tilt w SCAN i TRACK).

### Polskie nazewnictwo (INT-05)
- **D-07:** Pełny refactor — wszystkie komentarze, zmienne, nazwy funkcji i komunikaty w kodzie po polsku. Zarówno nowy kod jak i istniejący. Dotyczy obu stron: RPi (`src/vision/*.py`) i Arduino (`aries_controller.ino`).
- **D-08:** Wyjątek: nazwy techniczne/biblioteczne zostają po angielsku — PID, UART, GPIO, EEPROM, constrain(), millis(), Serial, INVERT. Polskie tylko nazwy domenowe (tryb, błąd, kąt, skan, śledź, ramka, klatka).

### Claude's Discretion
- Metoda pomiaru latencji end-to-end — D-05
- Scenariusz testowy E2E — D-06
- Wewnętrzna struktura klas C++ Arduino (pola, metody, kolejność)
- Kolejność refaktoru: najpierw integracja czy najpierw OOP
- Zakres refaktoru nazewnictwa: które konkretne zmienne/funkcje zmieniać (np. MODE_IDLE → TRYB_BEZCZYNNY, pid_tick → pid_krok, error_x → blad_x)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Protokół binarny
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja ramki 8B, przykłady referencyjne Python + Arduino C

### Firmware Arduino
- `src/arduino/aries_controller/aries_controller.ino` — Aktualny firmware: PID, state machine, HMI (LCD+buzzer+przycisk), parser serial. Baza do refaktoru OOP.

### Kod RPi (wizja)
- `src/vision/brain.py` — MozgRPi: pętla sterowania, obliczanie błędu, heartbeat, HUD
- `src/vision/serial_interface.py` — SerialInterface: send_frame(), send_heartbeat(), low_latency
- `src/vision/detector.py` — WykrywaczTwarzy: MediaPipe FaceDetector, sticky tracking
- `src/vision/camera.py` — KameraRPi: Picamera2 backend

### Kontekst wcześniejszych faz
- `.planning/phases/20-firmware-arduino-pid-servo/20-CONTEXT.md` — PID gainy (Kp=2.0, Ki=0.1, Kd=0.5), normalizacja błędu, PAN_INVERT/TILT_INVERT, maszyna stanów
- `.planning/phases/21-wizja-rpi-mediapipe/21-CONTEXT.md` — MediaPipe, sticky tracking, heartbeat 200ms, AWB fix
- `.planning/phases/22-hmi-lcd-buzzer-przycisk/22-CONTEXT.md` — HMI: LCD layout, buzzer tone(), przycisk abort

### Skrypt kalibracyjny (referencja)
- `scripts/echo_test.py` — Istniejący skrypt testowy serial (Phase 19) — wzorzec do skryptu kalibracyjnego

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SerialInterface` (`src/vision/serial_interface.py`): gotowa klasa OOP — send_frame() do skryptu kalibracyjnego
- `echo_test.py` (`scripts/`): wzorzec jednorazowego skryptu testowego serial
- PAN_INVERT/TILT_INVERT `#define` w firmware — mechanizm kalibracji już istnieje

### Established Patterns
- Polskie nazwy klas w nowym kodzie: MozgRPi, WykrywaczTwarzy, KameraRPi, WatekHeartbeat
- Angielskie stałe trybów: MODE_IDLE, MODE_SCAN, MODE_TRACK (do zmiany per D-07)
- Arduino: proceduralne C z polskimi komentarzami i mieszanymi nazwami (pid_tick, dispatch_ramke, skan_tick)

### Integration Points
- `brain.py:_oblicz_error()` → `serial_interface.send_frame()` → Arduino parser → `dispatch_ramke()` → `pid_tick()` → `ustaw_serwa()` — cały łańcuch end-to-end już istnieje
- Kalibracja: PAN_INVERT/TILT_INVERT w firmware linia 30-31 — jedyne miejsce do zmiany kierunku

</code_context>

<specifics>
## Specific Ideas

- Skrypt kalibracyjny: deterministyczny, powtarzalny — wysyła znane błędy i użytkownik potwierdza kierunek
- STATE.md notatka: "pan+=prawo, tilt+=dół — wymaga re-weryfikacji na nowym montażu Arduino" — kalibracja to główny cel fazy
- Arduino OOP: klasy w tym samym pliku .ino (nie osobne .h/.cpp) — prostsze dla projektu hobby

</specifics>

<deferred>
## Deferred Ideas

None — dyskusja pozostała w zakresie fazy.

</deferred>

---

*Phase: 23-integracja-kalibracja*
*Context gathered: 2026-03-31*
