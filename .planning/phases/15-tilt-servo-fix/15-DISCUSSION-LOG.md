# Phase 15: PID Tracking Fix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 15-tilt-servo-fix
**Areas discussed:** Strategia tuningu PID, Metoda weryfikacji, Podejście do strojenia

---

## Strategia tuningu PID

| Option | Description | Selected |
|--------|-------------|----------|
| Tylko OUTPUT_LIMIT | Zmniejsz OUTPUT_LIMIT z 5.0 na 3.0°/tick. Gainy bez zmian — PID nadal responsywny, ale fizycznie ograniczony. Najprostsza zmiana, łatwo odwracalna. | ✓ |
| Gainy + OUTPUT_LIMIT | Redukuj KP (2.0→1.0), KI (0.1→0.05), KD (0.5→0.3) ORAZ OUTPUT_LIMIT 5→3. Większa zmiana, potencjalnie wolniejsza konwergencja. | |
| Tylko gainy PID | Zostaw OUTPUT_LIMIT=5.0, zmniejsz KP/KI/KD. Zachowuje pełen zakres ruchu ale łagodniejsza reakcja. | |
| Adaptive (dwa zestawy) | Niskie gainy przez pierwsze 1-2s po wejściu w TRACKING, potem normalne. Bardziej złożone, więcej kodu. | |

**User's choice:** Tylko OUTPUT_LIMIT (Rekomendowane)
**Notes:** Reset PID już istnieje w kodzie (Phase 14). Problem to agresywność reakcji, nie brak resetu.

---

## Wartość OUTPUT_LIMIT

| Option | Description | Selected |
|--------|-------------|----------|
| 3.0°/tick | Roadmap target. Maksymalnie 300°/s — wciąż szybka konwergencja, ale bez szarpnięć do limitów. | ✓ |
| 2.0°/tick | Bardziej konserwatywne. Wolniejsza reakcja, ale płynniejszy ruch. Może wymagać dłuższego czasu konwergencji. | |
| Claude zdecyduje | Researcher zbada optymalną wartość na podstawie analizy dynamiki serw MG-90S i obecnych gainów. | |

**User's choice:** 3.0°/tick (Rekomendowane)
**Notes:** —

---

## Metoda weryfikacji

| Option | Description | Selected |
|--------|-------------|----------|
| Logi SD + obserwacja | Uruchom system, wejdź w TRACKING, przejrzyj CSV z SD — szukaj: pan/tilt nie dociągają do ±60/±30 w pierwszych 2s, error maleje. Plus wizualne potwierdzenie. | ✓ |
| Tylko obserwacja wizualna | Prostsze — patrz czy serwa nie uciekają do limitów i czy twarz się centruje. Mniej precyzyjne, ale szybsze. | |
| Skrypt testowy | Dedykowany skrypt wysyłający syntetyczne ramki z error_x/y i mierzący odpowiedź serw. Deterministyczny, ale wymaga dodatkowego kodu. | |

**User's choice:** Logi SD + obserwacja (Rekomendowane)
**Notes:** DataLogger CSV już dostępny (LOG-01) — naturalne źródło danych bez dodatkowego kodu.

---

## Podejście do strojenia

| Option | Description | Selected |
|--------|-------------|----------|
| Max 2-3 iteracje | Zacznij od 3.0, jeśli logi SD pokażą że konwergencja za wolna lub wciąż clampuje — popraw. Max 2-3 próby z analizą logów między nimi. | ✓ |
| Jednorazowa zmiana | Zmień na 3.0 i zamknij fazę. Jeśli nie działa — ew. nowa faza/fix później. | |
| Nieograniczone strojenie | Iteruj aż wszystkie 3 success criteria spełnione. Może wymagać zmiany gainów jeśli sam limit nie wystarczy. | |

**User's choice:** Tak, max 2-3 iteracje (Rekomendowane)
**Notes:** —

---

## Claude's Discretion

- Kolejność kroków w planie (zmiana stałej → kompilacja → upload → test → analiza logów)
- Kryterium akceptacji iteracji na podstawie logów CSV
- Ewentualna korekta w drugiej/trzeciej iteracji

## Deferred Ideas

None — discussion stayed within phase scope
