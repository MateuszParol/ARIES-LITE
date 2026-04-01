# Phase 25: RTC DS1307 Izolowana Integracja - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 25-rtc-ds1307-izolowana-integracja
**Areas discussed:** Fizyczne podlaczenie I2C, Wyswietlanie czasu na LCD, Fallback bez RTC, Klasa RTC w strukturze OOP

---

## Fizyczne podlaczenie I2C

| Option | Description | Selected |
|--------|-------------|----------|
| Kable jumper | A4→SDA, A5→SCL — najpierw sprawdzamy bez mechanicznych problemow | |
| Shield osadzony + cynowanie | Cynujesz szpilki A4/A5 przed osadzeniem | |
| Shield osadzony bez cynowania | Probujez bez cynowania | |

**User's choice:** Other — "shield jest oficjalny i jest osadzony na gold pinach stabilnie bez cynowania bo nie ma takiej potrzeby"
**Notes:** Pitfall 2 z research nie dotyczy tego shielda — gold piny zapewniaja stabilny kontakt.

### Follow-up: I2C scanner

| Option | Description | Selected |
|--------|-------------|----------|
| Tak, osobny sketch | Najpierw flash I2C scanner — potwierdza 0x68 | ✓ |
| Nie, od razu RTClib | rtc.begin() sam sprawdzi polaczenie | |

**User's choice:** Tak, osobny sketch
**Notes:** I2C scanner jako pierwszy task eliminuje zagadke hardware vs software.

---

## Wyswietlanie czasu na LCD

| Option | Description | Selected |
|--------|-------------|----------|
| Bootscreen + wiersz 1 cyklicznie | Przelaczanie co 3s miedzy bledami a czasem | |
| Tylko bootscreen | Bootscreen pokazuje czas, potem standardowy widok | ✓ |
| Zastap wiersz 1 na stale | HH:MM:SS zamiast bledow Bx/By | |

**User's choice:** Tylko bootscreen
**Notes:** Minimalny wplyw na istniejacy kod lcd_krok().

---

## Fallback bez RTC

| Option | Description | Selected |
|--------|-------------|----------|
| millis() fallback + warning | setup() nie zawiesza sie, flaga rtc_dostepne=false | |
| Zablokuj start | System nie startuje bez RTC — buzzer alarm + LCD error | ✓ |
| Ignoruj cicho | RTClib zwroci domyslny czas 2000-01-01 | |

**User's choice:** Zablokuj start
**Notes:** RTC jest wymagany, bez niego system nie startuje. Wymaga fizycznego resetu po naprawie.

---

## Klasa RTC w strukturze OOP

| Option | Description | Selected |
|--------|-------------|----------|
| Nowa klasa ZegarRTC | Osobna klasa, HMI i DataLogger dostaja referencje | ✓ |
| Rozszerz klase HMI | RTC jako pole HMI | |
| Bez klasy — funkcje globalne | Wire.begin() + rtc.begin() w setup() | |

**User's choice:** Nowa klasa ZegarRTC
**Notes:** Spojne z istniejacym OOP (ServoPID, HMI, MaszynaStanow).

### Follow-up: Kolejnosc inicjalizacji

| Option | Description | Selected |
|--------|-------------|----------|
| Po HMI, przed serwami | Serial→pinMode→HMI→Wire+RTC→Soft Start→Serwa | ✓ |
| Przed HMI | Wire+RTC jako pierwsze po Serial | |
| Claude's Discretion | Researcher/planner decyduja | |

**User's choice:** Po HMI, przed serwami
**Notes:** RTC init po LCD zeby bootscreen mogl pokazac czas lub "RTC FAIL".

---

## Claude's Discretion

- Format czasu na bootscreen (HH:MM:SS vs HH:MM)
- Czy rtc.adjust() wywolywac przy pierwszym uruchomieniu
- Nazewnictwo metod klasy ZegarRTC
- Czas wyswietlania bootscreen
- Walidacja czasu — definicja "niepoprawny"

## Deferred Ideas

None — discussion stayed within phase scope.
