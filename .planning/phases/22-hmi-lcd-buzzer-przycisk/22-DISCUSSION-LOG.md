# Phase 22: HMI LCD + Buzzer + Przycisk - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 22-hmi-lcd-buzzer-przycisk
**Areas discussed:** LCD layout + piny, Buzzer zachowanie, Przycisk logika, Integracja z petla

---

## LCD layout + piny

### Q1: Piny LCD 1602

| Option | Description | Selected |
|--------|-------------|----------|
| RS=2, EN=3, D4=4, D5=5, D6=6, D7=11 | Omija D7/D8/D9/D10. | |
| I2C backpack (A4/A5) | 2 piny, wymaga LiquidCrystal_I2C. | |
| Claude decyduje | Researcher zbada optymalne mapowanie. | ✓ |

**User's choice:** Claude decyduje

### Q2: Layout LCD 2x16

| Option | Description | Selected |
|--------|-------------|----------|
| Row 0: tryb, Row 1: blad X/Y | Czytelne, zwiezle. | |
| Row 0: tryb + FPS, Row 1: katy serw | Bardziej diagnostyczne. | ✓ |
| Claude decyduje | | |

**User's choice:** Row 0: tryb + FPS, Row 1: katy serw

---

## Buzzer zachowanie

### Q3: Dzwieki buzzera

| Option | Description | Selected |
|--------|-------------|----------|
| Tylko przy TRACK (target lock) | 100ms beep ~1kHz. Per HMI-02. | ✓ |
| Rozne tony per stan | Bogatsza informacja, glosniejsze. | |
| Claude decyduje | | |

**User's choice:** Tylko przy TRACK

---

## Przycisk logika

### Q4: Co robi przycisk D7

| Option | Description | Selected |
|--------|-------------|----------|
| Abort TRACK → SCAN only | Aktywny tylko w TRACK. Per HMI-03. | ✓ |
| Toggle trybow | Cyklicznie przelacza. | |
| Claude decyduje | | |

**User's choice:** Abort TRACK → SCAN only

---

## Integracja z petla

### Q5: Czestotliwosc odswiezania LCD

| Option | Description | Selected |
|--------|-------------|----------|
| Max 5 Hz (co 200ms) via millis() | Nie blokuje PID. Per HMI-01. | ✓ |
| Co iteracje loop() | Max speed, wiecej obciazenia. | |
| Claude decyduje | | |

**User's choice:** Max 5 Hz via millis()

---

## Claude's Discretion

- Mapowanie pinow LCD (Q1)

## Deferred Ideas

None.
