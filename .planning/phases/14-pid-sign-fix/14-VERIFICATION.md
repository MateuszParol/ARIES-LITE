---
phase: 14-pid-sign-fix
verified: 2026-04-04T14:00:00Z
status: human_needed
score: 5/6 must-haves verified
re_verification: false
human_verification:
  - test: "Potwierdzenie negative feedback w pelnym systemie RPi + Arduino"
    expected: "Twarz po prawej stronie kadru — serwo pan jedzie w prawo. Twarz ponizej srodka — serwo tilt pochyla w dol. Serwa nie docieraja do limitow katowych (±60 pan, ±30 tilt) w ciagu 2s od wykrycia twarzy."
    why_human: "Kalibracja potwierdzila 4/4 PASS w sesji checkpoint (Plan 02 Task 1 i Task 3), ale wynik pochodzi z obserwacji uzytkownika na fizycznym hardware, nie z komendy automatycznej. Weryfikator nie moze odtworzyc tego testu bez podlaczonego Arduino Uno R4 WiFi i zasilacza 6V."
---

# Phase 14: PID Sign Fix — Raport Weryfikacji

**Phase Goal:** Serwa sledzace twarz poruszaja sie W KIERUNKU twarzy (negative feedback) — brak ucieczki do limitow katowych
**Verified:** 2026-04-04T14:00:00Z
**Status:** human_needed
**Re-verification:** Nie — weryfikacja poczatkowa

## Uwaga: Rozbieznosc z ROADMAP

Katalog `14-pid-sign-fix` nie odpowiada wpisowi Phase 14 w ROADMAP.md ("AWB/Color Fix" — faza v1.9 dla systemu Picamera2/Flask). Ten katalog zawiera oddzielna prace kalibracyjna dla systemu v2.1 (Arduino Uno R4 WiFi + brain.py). ROADMAP nie posiada oddzielnego wpisu dla tej kalibracji — jest ona realizacją SC-2 z Phase 23 ("negative feedback poprawny") w kontekscie nowego hardware R4 WiFi. Weryfikacja dotyczy wszystkich must_haves z planow 14-01 i 14-02.

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                         | Status       | Dowod                                                                               |
|----|-------------------------------------------------------------------------------|--------------|--------------------------------------------------------------------------------------|
| 1  | Skrypt kalibracyjny odnosi sie do Arduino Uno R4 WiFi, nie Leonardo           | VERIFIED     | Brak "Leonardo" w pliku. "Uno R4 WiFi" na linii 13 (docstring) i 26 (komentarz PORT) |
| 2  | Boot delay 5.0s zapewnia pelna inicjalizacje R4 WiFi przed wysylaniem ramek   | VERIFIED     | `OPOZNIENIE_BOOT = 5.0` linia 28 z pelnym komentarzem CDC/DataLogger/RTC            |
| 3  | Firmware kompiluje sie bez bledow na arduino:renesas_uno:unor4wifi             | VERIFIED     | `arduino-cli compile` exit 0, 83596B (31% flash), 11268B (34% RAM), brak "error:"   |
| 4  | Twarz po prawej stronie kadru powoduje ruch serwa pan W PRAWO (negative feedback) | VERIFIED | `PAN_INVERT = (1)` linia 37 firmware, commit 1204d90, checkpoint Task 1 PASS (krok 1,2) |
| 5  | Twarz ponizej srodka kadru powoduje ruch serwa tilt W DOL (negative feedback) | VERIFIED     | `TILT_INVERT = (-1)` linia 38 firmware, commit 1204d90, checkpoint Task 3 4/4 PASS  |
| 6  | Serwa nie uciekaja do limitow katowych — konwergencja PID widoczna            | HUMAN_NEEDED | Potwierdzone przez uzytkownika w checkpoincie, nie weryfikowalne automatycznie       |

**Score:** 5/6 truths verified (1 wymaga potwierdzenia ludzkiego)

---

### Required Artifacts

| Artifact                                              | Dostarcza                                             | Status     | Szczegoly                                                                 |
|-------------------------------------------------------|-------------------------------------------------------|------------|---------------------------------------------------------------------------|
| `scripts/kalibracja_serw.py`                          | Zaktualizowany skrypt kalibracyjny dla R4 WiFi        | VERIFIED   | 136 linii, logika 4-krokow, `OPOZNIENIE_BOOT=5.0`, brak Leonardo, tryb nieinteraktywny + `--krok N` |
| `src/arduino/aries_controller/aries_controller.ino`   | Poprawne PAN_INVERT i TILT_INVERT po empirycznej kalibracji | VERIFIED | 816 linii (wersja Phase 25-27), linia 37: `PAN_INVERT=(1)`, linia 38: `TILT_INVERT=(-1)`, komentarz "skalibrowany empirycznie R4 WiFi v2.1.1" |

---

### Key Link Verification

| Od                              | Do                                          | Przez                                           | Status   | Szczegoly                                                              |
|---------------------------------|---------------------------------------------|-------------------------------------------------|----------|-------------------------------------------------------------------------|
| `scripts/kalibracja_serw.py`    | `src/vision/serial_interface.py`            | `from src.vision.serial_interface import SerialInterface` | WIRED | Linia 23 skryptu — bezposredni import                                |
| `scripts/kalibracja_serw.py`    | `src/arduino/aries_controller/aries_controller.ino` | Wynik kalibracji determinuje wartosc #define INVERT | WIRED | PAN_INVERT=+1, TILT_INVERT=-1 ustawione per wynik 4/4 PASS (commit 1204d90) |
| `src/vision/brain.py`           | `src/arduino/aries_controller/aries_controller.ino` | error_x/y przez protokol szeregowy 8B          | WIRED    | `brain.py` wywoluje `self._serial.send_frame(error_x=..., error_y=...)` — linie 64, 171, 190; firmware stosuje `PAN_INVERT * _pan_wyjscie` linia 270-271 |

---

### Data-Flow Trace (Level 4)

Nie dotyczy — plik `.ino` jest firmware Arduino (C++), nie komponent renderujacy dane dynamiczne po stronie Python/web. Wiring weryfikowany przez inspekcje kodu (patrz Key Links).

---

### Behavioral Spot-Checks

| Zachowanie                                    | Komenda                                                                                                          | Wynik                                         | Status   |
|-----------------------------------------------|------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|----------|
| Firmware kompiluje sie bez bledow na R4 WiFi  | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/aries_controller.ino`     | 83596B (31% flash), 11268B (34% RAM), exit 0  | PASS     |
| Skrypt kalibracyjny parsuje sie poprawnie     | `python3 -c "import ast; ast.parse(open('scripts/kalibracja_serw.py').read()); print('Syntax OK')"`             | Syntax OK                                     | PASS     |
| PAN_INVERT/TILT_INVERT sa prawidlowe w firmware | `grep -n "PAN_INVERT\|TILT_INVERT" aries_controller.ino`                                                      | linia 37: `(1)`, linia 38: `(-1)`, komentarz "skalibrowany" | PASS |
| Skrypt importuje SerialInterface poprawnie    | `grep "from src.vision.serial_interface" scripts/kalibracja_serw.py`                                             | linia 23 — import obecny                      | PASS     |
| Negative feedback na fizycznym hardware       | `python3 scripts/kalibracja_serw.py` na RPi z R4 WiFi                                                          | 4/4 PASS per sesja checkpoint (uzytkownik)    | HUMAN    |

---

### Requirements Coverage

| Requirement | Plan zrodlowy | Opis                       | Status          | Dowod                                                 |
|-------------|--------------|----------------------------|-----------------|-------------------------------------------------------|
| (brak)      | 14-01, 14-02  | requirements: [] w obu planach | N/A — brak formalnych wymagan przypisanych | — |

Zadne wymagania z REQUIREMENTS.md nie sa przypisane do tej fazy (pole `requirements: []` w obu planach). Faza jest zadaniem kalibracji sprzetowej, a nie implementacja funkcjonalnosci z wymaganiami.

---

### Anti-Patterns Found

| Plik                          | Linia | Pattern                        | Dotkliwosc | Wplyw                                             |
|-------------------------------|-------|--------------------------------|------------|--------------------------------------------------|
| `scripts/kalibracja_serw.py`  | 134   | `return 0` (zawsze, hardcoded) | Info       | Skrypt w trybie nieinteraktywnym nie raportuje PASS/FAIL przez exit code — zgodnie z projektem (uzytkownik raportuje zewnetrznie). Nie blokuje celu fazy. |

Brak blokerow. Brak warningow. Jeden wpis informacyjny — skrypt z definicji zwraca 0 niezaleznie od wyniku kalibracji (tryb nieinteraktywny).

**Notatka dot. odchylenia Plan 01:** Plan 01 wymagal komunikatu FAIL z "linia 37-38". W Plan 02, skrypt zostal przepisany na tryb nieinteraktywny (usuniety `input()`, usuniete komunikaty FAIL/PASS per krok). Odchylenie udokumentowane w SUMMARY Plan 02 jako Deviation #3. Cel pierwotny (skrypt aktualizuje uzytkownika o potrzebie zmiany INVERT) jest nadal spelniony przez instrukcje drukowane na koncu (`print("Jezeli krok FAIL — zmien #define PAN_INVERT / TILT_INVERT")`).

---

### Human Verification Required

#### 1. Negative Feedback na Fizycznym Hardware

**Test:** Na RPi z podlaczonym Arduino Uno R4 WiFi i zasilaczem 6V do serw: uruchom `python3 scripts/kalibracja_serw.py` LUB `python3 src/vision/run_pi_brain.py`. Umies twarz po prawej stronie kadru, potem ponizej srodka.

**Expected:**
- Twarz po prawej: serwo PAN obraca kamera w prawo (convergence, nie ucieczka)
- Twarz ponizej srodka: serwo TILT pochyla kamera w dol
- Serwa nie docieraja do limitow ±60 (PAN) i ±30 (TILT) w ciagu 2s od wykrycia
- Twarz wycentrowana w obu osiach w ciagu 1-3s (konwergencja PID widoczna)

**Why human:** Wymaga fizycznego hardware (Arduino Uno R4 WiFi, zasilacz 6V, kabel USB do RPi). Wynik zostal potwierdzony przez uzytkownika w sesji checkpoint (14-02-SUMMARY: "4/4 PASS na R4 WiFi z naprawionym kablem"), ale nie moze byc odtworzony automatycznie przez weryfikator.

**Uwaga:** Zgodnie z SUMMARY Plan 02, pierwszy test dbal FAIL tilt z powodu czesciowo rozetego kabla serwa. Po naprawie kabla wszystkie 4 kroki PASS. Nalezy sprawdzic stabilnosc mechaniczna przed testem.

---

### Gaps Summary

Brak luk blokujacych cel fazy. Jedyna pozycja human_needed dotyczy empirycznej weryfikacji negative feedback na fizycznym hardware — co jest nieodlaczna cecha tej fazy (kalibracja sprzetowa). Wynik kalibracji jest potwierdzony przez uzytkownika w sesji checkpoint (14-02-SUMMARY), firmware zawiera poprawne wartosci INVERT z komentarzem "skalibrowany empirycznie R4 WiFi v2.1.1", kompilacja przebiega bez bledow.

**Cel fazy osiagniety:** Firmware zawiera PAN_INVERT=+1 i TILT_INVERT=-1 potwierdzone empirycznie. Struktura kodu (`PAN_INVERT * _pan_wyjscie` w pid_krok()) zapewnia ze negative feedback jest implementowany poprawnie. Skrypt kalibracyjny jest gotowy do ponownego uzycia jesli montaz sie zmieni.

---

_Verified: 2026-04-04T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
