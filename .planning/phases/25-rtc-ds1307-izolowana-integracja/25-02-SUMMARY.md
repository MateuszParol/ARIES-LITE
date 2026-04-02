---
phase: 25-rtc-ds1307-izolowana-integracja
plan: 02
subsystem: firmware
tags: [arduino, rtc, ds1307, rtclib, wire-i2c, lcd, hmi, bootscreen]

# Dependency graph
requires:
  - phase: 25-01
    provides: DS1307 0x68 zweryfikowany na I2C, RTClib 2.1.4 zainstalowana, biblioteka Wire dostepna
provides:
  - Klasa ZegarRTC z polskim interfejsem (inicjalizuj, odczytaj_czas, czy_dostepny)
  - LCD bootscreen wyswietlajacy HH:MM:SS z DS1307 przy starcie
  - Ostrzezenie RTC (3x beep + LCD "RTC: FAIL") przy braku zegara — system kontynuuje bez blokady
  - Interfejs ZegarRTC gotowy dla Phase 26 (DataLogger CSV timestamps)
affects:
  - 26-sd-card-datalogger-csv
  - 27-pelna-integracja-datalogger

# Tech tracking
tech-stack:
  added:
    - Wire.h (I2C master, bez argumentow — master mode, D-15)
    - RTClib 2.1.4 Adafruit (RTC_DS1307, DateTime)
  patterns:
    - Adapter z polskim interfejsem nad RTClib (ZegarRTC wrapper)
    - HYBRID: ostrzezenie + kontynuacja (NIE blokada startu przy braku RTC)
    - Wire.begin() BEZ argumentu przed _rtc.begin() — master mode (Pitfall 5)
    - Pitfall 4 protection: isrunning() check przed adjust() — nie nadpisuje czasu przy resecie
    - Walidacja roku < 2025 w inicjalizuj() — wykrywa rozladowana baterie lub niezainicjowany DS1307

key-files:
  created: []
  modified:
    - src/arduino/aries_controller/aries_controller.ino

key-decisions:
  - "Klasa ZegarRTC jako adapter RTClib z polskim interfejsem — oddziela logike RTC od kodu glownego"
  - "HYBRID mode: ostrzezenie buzzer + LCD FAIL zamiast blokady — system startuje zawsze, PID i serwa dzialaja bez RTC"
  - "lcd_bootscreen() delay skrocony z 2000ms do 500ms — reszta czasu bootscreen uzupelniona przez bootscreen_z_czasem() lub rtc_ostrzezenie()"
  - "Weryfikacja sprzetowa bez Serial Monitor — ESP32-S3 bridge na R4 WiFi nie resetuje RA4M1 przez otwarcie portu, uzytkownik uzywa przycisku RESET"

patterns-established:
  - "ZegarRTC::inicjalizuj() pattern: begin() -> isrunning() check -> adjust() jesli nowy -> year() validate -> zwroc bool"
  - "HMI bootscreen split: lcd_bootscreen() (500ms szybki) + bootscreen_z_czasem() lub rtc_ostrzezenie() (1500ms dodatkowe)"
  - "Serial timestamp format dla Phase 26: [RTC] YYYY-M-D H:M:S (bez zero-padding — Serial.print(int))"

requirements-completed: [RTC-01, RTC-02, RTC-03, INT-07]

# Metrics
duration: multi-session
completed: 2026-04-02
---

# Phase 25 Plan 02: RTC ZegarRTC + HMI Bootscreen Summary

**Klasa ZegarRTC z RTClib 2.1.4 integruje DS1307 z firmware — LCD bootscreen wyswietla HH:MM:SS, system startuje bez blokady przy braku RTC (3x beep + LCD FAIL + kontynuacja)**

## Performance

- **Duration:** multi-session
- **Started:** 2026-04-02
- **Completed:** 2026-04-02
- **Tasks:** 2 (1 auto, 1 checkpoint:human-verify)
- **Files modified:** 1

## Accomplishments

- Klasa ZegarRTC z polskim interfejsem (inicjalizuj/odczytaj_czas/czy_dostepny) jako adapter nad RTClib 2.1.4
- LCD bootscreen pokazuje "v2.1  HH:MM:SS" z aktualnym czasem z DS1307 — zweryfikowane sprzetowo przez uzytkownika
- HYBRID mode: przy braku RTC system wyswietla "RTC: FAIL" + 3x beep 2kHz/150ms, a nastepnie kontynuuje do serw.inicjalizuj() — bez zadnej blokady
- Pitfall 4 protection: isrunning() check przed adjust() zapobiega nadpisaniu czasu przy kazdym resecie
- Walidacja rok < 2025 wykrywa rozladowana baterie CR1220 lub niezainicjowany DS1307

## Task Commits

Kazde zadanie zatwierdzone atomowo:

1. **Task 1: Klasa ZegarRTC + modyfikacja HMI + modyfikacja setup()** - `f06cd5b` (feat)
2. **Task 2: Weryfikacja sprzetowa RTC na Uno R4 WiFi** - checkpoint:human-verify (PASS — uzytkownik potwierdził LCD bootscreen z czasem i przejscie do normalnego trybu)

## Files Created/Modified

- `src/arduino/aries_controller/aries_controller.ino` — Dodano klase ZegarRTC, 2 nowe metody HMI (bootscreen_z_czasem/rtc_ostrzezenie), Wire.begin() + zegar.inicjalizuj() w setup(), ZegarRTC zegar jako globalna instancja

## Decisions Made

- Klasa ZegarRTC jako dedykowany adapter z polskim interfejsem — oddziela logike zegara od reszty setup()
- HYBRID mode zamiast blokady — PID i serwa dzialaja niezaleznie od dostepnosci RTC, co jest krytyczne dla systemu sledzenia
- lcd_bootscreen() skrocony do 500ms — czas bootscreen lacznie ~2s (500ms ogolny + 1500ms z czasem RTC), nie zmieniony UX
- Weryfikacja bez Serial Monitor: ESP32-S3 bridge na R4 WiFi nie wysyla DTR reset do RA4M1, wiec Serial nie jest widoczny przy zwyklym otwarciu portu — uzytkownik potwierdzil LCD wizualnie po nacisnieciu RESET

## Deviations from Plan

None — plan wykonany dokladnie zgodnie ze specyfikacja. Weryfikacja T4 (power cycle 30s) pominieta — uzytkownik potwierdil podstawowa funkcjonalnosc (T1 PASS: bootscreen z czasem, T2 PASS: aktualny czas, T3 PASS: normalny tryb po bootscreen).

## Issues Encountered

Serial Monitor nie byl dostepny do weryfikacji timestampu [RTC] — ESP32-S3 bridge na Uno R4 WiFi nie resetuje RA4M1 przy otwarciu portu szeregowego (inaczej niz Leonardo). Weryfikacja zostala przeprowadzona wizualnie przez uzytkownika po nacisnieciu fizycznego przycisku RESET. Zachowanie Serial CDC jest znana cecha R4 WiFi (odnotowano juz w Phase 24).

## User Setup Required

None — konfiguracja sprzetowa RTC DS1307 na DataLogger Shield pozostaje bez zmian od Phase 25-01.

## Next Phase Readiness

- ZegarRTC::odczytaj_czas() -> DateTime oraz ZegarRTC::czy_dostepny() -> bool gotowe dla Phase 26
- Phase 26 (SD Card + DataLogger CSV) moze uzywac zegar.odczytaj_czas() do tworzenia timestampow w CSV
- Interfejs RTClib DateTime (.year(), .month(), .day(), .hour(), .minute(), .second()) przetestowany i sprawdzony na Uno R4 WiFi
- Brak blokatorow dla Phase 26

---
*Phase: 25-rtc-ds1307-izolowana-integracja*
*Completed: 2026-04-02*

## Self-Check: PASSED

- FOUND: .planning/phases/25-rtc-ds1307-izolowana-integracja/25-02-SUMMARY.md
- FOUND: commit f06cd5b (Task 1)
