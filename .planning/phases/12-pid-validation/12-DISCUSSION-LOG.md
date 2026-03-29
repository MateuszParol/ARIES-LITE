# Phase 12: PID Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 12-pid-validation
**Areas discussed:** Strategia walidacji, Reakcja na failure, Scope tilt freeze

---

## Strategia walidacji

### Q1: Jak weryfikujemy ze PID dziala poprawnie?

| Option | Description | Selected |
|--------|-------------|----------|
| Test empiryczny z logami | Uruchom run_test_tracker.py, obserwuj HUD + logi PID | ✓ |
| Structured test scenario | Konkretny scenariusz krok po kroku | |
| Automatyczny test z logow | Parse logow, sprawdz konwergencje | |

**User's choice:** Test empiryczny z logami
**Notes:** Logi PID per-tick z Phase 9 daja wystarczajace dane

### Q2: Czy logi PID per-tick z Phase 9 sa wystarczajace?

| Option | Description | Selected |
|--------|-------------|----------|
| Wystarczajace | Phase 9 format kompaktowy, uruchomie z DEBUG | ✓ |
| Dodac INFO summary | DEBUG per-tick + INFO co N klatek | |
| You decide | Claude zdecyduje | |

**User's choice:** Wystarczajace

### Q3: Jak uruchomisz test z DEBUG?

| Option | Description | Selected |
|--------|-------------|----------|
| Wiem jak | Sam ustawie logging.DEBUG | |
| Dodac flag --debug | Argument CLI do run_test_tracker.py | ✓ |
| Domyslnie DEBUG w TRACKING | Auto-switch na DEBUG w TRACKING | |

**User's choice:** Dodac flag --debug

---

## Reakcja na failure

### Q1: Co robimy gdy PID nie konwerguje?

| Option | Description | Selected |
|--------|-------------|----------|
| Diagnoza + fix w tej fazie | Bledy logiki napraw tu, gains locked | ✓ |
| Tylko diagnoza, fix osobno | Zbierz dane, fix w 12.1 | |
| Fix gains jesli trzeba | Overrule Out of Scope | |

**User's choice:** Diagnoza + fix w tej fazie

### Q2: Jakie bledy sa dopuszczalne do naprawy?

| Option | Description | Selected |
|--------|-------------|----------|
| Bledy znaku i wiring | Zly znak, bledna os, brakujacy call | ✓ |
| Bledy znaku + output limit | Jak wyzej + PID_OUTPUT_LIMIT | |
| Wszystko oprocz gains | Kazda zmiana oprocz Kp/Ki/Kd | |

**User's choice:** Bledy znaku i wiring

---

## Scope tilt freeze

### Q1: Tilt freeze — scope Phase 12?

| Option | Description | Selected |
|--------|-------------|----------|
| Tak, core scope | PID-04 wymaga tilt | |
| Diagnoza tak, fix warunkowo | Zbadaj, napraw jesli blad znaku | |
| Osobna faza | Tilt freeze to osobny bug fix | ✓ |

**User's choice:** Osobna faza

### Q2: Jak Phase 12 waliduje PID-04 bez tilt fix?

| Option | Description | Selected |
|--------|-------------|----------|
| PID-04 przechodzi jesli error niezerowy | Software path validated | ✓ |
| PID-04 wymaga fizycznej reakcji | Phase 12 incomplete na PID-04 | |
| Przenies PID-04 do tilt-fix | PID-04 w osobnej fazie | |

**User's choice:** PID-04 przechodzi jesli error jest niezerowy

---

## Claude's Discretion

- Format flagi --debug (argparse vs sys.argv)
- Kolejnosc sprawdzen w walidacji

## Deferred Ideas

- Tilt freeze fix — osobna faza
- Tuning gains (Kp/Ki/Kd) — po zebraniu danych z logow
- Automatyczny test konwergencji z parsowania logow
