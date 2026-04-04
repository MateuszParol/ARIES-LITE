---
phase: 27-pelna-integracja-datalogger-z-maszynastanow
verified: 2026-04-04T09:00:00Z
status: human_needed
score: 5/5 code-level must-haves verified (4 hardware truths pending human)
gaps: []
human_verification:
  - test: "Komenda 'D' z karta SD wlozona — wyslic bajt 'D' na Serial, oczekiwac [DUMP] wpisy CSV zamiast pustego bufora"
    expected: "[DUMP] Ostatnie 10 wpisow DataLogger: ... wpisy CSV ... [DUMP] Koniec."
    why_human: "Karta SD nie byla wlozona podczas poprzedniego testu — bufor byl pusty. Potrzebna weryfikacja z SD."
  - test: "Sesja E2E z RPi — uruchom run_pi_brain.py, staw twarz, zakryj, odkryj (2-3 cykle)"
    expected: "Serwa sledzą twarz (SLEDZENIE), wracaja do Lissajous (SKANOWANIE), CSV zawiera przejscia 1->2 i 2->1"
    why_human: "Hardware E2E test — wymaga fizycznej kamery RPi, karty SD, i Arduino podlaczonego USB. Tilt servo Y wykazuje problem (err_y ~-80 stale) — wymaga diagnostyki sprzetowej pin D9 lub zasilania."
  - test: "Analiza CSV z karty SD — sprawdz plik LYYMMDD.CSV"
    expected: "Wiersze ze zmianami stanow, face_size > 0 w wierszach SLEDZENIE, latency_ms w okolicach 30-50ms"
    why_human: "Wymaga fizycznej karty SD z zarejestrowana sesja."
  - test: "Plynnosc PID podczas logowania SD — obserwacja serw przy zmianie stanu"
    expected: "Brak widocznych szarpan lub przerw przy przejsciach SCAN<->TRACK (natychmiastowy flush SD nie blokuje petli 100 Hz)"
    why_human: "Zachowanie real-time — nie mozna zweryfikowac statycznie z kodu."
---

# Phase 27: Pelna Integracja DataLogger z MaszynaStanow — Raport Weryfikacji

**Cel fazy:** Kazda zmiana stanu SCAN/TRACK/IDLE jest automatycznie logowana z RTC timestamp, ciagla telemetria dziala podczas TRACKING, system end-to-end z RPi i DataLogger jest funkcjonalny
**Zweryfikowano:** 2026-04-04T09:00:00Z
**Status:** human_needed — kod zweryfikowany w pelni, 4 testy sprzetowe oczekuja na weryfikacje czlowieka
**Re-weryfikacja:** Nie — weryfikacja inicjalna

---

## Osiagniecie celu

### Kryteria sukcesu z ROADMAP.md (Success Criteria)

Faza 27 definiuje 4 kryteria sukcesu z ROADMAP.md. Wszystkie sa behawioralne / sprzetowe i wymagaja weryfikacji czlowieka (patrz Sekcja "Weryfikacja przez czlowieka"). Kod zaimplementowany w sposob umozliwiajacy ich spelnienie.

| # | Kryterium | Status kodu | Status sprzetowy |
|---|-----------|-------------|-----------------|
| 1 | Zakrycie/odkrycie twarzy tworzy wpisy SCAN->TRACK w CSV | Kod poprawny | Oczekuje human UAT |
| 2 | TRACKING CSV zawiera wiersze co ~10 klatek | Kod poprawny (logger.krok() filtruje co 10 kl.) | Oczekuje human UAT |
| 3 | Zmiana stanu nie powoduje zawieszenia PID | Kod poprawny (flush tylko w loguj_zmiane_stanu, krok() buforowany) | Oczekuje human UAT |
| 4 | Pelna sesja RPi + Arduino exportowalna do CSV | Kod gotowy | Oczekuje human UAT |

### Prawdy obserwowalne (z must_haves planu 27-01)

| # | Prawda | Status | Dowod |
|---|--------|--------|-------|
| 1 | Zmiana stanu SCAN<->TRACK logowana z RTC timestamp do CSV | ZWERYFIKOWANA | `_logger.loguj_zmiane_stanu(stary, nowy, ...)` w `_przejdz_do()` linia 699; `loguj_zmiane_stanu()` wywoluje `_zegar.odczytaj_czas()` i `_plik.flush()` linia 481-492 |
| 2 | face_size z ramki 8B zapisywany w CSV zamiast placeholder 0 | ZWERYFIKOWANA | `ostatni_face_size = _ramka_buf[6]` linia 678; `maszyna.ostatni_face_size` przekazywane do `logger.krok()` linia 814 |
| 3 | latency_ms obliczany z millis() delta i zapisywany w CSV | ZWERYFIKOWANA | `uint16_t latency_ms = (uint16_t)(millis() - maszyna.czas_ostatniej_ramki())` linia 811; przekazywane do `logger.krok()` linia 815 |
| 4 | Komenda 'D' na Serial zrzuca 10 ostatnich wpisow diagnostycznych | ZWERYFIKOWANA | `if (bajt == 'D') { logger.zrzuc_ostatnie(); }` linia 787-788; `zrzuc_ostatnie()` wypisuje `[DUMP] Ostatnie 10 wpisow DataLogger:` linia 498 |
| 5 | Guard w `_przejdz_do()` zapobiega wielokrotnemu logowaniu tego samego stanu | ZWERYFIKOWANA | `if (nowy == _stan_systemu) return;` linia 696 — guard PRZED wywolaniem `loguj_zmiane_stanu()` |

**Wynik kodu:** 5/5 prawd zweryfikowanych

---

## Artefakty

### Artefakty wymagane

| Artefakt | Dostarcza | Status | Szczegoly |
|----------|-----------|--------|-----------|
| `src/arduino/aries_controller/aries_controller.ino` | Pelna integracja DataLogger z MaszynaStanow | ZWERYFIKOWANY | 816 linii, zawiera `loguj_zmiane_stanu`, `zrzuc_ostatnie`, `_bufor_diagnostyczny`, kompiluje sie (83596B Flash / 11268B RAM) |

Poziom 1 (istnieje): TAK — plik istnieje, 816 linii
Poziom 2 (merytoryczny): TAK — zawiera wszystkie wymagane metody, nie jest skeletonem
Poziom 3 (podlaczony): TAK — `DataLogger` zintegrowany z `MaszynaStanow` przez referencje; instancje globalne w poprawnej kolejnosci
Poziom 4 (dane plyna): CZESCIOWE — kod poprawny, weryfikacja hardware E2E oczekuje czlowieka

---

## Weryfikacja polaczen kluczowych (Key Links)

| Od | Do | Przez | Status | Szczegoly |
|----|-----|-------|--------|-----------|
| `MaszynaStanow::_przejdz_do()` | `DataLogger::loguj_zmiane_stanu()` | Referencja `_logger` | PODLACZONE | Linia 699: `_logger.loguj_zmiane_stanu(stary, nowy, _serwa.kat_pan, _serwa.kat_tilt)` |
| `MaszynaStanow::_przetworz_ramke()` | `ostatni_face_size` | Ekstrakcja bajtu 6 ramki | PODLACZONE | Linia 678: `ostatni_face_size = _ramka_buf[6];` |
| `loop()` serial parser | `DataLogger::zrzuc_ostatnie()` | Intercept bajtu 'D' | PODLACZONE | Linia 787: `if (bajt == 'D') { logger.zrzuc_ostatnie(); }` |
| Instancje globalne | Kolejnosc DataLogger PRZED MaszynaStanow | Deklaracja globalna | POPRAWNE | Linia 717: `DataLogger logger(zegar)` PRZED linią 718: `MaszynaStanow maszyna(serwa, hmi, logger)` |

---

## Sledzenie przeplywu danych (Level 4)

| Artefakt | Zmienna danych | Zrodlo | Produkuje realne dane | Status |
|----------|----------------|--------|----------------------|--------|
| `DataLogger::loguj_zmiane_stanu()` | timestamp | `_zegar.odczytaj_czas().unixtime()` | Tak — RTC DS1307 | PLYNIE (gdy RTC dostepny) |
| `DataLogger::_zapisz_csv()` | face_size | `maszyna.ostatni_face_size` z `_ramka_buf[6]` | Tak — bajt 6 ramki 8B z RPi | PLYNIE (gdy RPi wysyla ramki) |
| `DataLogger::_zapisz_csv()` | latency_ms | `millis() - maszyna.czas_ostatniej_ramki()` | Tak — delta czasu millis() | PLYNIE |
| `DataLogger::_bufor_diagnostyczny` | wpisy diagnostyczne | `strncpy` przy kazdym `_zapisz_csv()` i `loguj_zmiane_stanu()` | Tak — ostatnie 10 wpisow | PLYNIE |

Uwaga: `_bufor_diagnostyczny` byl pusty podczas testu komendy 'D' (27-02-flash-log.md) bo sesja E2E z RPi nie byla przeprowadzona — SD niedostepna w tamtym momencie. Logika kodu poprawna — weryfikacja hardware wymagana.

---

## Sprawdzenie behawioralne (Spot-Checks)

**Sprawdzono statycznie** — firmware Arduino nie uruchamia sie na tej maszynie.

| Zachowanie | Metoda | Wynik | Status |
|------------|--------|-------|--------|
| Firmware kompiluje sie na Uno R4 WiFi | arduino-cli compile (udokumentowane w 27-02-flash-log.md) | Flash 83596B (31%), RAM 11268B (34%) | PASS |
| Firmware wgrany i startuje | arduino-cli upload + monitoring Serial (27-02-flash-log.md) | 83604 bajtow, 5.085s, brak watchdog reset | PASS |
| Komenda 'D' zwraca dump | Manualny test Serial (27-02-flash-log.md) | `[DUMP] Ostatnie 10 wpisow DataLogger:` + `[DUMP] Koniec.` | PASS (bufor pusty — brak sesji E2E) |
| Brak placeholder `0, 0` w logger.krok() | grep w pliku .ino | Brak matchow | PASS |

---

## Pokrycie wymagan

| Wymaganie | Plan | Opis | Status | Dowod |
|-----------|------|------|--------|-------|
| INT-06 | 27-01-PLAN.md | Klasa DataLogger zintegrowana z MaszynaStanow — logowanie zmian stanow | SPELNIONE (kod) | `_logger.loguj_zmiane_stanu()` wywolywane z `_przejdz_do()`; face_size i latency_ms rzeczywiste |
| INT-08 | 27-02-PLAN.md | End-to-end: firmware z DataLogger dziala na Uno R4 z pelnym trackingiem RPi | CZESCIOWE — hardware Task 2 DEFERRED | Firmware wgrany i startuje; E2E sesja z RPi nie przeprowadzona; tilt servo problem niezdiagnozowany |

**Uwaga INT-08:** REQUIREMENTS.md oznacza INT-08 jako `[x] Complete`. Jednak 27-02-SUMMARY.md dokumentuje `requirements-completed: []` (pusty) i explicitnie odsyla Task 2 (checkpoint E2E) jako DEFERRED. Jest to rozbienznosc — INT-08 wymaga weryfikacji sprzetowej E2E ktora nie zostala przeprowadzona.

---

## Anti-wzorce

Przeskanowano plik `src/arduino/aries_controller/aries_controller.ino`:

| Plik | Linia | Wzorzec | Waznosc | Wplyw |
|------|-------|---------|---------|-------|
| aries_controller.ino | brak | Brak TODO/FIXME/PLACEHOLDER | - | OK |
| aries_controller.ino | brak | Brak placeholder `0, 0` w logger.krok() | - | OK |
| aries_controller.ino | 458 | `if (stan != SLEDZENIE) { _licznik_klatek = 0; return; }` — krok() loguje TYLKO w SLEDZENIE | Info | Zamierzone per D-08; loguj_zmiane_stanu() jest niezalezna i dziala we wszystkich stanach |

Znany problem sprzetowy (nie blokujacy kodu):

| Problem | Status | Wplyw |
|---------|--------|-------|
| Serwo tilt (Y) nie reaguje podczas sledzenia — err_y stale ~-80 | Badanie — wymaga diagnostyki sprzetowej (pin D9, zasilanie) | Nie blokuje INT-06 (logowanie zmian stanow dziala niezaleznie od serw); blokuje pelna weryfikacje INT-08 E2E |

---

## Weryfikacja przez czlowieka (wymagana)

### 1. Komenda 'D' z karta SD i danymi

**Test:** Podlacz Arduino z wlozoną kartą SD. Uruchom krotka sesje (chocby watchdog scan Lissajous). Nastepnie wyslij bajt 'D':
```python
python3 -c "import serial,time; s=serial.Serial('/dev/ttyACM0',115200,timeout=2); time.sleep(2); s.write(b'D'); time.sleep(0.5); print(s.read(s.in_waiting).decode('ascii',errors='replace')); s.close()"
```
**Oczekiwane:** `[DUMP] Ostatnie 10 wpisow DataLogger:` + linie CSV z wpisami (nie pusty bufor) + `[DUMP] Koniec.`
**Dlaczego czlowiek:** Poprzedni test mial pusty bufor (brak sesji E2E i karta SD niedostepna). Potrzebna weryfikacja ze wpisami.

### 2. Diagnostyka serwa tilt (Y) — blokuje E2E

**Test:** Wlacz Arduino samo (bez RPi). Obserwuj skan Lissajous — czy serwo tilt (D9) porusza sie podczas SKANOWANIE? Jesli nie: sprawdz zasilanie serwa 6V (osobny zasilacz), sprawdz pin D9 opornikiem/oscyloskopem.
**Oczekiwane:** Serwo tilt porusza sie sinusoidalnie podczas SKANOWANIE
**Dlaczego czlowiek:** Problem sprzetowy (pin D9 / zasilanie) — nie mozna zdiagnozowac statycznie.

### 3. Sesja E2E z RPi + analiza CSV

**Test:** Po naprawieniu tilt servo — uruchom `python3 run_pi_brain.py` na RPi. Staw twarz (SLEDZENIE), zakryj (SKANOWANIE), odkryj (SLEDZENIE). Powtorz 2-3 razy. Zatrzymaj. Wyjmij karte SD, sprawdz LYYMMDD.CSV:
- Czy sa wiersze ze `stan=1` (SKANOWANIE) i `stan=2` (SLEDZENIE)?
- Czy `face_size` > 0 w wierszach SLEDZENIE?
- Czy `latency_ms` jest w okolicach 30-50ms?
- Czy widoczne przejscia 1->2 i 2->1?

**Oczekiwane:** CSV zawiera kompletna telemetrie korelujaca z obserwowanym zachowaniem serw
**Dlaczego czlowiek:** Wymaga fizycznego sprzetu RPi + Arduino + karta SD + kamera.

### 4. Plynnosc PID podczas logowania SD

**Test:** Podczas sesji E2E (Test 3) — obserwuj serwa wzrokowo przy przejsciach SCAN<->TRACK.
**Oczekiwane:** Brak widocznych szarpan / przerw (natychmiastowy flush SD w loguj_zmiane_stanu() nie blokuje petli 100 Hz)
**Dlaczego czlowiek:** Zachowanie real-time nie mozna zweryfikowac statycznie.

---

## Podsumowanie wynikow

### Co jest zweryfikowane (kod)

Wszystkie 5 prawd z planu 27-01 sa w pelni zaimplementowane w kodzie:
- `loguj_zmiane_stanu()` istnieje i jest wywolywana z `_przejdz_do()` z guard'em
- `zrzuc_ostatnie()` istnieje i jest wywolywana przy bajcie 'D'
- `_bufor_diagnostyczny[10][64]` zadeklarowany, inicjalizowany, zapisywany
- `ostatni_face_size = _ramka_buf[6]` — ekstrakcja bajtu 6, nie placeholder
- `latency_ms = millis() - maszyna.czas_ostatniej_ramki()` — delta czasu, nie placeholder
- Kolejnosc instancji globalnych poprawna: DataLogger PRZED MaszynaStanow
- Firmware kompiluje sie bez bledow i zostal wgrany na Uno R4 WiFi

### Co oczekuje na weryfikacje sprzetowa

- Komenda 'D' z niepustym buforem (karta SD + sesja)
- Diagnostyka serwa tilt Y (problem sprzetowy)
- Sesja E2E z RPi — CSV z kompletna telemetria
- Brak zawieszenia PID podczas logu SD

### Status wymagan

- **INT-06** (logowanie zmian stanow): SPELNIONE w kodzie
- **INT-08** (E2E na Uno R4 z trackingiem RPi): CZESCIOWE — firmware wgrany i startuje; pelna sesja E2E nie przeprowadzona; znany problem z tilt servo Y blokuje pelna weryfikacje

---

_Zweryfikowano: 2026-04-04T09:00:00Z_
_Weryfikator: Claude (gsd-verifier)_
