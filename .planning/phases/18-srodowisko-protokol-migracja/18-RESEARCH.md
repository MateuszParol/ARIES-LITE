# Phase 18: Srodowisko + Protokol + Migracja - Research

**Researched:** 2026-03-30
**Domain:** Python 3.12 venv setup on Debian Trixie, arduino-cli install, binary serial protocol specification, git mv migration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Ramka 8B: `0xAA` (start marker, 1B) + `mode` (uint8, 1B) + `error_x` (int16 LE, 2B) + `error_y` (int16 LE, 2B) + `face_size` (uint8, 1B) + `checksum` (XOR, 1B)
- **D-02:** Blad X/Y kodowany jako surowe piksele (int16 little-endian). Zakres: -160..+160 przy rozdzielczosci 320x240. Arduino normalizuje do swoich potrzeb PID.
- **D-03:** Tryb kodowany jako uint8: 0=IDLE, 1=SCAN, 2=TRACK
- **D-04:** Rozmiar twarzy kodowany jako uint8 (0-255, procent kadru skalowany)
- **D-05:** Little-endian (natywny format AVR) — zero konwersji po stronie Arduino. Python uzywa `struct.pack('<h', val)`.
- **D-06:** XOR checksum calej ramki (bajty 1-6, bez start markera)
- **D-07:** Caly runtime do legacy/: `src/`, `web/`, `main.py`, `run_test_tracker.py`, `models/` → `legacy/`
- **D-08:** Pozostaja w root: `tests/`, `scripts/`, `docs/`, `requirements.txt`, config files, `.planning/`
- **D-09:** Migracja via `git mv` — zachowuje historie plikow w `git log --follow`. Jeden commit: `refactor: move monolith to legacy/`
- **D-10:** Nowy venv z systemowego Python na RPi4 Bookworm. Weryfikacja: `python3 --version` na RPi jako pierwszy krok.
- **D-11:** Flaga `--system-site-packages` w venv — wymagana dla picamera2 + libcamera (zainstalowane systemowo)
- **D-12:** `pip install mediapipe pyserial numpy` w nowym venv. Jezeli mediapipe fail na Python 3.11 → eskalacja (deadsnakes PPA lub build ze zrodla)
- **D-13:** arduino-cli zainstalowane na RPi4. Kompilacja + upload bezposrednio z RPi przez USB (/dev/ttyACM0).
- **D-14:** Firmware w tym samym repo ARIES-LITE: `src/arduino/aries_controller/aries_controller.ino`
- **D-15:** Biblioteki Arduino: QuickPID, Servo (built-in), LiquidCrystal (built-in). Instalacja via `arduino-cli lib install`.

### Claude's Discretion

- Dokladna struktura katalogowa nowego `src/vision/` (ile plikow, jak rozdzielic klasy) — do ustalenia w planowaniu
- Format dokumentu specyfikacji protokolu (markdown w .planning/ vs komentarz w kodzie) — Claude decyduje

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENV-01 | Python 3.11 venv na RPi4 z zainstalowanym MediaPipe (weryfikacja empiryczna) | Sekcja "MediaPipe na Trixie" — mediapipe 0.10.18 cp312 dziala na glibc 2.41; Python 3.12 wymagany przez pyenv lub kompilacje |
| ENV-02 | Arduino IDE/arduino-cli z bibliotekami QuickPID, Servo, LiquidCrystal gotowe do kompilacji firmware | Sekcja "arduino-cli install" — binarne z curl, 3 komendy lib install |
| SER-01 | Specyfikacja ramki binarnej (8 bajtow: start marker 0xAA + tryb + blad X/Y + rozmiar twarzy + checksum XOR) | Sekcja "Specyfikacja protokolu" — format zamkniety w D-01..D-06 |
| MIG-01 | Stary kod monolitu przeniesiony do katalogu legacy/ jako referencja | Sekcja "Migracja git mv" — wykaz plikow, kolejnosc, jednoatomowy commit |
| MIG-02 | Nowa struktura katalogow: src/arduino/ (firmware), src/vision/ (pi brain) | Sekcja "Nowa struktura katalogow" — tylko katalogi tworzone, bez kodu |
</phase_requirements>

---

## Summary

Faza 18 to faza przygotowawcza — zadny kod runtime nie powstaje. Trzy zadania: (1) srodowisko deweloperskie gotowe, (2) specyfikacja protokolu binarnego zamknieta jako dokument, (3) stary monolit przeniesiony do `legacy/` atomowym commitem `git mv`.

**Krytyczne odkrycie (HIGH confidence, zweryfikowane empirycznie):** Ten RPi dziala pod Debian Trixie (Debian 13, Python 3.13.5). CONTEXT.md zakladal Bookworm z Python 3.11 — to zalozenie jest NIEPRAWIDLOWE. System ma tylko Python 3.13 w `/usr/bin/python3`. MediaPipe nie ma zadnego kola dla Linux aarch64 na PyPI w wersji >0.10.18 (cp312 jest ostatnim) i nie ma zadnego kola dla cp313. Wymaga to zainstalowania Python 3.12 przez pyenv przed stworzeniem venv.

**Drugie krytyczne odkrycie:** arduino-cli nie jest zainstalowane i nie ma go w repozytorium apt Trixie. Musi byc zainstalowane binarnie przez oficjalny skrypt curl.

**Rekomendacja glowna:** Python 3.12 przez pyenv (build ze zrodla na aarch64, ~15-20 minut) → venv z `--system-site-packages` → `pip install mediapipe==0.10.18 pyserial numpy`. arduino-cli przez `curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sh`.

---

## Standard Stack

### Core
| Biblioteka | Wersja | Cel | Uzasadnienie |
|-----------|--------|-----|-------------|
| Python | 3.12.x (przez pyenv) | Runtime dla MediaPipe | Ostatnia wersja z aarch64 wheels dla mediapipe |
| mediapipe | 0.10.18 | Face detection na RPi4 | Jedyna wersja z cp312 + manylinux_2_17_aarch64 na PyPI |
| pyserial | 3.5 (system) | USB serial TX | Juz zainstalowana systemowo; wystarczy w venv |
| numpy | >=1.26 | Operacje na tablicach | Wymagana przez mediapipe |
| picamera2 | system apt | Kamera backend | `python3-picamera2` przez apt, wymaga `--system-site-packages` |
| arduino-cli | v1.4.1 | Kompilacja + upload firmware | Oficjalne CLI Arduino; najnowsza stabilna (2026-01-19) |
| QuickPID | 3.1.9 | PID z anti-windup na Arduino | `arduino-cli lib install "QuickPID"` |
| Servo | 1.3.0 | Sterowanie serw MG-90S | Wbudowana w Arduino IDE/CLI |
| LiquidCrystal | wbudowana | LCD 1602 w trybie 4-bit | Wbudowana w Arduino IDE/CLI |

### Alternatywy odrzucone
| Zamiast | Mozna uzyc | Dlaczego nie |
|---------|-----------|-------------|
| mediapipe 0.10.18 | mediapipe 0.10.33 (py3-none) | 0.10.33 py3-none nie ma wariantu linux_aarch64 — tylko macOS arm64 i Windows |
| pyenv Python 3.12 | deadsnakes PPA | deadsnakes to Ubuntu PPA — nie dziala na Debian. Na Trixie brak apt python3.12 |
| arduino-cli binarny | arduino-builder (apt) | arduino-builder 1.3.25 jest przestarzaly, nie obsluguje bibliotek przez CLI |

**Instalacja — Python 3.12 przez pyenv:**
```bash
# Krok 1: Zainstaluj pyenv
curl https://pyenv.run | bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Krok 2: Zainstaluj zaleznosci kompilacji Python
sudo apt install -y libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev \
  libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

# Krok 3: Skompiluj Python 3.12 (~15-20 min na RPi4)
pyenv install 3.12.10

# Krok 4: Stwoz venv z --system-site-packages (dla picamera2)
cd /home/parolisko/ARIES-LITE
/home/parolisko/.pyenv/versions/3.12.10/bin/python3.12 -m venv venv --system-site-packages

# Krok 5: Zainstaluj mediapipe i pozostale zaleznosci
source venv/bin/activate
pip install mediapipe==0.10.18 pyserial numpy

# Weryfikacja
python3 -c "import mediapipe; print(mediapipe.__version__)"
```

**Instalacja — arduino-cli:**
```bash
# Zainstaluj binarne
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sh

# Inicjalizuj konfiguracje
arduino-cli config init
arduino-cli core update-index

# Zainstaluj rdzen AVR (dla Arduino Leonardo)
arduino-cli core install arduino:avr

# Zainstaluj biblioteki
arduino-cli lib install "QuickPID"
# Servo i LiquidCrystal sa wbudowane w arduino:avr — nie wymagaja osobnej instalacji

# Weryfikacja
arduino-cli version
arduino-cli lib list
```

**Weryfikacja mediapipe wheel przed uzyciem:**
```bash
npm view mediapipe version  # NIE — sprawdz PyPI:
pip index versions mediapipe  # NIE na Trixie (externally-managed)
# Zamiast tego, w aktywnym venv:
pip show mediapipe
python -c "import mediapipe as mp; print(mp.__version__); fd = mp.tasks.vision.FaceDetector; print('FaceDetector OK')"
```

---

## Architecture Patterns

### Rekomendowana struktura katalogow (po migracji)

```
ARIES-LITE/
├── src/
│   ├── arduino/
│   │   └── aries_controller/
│   │       └── aries_controller.ino    # placeholder — pusty szkielet .ino w Phase 18
│   └── vision/                         # katalog tworzony; pi_brain.py dopiero w Phase 21
├── legacy/
│   ├── main.py                         # git mv z root
│   ├── run_test_tracker.py             # git mv z root
│   ├── src/                            # git mv z root
│   ├── web/                            # git mv z root
│   └── models/                         # git mv z root
├── tests/                              # pozostaje w root (D-08)
├── scripts/                            # pozostaje w root (D-08)
├── docs/                               # pozostaje w root (D-08)
├── requirements.txt                    # pozostaje (bedzie zaktualizowany w tej fazie)
├── .planning/                          # pozostaje
└── CLAUDE.md, README.md, etc.         # pozostaja
```

### Pattern 1: Specyfikacja protokolu jako zamkniety dokument Markdown

**Co:** Plik `.planning/protocol/PROTOCOL_SPEC.md` opisuje kazdy bajt ramki, wartosc, zakres i kodowanie. Dokument jest ZATWIERDZONY przed jakimkolwiek kodem parsera lub nadajnika.

**Kiedy uzywac:** Kiedy obie strony protokolu (RPi i Arduino) rozwijaja niezalezny kod. Specyfikacja jest punktem odniesienia — zmiany wymagaja jawnej aktualizacji dokumentu.

**Przyklad struktury dokumentu:**
```markdown
# ARIES-LITE Serial Protocol v1.0 — ZATWIERDZONA

**Status:** LOCKED — nie zmieniaj bez aktualizacji wersji protokolu
**Data zatwierdzenia:** 2026-03-30

## Ramka — 8 bajtow

| Offset | Nazwa      | Typ    | Kodowanie       | Zakres          | Opis                    |
|--------|------------|--------|-----------------|-----------------|-------------------------|
| 0      | start      | uint8  | 0xAA (staly)    | 0xAA            | Marker poczatku ramki   |
| 1      | mode       | uint8  | 0=IDLE,1=SCAN,2=TRACK | 0..2     | Tryb pracy kamery       |
| 2-3    | error_x    | int16  | little-endian   | -160..+160 px   | Blad poziomy wzg. srodka|
| 4-5    | error_y    | int16  | little-endian   | -160..+160 px   | Blad pionowy wzg. srodka|
| 6      | face_size  | uint8  | percent*255/100 | 0..255          | Wzgledny rozmiar twarzy |
| 7      | checksum   | uint8  | XOR bajtow 1-6  | 0..255          | Weryfikacja integralnosci|

## Obliczanie checksum

checksum = mode XOR error_x_lo XOR error_x_hi XOR error_y_lo XOR error_y_hi XOR face_size

## Przyklad (Python)

import struct
mode = 2  # TRACK
ex, ey = 45, -12
face_size = 128
frame = struct.pack('<BBhhBB', 0xAA, mode, ex, ey, face_size, 0)
payload = frame[1:7]
checksum = 0
for b in payload:
    checksum ^= b
frame = struct.pack('<BBhhBB', 0xAA, mode, ex, ey, face_size, checksum)
```

**Format dokumentu:** Markdown w `.planning/protocol/PROTOCOL_SPEC.md` (nie komentarz w kodzie). Uzasadnienie: widoczny w git historii, edytowalny zanim istnieje jakikolwiek kod, latwy do weryfikacji przez obie strony.

### Pattern 2: Szkielet .ino jako dowod kompilacji (ENV-02)

**Co:** Minimalny `aries_controller.ino` zawiera `#include <QuickPID.h>`, `#include <Servo.h>`, `#include <LiquidCrystal.h>` z pustymi `setup()` i `loop()`. Celem jest weryfikacja, ze arduino-cli kompiluje biblioteki bez bledow — nie implementacja funkcji.

**Kiedy uzywac:** Faza 18. Szkielet zostaje rozwiniety w fazach 19-22.

**Przyklad szkieletu:**
```cpp
// aries_controller.ino — szkielet do weryfikacji kompilacji
// Faza 18: tylko include + puste funkcje
#include <QuickPID.h>
#include <Servo.h>
#include <LiquidCrystal.h>

void setup() {
    Serial.begin(115200);
}

void loop() {
    // implementacja w fazach 19-22
}
```

**Weryfikacja kompilacji:**
```bash
arduino-cli compile \
  --fqbn arduino:avr:leonardo \
  src/arduino/aries_controller/aries_controller.ino
```

### Pattern 3: git mv atomowy do legacy/

**Co:** Jeden commit `git mv` przenosi wszystkie wskazane pliki/katalogi. Jeden atomowy commit — nie rozdzielac.

**Kolejnosc operacji:**
```bash
# 1. Stworz katalog legacy/
mkdir -p legacy

# 2. Przesuniecia atomowe (git mv zachowuje histori przez git log --follow)
git mv src legacy/src
git mv web legacy/web
git mv main.py legacy/main.py
git mv run_test_tracker.py legacy/run_test_tracker.py
git mv models legacy/models

# 3. Stworz nowe katalogi src/ dla v2.0
mkdir -p src/arduino/aries_controller
mkdir -p src/vision

# 4. Weryfikacja — stary kod musi byc dostepny w legacy/
python3 legacy/run_test_tracker.py --help 2>&1 | head -3  # lub odpowiedni test

# 5. Jeden commit
git add -A
git commit -m "refactor: move monolith to legacy/"
```

**UWAGA:** `__pycache__/` z `.pyc` plikami NIE sa w git (brak wpisu `.gitignore` dla `__pycache__`). Sprawdz przed commitem: `git status` musi pokazac git mv ruchow, nie .pyc plikow.

### Anti-Patterns

- **Rozdzielanie git mv na wiele commitow:** Prowadzi do niejasnej historii; D-09 wymaga jednego commitu.
- **Uzywanie `cp` zamiast `git mv`:** Traci trace historii w `git log --follow`.
- **Nadpisywanie requirements.txt starymi zaleznosciami:** requirements.txt POZOSTAJE w root ale nie musi byc aktualizowany w tej fazie — aktualizacja (usuniecie gpiozero/dlib) moze byc czescia tej fazy lub odlozona do Phase 21.
- **Pominiecie weryfikacji `import mediapipe` przed commitem fazy:** ENV-01 wymaga dowodu empirycznego.

---

## Don't Hand-Roll

| Problem | Nie buduj | Uzyj zamiast | Dlaczego |
|---------|-----------|-------------|---------|
| Python 3.12 na Trixie | Kompilacja ze zrodla recznie | pyenv install 3.12.10 | pyenv zarzadza wersja, PATH, venv integration |
| arduino-cli | Vlastny skrypt apt | curl install script | arduino-cli 1.4.1 jest oficjalnym narzedziem Arduino |
| Checksum XOR | Wlasna implementacja | struct.pack + XOR | Proste, ale MUSI byc identyczne z Arduino — uzywaj referencyjnego przykladu z PROTOCOL_SPEC.md |
| Katalogi src/vision/ i src/arduino/ | Recznie z mkdir | mkdir -p w trakcie migracji | Nie tworz ich przed git mv — kolejnosc ma znaczenie |

---

## Runtime State Inventory

Faza 18 zawiera migracje katalogow przez `git mv`.

| Kategoria | Znalezione | Wymagane dzialanie |
|-----------|------------|-------------------|
| Stored data | Brak — projekt nie uzywa zadnej bazy danych. `tmp_faces/` to katalog runtime, nie git. | Brak — `tmp_faces/` pozostaje w root lub git mv do legacy/. |
| Live service config | Brak zewnetrznych serwisow. Flask to lokalny serwer. | Brak migracji danych. |
| OS-registered state | `pigpiod` daemon — nie zwiazany z nazwa katalogu. Nie dotyczy tej fazy. | Brak — pigpiod usuniety z v2.0 stack w pozniejszych fazach. |
| Secrets/env vars | Brak — projekt nie uzywa .env ani sekretow. Konfiguracja w `src/config.py`. | Po git mv: sciezka do config.py zmienia sie na `legacy/src/config.py` — nowy kod w Phase 21 stworzy nowy config. |
| Build artifacts | `src/modes/__pycache__/` zawiera `.pyc` pliki (`test_tracker.cpython-313.pyc`, `test_tracker.cpython-314.pyc`). NIE sa w git. | Brak akcji — `.pyc` nie sa sledzene przez git. `git mv src legacy/src` nie przeniesie ich (sa ignorowane). Nalezy sprawdzic `git status` po migracji. |

**Wazne:** Po `git mv src legacy/src` stara sciezka importu `from src.modes.test_tracker import ...` przestaje dzialac. Kod w `legacy/` moze wymagac poprawki lub uruchamiania z `cd legacy/`. Weryfikacja success criteria (D-07) to: `legacy/main.py` i `legacy/run_test_tracker.py` pozostaja funkcjonalne — wymaga to testowania z poziomu katalogu `legacy/` lub z dodaniem `legacy/` do `sys.path`.

---

## Common Pitfalls

### Pitfall 1: Debian Trixie ma tylko Python 3.13 — mediapipe sie nie zainstaluje

**Co sie psuje:** `pip install mediapipe` w aktualnym srodowisku (Python 3.13.5, Debian Trixie) konczy sie `ERROR: No matching distribution found for mediapipe`. Potwierdzone empirycznie: brak wheelu cp313 dla linux aarch64 na PyPI. Ostatni wheel aarch64 to mediapipe-0.10.18-cp312.

**Dlaczego:** MediaPipe oficjalnie wspiera Python 3.9–3.12. Python 3.13 wprowadza zmiany ABI pybind11 niezgodne z istniejacymi wheelami.

**Jak unikac:** Zainstalowac Python 3.12 przez pyenv PRZED stworzeniem venv. Kolejnosc: pyenv → python 3.12.x → venv → pip install mediapipe==0.10.18.

**Sygnaly ostrzegawcze:**
- `python3 --version` zwraca `3.13.x`
- `pip install mediapipe` zwraca `No matching distribution found`

### Pitfall 2: `--system-site-packages` NIE dziala z pyenv venv dla picamera2

**Co sie psuje:** `picamera2` zainstalowana przez apt (`python3-picamera2`) jest scisle zwiazana z systemowym Python 3.13. Venv oparty na pyenv Python 3.12 z flaga `--system-site-packages` wskazuje na paczki systemowe 3.13 — picamera2 dla 3.13 nie zadziala pod 3.12.

**Jak unikac:** `--system-site-packages` jest konieczna dla picamera2, ALE picamera2 musi byc zainstalowana dla tej samej wersji Pythona. Opcje:
1. Zainstalowac picamera2 dla Python 3.12 recznie (trudne — libcamera bindingi)
2. Sprawdzic czy `python3-picamera2` apt package ma wsparcie dla 3.12 przez `apt show python3-picamera2`

**To jest OPEN QUESTION — patrz sekcja ponizej.**

### Pitfall 3: git mv `src/` nie usuwa `__pycache__` z git

**Co sie psuje:** Po `git mv src legacy/src` w `git status` pojawia sie `src/modes/__pycache__/test_tracker.cpython-313.pyc` jako untracked (bo `.gitignore` nie zawiera `__pycache__`). Commit `refactor: move monolith to legacy/` moze przypadkowo dodac `.pyc` jesli uzyjemy `git add -A`.

**Jak unikac:** Przed commitem dodaj do `.gitignore`:
```
__pycache__/
*.pyc
*.pyo
venv/
```
Lub uzywaj `git add` per-plik zamiast `git add -A`.

### Pitfall 4: arduino-cli nie jest w apt Trixie

**Co sie psuje:** `sudo apt install arduino-cli` konczy sie `E: Unable to locate package arduino-cli`. Dostepny jest przestarzaly `arduino-builder` (1.3.25) ktory nie obsluguje CLI `lib install`.

**Jak unikac:** Uzyc oficjalnego skryptu instalacyjnego:
```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sh
```
Po instalacji, weryfikacja: `arduino-cli version` powinno zwrocic `v1.4.1` lub nowszy.

### Pitfall 5: arduino-cli wymaga `core update-index` przed `core install`

**Co sie psuje:** `arduino-cli core install arduino:avr` przed `arduino-cli core update-index` konczy sie bledem o braku indeksu.

**Jak unikac:** Kolejnosc wymagana:
```bash
arduino-cli config init
arduino-cli core update-index
arduino-cli core install arduino:avr
arduino-cli lib update-index
arduino-cli lib install "QuickPID"
```

### Pitfall 6: Specyfikacja protokolu z blednym checksum (bajty 0 vs bajty 1-6)

**Co sie psuje:** D-06 mowi "XOR checksum calej ramki (bajty 1-6, bez start markera)". Jesli implementacja policzy XOR wlacznie z bajtem 0 (0xAA), Arduino i RPi beda miec rozne checksumy. Blad jest cichy — checksum bedzie zly ale staly, wiec moze przez chwile "dzialac".

**Jak unikac:** W PROTOCOL_SPEC.md wyraznie napisac: `checksum = mode XOR error_x_lo XOR error_x_hi XOR error_y_lo XOR error_y_hi XOR face_size`. Przetestowac z przykladem referencyjnym (konkretne wartosci wejsciowe → oczekiwany checksum).

---

## Code Examples

Zweryfikowane wzorce z oficjalnych zrodel:

### Obliczanie i pakowanie ramki (Python, struct)
```python
# Zrodlo: Python docs struct.pack, D-01..D-06 z CONTEXT.md
import struct

FRAME_START = 0xAA
MODE_IDLE   = 0
MODE_SCAN   = 1
MODE_TRACK  = 2

def pakuj_ramke(mode: int, error_x: int, error_y: int, face_size: int) -> bytes:
    """Pakuje 8-bajtowa ramke binarna protokolu ARIES-LITE v1.0.

    Checksum: XOR bajtow 1-6 (z wylaczeniem start markera 0xAA).
    Kodowanie: little-endian (natywny format AVR).
    """
    # Pakuj bajty 1-6 (payload bez start markera i checksum)
    payload = struct.pack('<BhhB', mode, error_x, error_y, face_size)

    # XOR checksum bajtow 1-6
    checksum = 0
    for b in payload:
        checksum ^= b

    # Pelna ramka: start marker + payload + checksum
    return struct.pack('<B', FRAME_START) + payload + struct.pack('<B', checksum)

# Weryfikacja: mode=TRACK(2), ex=45, ey=-12, face_size=128
# payload bytes: 02 2D 00 F4 FF 80
# checksum: 02 ^ 2D ^ 00 ^ F4 ^ FF ^ 80 = ?
```

### Szkielet firmware Arduino z wymaganymi includami
```cpp
// Zrodlo: arduino.cc, QuickPID GitHub (Dlloydev/QuickPID 3.1.9)
#include <QuickPID.h>      // anti-windup PID
#include <Servo.h>          // wbudowana w arduino:avr
#include <LiquidCrystal.h>  // wbudowana w arduino:avr

void setup() {
    Serial.begin(115200);
}

void loop() {
    // implementacja w fazach 19-22
}
```

### Weryfikacja kompilacji arduino-cli
```bash
# Zrodlo: arduino-cli docs v1.4.1
arduino-cli compile \
  --fqbn arduino:avr:leonardo \
  --verbose \
  src/arduino/aries_controller/aries_controller.ino
```

### Weryfikacja mediapipe import
```python
# Zrodlo: mediapipe.readthedocs.io — Tasks API
import mediapipe as mp
print(mp.__version__)  # oczekiwane: 0.10.18

# Weryfikacja ze FaceDetector (Tasks API) jest dostepny
from mediapipe.tasks.python.vision import FaceDetector
print("FaceDetector dostepny — ENV-01 PASS")
```

---

## State of the Art

| Stare podejscie | Obecne podejscie | Kiedy zmienione | Wplyw |
|----------------|-----------------|-----------------|-------|
| mediapipe-rpi4 (0.8.8, stary) | mediapipe PyPI (0.10.18, Tasks API) | 2023 — Google przepisalo API | BlazeFace przez Tasks API, nie Face Mesh |
| `mp.solutions.face_detection` (legacy API) | `mp.tasks.vision.FaceDetector` (Tasks API) | mediapipe >= 0.10.0 | Nowe API wymagane — legacy API usuniete |
| pip install mediapipe na Python 3.13 | Wymaga Python 3.12 przez pyenv | Marzec 2026 (Trixie) | Dodatkowy krok instalacji |
| arduino-cli z apt | curl install script | arduino-cli usuniete z debian main | 2 dodatkowe minuty instalacji |

**Przestarzale:**
- `mp.solutions.face_detection`: Usuniete w mediapipe >=0.10.x — uzyj `mp.tasks.vision.FaceDetector`
- `mediapipe-rpi4` (PyPI): Zatrzymane na 0.8.8, niezgodne z nowymi API
- `arduino-builder` (apt 1.3.25): Nie ma `lib install` — tylko `arduino-cli` CLI

---

## Open Questions

1. **Czy picamera2 (apt, cp313) bedzie importowalna w venv Python 3.12?**
   - Co wiemy: `python3-picamera2` zainstalowane przez apt jest skomilowane dla Python 3.13. `--system-site-packages` wskazuje na paczki systemowe systemu 3.13.
   - Co jest niejasne: Czy venv 3.12 z `--system-site-packages` znajdzie i zaladuje paczki 3.13, czy wyrzuci ABI error?
   - Rekomendacja: Jako PIERWSZY krok weryfikacji po stworzeniu venv 3.12 wykonaj `python3 -c "import picamera2"` ZANIM zainstaluje sie mediapipe. Jesli fail — sprawdz `apt show python3-picamera2 | grep Python`. Jesli picamera2 jest ABI-locked do 3.13, rozwiazaniem jest zainstalowanie Python 3.12 przez Picamera2 ze zrodla (bardzo ciezkie) lub uzywanie Python 3.12 wylacznie do mediapipe/serial i Python 3.13 do Picamera2 przez subprocess (skomplikowane). Najlepsza sciezka: sprawdz empirycznie.

2. **Czy pyenv install 3.12.x zajmie >20 minut na tym konkretnym RPi4?**
   - Co wiemy: Build C extension na aarch64 jest wolny. 14GB free na 29GB partycji — miejsca wystarczy.
   - Co jest niejasne: Dok ladny czas kompilacji.
   - Rekomendacja: Uruchom w tle lub zaplanuj jako pierwszy krok fazy (task 1) z timeout alertem.

3. **Czy `tmp_faces/` powinien isc do `legacy/` czy zostac w root?**
   - Co wiemy: `tmp_faces/` jest katalogiem runtime (`web/server.py` tworzy go przy starcie). Nie jest w git. D-07 wymaga `web/` do `legacy/` ale nie wymienia `tmp_faces/`.
   - Rekomendacja: Zostaw `tmp_faces/` w root (nie istnieje w git — nie trzeba `git mv`). Wzmianka w PROTOCOL_SPEC.md jako "katalog legacy, uzywany wylacznie przez legacy/web/server.py".

---

## Environment Availability

| Zaleznosc | Wymagana przez | Dostepna | Wersja | Fallback |
|-----------|---------------|---------|--------|---------|
| Python 3.12 | ENV-01 (mediapipe) | NIE | — | pyenv install 3.12.10 (~15-20min) |
| Python 3.13 | istniejacy kod (legacy) | TAK | 3.13.5 | — |
| mediapipe | ENV-01 | NIE | — | pip install po pyenv 3.12 |
| pyserial | SER-01 | TAK (system) | 3.5 | dostepna w venv przez system-site-packages |
| picamera2 | Phase 21 (nie ta faza) | TAK (system, apt) | system | — |
| arduino-cli | ENV-02 | NIE | — | curl install script (2min) |
| arduino:avr core | ENV-02 | NIE | — | arduino-cli core install arduino:avr |
| QuickPID library | ENV-02 | NIE | — | arduino-cli lib install "QuickPID" |
| git | MIG-01, MIG-02 | TAK | 2.47.3 | — |
| gcc, build-essential | pyenv Python compile | TAK | gcc 14 | — |
| libssl-dev, zlib1g-dev itp. | pyenv Python compile | WYMAGA SPRAWDZENIA | — | sudo apt install |
| /dev/ttyACM0 | ENV-02 verify | NIE (Arduino nie podlaczone) | — | Kompilacja bez uploadu wystarczy dla ENV-02 |

**Zaleznosci blokujace bez fallbacku:**
- Python 3.12: wymagany przed pip install mediapipe — pyenv jest jedynym realnym rozwiazaniem na Trixie

**Zaleznosci z fallbackiem:**
- arduino upload przez /dev/ttyACM0: ENV-02 wymaga tylko kompilacji, nie uploadu — moze byc wykonany bez podlaczonego Arduino

---

## Validation Architecture

Zgodnie z `test_framework: "none"` w `.planning/config.json` i CLAUDE.md ("There are no unit tests or linting tools configured. Verification is empirical"), ta faza nie ma zautomatyzowanych testow.

### Weryfikacja empiryczna (Success Criteria z CONTEXT.md)

| Wymaganie | Zachowanie | Typ testu | Komenda | Plik istnieje? |
|-----------|----------|-----------|---------|---------------|
| ENV-01 | `import mediapipe` dziala na Python 3.12 | smoke (reczny) | `python3 -c "import mediapipe; print(mediapipe.__version__)"` | N/A — output komendy |
| ENV-02 | arduino-cli kompiluje szkielet z QuickPID/Servo/LiquidCrystal | smoke (reczny) | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/aries_controller.ino` | aries_controller.ino |
| SER-01 | PROTOCOL_SPEC.md istnieje i opisuje wszystkie 8 bajtow | manual review | `cat .planning/protocol/PROTOCOL_SPEC.md` | .planning/protocol/PROTOCOL_SPEC.md |
| MIG-01 | `legacy/main.py` i `legacy/run_test_tracker.py` istnieja | smoke (reczny) | `ls legacy/main.py legacy/run_test_tracker.py` | legacy/ (po git mv) |
| MIG-02 | `src/arduino/` i `src/vision/` istnieja w repo | smoke (reczny) | `ls src/arduino/ src/vision/` | src/ (po mkdir) |

### Wave 0 Gaps

Brak plikow testowych do stworzenia — weryfikacja jest empiryczna (output komend). Nie ma frameworka testowego w tym projekcie.

---

## Project Constraints (from CLAUDE.md)

- **Jezyk komentarzy:** Wszystkie komentarze, nazwy zmiennych i metod w jezyku polskim
- **Brak testow jednostkowych:** Weryfikacja empiryczna — output komend, visual confirmation
- **Brak linterow:** Zadne narzedzia statycznej analizy nie sa skonfigurowane
- **Konwencje commitow:** `type(scope): description` — `refactor: move monolith to legacy/`
- **Venv z `--system-site-packages`:** Wymagane dla picamera2 (zainstalowanej systemowo przez apt)
- **Platforma docelowa:** Raspberry Pi 4 (aarch64, Linux 6.12.75+rpt-rpi-v8)
- **Metodologia GSD:** Nie ma implementacji bez SPEC.md (tu: PROTOCOL_SPEC.md) w statusie FINALIZED

---

## Sources

### Primary (HIGH confidence)
- PyPI API `https://pypi.org/pypi/mediapipe/*/json` — bezposrednie sprawdzenie wszystkich wheels; brak cp313 linux aarch64 potwierdzony empirycznie
- `apt list --installed`, `python3 --version`, `/etc/os-release` — empiryczna weryfikacja srodowiska (Debian Trixie, Python 3.13.5)
- Arduino Library Index `https://downloads.arduino.cc/libraries/library_index.json.gz` — QuickPID 3.1.9, Servo 1.3.0
- GitHub arduino/arduino-cli releases API — v1.4.1 (2026-01-19)
- `.planning/research/PITFALLS.md` — DTR reset Leonardo, USB CDC 16ms latency, mediapipe 3.13 incompatibility
- `.planning/research/SUMMARY.md` — v2.0 architecture, protocol spec

### Secondary (MEDIUM confidence)
- GitHub google-ai-edge/mediapipe issues #6159, #6025 — Python 3.13 brak wsparcia (wielokrotnie zgloszone, brak officialnego rozwiazania)
- GitHub Dlloydev/QuickPID library.properties — wersja 3.1.9, anti-windup modes
- deadsnakes launchpad.net — Python 3.11 dostepne dla Ubuntu noble/jammy, NIE dla Debian (wazne negatywne ustalenie)

### Tertiary (LOW confidence)
- WebSearch wyniki dla mediapipe 0.10.33 aarch64 — brak potwierdzenia lnux_aarch64 wheel poza macOS arm64

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zweryfikowany przez PyPI API, apt, empiryczne testy
- Architecture: HIGH — bazuje na zatwierdzonych decyzjach D-01..D-15 i istniejacych badaniach
- Pitfalls: HIGH — Pitfall 1 potwierdzony empirycznie na tym systemie; pozostale z PITFALLS.md
- Srodowisko: HIGH — bezposrednie sprawdzenie OS i Python wersji

**Research date:** 2026-03-30
**Valid until:** 2026-04-13 (14 dni — mediapipe releases sa rzadkie, ale Python 3.12 stan mozna zweryfikowac)
