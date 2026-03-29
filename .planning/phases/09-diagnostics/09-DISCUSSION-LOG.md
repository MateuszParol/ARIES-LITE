# Phase 9: Diagnostics - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 09-diagnostics
**Areas discussed:** Mock mode indicator, PID logging format, AWB diagnostics

---

## Mock Mode Indicator

| Option | Description | Selected |
|--------|-------------|----------|
| HUD overlay [MOCK] | Czerwony tekst [MOCK] w rogu HUD — natychmiast widoczny | ✓ |
| Log WARNING + HUD | Oba: WARNING w terminalu + [MOCK] na HUD | |
| Tylko log | WARNING w terminalu — bez zmian w HUD | |

**User's choice:** HUD overlay [MOCK] (Recommended)
**Notes:** Operator musi widzieć mock mode bez czytania terminala

---

## PID Logging Format

| Option | Description | Selected |
|--------|-------------|----------|
| Co tick, kompaktowy | PAN err=+12.3 P=1.2 I=0.1 D=-0.3 out=+1.0 \| TILT ... | ✓ |
| Co 10 ticków | Mniej spamu, ale można przegapić spike | |
| Claude zdecyduje | Claude wybierze format | |

**User's choice:** Co tick, kompaktowy (Recommended)
**Notes:** Użyć simple-pid.components property

---

## AWB Diagnostyka

| Option | Description | Selected |
|--------|-------------|----------|
| Weryfikacja gains | Re-read metadata po set_controls — wykrywa silent failure | ✓ |
| Pełna metadata | Loguj też ExposureTime, AnalogueGain, Lux | |
| Claude zdecyduje | Claude wybierze co logować | |

**User's choice:** Tylko weryfikacja gains (Recommended)
**Notes:** Porównanie wymaganych vs rzeczywistych gains

---

## Claude's Discretion

- Log level dla PID per-tick (debug vs info)
- Pozycja i kolor [MOCK] tekstu na HUD

## Deferred Ideas

None
