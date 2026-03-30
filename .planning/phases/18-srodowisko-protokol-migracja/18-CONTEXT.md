# Phase 18: Srodowisko + Protokol + Migracja - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Przygotowanie srodowiska deweloperskiego na obu wezlach (RPi4 + Arduino Leonardo), zaprojektowanie i zamkniecie specyfikacji protokolu binarnego 8B, oraz migracja starego monolitu do legacy/ z zachowaniem git history. Zadny kod runtime nie powstaje w tej fazie — tylko env, spec, i restrukturyzacja.

</domain>

<decisions>
## Implementation Decisions

### Protokol binarny (8 bajtow)
- **D-01:** Ramka 8B: `0xAA` (start marker, 1B) + `mode` (uint8, 1B) + `error_x` (int16 LE, 2B) + `error_y` (int16 LE, 2B) + `face_size` (uint8, 1B) + `checksum` (XOR, 1B)
- **D-02:** Blad X/Y kodowany jako surowe piksele (int16 little-endian). Zakres: -160..+160 przy rozdzielczosci 320x240. Arduino normalizuje do swoich potrzeb PID.
- **D-03:** Tryb kodowany jako uint8: 0=IDLE, 1=SCAN, 2=TRACK
- **D-04:** Rozmiar twarzy kodowany jako uint8 (0-255, procent kadru skalowany)
- **D-05:** Little-endian (natywny format AVR) — zero konwersji po stronie Arduino. Python uzywa `struct.pack('<h', val)`.
- **D-06:** XOR checksum calej ramki (bajty 1-6, bez start markera)

### Strategia migracji
- **D-07:** Caly runtime do legacy/: `src/`, `web/`, `main.py`, `run_test_tracker.py`, `models/` → `legacy/`
- **D-08:** Pozostaja w root: `tests/`, `scripts/`, `docs/`, `requirements.txt`, config files, `.planning/`
- **D-09:** Migracja via `git mv` — zachowuje historie plikow w `git log --follow`. Jeden commit: `refactor: move monolith to legacy/`

### Python venv
- **D-10:** Nowy venv z systemowego Python 3.11 na RPi4 Bookworm. Weryfikacja: `python3 --version` na RPi jako pierwszy krok.
- **D-11:** Flaga `--system-site-packages` w venv — wymagana dla picamera2 + libcamera (zainstalowane systemowo)
- **D-12:** `pip install mediapipe pyserial numpy` w nowym venv. Jezeli mediapipe fail na Python 3.11 → eskalacja (deadsnakes PPA lub build ze zrodla)

### Arduino workflow
- **D-13:** arduino-cli zainstalowane na RPi4. Kompilacja + upload bezposrednio z RPi przez USB (/dev/ttyACM0).
- **D-14:** Firmware w tym samym repo ARIES-LITE: `src/arduino/aries_controller/aries_controller.ino`
- **D-15:** Biblioteki Arduino: QuickPID, Servo (built-in), LiquidCrystal (built-in). Instalacja via `arduino-cli lib install`.

### Claude's Discretion
- Dokladna struktura katalogowa nowego `src/vision/` (ile plikow, jak rozdzielic klasy) — do ustalenia w planowaniu
- Format dokumentu specyfikacji protokolu (markdown w .planning/ vs komentarz w kodzie) — Claude decyduje

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research
- `.planning/research/STACK.md` — Wersje bibliotek, mediapipe aarch64 instalacja, QuickPID vs PID_v1, Leonardo DTR reset
- `.planning/research/ARCHITECTURE.md` — Wzorzec Brain-Muscle, data flow, serial protocol patterns
- `.planning/research/PITFALLS.md` — MediaPipe Python 3.13 incompatibility, Leonardo WDT bootloader bug, USB CDC latency
- `.planning/research/SUMMARY.md` — Synteza: 6 faz, kluczowe ryzyka

### Codebase
- `.planning/codebase/STRUCTURE.md` — Aktualna struktura katalogow (co przenosic do legacy/)
- `.planning/codebase/STACK.md` — Aktualny stack (Python 3.13, OpenCV, gpiozero, etc.)

### Project
- `.planning/PROJECT.md` — Hardware spec (piny Arduino, baudrate, zasilanie)
- `.planning/REQUIREMENTS.md` — ENV-01, ENV-02, SER-01, MIG-01, MIG-02 mapped to this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/modes/test_tracker.py` — Referencja Picamera2Stream, AWB lock pattern (start + 2s sleep + capture_metadata)
- `src/config.py` — PID gains (P=0.05, I=0.001, D=0.005) jako punkt startowy dla Arduino (I redukowac 3x dla 100Hz)
- `src/hardware.py` — Wzorzec PIGPIO_AVAILABLE flag + mock mode (analogiczny pattern potrzebny dla serial port)

### Established Patterns
- Polish-language naming w nowszym kodzie (wykryj(), odczytaj(), zatrzymaj())
- Type hints z typing module (Tuple, Optional) w test_tracker.py
- try/except z logging.error() — nigdy re-raise, zawsze log + graceful continue

### Integration Points
- `/dev/ttyACM0` @ 115200 — punkt integracji RPi ↔ Arduino
- Nowy `src/vision/` zastepuje stary `src/` — entry point bedzie `src/vision/pi_brain.py` zamiast `main.py`
- Nowy `src/arduino/aries_controller/` — firmware kompilowany i uploadowany z RPi via arduino-cli

</code_context>

<specifics>
## Specific Ideas

- Specyfikacja protokolu powinna byc zamknieta (dokument) PRZED jakimkolwiek kodem parsera/nadajnika
- `git mv` do legacy/ w jednym atomowym commicie — nie rozdzielac na wiele commitow
- Weryfikacja `python3 --version` na RPi jako PIERWSZY krok fazy — fail fast jesli Python 3.13

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-srodowisko-protokol-migracja*
*Context gathered: 2026-03-30*
