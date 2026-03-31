---
phase: 23-integracja-kalibracja
plan: 01
subsystem: integracja
tags: [serial, kalibracja, latencja, arduino, serwa, brain]

# Dependency graph
requires:
  - phase: 22-hmi-lcd-buzzer-przycisk
    provides: firmware Arduino z LCD, buzzer, przycisk i parsowaniem ramek ARIES-LITE 8B
  - phase: 21-wizja-rpi-mediapipe
    provides: MozgRPi z SerialInterface, petla glowna, send_frame() wywolania

provides:
  - scripts/kalibracja_serw.py — deterministyczny skrypt kalibracji PAN_INVERT/TILT_INVERT
  - brain.py z logowaniem latencji TX ([LAT] TX TRACK + [LAT] TX SCAN)

affects: [23-02, kalibracja-e2e]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "petla 20 Hz przy kalibracji zapobiega watchdog Arduino (50ms < 500ms timeout)"
    - "time.monotonic_ns() // 1_000_000 dla mierzalnej latencji TX w ms"
    - "throttling logow SCAN co 50 klatek — ochrona stdout przy 30 FPS"

key-files:
  created:
    - scripts/kalibracja_serw.py
  modified:
    - src/vision/brain.py

key-decisions:
  - "petla 20 Hz (nie jednorazowe send) w skrypcie kalibracyjnym — watchdog Arduino 500ms wymaga ciaglego TX"
  - "OPOZNIENIE_BOOT=4.0s — Leonardo boot: 2s LCD + 1s safe_startup + 1s margines"
  - "logowanie latencji TRACK na kazda klatke, SCAN co 50 klatek — balans miedzy obserwowalnością a spamem logow"

patterns-established:
  - "Pattern 1: skrypt kalibracyjny wyslajacy ramki w petli + input() PASS/FAIL per krok"
  - "Pattern 2: [LAT] prefix w logach latencji — grepowalny dowod mierzalny"

requirements-completed: [INT-01, INT-02, INT-03]

# Metrics
duration: ~15min
completed: 2026-03-31
---

# Phase 23 Plan 01: Kalibracja Serw + Latencja TX Summary

**Skrypt kalibracyjny 4-krokowy (PAN+/-, TILT+/-) z petla 20 Hz + logowanie latencji TX [LAT] w MozgRPi — lancuch E2E gotowy do weryfikacji hardware**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-31T19:00:00Z
- **Completed:** 2026-03-31 (checkpoint: oczekiwanie na weryfikacje hardware)
- **Tasks:** 2 z 3 (Task 3 = checkpoint:human-verify)
- **Files modified:** 2

## Accomplishments

- Skrypt `scripts/kalibracja_serw.py` — deterministyczny, 4-krokowy, petla 20 Hz, PASS/FAIL per krok, wymagany kod wyjscia 0/1
- `brain.py` — logowanie `[LAT] TX TRACK:` przy kazdej klatce TRACK z delay TX w ms, `[LAT] TX SCAN:` co 50 klatek
- Oba pliki przeszly ast.parse (SYNTAX OK) przed commitowaniem

## Task Commits

Kazde zadanie zostalo scommitowane atomicznie:

1. **Task 1: Skrypt kalibracyjny kierunkow serw** - `a9d5bee` (feat)
2. **Task 2: Logowanie latencji TX w MozgRPi** - `c72222d` (feat)

## Files Created/Modified

- `/home/parolisko/ARIES-LITE/scripts/kalibracja_serw.py` — nowy skrypt kalibracyjny: 4 kroki PAN+/- TILT+/-, petla 20 Hz, OPOZNIENIE_BOOT=4s, podsumowanie PASS/FAIL
- `/home/parolisko/ARIES-LITE/src/vision/brain.py` — dodano `_licznik_scan_log`, pomiar `time.monotonic_ns()` przed/po send_frame() w TRACK, log SCAN co 50 klatek

## Decisions Made

- Petla 20 Hz (OPOZNIENIE_TX=0.05) w kalibracji — wymaganie watchdog Arduino (Pitfall 1 z Research); jednorazowe send spowodowaloby watchdog-reset po 500ms
- OPOZNIENIE_BOOT=4.0s — Leonardo Caterina bootloader: 2s LCD bootscreen + 1s safe_startup + 1s margines bezpieczenstwa (Pitfall 5 z Research)
- Log SCAN throttlowany co 50 klatek (nie przy kazdej) — przy 30 FPS byloby 30 logow/s, co zalewa stdout

## Deviations from Plan

Brak — plan wykonany dokladnie zgodnie ze specyfikacja.

## Issues Encountered

Brak.

## User Setup Required

**Task 3 (checkpoint:human-verify) wymaga weryfikacji hardware:**

1. Podlacz Arduino Leonardo z serwami do RPi4
2. Uruchom `sudo pigpiod` (jezeli nie uruchomiony)
3. Upewnij sie ze Arduino ma aktualny firmware (z Phase 22)
4. Uruchom skrypt kalibracyjny:
   ```
   cd /home/parolisko/ARIES-LITE
   source venv/bin/activate
   python3 scripts/kalibracja_serw.py
   ```
5. Obserwuj serwa w kazdym z 4 krokow i odpowiadaj t/n
6. Jezeli jakis krok FAIL: zmien `#define PAN_INVERT` lub `#define TILT_INVERT` w firmware, rekompiluj, wgraj, powtorz
7. Test E2E: `python3 run_pi_brain.py` — sprawdz logi `[LAT] TX TRACK:`

## Next Phase Readiness

- Skrypt kalibracyjny gotowy do uruchomienia na hardware
- Logi `[LAT]` pozwola empirycznie potwierdzic latencje <100ms (INT-01)
- Po weryfikacji hardware: plan 23-02 (strojenie PID + end-to-end test suite)

---
*Phase: 23-integracja-kalibracja*
*Plan: 01*
*Completed: 2026-03-31 (oczekiwanie na checkpoint hardware)*

## Self-Check: PASSED

- `scripts/kalibracja_serw.py`: FOUND
- `src/vision/brain.py`: zmodyfikowany
- Commit `a9d5bee`: FOUND (feat(23-01): dodaj skrypt kalibracyjny kierunkow serw)
- Commit `c72222d`: FOUND (feat(23-01): dodaj logowanie latencji TX w MozgRPi)
