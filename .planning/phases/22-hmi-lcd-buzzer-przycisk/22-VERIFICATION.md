---
phase: 22-hmi-lcd-buzzer-przycisk
verified: 2026-03-31T14:30:00Z
status: human_needed
score: 11/11 must-haves verified
human_verification:
  - test: "Podlacz Arduino Leonardo do zasilania i sprawdz LCD"
    expected: "Po resecie widoczny 'ARIES-LITE v2.0' przez ~2 sekundy, nastepnie 'Inicjalizacja...', potem Row 0 pokazuje 'IDLE P:  0 T:  0', Row 1 'Bx:0    By:0   '"
    why_human: "Wymaga fizycznego wyswietlacza LCD 1602 podlaczonego na D2/D3/D4/D5/D6/D11"
  - test: "Wyslij ramke trybu TRACK z RPi i nasluchaj buzzera"
    expected: "Krotki ton ~1kHz slyszalny z odleglosci 1m, trwajacy okolo 100ms — bez blokowania ruchu serw"
    why_human: "Wymaga buzzera na D8 i Arduino na sprzetowym stanowisku, ton nieweryfikowalny programowo"
  - test: "Wcisnij przycisk D7 podczas TRACK"
    expected: "Arduino przechodzi do SCAN w ciagu 50ms od wcisniecia (po 20ms debounce), buzzer NIE emituje tonu przy przejsciu TRACK→SCAN"
    why_human: "Wymaga fizycznego przycisku, timing 50ms i brak faltszywych wyzwolen nieweryfikowalny bez hardware"
  - test: "Obserwuj LCD podczas ruchu serw w TRACK"
    expected: "Row 0 aktualizuje katy co ~200ms bez widocznego migotania; Row 1 aktualizuje bledy X/Y"
    why_human: "Migotanie LCD (brak lub obecnosc) i czytelnosc wartosci weryfikowalna tylko wzrokowo"
---

# Phase 22: HMI LCD + Buzzer + Przycisk — Raport Weryfikacji

**Cel fazy:** Uzytkownik widzi stan systemu na LCD i slyszy potwierdzenie dzwiekowe przy zmianie stanu — fizyczny przycisk przywraca SCAN
**Zweryfikowano:** 2026-03-31T14:30:00Z
**Status:** human_needed
**Ponowna weryfikacja:** Nie — weryfikacja inicjalna

## Osiagniecie celu

### Prawdy obserwowalne

| # | Prawda | Status | Dowod |
|---|--------|--------|-------|
| 1 | LCD Row 0 pokazuje tryb (SKAN/SLEDZ/IDLE) i katy serw — aktualizacja co 200ms | VERIFIED | `lcd_tick()` linia 273: timer `LCD_INTERVAL_MS=200`, switch na `stan_systemu`, `dtostrf` dla katow |
| 2 | LCD Row 1 pokazuje bledy X/Y z ostatniej ramki | VERIFIED | `lcd_tick()` linia 294: `snprintf(linia1, ..., "Bx:%-5dBy:%-5d", ostatni_blad_x, ostatni_blad_y)` |
| 3 | LCD bootscreen "ARIES-LITE v2.0" widoczny przez 2 sekundy po starcie | VERIFIED | `setup()` linia 329-335: `lcd.begin(16,2)`, `lcd.print("ARIES-LITE v2.0")`, `delay(2000)` |
| 4 | LCD odswiezanie nie powoduje migotania (brak `lcd.clear()` w `lcd_tick`) | VERIFIED | `lcd_tick()` nie zawiera `lcd.clear()` — potwierdzone programowo. Jedyne `lcd.clear()` w linii 330 (setup bootscreen) |
| 5 | LCD nie blokuje PID tick 100Hz — `lcd_tick()` wywolany poza `pid_tick()` | VERIFIED | `loop()` linia 378: `lcd_tick()` po `pid_tick()` ale poza jego cialem. `pid_tick()` nie zawiera `lcd_tick()` |
| 6 | Buzzer emituje krotki ton 1kHz/100ms przy przejsciu do TRACK | VERIFIED | `przejdz_do()` linia 161: `tone(BUZZER_PIN, 1000, 100)` wylacznie w galezi `nowy_stan == TRACK` |
| 7 | Buzzer NIE emituje tonu przy przejsciu do SCAN ani IDLE | VERIFIED | `przejdz_do()`: blok `SCAN` nie zawiera `tone()`, blok `IDLE` pusty. `tone()` tylko w galezi TRACK |
| 8 | Przycisk D7 w trybie TRACK przywraca SCAN — reakcja w ciagu 50ms | VERIFIED* | `przycisk_tick()` linia 303: guard `!= TRACK return`, debounce 20ms, `przejdz_do(SCAN)` po stabilnym LOW. *50ms timing wymaga weryfikacji sprzetowej |
| 9 | Przycisk ignorowany w trybach SCAN i IDLE | VERIFIED | `przycisk_tick()` linia 304: `if (stan_systemu != TRACK) return;` — natychmiastowy powrot poza TRACK |
| 10 | Debounce 20ms eliminuje false triggers | VERIFIED | `przycisk_tick()`: millis()-based debounce z `przycisk_czas_zmiany`, warunek `>= DEBOUNCE_MS` i stan LOW + poprzedni HIGH |
| 11 | Buzzer i przycisk nie wplywaja na PID 100Hz timing | VERIFIED | `tone()` nieblokujace (Timer3 w tle), `przycisk_tick()` w loop() poza `pid_tick()`, guard na TRACK zwraca natychmiast w SCAN/IDLE |

**Wynik: 11/11 prawd zweryfikowanych** (4 wymagaja potwierdzenia sprzetowego)

### Artefakty wymagane

| Artefakt | Opis | Status | Szczegoly |
|----------|------|--------|-----------|
| `src/arduino/aries_controller/aries_controller.ino` | LCD defines, lcd global, lcd_tick(), bootscreen, buzzer, przycisk_tick() | VERIFIED | Istnieje, substantive (383 linie), wired — wszystkie funkcje wywolywane z loop()/setup() |

**Poziom 1 (istnieje):** Plik istnieje — commit `65ca09d` (LCD) + `657df8f` (buzzer/przycisk)
**Poziom 2 (substantive):** 383 linie, 16506B flash (57%) — nie stub
**Poziom 3 (wired):** `lcd_tick()` wywolywany z `loop()` (L378), `przycisk_tick()` z `loop()` (L381), `tone()` z `przejdz_do()` (L161), `lcd.begin()` z `setup()` (L329)

### Weryfikacja kluczowych polaczen

| Od | Do | Przez | Status | Szczegoly |
|----|----|----|--------|-----------|
| `loop()` | `lcd_tick()` | wywolanie w loop() poza pid_tick() | WIRED | L378: `lcd_tick();` po `pid_tick();` |
| `setup()` | `lcd.begin(16, 2)` | inicjalizacja z bootscreen | WIRED | L329: `lcd.begin(16, 2)` w setup() |
| `przejdz_do()` | `tone(BUZZER_PIN, 1000, 100)` | warunek nowy_stan == TRACK | WIRED | L161: w galezi `else if (nowy_stan == TRACK)` |
| `loop()` | `przycisk_tick()` | wywolanie w loop() poza pid_tick() | WIRED | L381: `przycisk_tick();` |
| `przycisk_tick()` | `przejdz_do(SCAN)` | abort TRACK po debounce | WIRED | L313: `przejdz_do(SCAN);` po warunku debounce |

### Data-Flow Trace (Poziom 4)

Firmware nie renderuje dynamicznych danych z zewnetrznego zrodla — LCD wyswietla bezposrednio zmienne globalne firmware (`stan_systemu`, `kat_pan`, `kat_tilt`, `ostatni_blad_x`, `ostatni_blad_y`). Te zmienne sa populowane przez `dispatch_ramke()` (z ramek serial) i `pid_tick()`/`skan_tick()`. Brak watpliwosci co do przepływu danych — zmienne sa rzeczywiste, nie hardcoded.

| Artefakt | Zmienna danych | Zrodlo | Produkuje rzeczywiste dane | Status |
|----------|----------------|--------|---------------------------|--------|
| `lcd_tick()` Row 0 | `stan_systemu`, `kat_pan`, `kat_tilt` | `dispatch_ramke()` + `pid_tick()` | Tak — PID oblicza katy, dispatch ustawia stan | FLOWING |
| `lcd_tick()` Row 1 | `ostatni_blad_x`, `ostatni_blad_y` | `dispatch_ramke()` linia 177-178 | Tak — z ramek serial | FLOWING |

### Behavioral Spot-Checks (Poziom 7b)

| Zachowanie | Komenda | Wynik | Status |
|------------|---------|-------|--------|
| Kompilacja firmware bez bledow | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/` | Exit 0, 16506B flash (57%), 565B RAM (22%) | PASS |
| lcd_tick() nie zawiera lcd.clear() | Python string search w body funkcji | `lcd_tick() has lcd.clear(): False` | PASS |
| tone() nie jest w pid_tick() | Python string search w body funkcji | `pid_tick() has tone(): False` | PASS |
| tone() nie jest bezposrednio w loop() | Python string search w body loop() | Brak linii z `tone(` | PASS |
| przycisk_tick() wywoluje przejdz_do(SCAN) | grep w body funkcji | L313: `przejdz_do(SCAN);` | PASS |

### Pokrycie wymagan

| Wymaganie | Plan zrodlowy | Opis | Status | Dowod |
|-----------|--------------|------|--------|-------|
| HMI-01 | 22-01-PLAN | LCD 1602 wyswietla tryb i blad X/Y — update max 5Hz, nie w petli PID | SATISFIED | `lcd_tick()` z `LCD_INTERVAL_MS=200` (5Hz), wywolywany z `loop()` poza `pid_tick()` |
| HMI-02 | 22-02-PLAN | Buzzer D8 krotki dzwiek przy przejsciu do TRACK | SATISFIED | `tone(BUZZER_PIN, 1000, 100)` w `przejdz_do()` przy `nowy_stan == TRACK` |
| HMI-03 | 22-02-PLAN | Przycisk D7 INPUT_PULLUP — Abort Track przywraca SCAN | SATISFIED | `przycisk_tick()` z debounce 20ms, `przejdz_do(SCAN)` po zboczu HIGH→LOW |
| HMI-04 | 22-01-PLAN | LCD bootscreen z nazwa systemu przy starcie | SATISFIED | `lcd.print("ARIES-LITE v2.0")` + `delay(2000)` w `setup()` |

**Wymagania osierozone (Phase 22):** Brak — tylko HMI-01, HMI-02, HMI-03, HMI-04 sa przypisane do Phase 22 w REQUIREMENTS.md, wszystkie cztery objete przez plany 22-01 i 22-02.

### Znalezione antypattern

| Plik | Linia | Pattern | Powaga | Wplyw |
|------|-------|---------|--------|-------|
| Brak | — | — | — | — |

Skanowanie: brak TODO/FIXME, brak `return null`/`return {}`, brak hardcoded empty values w kodzie wynikowym. Wzmianka `// Faza 22: HMI...` w naglowku to komentarz dokumentacyjny, nie stub.

### Wymagana weryfikacja sprzetowa

#### 1. LCD bootscreen i odswiezanie

**Test:** Podlacz LCD 1602 do Arduino Leonardo (RS=D2, EN=D3, D4-D7=D4-D6,D11), zaladuj firmware, wykonaj reset
**Oczekiwane:** Przez ~2 sekundy widoczny "ARIES-LITE v2.0" + "Inicjalizacja...", nastepnie tryb IDLE z katami 0/0
**Dlaczego human:** Wymaga fizycznego wyswietlacza, czytelnosc i brak migotania nieweryfikowalne bez hardware

#### 2. Buzzer "Target Lock"

**Test:** Z RPi wyslij ramke z trybem TRACK (bajt 1 = 0x02) przez SerialInterface
**Oczekiwane:** Krotki ton ~1kHz slyszalny z odleglosci 1m, trwajacy ~100ms, serwa nie zamierajace na czas tonu
**Dlaczego human:** Wyslyszalnosc tonu i jego nieblokujacy charakter wymagaja hardware

#### 3. Przycisk abort TRACK→SCAN

**Test:** W trybie TRACK wcisnij przycisk D7
**Oczekiwane:** Arduino przechodzi do SCAN w ciagu 50ms, LCD aktualizuje sie na "SKAN ", przycisk NIE wyzwala w SCAN/IDLE
**Dlaczego human:** Timing 50ms, brak false triggers i zachowanie debounce wymagaja sprzetowej weryfikacji

#### 4. Brak migotania LCD

**Test:** Obserwuj LCD podczas aktywnego sledzenia (TRACK z ruchoma twarza)
**Oczekiwane:** Row 0 i Row 1 aktualizuja sie plynnie co ~200ms bez widocznego migotania — odczyt czytelny
**Dlaczego human:** Migotanie jest efektem wizualnym, nieweryfikowalnym programowo

### Podsumowanie luk

Brak luk blokujacych. Wszystkie 11 prawd zweryfikowanych w kodzie. Firmware kompiluje sie czysto (exit 0, 57% flash). Wszystkie cztery wymagania HMI sa zaimplementowane i polaczone. Faza wymaga wylacznie weryfikacji sprzetowej (LCD podlaczony, buzzer slyszalny, przycisk reaguje) przed zamknieciem — nie jest to luka w implementacji, lecz standardowe UAT dla kodu firmware.

---

_Zweryfikowano: 2026-03-31T14:30:00Z_
_Weryfikator: Claude (gsd-verifier)_
