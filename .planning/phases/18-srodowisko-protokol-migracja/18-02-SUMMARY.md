---
phase: 18-srodowisko-protokol-migracja
plan: 02
subsystem: infra
tags: [python312, pyenv, mediapipe, arduino-cli, quickpid, servo, liquidcrystal, venv]

# Dependency graph
requires:
  - phase: 18-srodowisko-protokol-migracja-01
    provides: szkielet firmware aries_controller.ino (do kompilacji w tym planie)

provides:
  - Python 3.12.10 zainstalowany przez pyenv (skompilowany ze zrodla na RPi4 Trixie)
  - venv/ z mediapipe 0.10.18, pyserial, numpy — zweryfikowane empirycznie (ENV-01)
  - arduino-cli v1.4.1 z rdzeniem arduino:avr i bibliotekami QuickPID/Servo/LiquidCrystal
  - kompilacja szkieletu aries_controller.ino dla Leonardo (ENV-02)
  - requirements-v2.txt z zaleznosciami v2.0

affects:
  - phase-19 (firmware implementation — wymaga arduino-cli + bibliotek)
  - phase-20 (hardware kalibracja — wymaga arduino-cli do uploadu)
  - phase-21 (pi_brain — wymaga venv z mediapipe)
  - phase-22 (integracja)

# Tech tracking
tech-stack:
  added:
    - pyenv 2.6.26 (menedzer wersji Python)
    - Python 3.12.10 (przez pyenv, skompilowany ze zrodla)
    - mediapipe 0.10.18 (cp312-manylinux_2_17_aarch64)
    - pyserial 3.5
    - numpy 1.26.4
    - arduino-cli v1.4.1
    - QuickPID 3.1.9
    - Servo 1.3.0
    - LiquidCrystal 1.0.7
    - arduino:avr 1.8.7 (rdzen AVR z kompilatorem avr-gcc 7.3.0)
  patterns:
    - Python venv z --system-site-packages dla dostepu do systemowych pakietow (picamera2 przez apt)
    - arduino-cli workflow: config init → core install → lib install → compile

key-files:
  created:
    - requirements-v2.txt (zaleznosci Python v2.0)
  modified: []

key-decisions:
  - "Servo i LiquidCrystal wymagaly osobnej instalacji przez arduino-cli lib install — nie sa builtin w arduino:avr 1.8.7"
  - "picamera2 nie importuje sie w Python 3.12 venv (systemowy cp313 vs cp312 venv) — problem znany, odlozony do Phase 21"
  - "mediapipe==0.10.18 instaluje sie bezproblemowo z cp312 manylinux_2_17_aarch64 wheel na Trixie"

patterns-established:
  - "Pattern 1: Python 3.12 przez pyenv — /home/parolisko/.pyenv/versions/3.12.10/bin/python3.12 -m venv venv --system-site-packages"
  - "Pattern 2: arduino-cli compile — arduino-cli compile --fqbn arduino:avr:leonardo path/do/sketch.ino"

requirements-completed: [ENV-01, ENV-02]

# Metrics
duration: ~35min (kompilacja Python 3.12 ~20min, reszta ~15min)
completed: 2026-03-30
---

# Phase 18 Plan 02: Weryfikacja Srodowiska Deweloperskiego Summary

**Python 3.12.10 venv z mediapipe 0.10.18 (ENV-01 PASS) i arduino-cli v1.4.1 z kompilacja szkieletu Leonardo (ENV-02 PASS) na RPi4 Debian Trixie**

## Performance

- **Duration:** ~35 min (kompilacja Pythona ~20 min + reszta ~15 min)
- **Started:** 2026-03-30
- **Completed:** 2026-03-30
- **Tasks:** 2 z 2 autonomicznych (Task 3 checkpoint — oczekuje weryfikacji uzytkownika)
- **Files modified:** 1

## Accomplishments

- Python 3.12.10 skompilowany ze zrodla przez pyenv na Debian Trixie (system ma tylko 3.13.5)
- mediapipe 0.10.18 zainstalowany w Python 3.12 venv — import i FaceDetector (Tasks API) zweryfikowane empirycznie
- arduino-cli v1.4.1 zainstalowany z rdzeniem arduino:avr i bibliotekami QuickPID 3.1.9 / Servo 1.3.0 / LiquidCrystal 1.0.7
- Szkielet aries_controller.ino kompiluje sie bez bledow dla Arduino Leonardo (4006B programu, 186B RAM)
- requirements-v2.txt zapisany z zaleznosciami v2.0

## Task Commits

Kazdy task zacommitowany atomowo:

1. **Task 1: Instalacja Python 3.12 przez pyenv + venv z mediapipe** - `48729ad` (feat)
2. **Task 2: Instalacja arduino-cli + weryfikacja kompilacji szkieletu** - `13fbd94` (feat, empty commit — narzedzie systemowe)

Task 3 jest checkpointem — oczekuje na weryfikacje uzytkownika.

## Files Created/Modified

- `/home/parolisko/ARIES-LITE/requirements-v2.txt` — Zaleznosci Python v2.0 (mediapipe 0.10.18, pyserial, numpy)

## Decisions Made

- Servo i LiquidCrystal wymagaly osobnej instalacji przez `arduino-cli lib install` — w arduino:avr 1.8.7 nie sa wbudowane (w odroznieniu od starszych wersji IDE)
- picamera2 nie importuje sie w Python 3.12 venv — problem wynika z systemowej instalacji dla cp313 vs cp312 w venv. Problem znany, rozwiazanie w Phase 21.
- mediapipe==0.10.18 instaluje sie bezproblemowo na Trixie aarch64 z wheel cp312-manylinux_2_17_aarch64

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Servo i LiquidCrystal wymagaly osobnej instalacji przez arduino-cli**
- **Found during:** Task 2 (kompilacja szkieletu)
- **Issue:** Plan zakladal ze Servo i LiquidCrystal sa wbudowane w arduino:avr — kompilacja fail na `Servo.h: No such file or directory`, nastepnie `LiquidCrystal.h: No such file or directory`
- **Fix:** Uruchomiono `arduino-cli lib install "Servo"` i `arduino-cli lib install "LiquidCrystal"` — zainstalowane odpowiednio 1.3.0 i 1.0.7
- **Files modified:** Brak (narzedzie systemowe, instalacja do ~/.arduino15/)
- **Verification:** Kompilacja szkieletu: "Szkic uzywa 4006 bajtow (13%)" — ENV-02 PASS
- **Committed in:** `13fbd94` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug w zalozeniu planu)
**Impact on plan:** Niezbedna naprawa dla ENV-02. Bez dodatkowych bibliotek kompilacja byla niemozliwa. Brak scope creep.

## Issues Encountered

- picamera2 nie importuje sie w Python 3.12 venv (`ModuleNotFoundError: No module named 'picamera2'`) — systemowe `python3-picamera2` jest zbudowane dla cp313. Zalogowane jako znany problem, rozwiazanie odlozone do Phase 21 (nie blokuje obecnej fazy).

## User Setup Required

Task 3 jest checkpointem weryfikacyjnym. Uzytkownik powinien potwierdzic:
1. `source venv/bin/activate && python3 --version` zwraca Python 3.12.x
2. `python3 -c "import mediapipe; print(mediapipe.__version__)"` zwraca 0.10.18
3. `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/aries_controller.ino` konczy sie sukcesem

## Next Phase Readiness

- ENV-01 PASS: mediapipe 0.10.18 gotowy do uzycia w Phase 21 (pi_brain)
- ENV-02 PASS: arduino-cli gotowy do kompilacji i uploadu firmware w Phase 19-20
- Srodowisko deweloperskie v2.0 w pelni skonfigurowane na RPi4 Trixie
- Znany bloker: picamera2 w Python 3.12 venv — wymaga rozwiazania w Phase 21

## Self-Check: PASSED

- requirements-v2.txt: FOUND
- 18-02-SUMMARY.md: FOUND
- Commit 48729ad (Task 1): FOUND
- Commit 13fbd94 (Task 2): FOUND

---
*Phase: 18-srodowisko-protokol-migracja*
*Completed: 2026-03-30*
