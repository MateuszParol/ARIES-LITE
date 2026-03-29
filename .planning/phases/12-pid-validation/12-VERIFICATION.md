---
phase: 12-pid-validation
verified: 2026-03-29T00:00:00Z
status: human_needed
score: 3/4 must-haves verified
human_verification:
  - test: "Uruchom python3 run_test_tracker.py --debug na RPi4 z kamera i serwami (sudo pigpiod). Stoj przed kamera, poczekaj na TRACKING. Obserwuj terminal."
    expected: "Logi PID per-tick pokazuja TILT err != 0 i TILT out != 0 gdy twarz jest poza centrum kadru — blad_tilt i korekta_tilt sa niezerowe (PID-04 empiryczny). Brak natychmiastowego skoku do limitow serw (PID-05). Po 10+ klatkach stabilnej detekcji blad maleje w kierunku zera (PID-06)."
    why_human: "PID-04 (fizyczna reakcja serwa tilt), PID-05 (brak runaway) i PID-06 (konwergencja) wymagaja fizycznego RPi4 z kamera i serwami. Software path jest zwalidowany statycznie — weryfikacja empiryczna zostala przeprowadzona przez uzytkownika w Task 2 i oznaczona 'approved', jednak REQUIREMENTS.md nie zostalo zaktualizowane (PID-04/05/06 pozostaja Pending). Wymagane potwierdzenie ze weryfikacja rzeczywiscie miala miejsce i aktualizacja REQUIREMENTS.md."
---

# Phase 12: PID Validation — Verification Report

**Phase Goal:** Oba serwomotory reaguja na ruch twarzy i konwerguja do srodka kadru bez ucieczki
**Verified:** 2026-03-29
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `run_test_tracker.py --debug` ustawia log level na DEBUG i PID per-tick logi sa widoczne | VERIFIED | `import argparse` na linii 17, `parser.add_argument("--debug")` na linii 39, `log_level = logging.DEBUG if args.debug else logging.INFO` na linii 42, `level=log_level` na linii 44. `python3 run_test_tracker.py --help` zwraca flage --debug. |
| 2 | Logi PID pokazuja blad_tilt != 0 i korekta_tilt != 0 gdy twarz jest poza centrum — software path PID-04 | VERIFIED (software path) | `blad_tilt = srodek_y - ramka_cy` (linia 287), `korekta_tilt = -self.pid_tilt(blad_tilt)` (linia 291), logger.debug loguje oba na liniach 303-305. Obliczenie matematycznie poprawne — gdy twarz nie jest w centrum, `blad_tilt != 0` z definicji. |
| 3 | Zadna os nie ucieka do limitu natychmiastowo — korekty proporcjonalne (PID-05) | HUMAN NEEDED | Software path: `output_limits = (-10.0, 10.0)`, negacja obu osi wdrozzona poprawnie. Weryfikacja empiryczna wymaga fizycznego sprzetu. SUMMARY twierdzi "approved" przez uzytkownika. |
| 4 | Po 10+ klatkach TRACKING blad pan i tilt maleje w kierunku zera — PID konwerguje (PID-06) | HUMAN NEEDED | Algorytm akumulacyjny PID (P+I+D z reset przy SCANNING) jest matematycznie zdolny do konwergencji przy Kp=0.05, Ki=0.001, Kd=0.005. Rzeczywista konwergencja wymaga fizycznej weryfikacji. SUMMARY twierdzi "approved" przez uzytkownika. |

**Score:** 2/4 truths fully verified programmatycznie, 2/4 zwalidowane empirycznie przez uzytkownika (human-verify checkpoint)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `run_test_tracker.py` | Flaga --debug ustawiajaca log level na DEBUG | VERIFIED | Plik istnieje, 65 linii, zawiera argparse, parser.add_argument("--debug"), log_level warunkowy, logging.basicConfig z level=log_level. Commit 48a505a. |
| `src/modes/test_tracker.py` | PID per-tick logger.debug w _sledz() | VERIFIED | Linie 298-306: logger.debug z formatem "PAN err=... TILT err=...". Istniejacy asset z Phase 9, niemodyfikowany w Phase 12. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run_test_tracker.py` | `logging.basicConfig` | argparse --debug flag sets level=logging.DEBUG | VERIFIED | Linia 39: `add_argument("--debug")`, linia 42: `logging.DEBUG if args.debug`, linia 44: `level=log_level`. Wzorzec `level=log_level` obecny (nie hardcoded INFO). |
| `src/modes/test_tracker.py` | `src/hardware.py` | set_angles() w _sledz() z korekta_pan i korekta_tilt | VERIFIED | Linia 296: `self.hardware.set_angles(nowy_pan, nowy_tilt)` gdzie `nowy_pan = self.hardware.pan_angle + korekta_pan` i `nowy_tilt = self.hardware.tilt_angle + korekta_tilt`. Wzorzec obecny. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `src/modes/test_tracker.py` _sledz() | blad_tilt, korekta_tilt | `blad_tilt = srodek_y - ramka_cy` (linia 287), `korekta_tilt = -self.pid_tilt(blad_tilt)` (linia 291) | Tak — obliczenie z pozycji bbox z kamery | FLOWING |
| `src/modes/test_tracker.py` _sledz() | nowy_tilt | `nowy_tilt = self.hardware.tilt_angle + korekta_tilt` (linia 294), przekazany do `set_angles(nowy_pan, nowy_tilt)` (linia 296) | Tak — aktualizuje rzeczywisty kat serwa | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| import przechodzi bez bledu | `python3 -c "import run_test_tracker; print('import OK')"` | `import OK` | PASS |
| --help pokazuje flage --debug | `python3 run_test_tracker.py --help` | `--debug  Ustaw log level na DEBUG (PID per-tick logi)` | PASS |
| Docstring zawiera `--debug` | grep w pliku | Linie 7 i 11: `python3 run_test_tracker.py --debug` | PASS |
| Empiryczna weryfikacja PID na RPi4 | Fizyczne uruchomienie | SUMMARY: "approved" przez uzytkownika (Task 2 human-verify checkpoint) | SKIP — wymaga fizycznego RPi4 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PID-04 | 12-01-PLAN.md | Wartosc Tilt na HUD zmienia sie w TRACKING — PID output dociera do set_angles() i serwo tilt reaguje fizycznie | PARTIAL — software path SATISFIED, fizyczna reakcja serwa HUMAN NEEDED | Software: blad_tilt obliczony (linia 287), korekta_tilt obliczona (linia 291), set_angles() wywolany z nowy_tilt (linia 296). Fizyczna reakcja serwa: SUMMARY "approved", REQUIREMENTS.md nadal "Pending" |
| PID-05 | 12-01-PLAN.md | Zaden z osi nie ucieka (runaway) po wejsciu w TRACKING — sprzezenie zwrotne jest negatywne na obu osiach | HUMAN NEEDED | Software: negacja obu osi wdrozzona (linie 290-291), output_limits (-10.0, 10.0) zabezpieczaja przed runaway. Brak runaway w hardware: SUMMARY "approved", REQUIREMENTS.md nadal "Pending" |
| PID-06 | 12-01-PLAN.md | Po stabilnej detekcji (10+ klatek) kamera centruje twarz w obu osiach — PID konwerguje do stanu ustalonego | HUMAN NEEDED | Software: PID z Kp=0.05 jest zdolny do konwergencji matematycznie. Rzeczywista konwergencja: SUMMARY "approved", REQUIREMENTS.md nadal "Pending" |

**Uwaga: REQUIREMENTS.md (linie 29-31, 62-64) nadal oznacza PID-04/PID-05/PID-06 jako `[ ]` Pending i "Pending" w tabeli traceability. SUMMARY twierdzi ze sa "requirements-completed", ale plik REQUIREMENTS.md nie zostal zaktualizowany.**

### Anti-Patterns Found

| Plik | Linia | Wzorzec | Severity | Impact |
|------|-------|---------|----------|--------|
| — | — | Brak anti-patternow w zmodyfikowanych plikach | — | — |

Skanowanie `run_test_tracker.py` i `src/modes/test_tracker.py`: brak TODO/FIXME/PLACEHOLDER, brak pustych implementacji, brak hardcoded empty data w krytycznych sciezkach.

### Human Verification Required

#### 1. Empiryczna weryfikacja PID-04/05/06 na RPi4

**Test:** Uruchom na RPi4 z podlaczonymi serwami i kamera: `sudo pigpiod && python3 run_test_tracker.py --debug`. Stoj ok. 60-80 cm przed kamera, poczekaj na zielony prostokat (TRACKING), obserwuj terminal przez 15+ sekund.

**Oczekiwane:**
- PID-04: Logi `TILT err=+XX.X ... out=+YY.Y` z niezerowymi wartosciami gdy twarz jest poza centrum. Serwo tilt reaguje fizycznie (HUD pokazuje zmianajaca sie wartosc Tilt).
- PID-05: Wartosci `out=` dla obu osi nie skacza natychmiast do +-10.0 po wejsciu w TRACKING. Brak WARNING "Clamp pan/tilt" w normalnym trackingu.
- PID-06: Po 10+ klatkach stabilnej detekcji wartosci `err=` maleja w kierunku 0. Prostokat twarzy zblizy sie do centrum kadru.

**Dlaczego human:** Fizyczne serwa i kamera wymagane. Zachowanie runtime (runaway, konwergencja) nie jest weryfikowalne statycznie.

**Aktualny status z SUMMARY:** Task 2 oznaczony jako "approved" przez uzytkownika w SUMMARY. Jednak REQUIREMENTS.md nie zostalo zaktualizowane — PID-04/05/06 nadal "Pending".

#### 2. Aktualizacja REQUIREMENTS.md

**Test:** Sprawdz czy REQUIREMENTS.md zostalo zaktualizowane po empirycznej walidacji.

**Oczekiwane:** PID-04, PID-05, PID-06 powinny byc oznaczone `[x]` w liscie i "Complete" w tabeli traceability.

**Dlaczego human:** Wymaga potwierdzenia ze empiryczna walidacja rzeczywiscie sie odbyly i czy wyniki byly pozytywne dla wszystkich trzech wymagan.

### Gaps Summary

**Brak blokujacych gap-ow w software.** Zmodyfikowany plik `run_test_tracker.py` jest kompletny i poprawny:
- `import argparse` istnieje
- `parser.add_argument("--debug")` istnieje
- `log_level = logging.DEBUG if args.debug else logging.INFO` istnieje
- `level=log_level` w basicConfig istnieje
- Docstring zawiera przyklad `python3 run_test_tracker.py --debug`

**Dwa elementy wymagajace potwierdzenia czlowieka:**
1. Empiryczna walidacja PID-04/05/06 na fizycznym RPi4 — SUMMARY twierdzi "approved" ale nie ma dowodow w plikach poza tym oswiadczeniem
2. REQUIREMENTS.md nie zostalo zaktualizowane po rzekomym zatwierdzeniu — wszystkie trzy wymagania pozostaja "Pending"

Jezeli uzytkownik potwierdzi ze empiryczna walidacja rzeczywiscie sie odbyla i wyniki byly pozytywne, faza moze zostac uznana za zakonczona. Nalezy wtedy zaktualizowac REQUIREMENTS.md.

---

_Verified: 2026-03-29_
_Verifier: Claude (gsd-verifier)_
