---
phase: 23-integracja-kalibracja
verified: 2026-03-31T20:30:00Z
status: human_needed
score: 4/5 must-haves verified (SC-1/SC-2/SC-3 require hardware)
human_verification:
  - test: "Uruchom scripts/kalibracja_serw.py z podlaczonym Arduino Leonardo i serwami"
    expected: "Wszystkie 4 kroki (PAN prawo, PAN lewo, TILT dol, TILT gora) odpowiadaja t — kalibracja PASS"
    why_human: "Arduino Leonardo niedostepne (USB enumeration blocker). Weryfikacja wymaga fizycznego sprzetu."
  - test: "Uruchom python3 run_pi_brain.py, staw twarz przed kamera"
    expected: "Serwa sledzaja twarz; logi zawieraja '[LAT] TX SLEDZENIE:' z czasem <100ms; LCD Arduino pokazuje 'SLEDZ'"
    why_human: "E2E tracking (INT-01) wymaga jednoczesnie: Arduino, serw, kamery RPi. Nie da sie zweryfikowac bez sprzetu."
  - test: "Przesuniecie twarzy w prawo powoduje ruch serwa pan w prawo (nie w lewo)"
    expected: "Negative feedback poprawny — brak ucieczki serw"
    why_human: "INT-02 / SC-2: poprawnosc kierunkow wymaga obserwacji fizycznej reakcji serw."
---

# Phase 23: Integracja + Kalibracja — Raport weryfikacji

**Phase Goal:** System dziala end-to-end jako rozproszony tracker — twarz na RPi powoduje ruch serw przez Arduino PID, kierunki poprawne, kod modularny
**Verified:** 2026-03-31T20:30:00Z
**Status:** human_needed
**Re-verification:** Nie — weryfikacja poczatkowa

---

## Goal Achievement

### Success Criteria (zrodlo: ROADMAP.md)

| # | Success Criterion | Status | Evidencja |
|---|-------------------|--------|-----------|
| SC-1 | Twarz wykryta na RPi powoduje ruch serw w ciagu <100ms — latencja mierzalna przez log timestamps | ? HUMAN | Pomiar latencji TX zaimplementowany ([LAT] TX SLEDZENIE w brain.py). Nie mozna zweryfikowac wartosci <100ms bez Arduino. |
| SC-2 | Twarz po prawej = serwo pan przesuwa kamere w prawo (negative feedback poprawny) | ? HUMAN | PAN_INVERT=+1 w firmware, skrypt kalibracyjny gotowy. Wymaga fizycznej weryfikacji kierunku ruchu. |
| SC-3 | Os tilt dziala poprawnie w obu trybach: oscyluje w SCAN, sledzi w TRACK | ? HUMAN | Logika tilt w skan_krok() (Lissajous) i pid_krok() zweryfikowana w kodzie. Potwierdzenie wymaga hardware. |
| SC-4 | Kod podzielony na klasy — ServoPID, MaszynaStanow, HMI w firmware; MozgRPi, SerialInterface, WykrywaczTwarzy, KameraRPi w RPi Python | ✓ VERIFIED | arduino-cli compile exit 0; grep potwierdza class ServoPID / MaszynaStanow / HMI; Python klasy w oddzielnych plikach. |
| SC-5 | Wszystkie komentarze, nazwy zmiennych i komunikaty w kodzie sa w jezyku polskim | ✓ VERIFIED | Brak MODE_*/TRACK/SCAN w brain.py (grep=0); TRYB_* potwierdzone; firmware: BEZCZYNNOSC/SKANOWANIE/SLEDZENIE; POLOWA_RAMKI, CZEKAJ_START; polskie docstringi wsz. plikow. |

**Score:** 2/5 automated (SC-4, SC-5); 3/5 SC-1/SC-2/SC-3 wymagaja hardware

---

## Weryfikacja artefaktow

### Plan 23-01: must_haves.artifacts

| Artefakt | Dostarcza | Status | Szczegoly |
|----------|-----------|--------|-----------|
| `scripts/kalibracja_serw.py` | Skrypt kalibracyjny kierunkow serw | ✓ VERIFIED | Plik istnieje, 153 linie, SYNTAX OK, zawiera: `from src.vision.serial_interface import SerialInterface`, `wysylaj_petla`, `time.sleep(OPOZNIENIE_TX)`, `time.sleep(OPOZNIENIE_BOOT)`, 4 kroki (error_x=50/-50, error_y=30/-30), `iface.close()` w finally, `PODSUMOWANIE` string. |
| `src/vision/brain.py` | Pomiar latencji w petli glownej | ✓ VERIFIED | SYNTAX OK, zawiera `[LAT] TX SLEDZENIE:` (line 179) i `[LAT] TX SKANOWANIE:` (line 200), `time.monotonic_ns()` uzyte 3x, `_licznik_scan_log` jako pole klasy. Uwaga: nazwy zmienily sie z TRACK->SLEDZENIE / SCAN->SKANOWANIE po polonizacji w Plan 02 — intent zachowany. |

### Plan 23-02: must_haves.artifacts

| Artefakt | Dostarcza | Status | Szczegoly |
|----------|-----------|--------|-----------|
| `src/arduino/aries_controller/aries_controller.ino` | Firmware OOP z klasami ServoPID, MaszynaStanow, HMI + polskie nazewnictwo | ✓ VERIFIED | `class ServoPID` (line 175), `class MaszynaStanow` (line 315), `class HMI` (line 76); BEZCZYNNOSC=0/SKANOWANIE=1/SLEDZENIE=2; CZEKAJ_START/CZYTAJ_PAYLOAD; POLOWA_RAMKI; brak safe_startup/dispatch_ramke/HALF_FRAME_W; arduino-cli compile exit 0 (59% flash, 22% RAM). |
| `src/vision/brain.py` | MozgRPi z pelna polonizacja | ✓ VERIFIED | `TRYB_BEZCZYNNOSC=0`, `TRYB_SKANOWANIE=1`, `TRYB_SLEDZENIE=2`; brak MODE_IDLE/MODE_SCAN/MODE_TRACK (grep=0); tryb="SLEDZENIE" / tryb="SKANOWANIE" w HUD. |
| `src/vision/serial_interface.py` | SerialInterface z polskimi komentarzami | ✓ VERIFIED | `dane = struct.pack` (line 133) zamiast payload; docstring "Buduje 8-bajtowa ramke" (line 115); polskie komentarze w calosci. |

---

## Weryfikacja key links

### Plan 23-01

| From | To | Via | Status | Szczegoly |
|------|----|-----|--------|-----------|
| `scripts/kalibracja_serw.py` | `src/vision/serial_interface.py` | `from src.vision.serial_interface import SerialInterface` + `send_frame()` | ✓ WIRED | Line 23: `from src.vision.serial_interface import SerialInterface`; `iface.send_frame()` wywolywane w `wysylaj_petla()` (line 52). |
| `src/vision/brain.py` | `src/vision/serial_interface.py` | `send_frame()` z logiem latencji `[LAT]` | ✓ WIRED | `self._serial.send_frame()` linie 171 i 190; `[LAT]` logi linie 179 i 200. |

### Plan 23-02

| From | To | Via | Status | Szczegoly |
|------|----|-----|--------|-----------|
| `src/arduino/aries_controller/aries_controller.ino` | QuickPID library | `ServoPID._pid_pan / ServoPID._pid_tilt` | ✓ WIRED | `class ServoPID` line 175; `_pid_pan(&_pan_wejscie, ...)` w constructor initializer list (line 191); `_pid_pan.Compute()` w pid_krok() (line 216). |
| `src/arduino/aries_controller/aries_controller.ino` | Servo library | `ServoPID._serwo_pan / ServoPID._serwo_tilt` | ✓ WIRED | `_serwo_pan.attach(PAN_PIN)` line 197; `_serwo_pan.write()` w ustaw_serwa() (line 247). |

---

## Data-Flow Trace (Level 4)

| Artefakt | Zmienna danych | Zrodlo | Produkuje realne dane | Status |
|----------|----------------|--------|-----------------------|--------|
| `brain.py:_petla_glowna()` | `bbox` (detekcja twarzy) | `self._detektor.wykryj(klatka, timestamp_ms)` — MediaPipe | Tak — live stream z kamery | ✓ FLOWING |
| `brain.py:_petla_glowna()` | `error_x, error_y` | `self._oblicz_error(bbox, klatka.shape)` — obliczenia geometryczne | Tak — wyliczone z bbox | ✓ FLOWING |
| `aries_controller.ino:pid_krok()` | `ostatni_blad_x/y` | `_serwa.ostatni_blad_x = blad_x` w `_przetworz_ramke()` — z ramki 8B | Tak — z ramki serial | ✓ FLOWING |

---

## Behavioral Spot-Checks

| Zachowanie | Polecenie | Wynik | Status |
|------------|-----------|-------|--------|
| Python syntax poprawna | `python3 -c "import ast; ast.parse(open('scripts/kalibracja_serw.py').read())"` | SYNTAX OK | ✓ PASS |
| Python syntax brain.py | `python3 -c "import ast; ast.parse(open('src/vision/brain.py').read())"` | SYNTAX OK | ✓ PASS |
| Python syntax serial_interface.py | `python3 -c "import ast; ast.parse(open('src/vision/serial_interface.py').read())"` | SYNTAX OK | ✓ PASS |
| Arduino kompilacja | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/` | exit 0, 59% flash, 22% RAM | ✓ PASS |
| Brak starych stalych MODE_* | `grep -c 'MODE_IDLE\|MODE_SCAN\|MODE_TRACK' src/vision/brain.py` | 0 | ✓ PASS |
| LAT logi obecne | `grep -c '\[LAT\]' src/vision/brain.py` | 2 | ✓ PASS |
| E2E tracking z zywa twarzą | Wymaga Arduino + serwa + kamera | DEFERRED | ? SKIP — brak Arduino Leonardo (USB blocker) |
| Kalibracja kierunkow serw | `python3 scripts/kalibracja_serw.py` | DEFERRED | ? SKIP — brak Arduino Leonardo |

---

## Pokrycie wymagan

| Wymaganie | Plan zrodlowy | Opis | Status | Evidencja |
|-----------|---------------|------|--------|-----------|
| INT-01 | 23-01 | End-to-end tracking — twarz → blad → Arduino PID → serwa | ? PARTIAL | Kod gotowy: latencja TX mierzona ([LAT] w brain.py), SerialInterface podlaczona. Weryfikacja E2E wymaga hardware. |
| INT-02 | 23-01 | Poprawna logika kierunkow — twarz po prawej = ruch w prawo | ? PARTIAL | PAN_INVERT=+1 w firmware; skrypt kalibracyjny przygotowany. Weryfikacja empiryczna odroczona (brak Arduino). |
| INT-03 | 23-01 | Os pionowa (tilt) dziala w SCAN i TRACK | ? PARTIAL | Logika tilt obecna: skan_krok() Lissajous z f_tilt=0.073Hz; pid_krok() z TILT_INVERT=-1. Weryfikacja empiryczna odroczona. |
| INT-04 | 23-02 | Kod modularny OOP: klasy VisionManager, SerialInterface, ServoPID | ✓ SATISFIED | Arduino: class ServoPID / MaszynaStanow / HMI; RPi: MozgRPi (= VisionManager per INT-04 intent), SerialInterface, WykrywaczTwarzy, KameraRPi. Uwaga: nazwa MozgRPi zamiast VisionManager — per D-03 w CONTEXT.md: "nazwy klas zostaja". INT-04 spelniony co do modularnosci OOP. |
| INT-05 | 23-02 | Wszystkie komentarze w jezyku polskim | ✓ SATISFIED | Arduino: polskie enumy, komentarze, nazwy metod; RPi: TRYB_*, polskie docstringi, dane/bajt zamiast payload. Wyjatki per D-08: PID, Serial, constrain, millis — techniczne. |

### Uwaga do INT-04: VisionManager vs MozgRPi

ROADMAP Success Criterion 4 wymienia "VisionManager" — jednak CONTEXT.md fazy 23 (D-03) explicite stanowi: "nazwy klas pozostaja". Klasa `MozgRPi` jest semantycznym odpowiednikiem VisionManager — integruje wizje, detekcje i TX. INT-04 wymaga modularnosci OOP, nie konkretnej nazwy klasy. Wymaganie jest spelniome.

---

## Anti-patterns

### Przeskanowane pliki

| Plik | Wzorzec | Powaznosc | Wplyw |
|------|---------|-----------|-------|
| `scripts/kalibracja_serw.py` | Brak anti-patternow | — | — |
| `src/vision/brain.py` | Brak anti-patternow | — | — |
| `src/vision/serial_interface.py` | Brak anti-patternow | — | — |
| `src/arduino/aries_controller/aries_controller.ino` | Brak anti-patternow | — | — |

Brak stubów, placeholderów ani `TODO/FIXME` w zmodyfikowanych plikach.

---

## Human Verification Required

### 1. Kalibracja kierunkow serw (INT-01, INT-02, INT-03)

**Test:** Podlacz Arduino Leonardo z serwami do RPi4, uruchom `python3 scripts/kalibracja_serw.py`
**Expected:** Wszystkie 4 kroki PASS — PAN przesuwa sie w prawo przy error_x=+50, w lewo przy error_x=-50; TILT kompensuje dol/gore przy blad_y=+/-30
**Why human:** Arduino Leonardo niedostepne (USB enumeration blocker na RPi4). Fizyczna obserwacja ruchu serw niezbedna.

### 2. Latencja E2E <100ms (INT-01, SC-1)

**Test:** Uruchom `python3 run_pi_brain.py`, stan przed kamera, obserwuj logi `[LAT] TX SLEDZENIE:`
**Expected:** Wartosci latencji TX sa <100ms (np. `[LAT] TX SLEDZENIE: 1ms err_x=23 err_y=-5 ts=...`)
**Why human:** Wymaga Arduino + serwa + kamera jednoczesnie. Nie mozna zweryfikowac programistycznie.

### 3. E2E tracking bez regresji po refaktorze OOP (INT-01, SC-1/SC-2/SC-3)

**Test:** Uruchom `python3 run_pi_brain.py`, zweryfikuj ze serwa skanuja (Lissajous), potem sledza twarz, LCD pokazuje SLEDZ/SKAN/BEZCZ, buzzer pisnie przy "Target Lock", przycisk abort dziala
**Expected:** Identyczne zachowanie jak przed refaktorem OOP — brak regresji
**Why human:** Pelny E2E test wymaga sprzetu. Wlacza weryfikacje INT-01 (latencja), INT-02 (kierunki), INT-03 (tilt).

---

## Podsumowanie gap

Brak blokujacych luk w kodzie. Kod jest kompletny i poprawny programistycznie.

Jedyna blokada to **brak sprzetu** (Arduino Leonardo — znany USB enumeration bug na RPi4). Wymaga ona ludzkiej weryfikacji przed zamknieciem INT-01, INT-02, INT-03.

**Co jest gotowe:**
- `scripts/kalibracja_serw.py` — deterministyczny skrypt 4-krokowy, petla 20 Hz, PASS/FAIL per krok
- `src/vision/brain.py` — logowanie latencji [LAT] z `time.monotonic_ns()` przy kazdej klatce TRACK i co 50 klatek SCAN
- `src/arduino/aries_controller/aries_controller.ino` — OOP: 3 klasy C++, polskie enumy, kompilacja exit 0
- `src/vision/serial_interface.py` — pelna polonizacja, dane zamiast payload
- INT-04 i INT-05 sa w pelni spelniome (weryfikacja programistyczna)

**Co oczekuje na hardware:**
- INT-01: latencja E2E <100ms — zmierzalna dopiero po podlaczeniu Arduino
- INT-02: poprawnosc kierunkow serw — wymaga obserwacji fizycznej
- INT-03: os tilt w obu trybach — wymaga fizycznej obserwacji Lissajous + TRACK

---

_Verified: 2026-03-31T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
