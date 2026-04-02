---
phase: 28-kompletny-szkic-arduino-ino
plan: 02
subsystem: testing
tags: [arduino, serial, mediapipe, picamera2, python-abi, e2e-testing]

# Dependency graph
requires:
  - phase: 28-01
    provides: Firmware v2.1 zaflashowany na Uno R4 WiFi — LCD, Serwa, Buzzer, Soft Start zweryfikowane

provides:
  - DEFERRED: Testy T4-T6 nie zostaly wykonane — blokada srodowiska Python ABI

affects:
  - 25-rtc-ds1307-izolowana-integracja
  - future-e2e-vision-testing

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "DEFERRED: mediapipe wymaga Python 3.12, picamera2 wymaga Python 3.13 — nie mozna wspoldzialac w jednym venv na ARM64/aarch64"
  - "pi_brain.py wymaga OBU bibliotek (mediapipe + picamera2) — E2E testing niemozliwy do czasu rozwiazania konfliktu ABI"
  - "Testy T4 (przycisk D7), T5 (Serial E2E z RPi), T6 (5x power cycle) odroczone do czasu rozwiazania konfliktu srodowiska"

patterns-established: []

requirements-completed: []

# Metrics
duration: 5min
completed: 2026-04-02
---

# Phase 28 Plan 02: Weryfikacja Sprzetowa Interaktywna — DEFERRED

**Testy T4/T5/T6 odroczone z powodu konfliktu ABI Python — mediapipe (3.12) vs picamera2 (3.13) uniemozliwia uruchomienie pi_brain.py na ARM64/aarch64**

## Performance

- **Duration:** 5 min (sesja administracyjna — brak wykonania)
- **Started:** 2026-04-02T16:32:51Z
- **Completed:** 2026-04-02T16:38:00Z
- **Tasks:** 0/2 (oba checkpointy DEFERRED)
- **Files modified:** 0

## Status: DEFERRED

Plan 28-02 zawiera dwa checkpointy wymagajace interakcji uzytkownika z hardware:

- **Task 1:** T4 (Przycisk D7 abort) + T5 (Serial E2E z RPi)
- **Task 2:** T6 (5x power cycle stabilnosc)

Obydwa checkpointy nie moga zostac zrealizowane z powodu krytycznej blokady srodowiska.

## Accomplishments

- Brak — zadne testy nie zostaly wykonane
- Plan 28-01 zweryfikowal T1-T3 czesciowo (bootscreen LCD, Soft Start, Buzzer); T3 (5x power cycle na R3) PASS

## Blocker: Konflikt ABI Python na ARM64/aarch64

### Opis problemu

`pi_brain.py` (glowny skrypt wizji RPi) wymaga jednoczesnie:
- `mediapipe` — dostepne TYLKO dla Python 3.12 (brak wheel dla Python 3.13 na ARM64/aarch64)
- `picamera2` — skompilowane TYLKO dla Python 3.13 (systemowe `.so` skompilowane dla `cpython-313`)

Te dwie zaleznosci nie moga wspoldzialac w jednym virtualenv. Nie istnieje zaden oficjalny wheel `mediapipe` dla Python 3.13 na ARM64.

### Skutki

- `python3 run_pi_brain.py` jest niemozliwy do uruchomienia
- Testy T4, T5, T6 wymagaja dzialajacego `pi_brain.py` na RPi4
- Blokuje nie tylko Phase 28 ale kazdy przyszly test E2E wizji

### Mozliwe rozwiazania (do zrealizowania w osobnej fazie badawczej)

| Opcja | Opis | Ryzyko |
|-------|------|--------|
| A | Downgrade Python do 3.12 (system) | Moze zepsuc picamera2 |
| B | Dwa oddzielne venv z subprocess bridge | Zlozonosc, latency IPC |
| C | Zastapic mediapipe inna biblioteką (np. OpenCV DNN) | Refaktoring pi_brain.py |
| D | Poczekac na mediapipe wheel dla Python 3.13 ARM64 | Nieznany termin |
| E | Uzywac Docker z Python 3.12 dla mediapipe | Konfiguracja Dockera na RPi4 |

Opcja C (zastapienie mediapipe na OpenCV DNN) jest najbardziej pragmatyczna — ARIES-LITE juz uzywa OpenCV DNN w `src/vision.py`.

## Task Commits

Brak — zadne zadania nie zostaly wykonane.

## Files Created/Modified

Brak zmian plikow.

## Decisions Made

- Testy T4-T6 DEFERRED do czasu rozwiazania konfliktu mediapipe vs picamera2
- Blokada jest pre-existing issue, nie spowodowana przez Phase 28
- Firmware v2.1 na Uno R4 WiFi pozostaje zaflashowany i gotowy na weryfikacje gdy blokada zostanie rozwiazana

## Deviations from Plan

### Blokada srodowiska (nie devijacja kodu)

Obydwa zadania w tym planie sa `type="checkpoint:human-verify"` — wymagaja interakcji uzytkownika z hardware. Uzytkownik nie mogl wykonac zadnych testow z powodu konfliktu Python ABI.

**Nie jest to autofix — wymaga decyzji architektonicznej** (jak rozwiazac konflikt mediapipe/picamera2).

## Issues Encountered

**BLOCKER: mediapipe (3.12) vs picamera2 (3.13) ABI conflict prevents pi_brain.py execution**

- `mediapipe` brak wheel dla Python 3.13 na ARM64/aarch64
- `picamera2` systemowe `.so` skompilowane dla `cpython-313`
- Nie mozna instalowac obu w jednym venv
- `pi_brain.py` wymaga obu bibliotek do dzialania

Blokada uniemozliwia jakikolwiek E2E test wizji na RPi4 do czasu rozwiazania.

## Next Phase Readiness

**Phase 28 NIE jest zakonczona** — testy T4-T6 pozostaja do wykonania.

Przed wykonaniem testow T4-T6 nalezy:
1. Rozwiazac konflikt mediapipe/picamera2 (oddzielna faza badawcza lub hotfix)
2. Zweryfikowac ze `python3 run_pi_brain.py` uruchamia sie bez bledu ImportError
3. Powtorzyc checkpointy z tego planu (Task 1 i Task 2)

Phase 25 (RTC DS1307) NIE blokuje na pi_brain.py — moze byc wykonana niezaleznie.

## Self-Check: PASSED

- SUMMARY.md: FOUND at `.planning/phases/28-kompletny-szkic-arduino-ino/28-02-SUMMARY.md`
- No task commits (0 tasks executed — both deferred)
- STATE.md updated: session, decision, progress bar (89%)
- ROADMAP.md updated: phase 28 plan progress (2/2 summaries)

---
*Phase: 28-kompletny-szkic-arduino-ino*
*Completed: 2026-04-02*
*Status: DEFERRED — environment blocker*
