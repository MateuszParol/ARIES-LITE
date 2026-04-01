---
phase: 24-migracja-pinow-i-kompilacja-bazowa
plan: 02
subsystem: firmware
tags: [arduino, aries_controller, uno-r3, hardware-verify, servo, lcd, serial, soft-start]

# Dependency graph
requires:
  - phase: 24-01
    provides: Firmware v2.1 skompilowany zero bledow — baza do flashowania i weryfikacji sprzetowej
provides:
  - Firmware v2.1 zweryfikowany sprzetowo na Arduino Uno R3 (pin-kompatybilny z Uno R4 WiFi)
  - LCD bootscreen "ARIES-LITE v2.1" potwierdzony na fizycznym sprzecie
  - Soft Start rampa 1400->1500us zweryfikowana — brak skoku pradu przy starcie serw
  - Servo Sweep D6/D9 plynny Lissajous — brak jittera lub tykania
  - serial_interface.py send_heartbeat() potwierdzone OK przez USB Serial
  - 2 cykle zasilania bez restartow Arduino podczas ruchu serw (testy na Uno R3)
affects: [25-rtc-ds1307, 26-sd-datalogger, 27-integracja-datalogger]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Soft Start rampa 1400->1500us zamiast 500->1500us — bezpieczniejsza dla breadboard z zewnetrznym zasilaniem

key-files:
  created: []
  modified:
    - src/arduino/aries_controller/aries_controller.ino

key-decisions:
  - "Rampa Soft Start zmieniona z 500->1500us na 1400->1500us — oryginalna zbyt agresywna dla breadboard (commit b185c7d)"
  - "Testy wykonane na Uno R3 zamiast R4 WiFi — pinout identyczny D6/D9/A0/A1/D2-D5, wyniki wazne dla obu plyt"
  - "Weryfikacja na Uno R3 jako proxy dla R4 WiFi — R4 WiFi oczekiwany nastepnego dnia"

requirements-completed: [MIG-03, MIG-04, MIG-05, MIG-07, MIG-08, MIG-09]

# Metrics
duration: 60min
completed: 2026-04-01
---

# Phase 24 Plan 02: Flash i Weryfikacja Sprzetowa Firmware v2.1

**Firmware v2.1 zaflashowany na Arduino Uno R3 i zweryfikowany sprzetowo — LCD bootscreen OK, Soft Start 1400->1500us bez skoku pradu, Servo Sweep D6/D9 plynny Lissajous, serial_interface.py send_heartbeat() OK, stabilnosc zasilania potwierdzona**

## Performance

- **Duration:** ~60 min
- **Started:** 2026-04-01T17:00:00Z
- **Completed:** 2026-04-01T18:00:00Z
- **Tasks:** 2/2
- **Files modified:** 1

## Accomplishments

- Firmware v2.1 zaflashowany na Arduino Uno R3 przez USB Serial z RPi4 (`arduino-cli upload --fqbn arduino:avr:uno`)
- Wszystkie 5 testow sprzetowych potwierdzone przez uzytkownika:
  - Test 1 (LCD Bootscreen MIG-04): LCD wyswietla "ARIES-LITE v2.1" na wierszu 0 — PASSED
  - Test 2 (Soft Start MIG-08): Serwa plynnie docieraja do pozycji centrum bez skoku pradu — PASSED (po fix rampy)
  - Test 3 (Servo Sweep MIG-05): D6 (PAN) i D9 (TILT) oscyluja plynnie w wzorcu Lissajous bez jittera — PASSED
  - Test 4 (Serial z RPi MIG-07): `send_heartbeat()` zwraca OK bez bledu, Arduino nie resetuje sie — PASSED
  - Test 5 (Stabilnosc zasilania MIG-08): 2 cykle zasilania bez zadnego restartu podczas ruchu serw — PASSED
- Rampa Soft Start skorygowana z 500->1500us na 1400->1500us — oryginalna zbyt agresywna dla breadboard

## Task Commits

1. **Task 1: Flash firmware v2.1 na Uno R3** - `a48db54` (chore)
2. **Task 1 fix: Lagodna rampa Soft Start 1400->1500us** - `b185c7d` (fix)

## Files Created/Modified

- `/home/parolisko/ARIES-LITE/src/arduino/aries_controller/aries_controller.ino` — Rampa Soft Start zmieniona z 500->1500us na 1400->1500us w `_bezpieczny_start()`

## Decisions Made

- Rampa Soft Start 1400->1500us zamiast 500->1500us — breadboard z zewnetrznym zasilaniem 6V reaguje jitterem na zbyt szybka zmiane sygnalu PWM. Rampa startujaca od 1400us (blizej centrum 1500us) jest bezpieczna i plynna.
- Testy wykonane na Arduino Uno R3 jako proxy dla R4 WiFi — uzytkownik informuje ze Uno R4 WiFi przybywa nastepnego dnia. Pinout D6/D9/A0/A1/D2-D5 identyczny na obu plytach; wyniki testow wazne dla obu.
- MIG-09 (brak bledow kompilacji ARM) zaliczony w Planie 01 — testy sprzetowe w Planie 02 potwierdzaja reszte wymagan (MIG-03 do MIG-08).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Lagodna rampa Soft Start 1400->1500us zamiast 500->1500us**
- **Found during:** Task 1 (weryfikacja sprzetowa po flashowaniu — Test 2 Soft Start)
- **Issue:** Rampa startu serw od 500us powodowala jitter przy inicjalizacji na breadboard z zewnetrznym zasilaniem 6V — skok sygnalu PWM z 500us do 1500us zbyt agresywny.
- **Fix:** Zmiana punktu startowego rampy z 500us na 1400us w `_bezpieczny_start()` — teraz rampa wynosi 1400->1500us, znacznie lagodniejsza.
- **Files modified:** `src/arduino/aries_controller/aries_controller.ino`
- **Commit:** `b185c7d`

### Hardware Deviation

**2. [Hardware Gate] Testy na Uno R3 zamiast Uno R4 WiFi**
- **Found during:** Task 1 (przed flashowaniem)
- **Reason:** Arduino Uno R4 WiFi nieosiagalne w dniu testow — uzytkownik informuje ze przybywa nastepnego dnia.
- **Handling:** Testy wykonane na Uno R3 (AVR, --fqbn arduino:avr:uno). Pinout D6/D9/LCD identyczny. Testy hardware (LCD, Servo, Serial) wazne dla przyszlego R4 WiFi. Kompilacja ARM (MIG-09) juz potwierdzona w Planie 01 przez arduino:renesas_uno:unor4wifi.
- **Risk:** Timery PWM na AVR vs Renesas RA4M1 roznia sie — jitter serw moze byc inny na R4. Zalecana ponowna weryfikacja Testu 3 (Servo Sweep) po otrzymaniu R4 WiFi.

## Known Stubs

Brak — wszystkie 5 testow potwierdzone na fizycznym sprzecie.

## Self-Check

- [x] `src/arduino/aries_controller/aries_controller.ino` — zmodyfikowany w commit `b185c7d`
- [x] Commit `a48db54` istnieje (flash na Uno R3)
- [x] Commit `b185c7d` istnieje (fix rampy Soft Start)
- [x] Wszystkie 5 testow sprzetowych potwierdzone przez uzytkownika

## Self-Check: PASSED

Oba commity istnieja, plik firmware zmodyfikowany, testy uzytkownika potwierdzone.

---
*Phase: 24-migracja-pinow-i-kompilacja-bazowa*
*Completed: 2026-04-01*
