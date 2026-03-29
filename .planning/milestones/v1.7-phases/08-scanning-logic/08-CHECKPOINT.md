---
phase: 8
plan: 08-01
status: awaiting_hardware_verification
commit: 4d623cb
created: 2026-03-27
---

# Phase 8 — Checkpoint: Hardware Verification

Kod wdrożony (commit `4d623cb`), czeka na fizyczny test na RPi4.

## Co zostało zaimplementowane

**Plik:** `src/modes/test_tracker.py`

**SCAN-01 — eliminacja skoku serwa przy TRACKING→SCANNING:**
- `self._scan_phase_offset: float = 0.0` dodany do `MaszynaStanow.__init__`
- W `_przejdz_do()` przy `STATE_SCANNING` entry: `_scan_phase_offset = math.asin(max(-1.0, min(1.0, pan / SCAN_AMPLITUDE)))`
- W `_skanuj()` sinusoida: `+ self._scan_phase_offset` w argumencie `math.sin()`

**SCAN-02 — pełny streak po TARGET_LOST:**
- `resetuj_streak()` przeniesiony z warunku `STATE_SCANNING entry` → `STATE_TARGET_LOST entry`

---

## Jak przetestować

```
python3 run_test_tracker.py
```

**Test SCAN-01 (brak skoku serwa):**
1. Pokaż twarz → poczekaj na TRACKING (HUD: "TRACKING")
2. Przesuń twarz na bok — servo podąża daleko od centrum
3. Zakryj twarz na ~2s → TARGET_LOST → SCANNING
4. Obserwuj pan servo: powinno wznowić sinusoidę **bez widocznego skoku**

**Test SCAN-02 (wymagany pełny streak):**
1. Pokaż twarz → poczekaj na TRACKING
2. Zakryj twarz → poczekaj na TARGET_LOST (HUD: "TARGET_LOST")
3. Pokaż twarz na 1-2 klatki, potem zakryj
4. HUD **NIE powinien** wejść w TRACKING — wymaga pełnych 3 kolejnych klatek

---

## Jak wznowić sesję

Po przetestowaniu uruchom nową sesję i napisz jedną z poniższych opcji:

### Gdy testy przeszły
```
/gsd:execute-phase 8
```
Potem wpisz `approved` na checkpoint.

### Gdy coś nie działa
Opisz zaobserwowane zachowanie, np.:
- "SCAN-01: servo nadal skacze przy powrocie do skanowania"
- "SCAN-02: wchodzi w TRACKING po 2 klatkach zamiast 3"

Wklej opis jako odpowiedź na checkpoint po uruchomieniu `/gsd:execute-phase 8`.
