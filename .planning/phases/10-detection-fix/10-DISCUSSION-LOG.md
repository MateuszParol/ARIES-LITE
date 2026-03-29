# Phase 10: Detection Fix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 10-detection-fix
**Areas discussed:** Parametry HAAR, Streak filter tuning, Synchronizacja z vision.py

---

## Parametry HAAR

| Option | Description | Selected |
|--------|-------------|----------|
| minSize=(40,40), minNeighbors=4 | Rekomendacja z research — detekcja 40-100cm, lekkie odchylenie glowy OK | ✓ |
| minSize=(30,30), minNeighbors=3 | Bardzo permisywne — max zasieg, ale wiecej false positives | |
| minSize=(50,50), minNeighbors=5 | Kompromis — mniejszy zasieg ale mniej false positives | |

**User's choice:** minSize=(40,40), minNeighbors=4
**Notes:** Zgodne z rekomendacja research. Streak filter (3) zapewnia dodatkowa filtracje.

---

## Streak filter tuning

| Option | Description | Selected |
|--------|-------------|----------|
| Zostaw 3 | 3 kolejne klatki = ~100ms przy 30fps. Wystarczajacy filtr | ✓ |
| Podnies do 5 | Wieksze bezpieczenstwo ~170ms — ale wolniejsza reakcja | |
| Obniz do 2 | Szybsza reakcja ~66ms — ale ryzyko false positive | |

**User's choice:** Zostaw 3
**Notes:** Brak zmian w streak filter — research potwierdza wystarczajaca filtracje.

---

## Synchronizacja z vision.py

| Option | Description | Selected |
|--------|-------------|----------|
| Tylko test_tracker | Phase 10 dotyczy test trackera — vision.py ma inna architekture | ✓ |
| Oba pliki | Ujednolicic na (40,40)/4 — spojnosc | |
| Wyciagnij do config.py | Wspolne stale w config.py | |

**User's choice:** Tylko test_tracker
**Notes:** vision.py ma CSRT + dlib jako backup — inne trade-offy, nie ruszac.

---

## Claude's Discretion

- scaleFactor tuning jesli potrzebne
- Dodatkowe logging przy zmianie parametrow

## Deferred Ideas

None
