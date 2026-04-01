# Phase 24: Migracja Pinow i Kompilacja Bazowa - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 24-migracja-pinow-i-kompilacja-bazowa
**Areas discussed:** Serial startup R4, Soft Start strategia, Plik firmware, dtostrf zamiennik

---

## Serial startup R4

| Option | Description | Selected |
|--------|-------------|----------|
| Usun calkowicie | R4 nie potrzebuje CDC wait. Serial.begin() wystarczy. Najczystsze. | |
| Zostaw krotki timeout | while(!Serial && <500ms) jako safety net. Bezpieczniejsze. | |
| Ty zdecyduj | Claude wybierze najlepsza opcje na podstawie researchu R4 | ✓ |

**User's choice:** Ty zdecyduj
**Notes:** Claude's Discretion — research R4 ESP32-S3 bridge behavior zweryfikuje czy Serial wait potrzebny

---

## Soft Start strategia

| Option | Description | Selected |
|--------|-------------|----------|
| 500ms delay PRZED rampa | delay(500) na stabilizacje zasilania, potem rampa 1000ms. Lacznie ~1.5s. | ✓ |
| Skroc rampe do 500ms | Rampa 500→1500µs w 25 krokow po 20ms = 500ms. Szybszy start. | |
| Ty zdecyduj | Claude dobierze strategie na podstawie specyfiki zasilacza 6V | |

**User's choice:** 500ms delay PRZED rampa
**Notes:** Jednoznaczna decyzja — delay(500) na stabilizacje napiecia zasilacza 6V, nastepnie pelna rampa 1000ms

---

## Plik firmware

| Option | Description | Selected |
|--------|-------------|----------|
| Rozbic na .h (Zalecane) | HMI.h, ServoPID.h, MaszynaStanow.h + glowny .ino. Czytelnosc. | |
| Jeden plik .ino | Zachowaj obecna strukture. Prostsze, ale ~800+ linii po DataLogger. | |
| Ty zdecyduj | Claude wybierze na podstawie rozmiaru koncowego kodu | ✓ |

**User's choice:** Ty zdecyduj
**Notes:** Claude's Discretion — uwzglednic ze Fazy 25-27 dodaja RTC, SD, DataLogger (rosnacy rozmiar)

---

## dtostrf zamiennik

| Option | Description | Selected |
|--------|-------------|----------|
| snprintf z int cast | snprintf(buf, 5, "%4d", (int)kat_pan) — prostsze, zero precision | |
| snprintf z %.0f | snprintf(buf, 5, "%.0f", kat_pan) — blizsze oryginalowi | |
| Ty zdecyduj | Claude wybierze najlepsza opcje kompatybilna z R4 | ✓ |

**User's choice:** Ty zdecyduj
**Notes:** Claude's Discretion — precision=0 w oryginale upraszcza zamiane

---

## Claude's Discretion

- Serial startup behavior na Uno R4 WiFi (usunac vs skrocic CDC wait)
- dtostrf zamiennik (snprintf int cast vs %.0f)
- Struktura plikow firmware (.ino vs .h/.cpp split)

## Deferred Ideas

None — discussion stayed within phase scope
