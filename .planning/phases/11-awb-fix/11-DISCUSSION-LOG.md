# Phase 11: AWB Fix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 11-awb-fix
**Areas discussed:** Strategia AWB lock, Wartosci fallback gains, Obsluga bledow AWB

---

## Strategia AWB Lock

| Option | Description | Selected |
|--------|-------------|----------|
| Dwa etapy | Fallback w create_video_configuration + re-lock po warm-up | ✓ |
| Tylko configure-time | Tylko fallback, nigdy auto-AWB converged values | |
| Tylko post-start | Obecne podejscie — 2-3s blue tint | |

**User's choice:** Dwa etapy
**Notes:** Research PITFALLS.md potwierdza to jako safest approach across Bookworm versions.

---

## Wartosci Fallback Gains

| Option | Description | Selected |
|--------|-------------|----------|
| (1.0, 1.0) neutralne | Brak wzmocnienia, minimalna ingerencja | ✓ |
| (2.0, 1.7) indoor LED | Typowe gains IMX219 indoor | |
| (1.5, 1.5) kompromis | Srednia wartosc | |

**User's choice:** (1.0, 1.0) neutralne
**Notes:** Uzytkownik wczesniej ustawil ta wartosc w kodzie. Konsekwentny wybor.

---

## Obsluga Bledow AWB

| Option | Description | Selected |
|--------|-------------|----------|
| Fallback + warning | Uzyj fallback, zaloguj WARNING. Nie crashuj | ✓ |
| Retry 3x z sleep | Probuj 3 razy co 0.5s zanim fallback | |
| Fallback bez warning | Cicho uzyj fallback | |

**User's choice:** Fallback + warning
**Notes:** Prostota — jeden fallback, jedno warning, zero crash risk.

---

## Claude's Discretion

- Czas warm-up (2s) — dostosowanie jesli potrzebne
- Format komunikatow logowania

## Deferred Ideas

None
