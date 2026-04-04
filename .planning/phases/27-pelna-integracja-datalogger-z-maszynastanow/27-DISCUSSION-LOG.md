# Phase 27: Pelna Integracja DataLogger z MaszynaStanow - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 27-pelna-integracja-datalogger-z-maszynastanow
**Areas discussed:** Logowanie zmian stanow, face_size i latency_ms, Format wpisu, Weryfikacja E2E

---

## Logowanie zmian stanow

### Ktore przejscia logowac?

| Option | Description | Selected |
|--------|-------------|----------|
| Wszystkie (BEZCZYNNOSC/SKANOWANIE/SLEDZENIE) | Pelny audit trail sesji | ✓ |
| Tylko SKANOWANIE↔SLEDZENIE | Interesujace dla analizy trackingu | |

**User's choice:** Wszystkie przejscia
**Notes:** —

### Mechanizm powiadamiania

| Option | Description | Selected |
|--------|-------------|----------|
| Bezposrednie wywolanie | MaszynaStanow wywoluje logger.loguj_zmiane() | |
| Flaga + poll | MaszynaStanow ustawia flage, DataLogger sprawdza w krok() | |
| Porownanie w loop() | loop() porownuje stan z poprzednia iteracja | |

**User's choice:** "ty zdecyduj"
**Notes:** Claude's Discretion — wybrac najprostszy sposob

---

## face_size i latency_ms

| Option | Description | Selected |
|--------|-------------|----------|
| face_size z ramki binarnej | uint8 bajt 6 ramki 8B od RPi | |
| latency_ms = czas petli loop() | millis() delta miedzy iteracjami | |
| latency_ms = czas reakcji PID | Od odebrania ramki do aktualizacji serw | |
| latency_ms = 0 | Zostawic placeholder | |

**User's choice:** "ty zadecyduj"
**Notes:** Claude's Discretion na oba

---

## Format wpisu zmiany stanu

| Option | Description | Selected |
|--------|-------------|----------|
| Ten sam format CSV | Zmiana stanu = zwykly wiersz z aktualnymi wartosciami | |
| Dedykowany wiersz z markerem | Dodatkowa kolumna event lub specjalny format | |
| Dwa pliki | Osobny log stanow, osobna telemetria | |

**User's choice:** "ty zadecyduj"
**Notes:** Claude's Discretion — wybrac co latwiej parsowac w Python/pandas

---

## Weryfikacja E2E

| Option | Description | Selected |
|--------|-------------|----------|
| Komenda serialowa | Zrzut ostatnich N wpisow bufora na Serial | ✓ |
| Tylko Serial logi | Logowac kazdy zapis na Serial (skrocony) | |
| Odlozyc weryfikacje | Czekac na fizyczny dostep do karty SD | |

**User's choice:** Komenda serialowa, 10 ostatnich wpisow
**Notes:** Umozliwia weryfikacje bez czytnika SD przez pyserial na RPi

---

## Claude's Discretion

- Mechanizm powiadamiania DataLogger o zmianie stanu
- Zrodlo face_size (udostepnienie z MaszynaStanow)
- Definicja latency_ms
- Format wiersza CSV dla zmiany stanu
- Trigger komendy serialowej (bajt/sekwencja)

## Deferred Ideas

None
