---
phase: 18-srodowisko-protokol-migracja
plan: 01
subsystem: infra
tags: [serial-protocol, git-migration, arduino, binary-protocol, legacy]

# Dependency graph
requires: []
provides:
  - "Zamknieta specyfikacja protokolu binarnego 8B (PROTOCOL_SPEC.md, Status: LOCKED)"
  - "Stary monolit zachowany w legacy/ z pelna historia git (git log --follow)"
  - "Nowa struktura src/arduino/ ze szkieletem .ino (QuickPID, Servo, LiquidCrystal)"
  - "Pusty src/vision/ gotowy na Phase 21 (pi_brain.py)"
affects: [19-arduino-parser, 21-pi-brain, 22-integracja]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Binary protocol: 8B frame — 0xAA + mode (uint8) + error_x (int16 LE) + error_y (int16 LE) + face_size (uint8) + checksum XOR"
    - "Legacy preservation: git mv zachowuje history, git log --follow dziala dla migrowanych plikow"
    - "Arduino firmware w tym samym repo: src/arduino/aries_controller/"

key-files:
  created:
    - ".planning/protocol/PROTOCOL_SPEC.md"
    - "src/arduino/aries_controller/aries_controller.ino"
    - "src/vision/.gitkeep"
  modified:
    - ".gitignore"

key-decisions:
  - "Protokol binarny 8B zamkniety jako dokument PRZED kodem: 0xAA + mode + error_x/y int16 LE + face_size + XOR checksum"
  - "Checksum: XOR bajtow 1-6 (bez start markera 0xAA)"
  - "Parametry transmisji: 115200 baud, 8N1, DTR=False (Leonardo Caterina bootloader)"
  - "Migracja via git mv — historia plikow zachowana przez git log --follow"
  - "Pyc files usuniete z git tracking (wczesniej tracked, teraz w .gitignore)"

patterns-established:
  - "Protocol-first: specyfikacja jako zamkniety dokument w .planning/protocol/ PRZED implementacja parsera"
  - "Legacy preservation: caly stary runtime w legacy/ atomowym commitem"

requirements-completed: [SER-01, MIG-01, MIG-02]

# Metrics
duration: 15min
completed: 2026-03-30
---

# Phase 18 Plan 01: Srodowisko + Protokol + Migracja Summary

**Protokol binarny 8B zamkniety w PROTOCOL_SPEC.md (LOCKED), monolit przeniesiony do legacy/ przez git mv, szkielet Arduino z QuickPID/Servo/LiquidCrystal utworzony w src/arduino/**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-30T18:05:00Z
- **Completed:** 2026-03-30T18:20:37Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Zamknieta specyfikacja protokolu binarnego 8B — `PROTOCOL_SPEC.md` z przykladami Python (`struct.pack`) i Arduino C (`buf[]` little-endian), checksum numerycznie obliczony (mode=2, error_x=45, error_y=-12, face_size=128 → checksum=0xA4)
- Monolit przeniesiony do `legacy/` jednym atomowym `git mv` — historia plikow zachowana, `.pyc` usuniete z git tracking
- Nowa struktura v2.0: `src/arduino/aries_controller/aries_controller.ino` (szkielet z include QuickPID/Servo/LiquidCrystal) i `src/vision/.gitkeep`

## Task Commits

Kazde zadanie commitowane atomicznie:

1. **Task 1: Utworzenie PROTOCOL_SPEC.md** - `439acdb` (docs)
2. **Task 0.5: Aktualizacja .gitignore** - `6db133c` (chore — dodany przed migracja per plan)
3. **Task 2: Migracja monolitu do legacy/** - `b007857` (refactor)
4. **Task 3: Nowa struktura src/ i szkielet Arduino** - `018bcf0` (feat)

## Files Created/Modified
- `.planning/protocol/PROTOCOL_SPEC.md` — Zamknieta specyfikacja protokolu binarnego 8B (Status: LOCKED)
- `src/arduino/aries_controller/aries_controller.ino` — Szkielet firmware Arduino: include QuickPID, Servo, LiquidCrystal + Serial.begin(115200)
- `src/vision/.gitkeep` — Pusty katalog gotowy na Phase 21 (pi_brain.py)
- `.gitignore` — Dodano `__pycache__/`, `*.pyc`, `*.pyo`
- `legacy/` — Caly stary runtime (main.py, run_test_tracker.py, src/, web/, models/)

## Decisions Made
- Checksum XOR obliczany z bajtow 1-6 (bez start markera 0xAA) — potwierdzone przykladem numerycznym 0xA4
- DTR=False dla Leonardo Caterina bootloader — serial nie resetuje Arduino przy polaczeniu
- `.pyc` files usuniete z git tracking w osobnym commicie przed migracja (plan mowil o osobnym commicie .gitignore)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Usunięcie .pyc z git tracking przed commitem migracji**
- **Found during:** Task 2 (git mv migration)
- **Issue:** `.pyc` pliki byly tracked przez git przed dodaniem do `.gitignore`. Po `git mv`, 11 plikow `.pyc` pojawilo sie w staging area jako renames do `legacy/`. Plan zakladal 0 `.pyc` w staging area przed commitem migracji.
- **Fix:** `git rm --cached -f` dla wszystkich `.pyc` files po `git mv`, co skutkowalo ich usunieciem z git tracking (pojawiaja sie jako `D` — deleted, nie jako renames do `legacy/`)
- **Files modified:** .gitignore (osobny commit przed migracja)
- **Verification:** `git diff --cached --name-only | grep "\.pyc" | grep -v "^D"` zwraca 0 wynikow (brak nowych `.pyc` dodanych)
- **Committed in:** `b007857` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical: git tracking cleanup)
**Impact on plan:** Konieczna korekta dla czystosci commitu migracji. Bez scope creep.

## Issues Encountered
- `.pyc` files byly wczesniej tracked w git — `git mv` automatycznie "przenioslby" je do `legacy/`. Wymagalo `git rm --cached -f` po `git mv` by usunac je z git tracking.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- `PROTOCOL_SPEC.md` gotowy jako kontrakt dla parsera (Plan 18-02, Phase 19-22)
- `legacy/` zachowuje caly stary kod jako referencje dla portowania logiki
- `src/arduino/aries_controller/aries_controller.ino` gotowy do weryfikacji kompilacji (Plan 18-02)
- `src/vision/` pusty katalog czeka na Phase 21 (pi_brain.py z MediaPipe)

---
*Phase: 18-srodowisko-protokol-migracja*
*Completed: 2026-03-30*
