---
phase: 24-migracja-pinow-i-kompilacja-bazowa
plan: 02
subsystem: firmware-hardware
tags: [arduino, uno-r3, uno-r4-wifi, flash, hardware-verify, lcd, servo, serial]

# Dependency graph
requires:
  - phase: 24-migracja-pinow-i-kompilacja-bazowa
    provides: Firmware v2.1 skompilowany zero bledow na arduino:renesas_uno:unor4wifi
provides:
  - Firmware v2.1 zaflashowany na Arduino Uno R3 (platforma testowa, ATmega328P)
  - CHECKPOINT: Oczekuje na 5 testow sprzetowych przez uzytkownika
affects: [24-completion, 25-rtc-ds1307]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Flash arduino:avr:uno jako platforma testowa przed przejsciem na R4 WiFi
    - arduino-cli upload --fqbn arduino:avr:uno --port /dev/ttyACM0

key-files:
  created: []
  modified: []

key-decisions:
  - "Flash na Uno R3 (ATmega328P) zamiast R4 WiFi — strategia testowania hardware przed dostarczeniem R4 (CONTEXT.md line 111)"
  - "Firmware v2.1 kompatybilny z Uno R3: CDC wait while(!Serial) wraca natychmiast na ATmega328P (harmless)"
  - "Pin mapping D6,D9,A0,A1,D2-D5,D7,D8 jest identyczny na R3 i R4 — testy sprzetowe wazne"

patterns-established: []

requirements-completed: []  # Oczekuje na weryfikacje sprzetowa (Task 2 checkpoint)

# Metrics
duration: partial (checkpoint at Task 2)
completed: 2026-04-01
status: AWAITING_HUMAN_VERIFY
---

# Phase 24 Plan 02: Weryfikacja Sprzetowa Firmware v2.1 (partial — checkpoint)

**Firmware v2.1 zaflashowany na Arduino Uno R3 (--fqbn arduino:avr:uno) — oczekuje na 5 testow sprzetowych (LCD, Servo Sweep, Serial, Soft Start, Stabilnosc zasilania)**

## Performance

- **Duration:** partial (checkpoint)
- **Started:** 2026-04-01T17:06:26Z
- **Completed:** PENDING (awaiting human-verify checkpoint)
- **Tasks:** 1/2 (Task 1 zakonczony, Task 2 = checkpoint:human-verify)
- **Files modified:** 0 (flash operacja CLI)

## Accomplishments

- Firmware v2.1 zaflashowany na Arduino Uno Rev3 (ATmega328P, /dev/ttyACM0)
- arduino-cli upload zakonczony sukcesem: `New upload port: /dev/ttyACM0 (serial)`
- Platforma testowa R3 gotowa do 5 testow sprzetowych
- Potwierdzono ze firmware v2.1 jest binarnie kompatybilny z AVR ATmega328P (choc docelowa platforma to R4)

## Task Commits

1. **Task 1: Flash firmware na Uno R3 (test hardware)** - `a48db54` (chore)

## Files Created/Modified

Brak — flash to operacja CLI, nie zmienia plikow w repo

## Decisions Made

- Flash z --fqbn arduino:avr:uno zamiast arduino:renesas_uno:unor4wifi — Arduino Uno R3 podlaczone (R4 WiFi dotrze jutro)
- Firmware v2.1 kompatybilny z obu platformami — CDC wait 500ms wraca natychmiast na ATmega328P

## Deviations from Plan

### Auto-applied (per objective instructions)

**1. [Objective Override] Flash --fqbn arduino:avr:uno zamiast arduino:renesas_uno:unor4wifi**
- **Found during:** Task 1
- **Reason:** Podlaczone urzadzenie to Uno R3 (ID 2a03:0043); objective explicite nakazuje --fqbn arduino:avr:uno jako strategia testowania na R3 przed dostarczeniem R4 WiFi
- **Fix:** Uzyto arduino:avr:uno core (zainstalowany: 1.8.7)
- **Wynik:** Upload zakonczony sukcesem
- **Files modified:** Brak
- **Commit:** a48db54

## Issues Encountered

- Brak — flash zakonczony bez bledow

## Awaiting Human Verify (Task 2 — CHECKPOINT)

**5 testow sprzetowych do wykonania przez uzytkownika na fizycznym Arduino Uno R3 z DataLogger Shield:**

### Test 1: LCD Bootscreen (MIG-04)
1. Wlacz zasilanie Arduino
2. LCD wiersz 0: powinno byc "ARIES-LITE v2.1"
3. LCD wiersz 1: "Inicjalizacja..."
4. Po 2 sekundach LCD powinno pokazac tryb + katy

### Test 2: Soft Start Serw (MIG-08)
1. Przy wlaczeniu zasilania obserwuj serwa — nie powinny szarpnac
2. Serwa powinny plynnie dojsc do pozycji 90/90 w ~1.5s
3. Brak restartu Arduino (LCD nie mignie/zniknie)

### Test 3: Servo Sweep (MIG-05)
1. Obserwuj skan Lissajous — serwa PAN (D6) i TILT (D9) powinny oscylowac plynnie
2. Brak jittera (tykania) lub nierowomiernego ruchu

### Test 4: Serial z RPi (MIG-07)
1. Na RPi: `python3 -c "from src.vision.serial_interface import SerialInterface; s = SerialInterface(); s.open(); s.send_heartbeat(); s.close(); print('OK')"`
2. Powinno wypisac "OK" bez bledu
3. Arduino NIE powinno sie zresetowac przy otwarciu portu

### Test 5: Stabilnosc zasilania (MIG-08)
1. Wylacz i wlacz zasilanie 5 razy
2. Zadne wlaczenie nie powinno spowodowac restartu podczas ruchu serw

## Next Phase Readiness

- PENDING: Task 2 wymaga fizycznej weryfikacji sprzetowej
- Po zatwierdzeniu przez uzytkownika: faza 24 zakonczona, gotowe do Fazy 25 (RTC DS1307)
- R4 WiFi dotrze jutro — po jego podlaczeniu: re-flash z --fqbn arduino:renesas_uno:unor4wifi i ponowna weryfikacja

---
*Phase: 24-migracja-pinow-i-kompilacja-bazowa*
*Status: PARTIAL — awaiting checkpoint:human-verify (Task 2)*
*Updated: 2026-04-01*
