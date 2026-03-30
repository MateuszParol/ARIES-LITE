# Phase 19: Serial Link + Echo Test - Research

**Researched:** 2026-03-30
**Domain:** pyserial (RPi sender) + Arduino C state-machine parser (Leonardo) + end-to-end binary protocol validation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Parser zaimplementowany jako state-machine: WAIT_START → READ_PAYLOAD → VERIFY_CHECKSUM → DISPATCH. Non-blocking, bajt po bajcie w loop(). Zgodny z SER-02.
- **D-02:** Po poprawnym odbiorze ramki Arduino odsyla identyczna ramke 8B z powrotem (echo). RPi porownuje wyslane vs odebrane bajt po bajcie.
- **D-03:** Bledna checksum lub przerwana ramka = cichy drop + powrot do WAIT_START (resync). Brak echo — RPi wykrywa brak odpowiedzi przez timeout.
- **D-04:** Klasa `SerialInterface` w `src/vision/serial_interface.py` — OOP wrapper na pyserial. Metody: open(), send_frame(), send_heartbeat(), close(). Zgodne z INT-04 (modularny OOP).
- **D-05:** low_latency ustawiane programowo (subprocess + setserial) przy kazdym open(). Nie wymaga sudo ani udev rules.
- **D-06:** Utrata portu USB = SerialException logowany jako warning + wyjatek podniesiony wyzej. Reconnect to odpowiedzialnosc wywolujacego (pi_brain.py w Phase 21). W Phase 19 echo test po prostu konczy sie.
- **D-07:** Skrypt jednorazowy `scripts/echo_test.py` — wysyla ramke, czyta echo, porownuje, drukuje PASS/FAIL + hex dump. Exit code 0/1.
- **D-08:** Scenariusz testowy: ramka TRACK z referencyjnego przykladu PROTOCOL_SPEC.md (mode=2, error_x=45, error_y=-12, face_size=128).
- **D-09:** Raport: sent=[hex], recv=[hex], PASS/FAIL. Minimalny, czytelny output.
- **D-10:** Heartbeat = normalna ramka 8B z mode=IDLE (0), error_x=0, error_y=0, face_size=0. Arduino traktuje kazda poprawna ramke jako dowod zywotnosci — zero specjalnej logiki.
- **D-11:** Metoda `send_heartbeat()` w SerialInterface — alias na send_frame(mode=0, 0, 0, 0). Timing co 200ms dopiero w pi_brain.py (Phase 21).

### Claude's Discretion

- Wewnetrzna implementacja state-machine parsera (nazwy stanow, zmienne pomocnicze)
- Dokladna struktura echo_test.py (argumenty CLI, timeout, ilosc powtorzen)
- Czy echo_test.py importuje SerialInterface czy ma wlasna logike serial (zalecane: importuje SerialInterface)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SER-02 | Arduino parser state-machine (non-blocking, WAIT_START → READ_PAYLOAD → VERIFY_CHECKSUM → DISPATCH) | D-01, Arduino C patterns below, non-blocking byte-by-byte loop() pattern |
| SER-03 | RPi nadajnik pyserial z dtr=False, timeout, low_latency na /dev/ttyACM0 @ 115200 baud | D-04/D-05, pyserial 3.5 set_low_latency_mode() API verified on device |
| SER-04 | Heartbeat TX z RPi co 200ms — Arduino rozpoznaje utrate komunikacji | D-10/D-11, heartbeat = IDLE frame, timing deferred to Phase 21 |
| SER-05 | Echo test — RPi wysyla ramke, Arduino potwierdza odczyt poprawny (walidacja end-to-end) | D-02/D-07/D-08/D-09, echo_test.py pattern documented below |

</phase_requirements>

---

## Summary

Phase 19 buduje warstwe komunikacji szeregowej od podstaw: klasa `SerialInterface` po stronie RPi (pyserial wrapper) i parser state-machine po stronie Arduino (C, non-blocking). Weryfikacja przez `echo_test.py` — skrypt jednorazowy wysylajacy referencyjny TRACK frame i porownujacy odpowiedz bajt po bajcie.

Protokol binarny 8B jest LOCKED w `PROTOCOL_SPEC.md`. Referencyjne implementacje (Python `build_frame` i Arduino C `parse_frame`) sa gotowe do bezposredniego uzycia. Szkielet Arduino (`aries_controller.ino`) kompiluje sie poprawnie na `arduino:avr:leonardo` — zweryfikowano arduino-cli compile.

Kluczowe odkrycie srodowiskowe: `setserial` nie jest zainstalowany na urzadzeniu (dostepny w apt, ale nie zainstalowany). **Nie jest potrzebny** — pyserial 3.5 w venv ma wbudowana metode `set_low_latency_mode(True)` uzywajaca `TIOCGSERIAL`/`TIOCSSERIAL` ioctl bezposrednio. D-05 powinno zostac zaktualizowane: uzyc `ser.set_low_latency_mode(True)` zamiast subprocess + setserial.

**Primary recommendation:** Uzyj `ser.set_low_latency_mode(True)` z pyserial 3.5 (wbudowane, bez subprocess, bez sudo) zamiast setserial w open(). Dla Arduino parsera — state-machine bajt po bajcie w loop() per D-01, z `Serial.write(buf, 8)` jako echo po poprawnej walidacji checksum.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyserial | 3.5 (zainstalowany w venv) | USB CDC serial RPi→Arduino | Standardowa biblioteka serial dla Python, DTR=False, timeout, set_low_latency_mode wbudowane |
| struct (stdlib) | Python 3.12 | Pakowanie ramki (`'<BhhB'`) | Stdlib, zero overhead, little-endian int16 bezposrednio |
| Arduino Servo | 1.3.0 (zainstalowana) | (nie uzywana w Phase 19, ale jest w .ino) | — |
| QuickPID | 3.1.9 (zainstalowana) | (nie uzywana w Phase 19) | — |
| LiquidCrystal | 1.0.7 (zainstalowana) | (nie uzywana w Phase 19) | — |

### Nie potrzebne w Phase 19

| Nie potrzebne | Powod |
|---------------|-------|
| subprocess + setserial | pyserial 3.5 ma wbudowane set_low_latency_mode() |
| threading | SerialInterface synchroniczny w Phase 19; async w Phase 21 |
| argparse | echo_test.py moze uzywac sys.argv lub argparse — decyzja implementacyjna |

### Weryfikacja wersji

Sprawdzone na urzadzeniu (2026-03-30):
- `python3 --version` w venv: **3.12.10**
- `python3 -c "import serial; print(serial.__version__)"` w venv: **3.5**
- `arduino-cli version`: **1.4.1**
- arduino:avr core: **1.8.7**
- Kompilacja aries_controller.ino: **OK** (4006 / 28672 bytes program, 186 / 2560 bytes RAM)

---

## Architecture Patterns

### Recommended Project Structure dla Phase 19

```
src/
└── vision/
    ├── .gitkeep            # juz istnieje — zastapic przez serial_interface.py
    └── serial_interface.py # NOWY: klasa SerialInterface

src/
└── arduino/
    └── aries_controller/
        └── aries_controller.ino  # ROZBUDOWAC: dodac parser + echo

scripts/
└── echo_test.py            # NOWY: skrypt weryfikacyjny end-to-end
```

### Pattern 1: SerialInterface OOP Wrapper (RPi, Python)

**Co:** Klasa hermetyzujaca pyserial. Odpowiada za: otwarcie portu (dtr=False, low_latency), budowanie i wysylanie ramek, zamkniecie. Nie obsluguje reconnect (to zadanie wywolujacego w Phase 21).

**Kiedy uzywac:** Wszystkie punkty wejscia wysylajace dane do Arduino importuja SerialInterface.

```python
# src/vision/serial_interface.py
# Zrodlo: pyserial 3.5 API (zweryfikowane na urzadzeniu) + PROTOCOL_SPEC.md

import struct
import logging
import serial  # pyserial 3.5

logger = logging.getLogger(__name__)

class SerialInterface:
    """Interfejs szeregowy RPi → Arduino. Protokol ARIES-LITE v1.0."""

    BAUDRATE = 115200
    START_MARKER = 0xAA
    FRAME_SIZE = 8

    def __init__(self, port: str = "/dev/ttyACM0", timeout: float = 1.0):
        self._port = port
        self._timeout = timeout
        self._ser: serial.Serial | None = None

    def open(self) -> None:
        """Otwiera port szeregowy. DTR=False zapobiega reset Leonardo."""
        ser = serial.Serial()
        ser.port = self._port
        ser.baudrate = self.BAUDRATE
        ser.bytesize = serial.EIGHTBITS
        ser.parity = serial.PARITY_NONE
        ser.stopbits = serial.STOPBITS_ONE
        ser.timeout = self._timeout
        ser.dtr = False  # kluczowe: Leonardo Caterina bootloader reset
        ser.open()
        # low_latency: redukuje latencje USB CDC z 16ms do ~1ms
        # pyserial 3.5 ma wbudowana metode — nie wymaga setserial ani sudo
        try:
            ser.set_low_latency_mode(True)
            logger.info("Tryb low_latency aktywowany.")
        except ValueError as e:
            logger.warning(f"Nie mozna ustawic low_latency: {e}")
        self._ser = ser
        logger.info(f"Port {self._port} otwarty @ {self.BAUDRATE} baud.")

    def send_frame(self, mode: int, error_x: int, error_y: int, face_size: int) -> None:
        """Wysyla ramke 8B zgodna z PROTOCOL_SPEC.md v1.0."""
        if self._ser is None or not self._ser.is_open:
            raise serial.SerialException("Port nie jest otwarty.")
        ramka = self._buduj_ramke(mode, error_x, error_y, face_size)
        self._ser.write(ramka)

    def send_heartbeat(self) -> None:
        """Alias: ramka IDLE (mode=0, wszystkie zera). Per D-11."""
        self.send_frame(mode=0, error_x=0, error_y=0, face_size=0)

    def close(self) -> None:
        """Zamyka port szeregowy."""
        if self._ser and self._ser.is_open:
            self._ser.close()
            logger.info("Port zamkniety.")
        self._ser = None

    @staticmethod
    def _buduj_ramke(mode: int, error_x: int, error_y: int, face_size: int) -> bytes:
        """Buduje ramke 8B per PROTOCOL_SPEC.md. Identyczna z przykladem referencyjnym."""
        payload = struct.pack('<BhhB', mode, error_x, error_y, face_size)
        checksum = 0
        for b in payload:
            checksum ^= b
        return bytes([0xAA]) + payload + bytes([checksum])
```

### Pattern 2: Arduino Parser State-Machine (non-blocking)

**Co:** Parser bajt po bajcie w `loop()`, bez blokujacego czekania. Stany: WAIT_START → READ_PAYLOAD → VERIFY_CHECKSUM → DISPATCH. Po poprawnej walidacji — echo identycznej ramki przez `Serial.write()`.

**Kiedy uzywac:** Jedyny wzorzec dla nieblokujacego USB CDC na Arduino.

```cpp
// src/arduino/aries_controller/aries_controller.ino
// Zrodlo: PROTOCOL_SPEC.md + wzorzec state-machine (non-blocking)

#define FRAME_SIZE 8
#define START_MARKER 0xAA

// Stany parsera
enum ParserState {
    WAIT_START,        // oczekiwanie na bajt 0xAA
    READ_PAYLOAD,      // odczyt bajtow 1-7
    VERIFY_CHECKSUM,   // weryfikacja XOR (wywolywana po zebraniu 7 bajtow)
    DISPATCH           // przekazanie gotowej ramki
};

// Bufor ramki i licznik
uint8_t ramka_buf[FRAME_SIZE];
uint8_t ramka_idx = 0;
ParserState stan_parsera = WAIT_START;

void setup() {
    Serial.begin(115200);
    // Czekaj az port USB CDC bedzie gotowy (Leonardo wymaga)
    while (!Serial) { delay(10); }
}

void loop() {
    while (Serial.available() > 0) {
        uint8_t bajt = (uint8_t)Serial.read();
        przetwarzaj_bajt(bajt);
    }
}

void przetwarzaj_bajt(uint8_t bajt) {
    switch (stan_parsera) {
        case WAIT_START:
            if (bajt == START_MARKER) {
                ramka_buf[0] = bajt;
                ramka_idx = 1;
                stan_parsera = READ_PAYLOAD;
            }
            // inny bajt: cichy drop, pozostan w WAIT_START
            break;

        case READ_PAYLOAD:
            ramka_buf[ramka_idx++] = bajt;
            if (ramka_idx == FRAME_SIZE) {
                stan_parsera = VERIFY_CHECKSUM;
                // Weryfikacja od razu
                uint8_t obliczona = 0;
                for (uint8_t i = 1; i <= 6; i++) {
                    obliczona ^= ramka_buf[i];
                }
                if (obliczona == ramka_buf[7]) {
                    // Checksum OK — echo identycznej ramki
                    Serial.write(ramka_buf, FRAME_SIZE);
                }
                // bledna checksum = cichy drop (D-03)
                // W obu przypadkach: resync do WAIT_START
                ramka_idx = 0;
                stan_parsera = WAIT_START;
            }
            break;

        default:
            // Bezpieczenstwo: nieznany stan = resync
            ramka_idx = 0;
            stan_parsera = WAIT_START;
            break;
    }
}
```

**Uwaga:** Stany `VERIFY_CHECKSUM` i `DISPATCH` sa logicznie polaczone w jednym miejscu po zebraniu 7 bajtow payload — nie wymagaja osobnych przejsc state-machine. To upraszcza implementacje i eliminuje jeden cykl loop().

### Pattern 3: echo_test.py

**Co:** Skrypt jednorazowy. Importuje SerialInterface, wysyla referencyjny TRACK frame (D-08), czeka na echo z timeoutem, porownuje bajt po bajcie, raportuje PASS/FAIL + hex dump.

```python
#!/usr/bin/env python3
# scripts/echo_test.py
# Zrodlo: D-07, D-08, D-09 z CONTEXT.md

import sys
import time
import serial
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

from src.vision.serial_interface import SerialInterface

PORT = "/dev/ttyACM0"
TIMEOUT = 2.0
FRAME_SIZE = 8

# Referencyjny przyklad z PROTOCOL_SPEC.md (D-08)
EXPECTED = bytes([0xAA, 0x02, 0x2D, 0x00, 0xF4, 0xFF, 0x80, 0xA4])

def main() -> int:
    iface = SerialInterface(port=PORT, timeout=TIMEOUT)
    try:
        iface.open()
        time.sleep(2.0)  # czekaj na Arduino USB CDC enumeration po DTR
        iface._ser.reset_input_buffer()

        # Wyslij referencyjny TRACK frame
        iface.send_frame(mode=2, error_x=45, error_y=-12, face_size=128)
        print(f"sent=[{' '.join(f'{b:02X}' for b in EXPECTED)}]")

        # Czytaj echo
        odebrano = iface._ser.read(FRAME_SIZE)
        hex_recv = ' '.join(f'{b:02X}' for b in odebrano) if odebrano else '(brak odpowiedzi)'
        print(f"recv=[{hex_recv}]")

        if odebrano == EXPECTED:
            print("PASS")
            return 0
        else:
            print("FAIL")
            return 1

    except serial.SerialException as e:
        print(f"BLAD PORTU: {e}")
        return 1
    finally:
        iface.close()

if __name__ == "__main__":
    sys.exit(main())
```

### Anti-Patterns to Avoid

- **`serial.Serial("/dev/ttyACM0", 115200)` bezposrednio bez `dtr=False`:** Resetuje Leonardo przez Caterina DTR-at-1200-baud. Zawsze ustaw `dtr=False` przed `open()`.
- **`Serial.readBytes(buf, 8)` blokujace w loop():** Zamraza Arduino na czas czekania. Uzywaj non-blocking bajt po bajcie z state-machine (D-01).
- **`Serial.peek() == 0xAA` + `Serial.readBytes(buf, 8)` (wzorzec z PROTOCOL_SPEC.md):** Referencyjne dla zrozumienia, ale blokujace jesli `available() < 8`. Wzorzec state-machine z D-01 jest poprawny.
- **Subprocess + setserial:** setserial nie jest zainstalowany. pyserial 3.5 `set_low_latency_mode(True)` jest dostepna i nie wymaga zewnetrznego programu.
- **`while (!Serial) {}` bez `delay()`:** Na Leonardo `Serial` to USB CDC — bez delay() busy-loop moze interferowac z USB enumeration.

---

## Don't Hand-Roll

| Problem | Nie buduj | Uzyj zamiast | Dlaczego |
|---------|-----------|--------------|----------|
| Pakowanie int16 little-endian | Wlasna petla bit-shift | `struct.pack('<BhhB', ...)` | Stdlib, poprawna obsuga znaku, kompatybilna z Arduino C `int16_t` |
| Low-latency serial na Linux | subprocess + setserial lub fcntl ioctl wlasnorecznie | `ser.set_low_latency_mode(True)` (pyserial 3.5) | Wbudowane, brak zewnetrznych zaleznosci, brak sudo |
| Checksum XOR | Dedykowana funkcja CRC/hash | Prosty XOR petla 6 bajtow jak w PROTOCOL_SPEC.md | Specyfikacja jest zamknieta, nie rozszerzac |
| Frame framing/sync | Wlasny protokol z dlugoscia | 0xAA start marker + stala dlugosc 8B | PROTOCOL_SPEC.md jest LOCKED |

---

## Common Pitfalls

### Pitfall 1: DTR Reset Leonardo — port znika po open()

**Co sie dzieje:** `serial.Serial("/dev/ttyACM0", 115200)` wywoluje DTR toggle. Leonardo Caterina bootloader interpretuje to jako sygnal do restartu. Port znika z /dev na ~2-3 sekundy.

**Dlaczego:** Leonardo uzywa natywnego USB CDC (ATmega32U4). Bootloader Caterina reaguje na DTR. Typowe dla kazdego jezyka ktory otwiera port z domyslnymi ustawieniami.

**Jak unikac:**
```python
ser = serial.Serial()
ser.port = "/dev/ttyACM0"
ser.baudrate = 115200
ser.dtr = False   # MUSI byc przed open()
ser.open()
time.sleep(2.0)   # czas na USB CDC re-enumeration
ser.reset_input_buffer()
```

**Objawy ostrzegawcze:** `dmesg | grep ttyACM` pokazuje `cdc_acm: ttyACM0: USB ACM device` wielokrotnie. Pierwszy `read()` zwraca pusty bytes. Arduino HUD pokazuje restart.

### Pitfall 2: setserial nie jest zainstalowany na docelowym RPi

**Co sie dzieje:** D-05 mowi o subprocess + setserial, ale setserial nie jest zainstalowany (`command -v setserial` zwraca blad). Subprocess call fail.

**Jak unikac:** Uzyj `ser.set_low_latency_mode(True)` — metoda wbudowana w pyserial 3.5 (zweryfikowana na urzadzeniu). Otacza w try/except z logger.warning jako fallback.

**Weryfikacja:** `python3 -c "import serial; import inspect; print(inspect.getsource(serial.Serial.set_low_latency_mode))"` w venv pokazuje implementacje TIOCGSERIAL.

### Pitfall 3: Arduino echo nadpisuje bufor gdy RPi nie czyta wystarczajaco szybko

**Co sie dzieje:** Arduino wysyla echo 8B natychmiast po walidacji. Jesli RPi nie wywola `read(8)` przed nastepnym `send_frame()`, bufor RX RPi kumuluje echo. Kolejne odczyty desynchronizuja sie.

**Jak unikac:** W echo_test.py: `reset_input_buffer()` przed wysylaniem. W SerialInterface: metody send nie czytaja — echo jest domena echo_test.py, nie SerialInterface.

**Objawy ostrzegawcze:** `read(8)` zwraca 16 bajtow po dwoch send_frame(). Trzeci wynik PASS mimo ze checksum sie rozni.

### Pitfall 4: `while (!Serial)` zamraza Arduino jesli USB nie jest gotowy

**Co sie dzieje:** Na Leonardo `Serial` to USB CDC. Bez podlaczonego hosta USB, `while (!Serial)` blokuje setup() na zawsze. Arduino nie uruchamia sie bez podlaczonego PC.

**Jak unikac:** Ogranicz czas oczekiwania:
```cpp
uint32_t start = millis();
while (!Serial && millis() - start < 3000) { delay(10); }
```
Dla Phase 19 (echo test) Arduino jest zawsze podlaczone do RPi, wiec blokowanie jest akceptowalne — ale lepiej jest miec timeout na przyszle fazy.

### Pitfall 5: Frame sync desync po partial send

**Co sie dzieje:** Jesli RPi wysyla ramke czescioiwo (np. 4 z 8 bajtow przed przerwaniem), Arduino parser wchodzi w READ_PAYLOAD i czeka na pozostale bajty. Nastepna pelna ramka zostaje przetworzona od offsetu 5, nie od 0 — checksum sie nie zgadza, drop. Jesli D-03 (resync do WAIT_START przy blednym checksum) jest prawidlowo zaimplementowane, jeden cykl recovery wystarczy.

**Jak unikac:** D-03 poprawnie obsluguje ten przypadek — resync do WAIT_START po blednym checksumie. `reset_input_buffer()` na Arduino side po DTR recovery (niemozliwe z RPi — Arduino nie ma tej metody). W praktyce: `ser.reset_input_buffer()` po stronie RPi i 2s delay wystarczy.

---

## Code Examples

Verified patterns z official sources:

### build_frame (Python) — PROTOCOL_SPEC.md referencja

```python
# Zrodlo: .planning/protocol/PROTOCOL_SPEC.md (LOCKED)
import struct

def build_frame(mode: int, error_x: int, error_y: int, face_size: int) -> bytes:
    payload = struct.pack('<BhhB', mode, error_x, error_y, face_size)
    checksum = 0
    for b in payload:
        checksum ^= b
    return bytes([0xAA]) + payload + bytes([checksum])

# Referencyjny wynik dla mode=2, error_x=45, error_y=-12, face_size=128:
# [0xAA, 0x02, 0x2D, 0x00, 0xF4, 0xFF, 0x80, 0xA4]
```

### pyserial DTR=False open() — zweryfikowane na pyserial 3.5

```python
# Zrodlo: pyserial docs + PITFALLS.md Pitfall 2 (DTR reset)
import serial

ser = serial.Serial()
ser.port = "/dev/ttyACM0"
ser.baudrate = 115200
ser.dtr = False   # KRYTYCZNE dla Leonardo
ser.timeout = 1.0
ser.open()
# NIE uzywaj: serial.Serial("/dev/ttyACM0", 115200) — DTR toggle domyslnie wlaczony
```

### set_low_latency_mode — wbudowane w pyserial 3.5

```python
# Zrodlo: pyserial 3.5 serialposix.py (zweryfikowane inspect.getsource na urzadzeniu)
# Implementacja wewnetrzna: TIOCGSERIAL / TIOCSSERIAL ioctl z flag ASYNC_LOW_LATENCY = 0x2000
try:
    ser.set_low_latency_mode(True)
    logger.info("Tryb low_latency aktywowany.")
except ValueError as e:
    logger.warning(f"Nie mozna ustawic low_latency (brak uprawnien lub nie USB serial): {e}")
```

### Arduino echo state-machine — kluczowe fragmenty

```cpp
// Zrodlo: D-01 CONTEXT.md + wzorzec non-blocking parser
// Checksum per PROTOCOL_SPEC.md: XOR bajtow 1-6 (bez start markera bajt 0)
uint8_t obliczona = 0;
for (uint8_t i = 1; i <= 6; i++) {
    obliczona ^= ramka_buf[i];
}
if (obliczona == ramka_buf[7]) {
    Serial.write(ramka_buf, FRAME_SIZE);  // echo identycznej ramki (D-02)
}
// bledna checksum = cichy drop, resync (D-03)
ramka_idx = 0;
stan_parsera = WAIT_START;
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 (venv) | SerialInterface, echo_test.py | ✓ | 3.12.10 | — |
| pyserial | SerialInterface | ✓ | 3.5 (w venv) | — |
| struct (stdlib) | build_frame | ✓ | stdlib | — |
| arduino-cli | Kompilacja + upload firmware | ✓ | 1.4.1 | — |
| arduino:avr core | Kompilacja Leonardo | ✓ | 1.8.7 | — |
| QuickPID library | Kompilacja .ino (include) | ✓ | 3.1.9 | — |
| Servo library | Kompilacja .ino (include) | ✓ | 1.3.0 | — |
| LiquidCrystal library | Kompilacja .ino (include) | ✓ | 1.0.7 | — |
| setserial CLI | D-05 (subprocess approach) | ✗ | — | `ser.set_low_latency_mode(True)` — pyserial 3.5 wbudowane |
| /dev/ttyACM0 | echo_test.py, firmware upload | ✗ (Arduino niepodlaczone) | — | Wymaga fizycznego podlaczenia Arduino Leonardo do USB RPi |

**Missing dependencies with no fallback:**
- `/dev/ttyACM0` — Arduino Leonardo musi byc fizycznie podlaczone do RPi przez USB. Bez Arduino echo_test.py zakonczy sie bledem portu. Nie ma emu ani mock dla testu end-to-end.

**Missing dependencies with fallback:**
- `setserial` — `ser.set_low_latency_mode(True)` (pyserial 3.5) obsluguje ten sam przypadek bez zewnetrznego programu.

---

## Validation Architecture

> `workflow.nyquist_validation` nie jest ustawione w config.json — traktowane jako enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Brak (test_framework: "none" w config.json) |
| Config file | none |
| Quick run command | `python3 scripts/echo_test.py` (exit 0/1) |
| Full suite command | `python3 scripts/echo_test.py` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SER-02 | Arduino parser odbiera TRACK frame bez bledu checksum | integration (hardware) | `python3 scripts/echo_test.py` — PASS oznacza parser dziala | ❌ Wave 0 |
| SER-03 | RPi otwiera port z dtr=False, low_latency, timeout | integration (hardware) | `python3 scripts/echo_test.py` — sukces open() jest weryfikacja posrednia | ❌ Wave 0 |
| SER-04 | send_heartbeat() wysyla poprawna ramke IDLE (8B) | unit (bez Arduino) | `python3 -c "from src.vision.serial_interface import SerialInterface; f=SerialInterface._buduj_ramke(0,0,0,0); assert f == bytes([0xAA,0,0,0,0,0,0,0]), f'FAIL: {f.hex()}'; print('send_heartbeat frame: PASS')"` | ❌ Wave 0 |
| SER-05 | End-to-end: wyslana ramka == odebrane echo | integration (hardware) | `python3 scripts/echo_test.py` | ❌ Wave 0 |

**Uwaga o testach jednostkowych:** SER-04 mozna zweryfikowac bez Arduino (poprawnosc build_frame). SER-02/SER-03/SER-05 wymagaja fizycznego Arduino — sa to testy integracyjne z hardware.

### Sampling Rate

- **Per task commit:** `python3 -c "from src.vision.serial_interface import SerialInterface; ..."` (unit check build_frame)
- **Per wave merge:** `python3 scripts/echo_test.py` (wymaga Arduino podlaczonego)
- **Phase gate:** echo_test.py zwraca exit 0 przed `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `src/vision/serial_interface.py` — klasa SerialInterface (SER-03, SER-04, SER-05)
- [ ] `scripts/echo_test.py` — skrypt weryfikacyjny end-to-end (SER-05)
- [ ] Rozbudowa `src/arduino/aries_controller/aries_controller.ino` — parser state-machine + echo (SER-02)

---

## Open Questions

1. **`while (!Serial)` z timeoutem vs bez w setup()**
   - Co wiemy: Leonardo wymaga USB CDC gotowosci. echo_test.py zawsze ma hosta (RPi). Bez timeoutu Arduino nie startuje bez USB.
   - Co jest niejasne: Czy w przyszlych fazach (watchdog Phase 20) Arduino moze startowac bez polaczenia USB?
   - Rekomendacja: Uzyj timeoutu 3s w `while (!Serial)` — bezpieczniejsze dla przyszlych faz.

2. **Uzycie `_ser` (prywatny atrybut) w echo_test.py**
   - Co wiemy: echo_test.py musi `read(8)` po `send_frame()`. `SerialInterface` nie ma metody `read()` (tylko send).
   - Co jest niejasne: Czy dodac publiczna metode `read_frame()` do SerialInterface?
   - Rekomendacja: W Phase 19 echo_test.py moze uzywac `iface._ser.read(8)` (akceptowalne dla skryptu testowego). Alternatively, dodaj `read_echo(size: int) -> bytes` do SerialInterface — lepsza enkapsulacja. To decyzja przy implementacji.

3. **Delay po `open()` — 2s czy krotszy?**
   - Co wiemy: PITFALLS.md zaleca 2s po DTR-induced reset. Z `dtr=False` reset nie powinien nastapic, ale USB CDC enumeration moze zajac ~200ms.
   - Rekomendacja: Uzyj `time.sleep(2.0)` w echo_test.py (bezpieczny margines), `time.sleep(0.5)` w SerialInterface.open() dla uzytku produkcyjnego. Obie wartosci sa empirycznie weryfikowalne.

---

## Sources

### Primary (HIGH confidence)

- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja ramki 8B, referencyjny Python i Arduino C kod (build_frame, parse_frame)
- `.planning/phases/19-serial-link-echo-test/19-CONTEXT.md` — wszystkie locked decisions D-01..D-11
- pyserial 3.5 source (zweryfikowane przez `inspect.getsource` na urzadzeniu) — `set_low_latency_mode()` implementacja
- arduino-cli compile test na urzadzeniu — aries_controller.ino kompiluje sie (4006 bytes)
- `.planning/research/PITFALLS.md` — Pitfall 2 (DTR reset), Pitfall 3 (USB latency 16ms), Pitfall 5 (frame sync loss)
- `.planning/research/ARCHITECTURE.md` — Brain-Muscle split, SerialSender pattern
- `.planning/REQUIREMENTS.md` — SER-02, SER-03, SER-04, SER-05 definitions

### Secondary (MEDIUM confidence)

- `.planning/research/STACK.md` — pyserial wersja i wzorce z poprzednich faz
- `.planning/codebase/INTEGRATIONS.md` — hardware interfaces, port /dev/ttyACM0 @ 115200
- `CLAUDE.md` — naming conventions (Polish in new modules), OOP patterns, error handling (try/except + logging)

### Tertiary (LOW confidence)

- Brak — wszystkie kluczowe ustalenia zweryfikowane bezposrednio na urzadzeniu lub przez oficjalne zrodla.

---

## Project Constraints (from CLAUDE.md)

Dyrektywy z CLAUDE.md obowiazujace w Phase 19:

| Dyrektywa | Zastosowanie w Phase 19 |
|-----------|------------------------|
| Komentarze i nazwy zmiennych po polsku | `serial_interface.py` i `echo_test.py` — komentarze i nazwy metod po polsku (wzorzec z `test_tracker.py`) |
| try/except z `logging.error()` — nigdy re-raise w warstwie runtime | SerialInterface.open() wrap w try/except; ALE D-06 mowi: SerialException jest swiadomie podnoszone wyzej — zgodne z CLAUDE.md "swiadoma decyzja" |
| Mock mode pattern (PIGPIO_AVAILABLE flag) | Analogiczny wzorzec SERIAL_AVAILABLE mozliwy dla non-RPi dev |
| Type hints z `typing` module dla wszystkiego nowego | Wszystkie metody SerialInterface musza miec type annotations |
| 4-space indentation | Obowiazuje |
| PascalCase klasy, snake_case metody | `SerialInterface` (klasa), `send_frame()`, `send_heartbeat()`, `_buduj_ramke()` |
| Polish method names w nowszym kodzie | `_buduj_ramke()` — polskie nazwy dla private methods (wzorzec z test_tracker.py) |
| `src/vision/serial_interface.py` | Lokalizacja nowego modulu — zdefiniowana w D-04 i zgodna ze struktura `src/vision/` |
| Brak test frameworka | Weryfikacja empiryczna: echo_test.py exit 0/1 |
| GSD workflow — nie edytowac bez kontekstu | Wszystkie zmiany przez `/gsd:execute-phase` |

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — pyserial 3.5 zweryfikowany na urzadzeniu; struct stdlib; arduino-cli kompilacja przetestowana
- Architecture (patterns): HIGH — PROTOCOL_SPEC.md jest LOCKED z gotowymi przykladami; state-machine wzorzec wg D-01
- Pitfalls: HIGH — DTR reset i setserial absence zweryfikowane empirycznie na urzadzeniu; frame sync loss z PITFALLS.md (Phase 18 research)
- Environment: HIGH — wszystkie narzedzia sprawdzone bezposrednio przez bash

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (biblioteki stabilne; hardware invariant)
