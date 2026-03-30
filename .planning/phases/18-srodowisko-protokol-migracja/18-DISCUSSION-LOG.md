# Phase 18: Srodowisko + Protokol + Migracja - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 18-srodowisko-protokol-migracja
**Areas discussed:** Ramka protokolu, Strategia migracji, Python venv, Arduino workflow

---

## Ramka protokolu

### Kodowanie bledu X/Y

| Option | Description | Selected |
|--------|-------------|----------|
| int16 piksele | Surowy blad w pikselach (-160..+160). Arduino normalizuje. Prostszy debug. | ✓ |
| int8 znormalizowane | Blad -100..+100 (procent). Mniejsza ramka ale tracimy precyzje. | |
| int16 znormalizowane | Blad -10000..+10000 (setne procenta). Pelna precyzja + normalizacja. | |

**User's choice:** int16 piksele (Rekomendowane)
**Notes:** Czytelne wartosci w Serial Monitor, zero konwersji po stronie RPi

### Tryb + rozmiar twarzy

| Option | Description | Selected |
|--------|-------------|----------|
| uint8 tryb + uint8 rozmiar | 8B ramka: 0xAA + tryb + errX(2) + errY(2) + faceSize(1) + XOR(1) | ✓ |
| uint8 tryb, bez rozmiaru | 7B ramka. Rozmiar w v2.1. | |
| uint8 tryb + uint16 rozmiar | Rozmiar w pikselach (0-65535). 9B ramka. | |

**User's choice:** uint8 tryb + uint8 rozmiar (Rekomendowane)

### Endianness

| Option | Description | Selected |
|--------|-------------|----------|
| Little-endian | Natywny format AVR. Python struct.pack('<h'). Zero konwersji Arduino. | ✓ |
| Big-endian | Network order. Arduino musi swapowac bajty. | |

**User's choice:** Little-endian (Rekomendowane)

---

## Strategia migracji

### Scope legacy/

| Option | Description | Selected |
|--------|-------------|----------|
| Caly runtime | src/, web/, main.py, run_test_tracker.py, models/ → legacy/. Zostaja: tests/, scripts/, docs/. | ✓ |
| Tylko src/ i entry points | src/, main.py, run_test_tracker.py → legacy/. web/ i models/ zostaja. | |
| Nic nie przenosic | Nowy kod obok starego. | |

**User's choice:** Caly runtime (Rekomendowane)

### Git history

| Option | Description | Selected |
|--------|-------------|----------|
| git mv | Zachowuje historie w git log --follow. Jeden commit. | ✓ |
| Kopiuj + usun | cp -r + git rm. Historia rozlaczona. | |
| Ty decydujesz | Claude wybiera. | |

**User's choice:** git mv (Rekomendowane)

---

## Python venv

### Python 3.11 na RPi4

| Option | Description | Selected |
|--------|-------------|----------|
| Nowy venv z system Python | Bookworm ma Python 3.11 jako systemowy. Weryfikacja: python3 --version. | ✓ |
| deadsnakes PPA | sudo add-apt-repository ppa:deadsnakes/ppa + apt install python3.11. | |
| Sprawdz na RPi najpierw | Nie decydujemy — Phase 18 zaczyna od sprawdzenia wersji. | |

**User's choice:** Nowy venv z system Python

### picamera2

| Option | Description | Selected |
|--------|-------------|----------|
| --system-site-packages | Nowy venv z flaga. Picamera2 + libcamera dostepne od razu. | ✓ |
| pip install picamera2 | Czysty venv + proba pip install. Moze nie dzialac. | |
| Ty decydujesz | Claude wybiera. | |

**User's choice:** --system-site-packages (Rekomendowane)

---

## Arduino workflow

### Build + upload

| Option | Description | Selected |
|--------|-------------|----------|
| arduino-cli na RPi | Kompilacja + upload bezposrednio z RPi przez USB. Jeden wezel. | ✓ |
| Arduino IDE na PC | Budowanie na Windows/PC, upload przez USB. | |
| arduino-cli na PC + deploy | Budowanie na PC, binarki na RPi, upload z RPi. | |

**User's choice:** arduino-cli na RPi (Rekomendowane)

### Repo

| Option | Description | Selected |
|--------|-------------|----------|
| Ten sam repo | src/arduino/aries_controller.ino w ARIES-LITE. Spojna wersja. | ✓ |
| Osobny repo | Firmware oddzielnie. Niezalezne wersjonowanie. | |

**User's choice:** Ten sam repo (Rekomendowane)

---

## Claude's Discretion

- Dokladna struktura katalogowa src/vision/ (ile plikow, jak rozdzielic klasy)
- Format dokumentu specyfikacji protokolu (markdown vs komentarz w kodzie)

## Deferred Ideas

None — discussion stayed within phase scope
