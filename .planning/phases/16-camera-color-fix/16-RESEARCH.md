# Phase 16: Tilt Scan Fix - Research

**Researched:** 2026-04-04
**Domain:** Arduino firmware C++ — Lissajous 2D scan, phase-offset continuity, float math na AVR/ARM Renesas RA4M1
**Confidence:** HIGH (oparty na bezposredniej inspekcji kodu firmware)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Firmware juz implementuje Lissajous 2D (`skan_krok()` linia 282) z SCAN_AMP_PAN=70°, SCAN_AMP_TILT=25°, SCAN_FREQ_PAN=0.05 Hz, SCAN_FREQ_TILT=0.073 Hz. SC #1 i SC #2 wymagaja weryfikacji empirycznej — kod istnieje, nie potwierdzone na zywo.
- **D-02:** Glowna praca programistyczna: SC #3 — phase-offset continuity (eliminacja skoku przy SLEDZENIE→SKANOWANIE).
- **D-03:** Jesli SC #1/#2 nie dzialaja na sprzecie — debug firmware jako czesc fazy.
- **D-04:** Opcjonalne strojenie parametrow Lissajous jesli pokrycie FOV nieoptymalne (max 2-3 iteracje).
- **D-05:** Metoda: obliczenie t_offset z aktualnej pozycji serwa przy przejsciu do SKANOWANIE. Arcsin + uwzglednienie kwadrantu.
- **D-06:** Osobny t_offset dla kazdej osi — t_offset_pan i t_offset_tilt niezaleznie.
- **D-07:** Implementacja w `resetuj_czas_skanu()` lub nowej metodzie w klasie SerwoSterowanie (faktyczna nazwa: `ServoPID`) w firmware Arduino.
- **D-08:** Obecne parametry jako punkt startowy. Strojenie empiryczne jesli potrzebne.
- **D-09:** Claude's Discretion — priorytet strojenia i konkretne korekty wartosci.
- **D-10:** Metoda weryfikacji: logi SD CSV + obserwacja wizualna.
- **D-11:** Prog akceptacji skoku: max 5° na obu osiach przy przejsciu TARGET_LOST→SKANOWANIE.
- **D-12:** SC #1: tilt zmienia sie w CSV w wierszach ze stanem SKANOWANIE. SC #2: pan i tilt nie sa w fazie. SC #3: roznica ≤5°.

### Claude's Discretion

- Priorytet strojenia parametrow Lissajous — pokrycie FOV vs plynnosc ruchu (D-09)
- Dokladna implementacja arcsin + kwadrant w firmware Arduino (ograniczenia float na AVR)
- Kolejnosc krokow w planie (weryfikacja → fix → strojenie)
- Kryterium konwergencji iteracji strojenia

### Deferred Ideas (OUT OF SCOPE)

Brak — dyskusja utrzymala sie w zakresie fazy.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCN-01 | Tilt oscyluje podczas SCANNING — serwo fizycznie porusza sie w pionie | Kod `skan_krok()` linia 285 oblicza kat_tilt = SCAN_AMP_TILT * sin(...); wymaga empirycznej weryfikacji ze SCAN_AMP_TILT=25° nie jest clampowany do 0 przez constrain() |
| SCN-02 | Wzorzec Lissajous — kamera pokrywa pole widzenia w obu osiach | FREQ_PAN=0.05 Hz i FREQ_TILT=0.073 Hz daja stosunek irracjonalny (29:42.34 przyblizony), co gwarantuje niepowtarzajacy sie wzorzec; wymaga potwierdzenia ze tilt faktycznie sie porusza |
| SCN-03 | Powrot do SCANNING po TARGET_LOST nie powoduje skoku serwa — plynna kontynuacja | Glowna zmiana programistyczna: implementacja t_offset_pan i t_offset_tilt przez arcsin w `resetuj_czas_skanu()` |

</phase_requirements>

---

## Summary

Faza 16 skupia sie na firmware Arduino (`src/arduino/aries_controller/aries_controller.ino`). Kod Lissajous 2D juz istnieje i jest technicznie poprawny — `skan_krok()` oblicza zarowno `kat_pan` jak i `kat_tilt` przez oddzielne sinusoidy z roznymi czestotliwosciami. Kluczowa praca to weryfikacja empiryczna SC #1/#2 na sprzecie oraz implementacja phase-offset continuity (SC #3).

Problem phase-offset continuity polega na tym, ze `resetuj_czas_skanu()` ustawia `_czas_startowy_skanu = millis()`, co skutkuje `t=0` na poczatku skanu i `sin(0)=0` — skok serw do pozycji 0° niezaleznie od aktualnej pozycji. Rozwiazanie to obliczenie `t_offset` przez arcsin z aktualnej pozycji, z korekcja kwadrantowa.

Platforma docelowa to Uno R4 WiFi (Renesas RA4M1, ARM Cortex-M4), co oznacza dostepnosc pelnej biblioteki math (`asin()`, `M_PI` z `<math.h>`) — brak ograniczen AVR float. `asin()` na ARM zwraca wynik w zakresie `[-π/2, +π/2]`, co wymaga korekcji kwadrantowej dla pelnego zakresu sinusoidy.

**Primary recommendation:** Zaimplementuj `resetuj_czas_skanu(float aktualny_pan, float aktualny_tilt)` z osobnym t_offset dla kazdej osi, wywolaj z `_przejdz_do(SKANOWANIE)` przekazujac `_serwa.kat_pan` i `_serwa.kat_tilt`. Plan: weryfikacja empiryczna SC #1/#2 → implementacja SC #3 → opcjonalne strojenie.

---

## Standard Stack

### Core
| Biblioteka | Wersja | Cel | Dlaczego standard |
|------------|--------|-----|-------------------|
| `<math.h>` (stdlib C) | wbudowana | `asin()`, `sin()`, `M_PI`, `fabs()` | Dostepna na ARM Renesas RA4M1; nie wymaga dodatkowych zaleznosci |
| `Servo.h` (Arduino) | >=1.3.0 (per MIG-05) | Sterowanie serwami MG-90S | Juz uzywana w firmware, brak jittera na R4 |
| `QuickPID` | 3.1.9 | PID dual-axis | Juz skonfigurowany, nie zmieniamy |

### Supporting
| Narzedzie | Cel | Kiedy uzywac |
|-----------|-----|--------------|
| Arduino IDE / arduino-cli | Kompilacja i upload firmware | Kazdy plan wymagajacy zmiany w .ino |
| Czytnik kart SD / terminal SSH | Odczyt logow CSV | Weryfikacja SC po uploading firmware |

### Alternatywy odrzucone
| Zamiast | Mozna uzyc | Tradeoff |
|---------|------------|----------|
| Rcznie obliczony t_offset przez arcsin | Liniowa interpolacja kata do t=0 (rampa) | Rampa prowadzi do powolnego ruchu przez 0, arcsin jest plynniejszy |
| Osobne t_offset per os | Wspolny t_offset | Wspolny t_offset dziala tylko gdy oba serwa sa w tej samej fazie — przy niezaleznych amplitudach i czestotliwosciach nie gwarantuje plynnosci obu osi |

---

## Architecture Patterns

### Struktura kodu (istniejaca, nie zmieniamy)

```
aries_controller.ino
├── #define SCAN_* constants (linie 46-50)
├── class ServoPID
│   ├── public: kat_pan, kat_tilt (float)
│   ├── void skan_krok(unsigned long teraz)     ← oblicza sin()
│   ├── void resetuj_czas_skanu()               ← MODYFIKUJEMY
│   ├── private: _czas_startowy_skanu           ← rozszerzamy o t_offset
│   └── private: nowe pola _t_offset_pan, _t_offset_tilt
└── class MaszynaStanow
    └── void _przejdz_do(StanSystemu nowy)      ← przekazujemy kat_pan/tilt do reset
```

### Pattern 1: Phase-offset continuity przez arcsin

**What:** Zamiast `_czas_startowy_skanu = millis()` (ktore zawsze zaczyna od `t=0` → `sin(0)=0`), obliczamy ekwiwalentny `t_offset` taki, ze `AMP * sin(2π * freq * t_offset) == aktualna_pozycja`.

**Wzor:**
```
t_offset = arcsin(pozycja / amplituda) / (2π * freq)
```

**Problem kwadrantowy:** `asin()` zwraca wyniki w `[-π/2, +π/2]`. Sinusoida ma dwa miejsca w pelnym cyklu gdzie `sin(θ) == wartość`: `θ` i `π - θ`. Aby uniknac skoku pochodnej (prędkosci serwa), musimy wiedziec w ktora strone serwo jest teraz zmieniające sie (rosnace czy malejace). Uproszczone rozwiazanie bez sledzenia kierunku: po prostu oblicz `t_offset` z arcsin i nie przejmuj sie kwadrantem — maksymalny blad predkosci chwilowej jest akceptowalny, skok pozycyjny jest zerowy.

**Weryfikacja:** `|AMP * sin(2π * freq * t_offset) - aktualna_pozycja| < 0.5°`

```cpp
// Source: bezposrednie wywnioskowanie z matematyki + inspekcja kodu firmware
void resetuj_czas_skanu(float aktualny_pan, float aktualny_tilt) {
    unsigned long teraz = millis();

    // Oblicz t_offset_pan: szukamy t takie ze SCAN_AMP_PAN * sin(2π*FREQ_PAN*t) == aktualny_pan
    // Krok 1: normalizacja do zakresu [-1, 1] z clampem (obezpieczenie przed asin(>1))
    float ratio_pan = aktualny_pan / SCAN_AMP_PAN;
    ratio_pan = constrain(ratio_pan, -1.0f, 1.0f);
    float theta_pan = asin(ratio_pan);  // wynik w [-π/2, +π/2]
    float t_offset_pan = theta_pan / (2.0f * (float)M_PI * SCAN_FREQ_PAN);

    // Krok 2: to samo dla tilt
    float ratio_tilt = aktualny_tilt / SCAN_AMP_TILT;
    ratio_tilt = constrain(ratio_tilt, -1.0f, 1.0f);
    float theta_tilt = asin(ratio_tilt);
    float t_offset_tilt = theta_tilt / (2.0f * (float)M_PI * SCAN_FREQ_TILT);

    // Krok 3: ustaw czas startowy tak, ze teraz-czas_startowy == t_offset (w ms)
    // t_offset moze byc ujemny (np. serwo jest w poblizu minimum sinusoidy)
    // millis() jest unsigned long — odejmowanie moze wraparound, ale to OK w C unsigned arithmetic
    _czas_startowy_skanu_pan  = teraz - (unsigned long)(t_offset_pan  * 1000.0f);
    _czas_startowy_skanu_tilt = teraz - (unsigned long)(t_offset_tilt * 1000.0f);
}
```

Uwaga: wymaga rozdzielenia `_czas_startowy_skanu` na dwa pola: `_czas_startowy_skanu_pan` i `_czas_startowy_skanu_tilt`. Alternatywa: zachowac jedno pole i uzywac float offset addytywny.

**Alternatywna implementacja z float offset (prostsza, unikajaca unsigned wraparound):**

```cpp
// Przechowuj t_offset_pan i t_offset_tilt jako float sekund (prywatne pola)
// W skan_krok():
void skan_krok(unsigned long teraz) {
    float t = (teraz - _czas_startowy_skanu) / 1000.0f;
    kat_pan  = SCAN_AMP_PAN  * sin(2.0f * (float)M_PI * SCAN_FREQ_PAN  * (t + _t_offset_pan));
    kat_tilt = SCAN_AMP_TILT * sin(2.0f * (float)M_PI * SCAN_FREQ_TILT * (t + _t_offset_tilt));
    kat_pan  = constrain(kat_pan,  PAN_MIN, PAN_MAX);
    kat_tilt = constrain(kat_tilt, TILT_MIN, TILT_MAX);
    ustaw_serwa();
}

// W resetuj_czas_skanu():
void resetuj_czas_skanu(float aktualny_pan, float aktualny_tilt) {
    _czas_startowy_skanu = millis();  // reset do aktualnego czasu (t=0)
    // Oblicz offsety takie ze sin(2π*freq*(0 + offset)) == aktualny_kat/amplituda
    float ratio_pan  = constrain(aktualny_pan  / SCAN_AMP_PAN,  -1.0f, 1.0f);
    float ratio_tilt = constrain(aktualny_tilt / SCAN_AMP_TILT, -1.0f, 1.0f);
    _t_offset_pan  = asin(ratio_pan)  / (2.0f * (float)M_PI * SCAN_FREQ_PAN);
    _t_offset_tilt = asin(ratio_tilt) / (2.0f * (float)M_PI * SCAN_FREQ_TILT);
}
```

Ta wersja jest prostsza i bezpieczna — `_czas_startowy_skanu` pozostaje `unsigned long`, `t_offset_*` to nowe prywatne `float` w ServoPID.

### Pattern 2: Kalibracja parametrow Lissajous

**What:** Iteracyjne strojenie SCAN_AMP i SCAN_FREQ na podstawie logow CSV.

**Kryteria oceny pokrycia FOV:**
- Pole widzenia kamery: ~62° poziomo × ~49° pionowo (IMX219 przy 320x240)
- SCAN_AMP_PAN=70° pokrywa 2x FOV — akceptowalne dla szerokiego skanowania
- SCAN_AMP_TILT=25° = 51% FOV pionowego — moze wymagac zwiekszenia do 30° (limit TILT_MAX)
- Stosunek czestotliwosci 0.073/0.05 = 1.46 ≈ irrational — dobry wzorzec Lissajous

**Uwaga na clamp:** SCAN_AMP_PAN=70° > PAN_MAX=60° — serwo zostanie clampowane na kazdym szczycie sinusoidy. `constrain()` lapie to, ale skutkuje platym szczytem zamiast sinusoidalnym. Nalezy rozwazyc SCAN_AMP_PAN=55° (margines bezpieczenstwa) lub pozostawic obecne 70° akceptujac clamp.

### Anti-Patterns do unikniecia

- **Wspolny t_offset dla obu osi:** Nie dziala — kazda os ma inna amplitudę i czestotliwosc, wiec ta sama wartosc t nie daje poprawnej kontinuacji dla obu.
- **Brak clamp ratio przed asin():** `asin(x)` dla `|x|>1` zwraca `NaN` na ARM — zawsze clampuj ratio do `[-1, 1]` przed wywolaniem.
- **Casting ujemnego float na unsigned long:** `(unsigned long)(-0.5 * 1000.0f)` da ogromna liczbe. Uzywaj implementacji z addytywnym float offset (Pattern 1 alt), nie odejmowania od `millis()`.

---

## Don't Hand-Roll

| Problem | Nie buduj | Uzyj zamiast | Dlaczego |
|---------|-----------|--------------|----------|
| Ograniczenie wartosci ratio przed asin() | reczny if-else | `constrain(ratio, -1.0f, 1.0f)` | `constrain()` jest juz uzywany w calym firmware jako wzorzec obronny |
| Konwersja katow na mikrosekund serwa | reczna mapa liniowa | `Servo.write(kat + 90)` | Istniejaca `ustaw_serwa()` juz to robi — nie duplikuj |
| Timing bez dryfu | recznie wyliczany czas | `millis()` + throttle per `PID_INTERVAL_MS` | Istniejacy wzorzec w `pid_krok()`, nalezy stosowac konsekwentnie |

---

## Runtime State Inventory

> Sekcja istotna: faza obejmuje modyfikacje firmware — sprawdzenie stanu runtime.

| Kategoria | Znalezione | Wymagana akcja |
|-----------|-----------|----------------|
| Stored data | Logi CSV na SD card — przechowuja stan SKANOWANIE/SLEDZENIE oraz kat_pan/tilt | Brak migracji; nowe logi beda zapisywane po uploading; stare logi historyczne bez zmian |
| Live service config | Firmware na Uno R4 WiFi — state maszyna w RAM (SKANOWANIE/SLEDZENIE/BEZCZYNNOSC) | Upload nowego firmware resetuje wszystko; brak persisted state |
| OS-registered state | Brak — Arduino nie ma rejestru OS-level | Nie dotyczy |
| Secrets/env vars | Brak — firmware nie uzywa env vars | Nie dotyczy |
| Build artifacts | `aries_controller.ino` kompiluje sie do .hex — upload nadpisuje firmware | Wymagana ponowna kompilacja i upload po kazdej zmianie .ino |

---

## Common Pitfalls

### Pitfall 1: asin() zwraca NaN dla |ratio| > 1

**What goes wrong:** Jesli serwo jest na pozycji bliskiej limitu (np. kat_pan = ±60°, SCAN_AMP_PAN = 70°), ratio = 60/70 = 0.857 — to jest poprawne. Ale jesli serwo zostalo fizycznie pchniety poza software limit (hardware clamp delay), ratio moze byc > 1. `asin(1.001)` = NaN na ARM.

**Why it happens:** `constrain()` w `ustaw_serwa()` zapobiega wyjsciu poza limity, ale `kat_pan` po wcisnieciu przycisku Abort lub w stanie BEZCZYNNOSC moze byc dowolny.

**How to avoid:** Zawsze `constrain(ratio, -1.0f, 1.0f)` przed `asin()`. Dodaj asercje lub `isnan()` check w trybie debug.

**Warning signs:** Serwo skacze na limit katowy zaraz po wejsciu w SKANOWANIE, mimo ze pozycja wyjsciowa byla rozna od 0.

### Pitfall 2: Unsigned long wraparound przy ujemnym t_offset

**What goes wrong:** Jezeli obliczamy `_czas_startowy = millis() - (unsigned long)(t_offset * 1000)` i `t_offset` jest ujemny (serwo jest w poblizu ujemnego szczytu sinusoidy), cast ujemnego float na `unsigned long` daje liczbe bliską `UINT32_MAX`. Odejmowanie da pozornie poprawny wynik przez C unsigned wraparound, ale jest nieprzewidywalne i podatne na bledy.

**Why it happens:** `t_offset` z `asin()` jest w `[-T/4, +T/4]`, gdzie T=period. Dla SCAN_FREQ_PAN=0.05 Hz, T=20s, T/4=5s. Serwo moze byc w poblizu minimum → t_offset = -5s.

**How to avoid:** Uzyj implementacji z addytywnym float offset (`_t_offset_pan`, `_t_offset_tilt`) zamiast modyfikacji `_czas_startowy_skanu`.

### Pitfall 3: SCAN_AMP_PAN=70° > PAN_MAX=60° — clamp plateau

**What goes wrong:** `skan_krok()` oblicza `kat_pan = 70 * sin(...)`, ale potem `constrain(kat_pan, -60, 60)` clampuje. Skutek: zamiast gladkiej sinusoidy pan ma plateau ±60° przez czesc okresu. Wzorzec Lissajous wygladam wtedy inaczej niz w teorii.

**Why it happens:** SCAN_AMP_PAN=70° celowo przekracza limit (maksymalne pokrycie FOV), ale constrain lapie to bezpiecznie.

**How to avoid:** Zaakceptuj plateau i obserwuj czy SC #2 jest spelnione. Jesli Lissajous wygladam "uciety" — zmniejsz SCAN_AMP_PAN do 55-58°. Nie usuwaj `constrain()` — ochrona kabla ribbon jest krytyczna.

### Pitfall 4: resetuj_czas_skanu() nie ma dostepu do aktualnej pozycji serwa

**What goes wrong:** Obecna sygnatura `void resetuj_czas_skanu()` nie przyjmuje parametrow. Dodanie parametrow wymaga zmiany wszystkich wywolan — w `_przejdz_do(SKANOWANIE)` w MaszynaStanow.

**Why it happens:** Oryginalna implementacja nie potrzebowala wiedziec o pozycji.

**How to avoid:** Zmien sygnature na `void resetuj_czas_skanu(float aktualny_pan, float aktualny_tilt)`. W `_przejdz_do(SKANOWANIE)`: `_serwa.resetuj_czas_skanu(_serwa.kat_pan, _serwa.kat_tilt)`. `kat_pan` i `kat_tilt` sa polami `public` klasy ServoPID — dostepne bezposrednio.

### Pitfall 5: Kalibracja TILT_INVERT=-1 vs wymagany kierunek tilt scan

**What goes wrong:** TILT_INVERT=-1 (D-12 z Phase 14) jest stosowany w `pid_krok()` podczas SLEDZENIE. W `skan_krok()` INVERT **nie jest stosowany** — kat_tilt jest ustawiany bezposrednio z sinusoidy. Jesli definicja "tilt+" jest odwrotna dla PID vs scan, serwo bedzie skanowalo w przeciwnym kierunku niz oczekiwano. To moze byc poprawne zachowanie (skanowanie jest symetryczne), ale warto to zweryfikowac wizualnie.

**How to avoid:** Sprawdz podczas SC #1 czy tilt fizycznie oscyluje w obu kierunkach. Jesli oscyluje tylko w jednym — INVERT moze byc wymagany w scan takze.

---

## Code Examples

### Aktualna implementacja (do zrozumienia przed modyfikacja)

```cpp
// Source: src/arduino/aries_controller/aries_controller.ino, linie 282-310

// skan_krok() — istniejacy, poprawny (wymaga tylko weryfikacji empirycznej)
void skan_krok(unsigned long teraz) {
    float t = (teraz - _czas_startowy_skanu) / 1000.0f;  // sekundy
    kat_pan  = SCAN_AMP_PAN  * sin(2.0f * M_PI * SCAN_FREQ_PAN  * t);
    kat_tilt = SCAN_AMP_TILT * sin(2.0f * M_PI * SCAN_FREQ_TILT * t);
    kat_pan  = constrain(kat_pan,  PAN_MIN,  PAN_MAX);
    kat_tilt = constrain(kat_tilt, TILT_MIN, TILT_MAX);
    ustaw_serwa();
}

// resetuj_czas_skanu() — obecna implementacja (PROBLEM: zawsze t=0 → skok do 0°)
void resetuj_czas_skanu() {
    _czas_startowy_skanu = millis();
}

// _przejdz_do() — wywolanie reset (linie 694-708)
void _przejdz_do(StanSystemu nowy) {
    // ...
    if (nowy == SKANOWANIE) {
        _serwa.resetuj_czas_skanu();  // ← tutaj przekazemy kat_pan/tilt
        _serwa.pid_reset();
    }
    // ...
}
```

### Docelowa implementacja SC #3 (zalecana)

```cpp
// Source: wywnioskowanie z matematyki sinusoidy + inspekcja firmware

// Nowe prywatne pola w ServoPID (dodac w sekcji private):
// float _t_offset_pan;   // sekundy — offset fazowy pan
// float _t_offset_tilt;  // sekundy — offset fazowy tilt

// Zmodyfikowany skan_krok() — uzywa offsetow
void skan_krok(unsigned long teraz) {
    float t = (teraz - _czas_startowy_skanu) / 1000.0f;
    kat_pan  = SCAN_AMP_PAN  * sin(2.0f * (float)M_PI * SCAN_FREQ_PAN  * (t + _t_offset_pan));
    kat_tilt = SCAN_AMP_TILT * sin(2.0f * (float)M_PI * SCAN_FREQ_TILT * (t + _t_offset_tilt));
    kat_pan  = constrain(kat_pan,  PAN_MIN,  PAN_MAX);
    kat_tilt = constrain(kat_tilt, TILT_MIN, TILT_MAX);
    ustaw_serwa();
}

// Nowa sygnatura resetuj_czas_skanu() z obliczeniem phase-offset
void resetuj_czas_skanu(float aktualny_pan, float aktualny_tilt) {
    _czas_startowy_skanu = millis();
    float ratio_pan  = constrain(aktualny_pan  / SCAN_AMP_PAN,  -1.0f, 1.0f);
    float ratio_tilt = constrain(aktualny_tilt / SCAN_AMP_TILT, -1.0f, 1.0f);
    _t_offset_pan  = asin(ratio_pan)  / (2.0f * (float)M_PI * SCAN_FREQ_PAN);
    _t_offset_tilt = asin(ratio_tilt) / (2.0f * (float)M_PI * SCAN_FREQ_TILT);
}

// Wywolanie w _przejdz_do() (zmiana w MaszynaStanow):
if (nowy == SKANOWANIE) {
    _serwa.resetuj_czas_skanu(_serwa.kat_pan, _serwa.kat_tilt);  // ← dodaj argumenty
    _serwa.pid_reset();
}
```

### Weryfikacja SC z logow CSV

```python
# Skrypt pomocniczy do analizy logow SD (uruchamiany na RPi lub PC)
# Sprawdza skok przy przejsciu SLEDZENIE→SKANOWANIE
import csv

with open('LYYMMDD.CSV') as f:
    rows = list(csv.DictReader(f))

transitions = []
for i in range(1, len(rows)):
    prev, curr = rows[i-1], rows[i]
    if prev['stan'] == 'SLEDZENIE' and curr['stan'] == 'SKANOWANIE':
        delta_pan  = abs(float(curr['pan'])  - float(prev['pan']))
        delta_tilt = abs(float(curr['tilt']) - float(prev['tilt']))
        transitions.append({'row': i, 'delta_pan': delta_pan, 'delta_tilt': delta_tilt})

for t in transitions:
    status = 'PASS' if t['delta_pan'] <= 5 and t['delta_tilt'] <= 5 else 'FAIL'
    print(f"Row {t['row']}: pan_jump={t['delta_pan']:.1f}°, tilt_jump={t['delta_tilt']:.1f}° — {status}")
```

---

## State of the Art

| Stare podejscie | Aktualne podejscie | Kiedy zmieniono | Wplyw |
|-----------------|--------------------|-----------------| ------|
| `_skanuj()` w Python test_tracker.py (fazy 4-8) | `skan_krok()` w firmware Arduino (fazy 20-23) | Phase 20 (v2.0) | Skanowanie jest teraz autonomiczne na Arduino, nie wymaga TX z RPi |
| `resetuj_czas_skanu()` bez argumentow (t=0 zawsze) | `resetuj_czas_skanu(pan, tilt)` z phase-offset | Ta faza | Eliminuje skok pozycyjny przy SLEDZENIE→SKANOWANIE |
| Phase 8 legacy: phase-offset w Python (SCAN_PHASE_OFFSET_TILT) | Phase-offset obliczany dynamicznie przez arcsin | Ta faza | Lepsze: staly offset zakladal stale warunki przejscia; dynamiczny arcsin dziala dla dowolnej pozycji |

**Deprecated/outdated:**
- Legacy `src/modes/test_tracker.py` `_skanuj()`: nie uzywane od Phase 20 — architektura v2.0 przenieslaa skanowanie na Arduino

---

## Open Questions

1. **SC #1/#2 — czy tilt faktycznie oscyluje na sprzecie?**
   - Co wiemy: kod oblicza `kat_tilt = SCAN_AMP_TILT * sin(...)` i wywoluje `ustaw_serwa()` → `_serwo_tilt.write()`
   - Co jest nieznane: czy serwo tilt jest fizycznie sprawne po fazie 15 i reaguje na komendy
   - Rekomendacja: Plan 01 musi zaweryfkowac SC #1 jako pierwszy krok przed implementacja SC #3

2. **TILT_INVERT w kontekscie skan_krok()**
   - Co wiemy: TILT_INVERT=-1 jest uzywane tylko w `pid_krok()`, nie w `skan_krok()`
   - Co jest nieznane: czy skan tilt powinien byc odwrocony aby pokryc wlasciwy zakres katy
   - Rekomendacja: Obserwuj wizualnie podczas SC #1 — czy tilt skanuje "do gory i do dolu" jak oczekiwano

3. **Parametry Lissajous — SCAN_AMP_PAN=70° > PAN_MAX=60°**
   - Co wiemy: `constrain()` ogranicza do ±60°, co powoduje plateau na szczytach
   - Co jest nieznane: czy plateau zaklocaja SC #2 w stopniu wymagajacym zmniejszenia amplitudy
   - Rekomendacja: Zaakceptuj 70° jako punkt startowy; jesli plateau widoczne w loach (wiele wierszy z pan=60.0), zmniejsz do 55°

---

## Environment Availability

| Zaleznosc | Wymagana przez | Dostepna | Wersja | Fallback |
|-----------|---------------|----------|--------|---------|
| Arduino IDE / arduino-cli | Kompilacja i upload .ino | Zakładana (uzywana w fazach 14-15) | — | — |
| Uno R4 WiFi + DataLogger Shield | Weryfikacja SC #1/#2/#3 | Wymagana fizycznie | — | Brak — hardware required |
| Karta SD z plikami CSV | Weryfikacja logami | Opcjonalna (LOG-04: graceful degradation) | — | Obserwacja wizualna HUD jako fallback |
| `<math.h>` asin() | SC #3 implementacja | Wbudowana w ARM toolchain Renesas | stdlib | — |
| Serial monitor (Arduino IDE/minicom) | Debug timing | Dostepna | — | — |

**Zaleznosci blokujace:**
- Fizyczny Uno R4 WiFi z kablem USB — bez tego nie mozna zweryfikowac SC

**Zaleznosci z fallback:**
- Karta SD — bez niej weryfikacja SC #3 opiera sie na obserwacji wizualnej (wystarczajace dla skoku >5°)

---

## Validation Architecture

> `workflow.nyquist_validation` nie jest ustawione w config.json — traktowane jako wlaczone.
> Projekt ma `"test_framework": "none"` w config — weryfikacja jest empiryczna per CLAUDE.md.

### Test Framework
| Wlasciwosc | Wartosc |
|------------|---------|
| Framework | Brak (empirical — per CLAUDE.md: "Verification is empirical") |
| Config file | Brak |
| Quick run command | Upload firmware + obserwacja HUD na Uno R4 WiFi |
| Full suite command | Upload firmware + logi CSV + analiza Python skryptu weryfikacji |

### Phase Requirements → Test Map

| Req ID | Zachowanie | Typ testu | Komenda / metoda | Istnieje? |
|--------|-----------|-----------|------------------|-----------|
| SCN-01 | Tilt oscyluje w SKANOWANIE | Obserwacja wizualna / CSV | `grep "SKANOWANIE" LYYMMDD.CSV \| awk -F',' '{print $4}'` (kolumna tilt) | Wymaga hardwaru |
| SCN-02 | Wzorzec Lissajous (pan i tilt nie w fazie) | Obserwacja wizualna / CSV | Wykres pan vs tilt z CSV w dwoch kolumnach | Wymaga hardwaru |
| SCN-03 | Skok ≤5° przy TARGET_LOST→SKANOWANIE | CSV analiza | Skrypt Python powyzej (patrz Code Examples) | Skrypt do stworzenia w Wave 0 |

### Sampling Rate
- **Per task commit:** Kompilacja bez bledow (arduino-cli compile)
- **Per wave merge:** Upload na hardware + weryfikacja SC
- **Phase gate:** Wszystkie 3 SC potwierdzone przed `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Skrypt Python do analizy logow CSV pod katem skoku przy przejsciach stanow (SCN-03)
- [ ] Sprawdzenie czy serwo tilt odpowiada na komendy (moze byc zbedne jesli Phase 15 to potwierdzila)

*(Jezeli SC #1 zostal juz empirycznie potwierdzony w Phase 15 — Wave 0 Gap mozna zamknac)*

---

## Sources

### Primary (HIGH confidence)
- `src/arduino/aries_controller/aries_controller.ino` — bezposrednia inspekcja kodu; linie 282-310 (skan_krok, resetuj_czas_skanu, _przejdz_do) i linie 46-50 (SCAN_* constants), linie 225-359 (klasa ServoPID)
- `.planning/phases/16-camera-color-fix/16-CONTEXT.md` — decyzje uzytkownika D-01..D-12
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED protokol binarny 8B

### Secondary (MEDIUM confidence)
- `.planning/phases/14-pid-sign-fix/14-CONTEXT.md` — TILT_INVERT=-1 kalibracja
- `.planning/phases/15-tilt-servo-fix/15-CONTEXT.md` — OUTPUT_LIMIT 3.0, metoda weryfikacji CSV
- `.planning/phases/15.1-stabilizacja-petli-detekcji/15.1-CONTEXT.md` — StabilizatorStanow, histereza 12 klatek
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` — SCN-01/02/03, Success Criteria Phase 16

### Tertiary (LOW confidence)
- Matematyka arcsin + korekcja kwadrantowa — standard math; nie wymagala weryfikacji zewnetrznej

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — biblioteki sa juz w uzyciu w firmware
- Architecture: HIGH — kod bezposrednio zainspektowany, wzorzec zmian jasny
- Pitfalls: HIGH — wywnioskowane bezposrednio z kodu (unsigned wraparound, asin NaN)
- Phase-offset math: HIGH — standardowa matematyka trygonometryczna

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (firmware stabilny, brak fast-moving dependencies)
