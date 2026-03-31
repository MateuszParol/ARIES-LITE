# Phase 23: Integracja + Kalibracja - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 23-integracja-kalibracja
**Areas discussed:** Kalibracja kierunków serw, Modularność OOP, Weryfikacja end-to-end, Polskie nazewnictwo

---

## Kalibracja kierunków serw

### Metoda kalibracji

| Option | Description | Selected |
|--------|-------------|----------|
| Skrypt kalibracyjny (Rekomendowane) | Skrypt Python na RPi wysyła sekwencję testową: error_x=+50 i obserwujesz czy serwo jedzie w prawo. Deterministyczne, powtarzalne. | ✓ |
| Ręczna obserwacja z pi_brain.py | Odpalasz pełny system, stajesz po prawej stronie kadru i patrzysz czy kamera podąża. | |
| Claude decyduje | Researcher zbada najlepszą metodę kalibracji. | |

**User's choice:** Skrypt kalibracyjny
**Notes:** Brak dodatkowych uwag.

### Utrwalenie wyniku kalibracji

| Option | Description | Selected |
|--------|-------------|----------|
| #define w firmware (obecne) | PAN_INVERT=+1/-1 jako #define — zmiana wymaga rekompilacji. Już tak jest w Phase 20. | ✓ |
| EEPROM Arduino | Wartości w EEPROM — zmiana bez rekompilacji, ale większa złożoność. | |
| Claude decyduje | Researcher oceni trade-offy. | |

**User's choice:** #define w firmware (obecne)
**Notes:** Brak dodatkowych uwag.

---

## Modularność OOP (INT-04)

### Klasy RPi

| Option | Description | Selected |
|--------|-------------|----------|
| Zachowaj MozgRPi (Rekomendowane) | MozgRPi spełnia rolę VisionManager — nazwa po polsku spójna z konwencją nowego kodu. | ✓ |
| Zmień na VisionManager | Użyj dokładnie nazw z INT-04. Angielskie nazwy klas. | |
| Claude decyduje | Researcher zbada spójność nazewnictwa. | |

**User's choice:** Zachowaj MozgRPi
**Notes:** Brak dodatkowych uwag.

### Arduino OOP

| Option | Description | Selected |
|--------|-------------|----------|
| Tak — klasy C++ w .ino | Wyodrębnij ServoPID, MaszynaStanow itp. jako klasy w tym samym pliku .ino. | ✓ |
| Nie — proceduralne wystarczy | Firmware działa, jest czytelne. INT-04 dotyczy głównie strony RPi. | |
| Claude decyduje | Researcher oceni ryzyko refaktoru firmware. | |

**User's choice:** Tak — klasy C++ w .ino
**Notes:** Brak dodatkowych uwag.

---

## Weryfikacja end-to-end (INT-01)

### Metoda pomiaru latencji

| Option | Description | Selected |
|--------|-------------|----------|
| Logi timestamps (Rekomendowane) | RPi loguje czas wysłania ramki, Arduino loguje czas odbioru+PID. | |
| Skrypt pomiarowy round-trip | Dedykowany skrypt: RPi wysyła ramkę, mierzy czas do reakcji serwa. | |
| Claude decyduje | Researcher zbada najlepszą metodę pomiaru na Arduino Leonardo. | ✓ |

**User's choice:** Claude decyduje
**Notes:** Brak dodatkowych uwag.

### Scenariusz testowy E2E

| Option | Description | Selected |
|--------|-------------|----------|
| Checklist ręczny | Lista kroków: stań przed kamerą, idź w prawo, kucnij itd. PASS/FAIL. | |
| Skrypt automatyczny + ręczna obs. | Skrypt wysyła syntetyczne błędy + ręczny test z żywą twarzą. | |
| Claude decyduje | Researcher oceni możliwości automatyzacji testów na hardware. | ✓ |

**User's choice:** Claude decyduje
**Notes:** Brak dodatkowych uwag.

---

## Polskie nazewnictwo (INT-05)

### Zakres polonizacji

| Option | Description | Selected |
|--------|-------------|----------|
| Pełny refactor (Rekomendowane) | Wszystkie komentarze, zmienne, nazwy funkcji po polsku — nowy i istniejący kod. | ✓ |
| Tylko nowy kod + komentarze | Nowe komentarze po polsku, istniejące angielskie nazwy zostawiamy. | |
| Claude decyduje | Researcher oceni zakres zmian. | |

**User's choice:** Pełny refactor
**Notes:** Brak dodatkowych uwag.

### Nazwy techniczne

| Option | Description | Selected |
|--------|-------------|----------|
| Zachowaj angielskie (Rekomendowane) | PID, UART, GPIO, EEPROM, constrain, millis — po angielsku. Polskie tylko domenowe. | ✓ |
| Wszystko po polsku | Również PID→Regulator, GPIO→WejścieWyjście. Maksymalna spójność. | |
| Claude decyduje | Researcher oceni czytelność. | |

**User's choice:** Zachowaj angielskie
**Notes:** Brak dodatkowych uwag.

---

## Claude's Discretion

- Metoda pomiaru latencji end-to-end (logi, round-trip, inna)
- Scenariusz testowy E2E (checklist, skrypt, hybryda)

## Deferred Ideas

Brak — dyskusja pozostała w zakresie fazy.
