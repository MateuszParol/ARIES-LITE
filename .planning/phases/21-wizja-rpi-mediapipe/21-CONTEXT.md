# Phase 21: Wizja RPi MediaPipe - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

RPi4 wykrywa twarze przez MediaPipe FaceDetector, oblicza blad X/Y wzgledem centrum kadru, wybiera stabilnie najwieksza twarz (sticky tracking), wysyla ramki binarne 8B do Arduino przez SerialInterface, i utrzymuje heartbeat co 200ms. Podglad HUD z bbox i bledem. Graceful shutdown na Ctrl+C.

Faza NIE obejmuje: Flask/web UI, LCD/buzzer/przycisk (HMI — Phase 22), kalibracji kierunkow serw (Phase 23), zmian w firmware Arduino (Phase 20 complete).

</domain>

<decisions>
## Implementation Decisions

### Architektura pi_brain.py
- **D-01:** Kod podzielony na moduly w `src/vision/`: osobne pliki dla kamery (Picamera2), detektora (MediaPipe), i glownej logiki (brain). SerialInterface juz istnieje w `src/vision/serial_interface.py`.
- **D-02:** Glowna petla sterowania — Claude's Discretion. Moze byc synchroniczna while-loop, callback Picamera2, lub asyncio — researcher zbada najlepsza opcje na 2026.
- **D-03:** Podglad wideo z HUD (cv2.imshow) jak w legacy test_tracker: bbox, blad X/Y, tryb. Headless fallback gdy brak monitora.

### AWB fix + kamera
- **D-04:** Strategia AWB — Claude's Discretion. Researcher zbada najlepsza opcje (sleep+metadata, stale ColourGains, nowe podejscie). Cel: brak niebieskiej/zielonej poswiaty na IMX219.
- **D-05:** Rozdzielczosc Picamera2 — Claude's Discretion. Researcher zbada optymalna rozdzielczosc dla MediaPipe na RPi4 aarch64. Punkt odniesienia: legacy 320x240, protokol error_x zakres -160..+160 (polowa szerokosci kadru). Jezeli rozdzielczosc != 320, nalezy przeskalowac blad do zakresu protokolu.

### Sticky tracking
- **D-06:** Strategia wyboru twarzy — Claude's Discretion. Researcher zbada: najwieksza (bbox area), najblizsza do centrum, lub hybryda. Wymaganie: stabilne sledzenie bez migotania miedzy celami przy wielu twarzach. Histereza lub prog przeskoku wymagany.

### Heartbeat + timing
- **D-07:** Brak detekcji twarzy = wysylanie ramki z mode=SCAN (1). Arduino skanuje autonomicznie (Lissajous). Heartbeat utrzymywany co 200ms nawet bez twarzy — watchdog Arduino nie odpala sie.
- **D-08:** Mechanizm heartbeat — Claude's Discretion. Researcher zbada: millis check w glownej petli vs osobny watek. Kryterium: gwarantowany interwal <=200ms nawet przy wolnej detekcji MediaPipe.

### Claude's Discretion
- Glowna petla sterowania (synchroniczna vs callback vs asyncio) — D-02
- Strategia AWB fix — D-04
- Rozdzielczosc Picamera2 — D-05
- Strategia sticky tracking (najwieksza vs centrum vs hybryda) — D-06
- Mechanizm heartbeat (glowna petla vs osobny watek) — D-08
- Wewnetrzna organizacja klas i nazewnictwo (polskie nazwy per konwencja nowego kodu)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Protokol binarny
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja ramki 8B, przyklady referencyjne Python + Arduino C, parametry transmisji

### Serial interface
- `src/vision/serial_interface.py` — Gotowa klasa OOP: send_frame(mode, error_x, error_y, face_size), send_heartbeat(), close(), open()

### Kontekst faz
- `.planning/phases/18-srodowisko-protokol-migracja/18-CONTEXT.md` — Decyzje srodowiskowe: Python 3.12 venv, --system-site-packages, MediaPipe instalacja, arduino-cli
- `.planning/phases/20-firmware-arduino-pid-servo/20-CONTEXT.md` — Decyzje firmware: normalizacja bledu po stronie Arduino, PID gainy, maszyna stanow IDLE/SCAN/TRACK

### Legacy wzorce
- `src/modes/test_tracker.py` — Picamera2Stream (YUV420→BGR), DetekcjaTwarzy (HAAR+streak), MaszynaStanow, TestTracker — wzorce kamery, HUD, graceful shutdown do adaptacji
- `src/vision.py` — HybridVision legacy: HAAR + CSRT + async dlib — wzorzec pipeline detekcji (ale MediaPipe zastepuje calosc)

### AWB fix
- `.planning/phases/11-awb-fix/11-CONTEXT.md` — Decyzje AWB legacy: ColourGains lock po warmup, configure-time vs runtime

### Requirements
- `.planning/REQUIREMENTS.md` §VIS — VIS-01..VIS-07: MediaPipe, sticky tracking, blad X/Y, AWB, serial TX, heartbeat, graceful shutdown

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SerialInterface` (`src/vision/serial_interface.py`): Gotowa klasa — open(), send_frame(), send_heartbeat(), close(). Bezposrednio uzywalna w pi_brain.
- `Picamera2Stream` wzorzec (`src/modes/test_tracker.py:68-131`): Daemon thread z frame lock, YUV420→BGR, retry logic. Adaptowalne do nowego modulu kamery.
- HUD drawing pattern (`src/modes/test_tracker.py:_rysuj_hud()`): cv2.rectangle, cv2.putText overlay — wzorzec do powielenia.
- Signal handlers (`src/modes/test_tracker.py:zatrzymaj()`): SIGINT/SIGTERM cleanup — camera.stop(), servo detach, cv2.destroyAllWindows.

### Established Patterns
- Polskie nazwy metod i zmiennych w nowym kodzie (per CLAUDE.md konwencja)
- Daemon thread dla kamery, glowny watek dla logiki
- Type hints z `typing` module na wszystkich nowych metodach
- try/except z logging.error() — nigdy re-raise, zawsze log and continue
- 4-space indentation, bez enforced line length

### Integration Points
- `src/vision/serial_interface.py` — juz w `src/vision/`, nowe moduly obok niego
- Entry point: nowy `run_pi_brain.py` w root (per wzorzec `run_test_tracker.py`)
- Picamera2 import via system-site-packages (venv z --system-site-packages)

</code_context>

<specifics>
## Specific Ideas

- Podglad HUD wzorowany na test_tracker — bbox, blad, tryb naniesione na obraz
- Heartbeat mode=SCAN(1) przy braku twarzy — aktywne szukanie, nie pasywne czekanie
- Moduly w src/vision/ — nie monolit, ale tez nie overengineering

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-wizja-rpi-mediapipe*
*Context gathered: 2026-03-31*
