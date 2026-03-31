---
phase: 19-serial-link-echo-test
plan: 01
subsystem: serial-link
tags: [serial, pyserial, arduino, protocol, state-machine]
one_liner: "SerialInterface OOP wrapper pyserial z DTR=False + low_latency oraz Arduino parser state-machine z echo 8B po poprawnym XOR checksumie"
dependency_graph:
  requires: []
  provides:
    - src/vision/serial_interface.py (SerialInterface — klasa importowalna przez echo_test.py i pi_brain.py)
    - src/arduino/aries_controller/aries_controller.ino (parser state-machine + echo — gotowy do wgrania)
  affects: []
tech_stack:
  added:
    - pyserial 3.5 set_low_latency_mode() — programowe ustawienie low latency bez setserial/subprocess
    - struct.pack('<BhhB') — pakowanie ramki binarnej (mode u8, error_x int16 LE, error_y int16 LE, face_size u8)
  patterns:
    - OOP wrapper na pyserial z DTR=False (Caterina bootloader Leonardo no-reset)
    - Arduino state-machine: WAIT_START → READ_PAYLOAD → VERIFY_CHECKSUM inline → DISPATCH (echo)
    - Non-blocking bajt-po-bajcie loop() bez blokujacego Serial.readBytes()
key_files:
  created:
    - src/vision/serial_interface.py
  modified:
    - src/arduino/aries_controller/aries_controller.ino
decisions:
  - "set_low_latency_mode(True) zamiast subprocess+setserial — pyserial 3.5 ma wbudowane ioctl TIOCGSERIAL/TIOCSSERIAL, nie wymaga setserial ani sudo"
  - "DTR=False ustawione PRZED ser.open() — zapobiega automatycznemu resetowi Leonardo przy polaczeniu USB CDC (Caterina bootloader)"
  - "VERIFY_CHECKSUM i DISPATCH inline po zebraniu 8 bajtow — nie potrzebuja osobnych stanow enum, state-machine ma tylko WAIT_START i READ_PAYLOAD"
metrics:
  duration: "135 sekund"
  completed_date: "2026-03-31"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
requirements_satisfied:
  - SER-02
  - SER-03
  - SER-04
---

# Phase 19 Plan 01: Serial Link — Nadajnik RPi + Parser Arduino Summary

SerialInterface OOP wrapper pyserial z DTR=False + low_latency oraz Arduino parser state-machine z echo 8B po poprawnym XOR checksumie.

## Co zostalo zbudowane

### Task 1: SerialInterface — nadajnik RPi pyserial

Klasa `SerialInterface` w `src/vision/serial_interface.py`:

- **`open()`** — tworzy `serial.Serial()` z 8N1/115200, ustawia `dtr=False` PRZED `ser.open()` (Caterina bootloader no-reset), wywoluje `ser.set_low_latency_mode(True)` w try/except ValueError
- **`send_frame(mode, error_x, error_y, face_size)`** — sprawdza `_ser.is_open`, buduje ramke przez `_buduj_ramke()`, wywoluje `_ser.write()`
- **`send_heartbeat()`** — alias na `send_frame(mode=0, error_x=0, error_y=0, face_size=0)` per D-11
- **`close()`** — zamyka port jesli otwarty, ustawia `_ser = None`
- **`@staticmethod _buduj_ramke(mode, error_x, error_y, face_size) -> bytes`** — `struct.pack('<BhhB', mode, error_x, error_y, face_size)` + XOR checksum bajtow payload + `bytes([0xAA]) + payload + bytes([checksum])`

Ramki referencyjne zweryfikowane:
- TRACK `(2, 45, -12, 128)` → `[0xAA, 0x02, 0x2D, 0x00, 0xF4, 0xFF, 0x80, 0xA4]` — PASS
- IDLE heartbeat `(0, 0, 0, 0)` → `[0xAA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]` — PASS
- SCAN `(1, 0, 0, 0)` → `[0xAA, 0x01, ...]`, len=8 — PASS

### Task 2: Arduino parser state-machine + echo

Rozbudowany `src/arduino/aries_controller/aries_controller.ino`:

- **Stale:** `#define FRAME_SIZE 8`, `#define START_MARKER 0xAA`
- **`enum StanParsera`:** `WAIT_START`, `READ_PAYLOAD` (VERIFY_CHECKSUM i DISPATCH inline)
- **Zmienne globalne:** `ramka_buf[8]`, `ramka_idx`, `stan_parsera = WAIT_START`
- **`przetwarzaj_bajt(uint8_t bajt)`:** switch/case non-blocking — WAIT_START czeka na 0xAA, READ_PAYLOAD zbiera bajty, po zebraniu 8B oblicza `obliczona ^= ramka_buf[i]` (i=1..6), jesli zgodna — `Serial.write(ramka_buf, FRAME_SIZE)` (echo D-02), zawsze resync do WAIT_START
- **`setup()`:** `Serial.begin(115200)` + `while (!Serial && millis() - start < 3000)` timeout 3s (Leonardo Pitfall 4)
- **`loop()`:** `while (Serial.available() > 0) { przetwarzaj_bajt(Serial.read()) }` — non-blocking

Kompilacja: `arduino-cli compile --fqbn arduino:avr:leonardo` — **exit 0** (4334/28672 bytes program, 197/2560 bytes RAM).

## Commits

| Task | Hash | Opis |
|------|------|------|
| Task 1 | 1fced2e | feat(19-01): SerialInterface — nadajnik RPi pyserial |
| Task 2 | db87ac5 | feat(19-01): Arduino parser state-machine + echo |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule — Aktualizacja D-05] set_low_latency_mode zamiast subprocess+setserial**
- **Found during:** Task 1
- **Issue:** D-05 w CONTEXT.md mowi "subprocess + setserial", ale 19-RESEARCH.md wyraznie rekomenduje aktualizacje: pyserial 3.5 ma wbudowane `set_low_latency_mode(True)` przez ioctl TIOCGSERIAL/TIOCSSERIAL — nie wymaga setserial ani sudo.
- **Fix:** Uzyta `ser.set_low_latency_mode(True)` z try/except ValueError (logger.warning) zamiast subprocess+setserial. Zgodne z wymaganiem z PLAN.md (acceptance criteria mowi: `ser.set_low_latency_mode(True)`) i zaleceniem z 19-RESEARCH.md.
- **Files modified:** src/vision/serial_interface.py
- **Commit:** 1fced2e

## Known Stubs

Brak — zaden modul nie zawiera hardcodowanych pustych wartosci ani placeholderow plynacych do renderowania.

## Self-Check: PASSED

Weryfikacja po wykonaniu:

- FOUND: src/vision/serial_interface.py
- FOUND: src/arduino/aries_controller/aries_controller.ino
- FOUND: .planning/phases/19-serial-link-echo-test/19-01-SUMMARY.md
- FOUND: commit 1fced2e (feat(19-01): SerialInterface)
- FOUND: commit db87ac5 (feat(19-01): Arduino parser state-machine + echo)
