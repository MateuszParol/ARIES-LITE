# Phase 16: Tilt Scan Fix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 16-camera-color-fix (Tilt Scan Fix)
**Areas discussed:** Zakres fazy, Phase-offset continuity, Parametry Lissajous, Weryfikacja empiryczna

---

## Zakres fazy — co jest do zrobienia?

| Option | Description | Selected |
|--------|-------------|----------|
| Juz potwierdzone | SC #1/#2 widoczne na zywo, faza tylko SC #3 | |
| Wymagaja weryfikacji | Kod jest, ale nie testowane na sprzecie | ✓ |
| Nie jestem pewien/pewna | Nie pamietam, trzeba sprawdzic | |

**User's choice:** Wymagaja weryfikacji
**Notes:** Firmware ma Lissajous 2D ale nie potwierdzono empirycznie na sprzecie.

| Option | Description | Selected |
|--------|-------------|----------|
| Tak, to caly zakres | Weryfikacja + phase-offset fix | |
| Dodaj strojenie parametrow | Dostrojenie amplitud/czestotliwosci jesli FOV nieoptymalne | ✓ |
| Dodaj log skanowania | Dodatkowy log CSV z pozycjami serw | |

**User's choice:** Dodaj strojenie parametrow
**Notes:** Zakres: weryfikacja SC #1/#2 + phase-offset fix SC #3 + ewentualne strojenie parametrow.

---

## Phase-offset continuity

| Option | Description | Selected |
|--------|-------------|----------|
| Oblicz t_offset (Rekomendowane) | arcsin z aktualnej pozycji, kontynuacja bez skoku | ✓ |
| Soft transition (rampa) | Interpolacja z aktualnej pozycji do sinusoidy | |
| Claude's Discretion | Researcher wybierze | |

**User's choice:** Oblicz t_offset
**Notes:** Arcsin z aktualnej pozycji serwa przy przejsciu do SKANOWANIE.

| Option | Description | Selected |
|--------|-------------|----------|
| Obie osie niezalezne | Osobny t_offset_pan i t_offset_tilt | ✓ |
| Wspolny t_offset z pan | Oblicz z dominujacej osi, maly skok na tilt | |
| Claude's Discretion | Researcher przeanalizuje tradeoff | |

**User's choice:** Obie osie niezalezne
**Notes:** Niezalezne t_offset dla kazdej osi — dokladniejsza kontynuacja, akceptowalne rozjechanie wzorca.

---

## Parametry Lissajous

| Option | Description | Selected |
|--------|-------------|----------|
| Obecne jako start | Zaczynaj od obecnych, dostrajaj empirycznie | ✓ |
| Zmniejsz amplitudy | 70° blisko limitu, mniejszy margines | |
| Zmien czestotliwosci | 0.05/0.073 Hz wolne, szybsze skanowanie | |

**User's choice:** Obecne jako start
**Notes:** AMP_PAN=70°, AMP_TILT=25°, FREQ_PAN=0.05, FREQ_TILT=0.073 jako punkt wyjscia.

| Option | Description | Selected |
|--------|-------------|----------|
| Max 2-3 iteracje, pokrycie FOV | Priorytet: max pokrycie pola widzenia | |
| Max 2-3 iteracje, plynnosc ruchu | Priorytet: brak szarpan | |
| Claude's Discretion | Researcher dobierze priorytet | ✓ |

**User's choice:** Claude's Discretion
**Notes:** Researcher oceni priorytet strojenia na podstawie charakterystyki serw MG-90S.

---

## Weryfikacja empiryczna

| Option | Description | Selected |
|--------|-------------|----------|
| Logi SD CSV + wizualne (Rekomendowane) | DataLogger loguje pan/tilt/stan, analiza CSV + obserwacja | ✓ |
| Tylko wizualne | Ocena golym okiem | |
| Logi SD + skrypt analizy | CSV + skrypt Python z wykresem Lissajous | |

**User's choice:** Logi SD CSV + wizualne
**Notes:** DataLogger juz loguje co 10 klatek — wystarczajace do weryfikacji.

| Option | Description | Selected |
|--------|-------------|----------|
| Max 5° na obu osiach | Niezauwazalny wizualnie | ✓ |
| Max 3° na obu osiach | Bardziej rygorystyczne | |
| Claude's Discretion | Researcher dobierze prog | |

**User's choice:** Max 5° na obu osiach
**Notes:** Prog akceptacji skoku przy przejsciu TARGET_LOST→SKANOWANIE: max 5° na kazdej osi.

---

## Claude's Discretion

- Priorytet strojenia parametrow Lissajous (pokrycie FOV vs plynnosc ruchu)
- Implementacja arcsin + kwadrant na Arduino (ograniczenia float)
- Kolejnosc krokow planu
- Kryterium konwergencji iteracji strojenia

## Deferred Ideas

None — dyskusja pozostala w zakresie fazy.
