# Phase 26: SD Card + DataLogger CSV - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 26-sd-card-datalogger-csv
**Areas discussed:** Format i kolumny CSV, Strategia zapisu i buforowanie, Degradation bez karty SD, Nazewnictwo plików i rotacja

---

## Format i kolumny CSV

### Timestamp format

| Option | Description | Selected |
|--------|-------------|----------|
| Epoch sekundy | Unix timestamp jako uint32 — kompaktowy, łatwy do parsowania | ✓ |
| ISO HH:MM:SS | Czytelny czas bez daty (data w nazwie pliku) | |
| ISO pełny YYYY-MM-DD HH:MM:SS | Pełna data+czas — redundancja z nazwą pliku | |

**User's choice:** Epoch sekundy
**Notes:** Brak dodatkowych uwag

### Precyzja float

| Option | Description | Selected |
|--------|-------------|----------|
| Integer | Pan/tilt int, error int — snprintf %d, mniejszy rozmiar | ✓ |
| 1 miejsce po przecinku | Pan/tilt %.1f, error %.1f — więcej precyzji | |
| Ty zdecyduj | Claude dobierze na podstawie rozdzielczości danych | |

**User's choice:** Integer
**Notes:** Brak dodatkowych uwag

### Separator CSV

| Option | Description | Selected |
|--------|-------------|----------|
| Przecinek | Standard CSV — Python/pandas natywny | ✓ |
| Średnik | Polskie locale Excela otwiera double-click | |

**User's choice:** Przecinek
**Notes:** Brak dodatkowych uwag

---

## Strategia zapisu i buforowanie

### Częstotliwość logowania

| Option | Description | Selected |
|--------|-------------|----------|
| Co 10 klatek RPi | ~3 wpisy/sek. Zgodne z ARCHITECTURE.md | ✓ |
| Co 30 klatek RPi | ~1/s — mniejszy plik, gorsza rozdzielczość | |
| Każda klatka RPi | ~30/s — max rozdzielczość, obciążenie SPI | |

**User's choice:** Co 10 klatek RPi
**Notes:** Brak dodatkowych uwag

### Ring buffer vs bezpośredni zapis

| Option | Description | Selected |
|--------|-------------|----------|
| Ring buffer 50 wpisów | ~4KB RAM, flush co ~17s, chroni PID | ✓ |
| Bezpośredni zapis + flush co 50 | Bez bufora RAM, file.print() co wpis | |
| Ty zdecyduj | Claude dobierze po benchmarku | |

**User's choice:** Ring buffer 50 wpisów
**Notes:** Brak dodatkowych uwag

### Kiedy logować

| Option | Description | Selected |
|--------|-------------|----------|
| Tylko SLEDZENIE | Error/face_size mają sens tylko z twarzą | ✓ |
| Wszystkie stany | Pełen obraz ruchu serw, error=0 w SKANOWANIE | |
| Ty zdecyduj | Claude dobierze wg use-case | |

**User's choice:** Tylko SLEDZENIE
**Notes:** Zmiany stanów logowane w Phase 27

---

## Degradation bez karty SD

### Detekcja SD

| Option | Description | Selected |
|--------|-------------|----------|
| Tylko w setup() | SD.begin(10) raz, fail = sd_dostepne=false | ✓ |
| setup() + retry co 30s | Próba reinicjalizacji, hot-insert | |

**User's choice:** Tylko w setup()
**Notes:** Brak dodatkowych uwag

### HMI SD fail

| Option | Description | Selected |
|--------|-------------|----------|
| Serial + LCD bootscreen | Serial + LCD "SD: BRAK" + buzzer 1x beep | |
| Tylko Serial | Minimalna ingerencja w HMI | |
| Ty zdecyduj | Claude dobierze wg spójności z RTC fail | ✓ |

**User's choice:** Ty zdecyduj
**Notes:** Claude zdecyduje — spójność z RTC fail (Phase 25 D-08)

### RTC + SD zależność

| Option | Description | Selected |
|--------|-------------|----------|
| Loguj z millis() fallback | millis() zamiast epoch, plik LOG_NORTC.CSV | |
| Wyłącz logowanie | Brak RTC = brak timestamps = sd_dostepne=false | |
| Ty zdecyduj | Claude zdecyduje wg użyteczności millis() | ✓ |

**User's choice:** Ty zdecyduj
**Notes:** Claude zdecyduje — czy millis() timestamps są użyteczne do analizy PID

---

## Nazewnictwo plików i rotacja

### Format nazwy

| Option | Description | Selected |
|--------|-------------|----------|
| LYYMMDD.CSV | Zgodne z roadmap, FAT 8.3, prefiks L=Log | ✓ |
| YYMMDD.CSV | Bez prefiksu, krótsza | |

**User's choice:** LYYMMDD.CSV
**Notes:** Brak dodatkowych uwag

### Mechanizm rotacji

| Option | Description | Selected |
|--------|-------------|----------|
| Porównanie daty co flush | Co ~17s, minimalne obciążenie | |
| Sprawdzenie co wpis | Szybsza reakcja na zmianę dnia | |
| Ty zdecyduj | Claude dobierze wg timing analysis | ✓ |

**User's choice:** Ty zdecyduj
**Notes:** Brak dodatkowych uwag

### Nagłówek kolumn

| Option | Description | Selected |
|--------|-------------|----------|
| Tak, zawsze | Pierwsza linia każdego pliku — self-contained | ✓ |
| Nie, dane od razu | Mniejszy plik | |

**User's choice:** Tak, zawsze
**Notes:** Brak dodatkowych uwag

---

## Claude's Discretion

- HMI zachowanie przy SD fail (spójność z RTC fail alarm)
- Zachowanie przy braku RTC (millis() fallback vs wyłączenie)
- Mechanizm wykrywania zmiany dnia (co flush vs co wpis)
- Rozmiar bufora linii (weryfikacja 80 bajtów)
- Szczegóły benchmarku latencji LOG-05

## Deferred Ideas

None — discussion stayed within phase scope
