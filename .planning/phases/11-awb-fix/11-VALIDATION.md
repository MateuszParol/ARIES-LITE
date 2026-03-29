---
phase: 11
slug: awb-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none (empirical verification only) |
| **Config file** | none |
| **Quick run command** | `python3 run_test_tracker.py` |
| **Full suite command** | `python3 run_test_tracker.py` (visual + log inspection) |
| **Estimated runtime** | ~10 seconds (startup + first frames) |

---

## Sampling Rate

- **After every task commit:** Run `python3 run_test_tracker.py` — sprawdz logi startowe
- **After every plan wave:** Run `python3 run_test_tracker.py` (visual + log inspection)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | AWB-01 | manual/log | `python3 run_test_tracker.py` + log grep `ColourGains` | N/A | ⬜ pending |
| 11-01-02 | 01 | 1 | AWB-01 | manual/log | `python3 run_test_tracker.py` + log grep `fallback` | N/A | ⬜ pending |
| 11-01-03 | 01 | 1 | AWB-02 | manual/visual | `python3 run_test_tracker.py` — visual check first frame | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. `run_test_tracker.py` provides startup log output and visual frame output for both AWB-01 and AWB-02 verification.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Brak blue tint od pierwszej klatki | AWB-02 | Visual — kolor skory nie da sie zweryfikowac automatycznie | 1. Uruchom `python3 run_test_tracker.py` 2. Obserwuj pierwsza klatke — skora powinna wygladac naturalnie 3. Brak niebieskiego odcienia |
| ColourGains niezerowe w logach | AWB-01 | Log inspection — grep wystarczy | 1. Uruchom `python3 run_test_tracker.py` 2. Grep log: `ColourGains zablokowane` 3. Wartosci R i B > 0.0 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
