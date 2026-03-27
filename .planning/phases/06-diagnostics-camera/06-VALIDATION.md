---
phase: 6
slug: diagnostics-camera
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — empirical verification only (CLAUDE.md: "no unit tests or linting tools configured") |
| **Config file** | None |
| **Quick run command** | `python3 run_test_tracker.py` (na hardware RPi4) |
| **Full suite command** | `python3 run_test_tracker.py` (to samo — jeden punkt wejścia) |
| **Estimated runtime** | ~10 sekund obserwacji po starcie |

---

## Sampling Rate

- **After every task commit:** Uruchom `python3 run_test_tracker.py` na RPi, obserwuj terminal i podgląd wideo przez 10 sekund
- **After every plan wave:** To samo — jedno uruchomienie weryfikuje wszystkie trzy wymagania jednocześnie
- **Before `/gsd:verify-work`:** Wszystkie cztery SUCCESS CRITERIA potwierdzone wizualnie i w terminalu
- **Max feedback latency:** ~15 sekund (start + 2s warm-up + 10s obserwacji)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Verification Method | Status |
|---------|------|------|-------------|-----------|---------------------|--------|
| 06-01-01 | 01 | 1 | DIAG-01 | manual | Terminal: `grep "Clamp"` podczas ruchu serwa poza limit | ⬜ pending |
| 06-01-02 | 01 | 1 | CAM-01 | manual | Terminal: INFO "Czekam na stabilizację AWB" → INFO "ColourGains zablokowane" | ⬜ pending |
| 06-01-03 | 01 | 1 | CAM-01 | manual | Wizualnie: neutralne kolory skóry w ciągu 3 sekund od startu | ⬜ pending |
| 06-01-04 | 01 | 1 | CAM-02 | manual | Code review: gałąź fallback `AWB_FALLBACK_GAINS` obecna + WARNING log gdy gains=None | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — istniejąca infrastruktura pokrywa wszystkie wymagania fazy. Weryfikacja jest empiryczna zgodnie z CLAUDE.md.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WARNING w terminalu gdy set_angles() otrzymuje wartość poza limitem | DIAG-01 | Brak frameworku testowego; wymaga hardware RPi | Ustaw twarz blisko krawędzi kadru (lub tymczasowo zmień SCAN_AMPLITUDE > 60); szukaj "Clamp pan" / "Clamp tilt" w terminalu |
| Brak niebieskiej dominanty po starcie (≤ 3s) | CAM-01 | Wymaga hardware RPi z kamerą IMX219 | Obserwuj podgląd wideo — klatki mogą być niebieskie przez pierwsze ~2s, potem neutralne |
| INFO logi AWB warm-up w terminalu | CAM-01 | Wymaga RPi | Terminal musi pokazać "Czekam na stabilizację AWB (2s)..." następnie "ColourGains zablokowane: (R=X.XX, B=X.XX)" |
| Fallback (2.5, 1.9) bez crasha gdy ColourGains=None | CAM-02 | Symulacja wymaga modyfikacji kodu | Code review: potwierdź gałąź `if gains is None:` z WARNING logiem i `AWB_FALLBACK_GAINS`; opcjonalnie tymczasowo wymuś `gains = None` dla testu |

---

## Validation Sign-Off

- [ ] Wszystkie zadania mają metodę weryfikacji (manual lub automated)
- [ ] Ciągłość próbkowania: brak 3 kolejnych tasków bez weryfikacji
- [ ] Wave 0: nie wymagana (brak brakujących plików testowych)
- [ ] Brak flag watch-mode
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` ustawione w frontmatter po ukończeniu

**Approval:** pending
