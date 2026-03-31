# Phase 21: Wizja RPi MediaPipe - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 21-wizja-rpi-mediapipe
**Areas discussed:** Architektura pi_brain.py, AWB fix + kamera, Sticky tracking, Heartbeat + timing

---

## Architektura pi_brain.py

### Q1: Jak zorganizowac kod pi_brain.py?

| Option | Description | Selected |
|--------|-------------|----------|
| Jeden plik pi_brain.py | Cala logika w jednym pliku — Picamera2, MediaPipe, petla, serial TX. Prosty jak test_tracker.py. | |
| Moduly w src/vision/ | Osobne pliki: camera.py, detector.py, brain.py. Wieksza separacja. | ✓ |
| Claude decyduje | Pozwol Claude wybrac. | |

**User's choice:** Moduly w src/vision/
**Notes:** Uzytkownik preferuje modularna organizacje kodu.

### Q2: Jak powinna wygladac glowna petla sterowania?

| Option | Description | Selected |
|--------|-------------|----------|
| Synchroniczna petla while | Prosta petla: grab→detect→track→send→repeat. Jak test_tracker.py. | |
| Callback z Picamera2 | Picamera2 callbacki wywoluja logike detekcji. | |
| Asyncio event loop | Asynchroniczna petla z coroutines. | |

**User's choice:** "Wybierz samodzielnie zgodnie ze standardami na 2026 rok" (Other — Claude's Discretion)
**Notes:** Uzytkownik ufa Claude w wyborze najnowszego podejscia.

### Q3: Czy pi_brain.py powinien miec podglad wideo?

| Option | Description | Selected |
|--------|-------------|----------|
| Tak, z HUD jak test_tracker | cv2.imshow z bbox, bledem, trybem. Headless fallback. | ✓ |
| Tylko logging, bez okna | Brak podgladu — feedback przez logi. | |
| Claude decyduje | Pozwol Claude zdecydowac. | |

**User's choice:** Tak, z HUD jak test_tracker
**Notes:** Podglad wizualny przydatny do kalibracji w Phase 23.

---

## AWB fix + kamera

### Q4: Jaka strategia naprawy kolorow AWB?

| Option | Description | Selected |
|--------|-------------|----------|
| Sleep 2s + capture_metadata | Sprawdzony wzorzec z Phase 11. | |
| Stale ColourGains hardcoded | Empiryczne wartosci bez dynamicznego odczytu. | |
| Claude decyduje | Researcher zbada optymalne podejscie. | ✓ |

**User's choice:** Claude decyduje
**Notes:** Uzytkownik ufa Claude w wyborze najlepszej strategii AWB.

### Q5: Jaka rozdzielczosc Picamera2?

| Option | Description | Selected |
|--------|-------------|----------|
| 320x240 jak test_tracker | Ta sama co legacy, skaluje sie z protokolem. | |
| 640x480 wyzsza jakosc | Wieksza dokladnosc, wolniejsze przetwarzanie. | |
| Claude decyduje | Researcher zbada optymalna rozdzielczosc. | ✓ |

**User's choice:** Claude decyduje
**Notes:** Uzytkownik ufa Claude w wyborze optymalnej rozdzielczosci.

---

## Sticky tracking

### Q6: Jak wybierac twarz do sledzenia?

| Option | Description | Selected |
|--------|-------------|----------|
| Najwieksza twarz (bbox area) | Zawsze sledz najwieksza. Histereza przy zblizonych rozmiarach. | |
| Najblizsza do centrum | Minimalizuje ruch serw. | |
| Claude decyduje | Researcher zbada najlepsza strategie. | ✓ |

**User's choice:** Claude decyduje
**Notes:** Uzytkownik ufa Claude w wyborze strategii sticky tracking.

---

## Heartbeat + timing

### Q7: Jaki tryb (mode) wysylac przy braku detekcji twarzy?

| Option | Description | Selected |
|--------|-------------|----------|
| SCAN (mode=1) | Arduino skanuje autonomicznie. Aktywne szukanie. | ✓ |
| IDLE (mode=0) | Arduino stoi nieruchomo. | |
| Claude decyduje | Researcher zbada optymalne zachowanie. | |

**User's choice:** SCAN (mode=1)
**Notes:** Brak twarzy = aktywne skanowanie, nie pasywne czekanie.

### Q8: Jak realizowac heartbeat co 200ms?

| Option | Description | Selected |
|--------|-------------|----------|
| W glownej petli z millis check | Sprawdzaj interwal w glownej petli. Prostsze. | |
| Osobny watek heartbeat | Daemon thread gwarantuje timing. | |
| Claude decyduje | Researcher zbada najlepsza strategie. | ✓ |

**User's choice:** Claude decyduje
**Notes:** Uzytkownik ufa Claude w wyborze mechanizmu heartbeat.

---

## Claude's Discretion

- Glowna petla sterowania (Q2)
- Strategia AWB fix (Q4)
- Rozdzielczosc Picamera2 (Q5)
- Strategia sticky tracking (Q6)
- Mechanizm heartbeat (Q8)

## Deferred Ideas

None — discussion stayed within phase scope.
