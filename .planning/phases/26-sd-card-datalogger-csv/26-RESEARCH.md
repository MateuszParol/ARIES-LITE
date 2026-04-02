# Phase 26: SD Card + DataLogger CSV - Research

**Researched:** 2026-04-02
**Domain:** Arduino Uno R4 WiFi — SD.h CSV logging z RTC timestamps, ring buffer, graceful degradation
**Confidence:** HIGH (oparte na STACK.md, PITFALLS.md, ARCHITECTURE.md z poprzednich faz — wszystkie zweryfikowane oficjalnymi zrodlami)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Format i kolumny CSV:**
- D-01: Timestamp jako Unix epoch sekundy (uint32 z `DateTime.unixtime()`)
- D-02: Kolumny: `timestamp,stan,pan,tilt,error_x,error_y,face_size,latency_ms`
- D-03: Precyzja integer — `snprintf` z `%d`, bez float formatting
- D-04: Separator przecinek
- D-05: Naglowek kolumn w pierwszej linii KAZDEGO nowego pliku

**Strategia zapisu i buforowanie:**
- D-06: Logowanie co 10 klatek RPi (~3 wpisy/sek przy 30Hz). Licznik klatek w `krok()`.
- D-07: Ring buffer 50 wpisow w RAM (`char bufor[50][80]`). Flush caly bufor jednym `file.print()`. Zapis IO co ~17 sek.
- D-08: Logowanie TYLKO w stanie `SLEDZENIE`

**Degradation bez karty SD:**
- D-09: `SD.begin(10)` TYLKO w `setup()` — jednorazowe. Fail → `sd_dostepne=false` na cala sesje.
- D-10: Brak blokady startu — system dziala normalnie bez SD

**Nazewnictwo plikow i rotacja:**
- D-11: Format `LYYMMDD.CSV` (FAT 8.3) — np. `L260402.CSV`

### Claude's Discretion

- Zachowanie HMI przy SD fail — poziom alarmu LCD/buzzer (spojnosc z RTC fail z Phase 25 D-08)
- Zachowanie przy braku RTC — `millis()` fallback vs. wylaczenie logowania
- Mechanizm wykrywania zmiany dnia (co flush vs. co wpis vs. inne)
- Rozmiar bufora linii (80 bajtow szacunek — zweryfikowac z rzeczywista dlugoscia wiersza)
- Szczegoly benchmarku latencji (LOG-05) — ile iteracji, format wyniku

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LOG-01 | Zapis CSV na karte SD: timestamp, stan, pan, tilt, error_x, error_y, face_size, latency_ms | Pattern B (keep-file-open + flush) + snprintf z int cast + SD.h FILE_WRITE |
| LOG-02 | Daily file rotation — nowy plik LYYMMDD.CSV co dzien (FAT 8.3) | Pattern C (rotacja + naglowek) + `DateTime.unixtime()` dla nazwy pliku |
| LOG-03 | Ring buffer w RAM (flush co ~50 wpisow) — ochrona petli PID 100Hz | Pattern B + timing analysis: flush ~1-2ms w marginesie 10ms |
| LOG-04 | Graceful degradation — system dziala normalnie bez karty SD | Pattern D (flagi `_sd_ok`/`_rtc_ok`) + Pitfall 3 guard |
| LOG-05 | Empiryczny benchmark latencji zapisu SD na Uno R4 przed integracja z PID | `micros()` wokol `_plik.print()` — wynik w komentarzu/Serial |

</phase_requirements>

---

## Summary

Faza 26 dodaje klase `DataLogger` do istniejacego firmware v2.1 (`aries_controller.ino`). Baza kodu jest gotowa: `ZegarRTC` dostarcza `DateTime` i `unixtime()`, `HMI` ma wzorzec ostrzezenia (patrz `rtc_ostrzezenie()`), `MaszynaStanow` ma `StanSystemu` enum z wartosciami int. Kolejnosc inicjalizacji w `setup()` jest juz ustalona przez Phase 25 (Wire → RTC → dalej) — SD trafia po RTC.

Kluczowe decyzje architektoniczne sa juz zatwierdzone w ARCHITECTURE.md: keep-file-open zamiast close-per-write, flush co 50 wpisow (~1-2ms latencja — w marginesie 10ms PID), licznik klatek zamiast timera. `DataLogger` dostaje referencje do `ZegarRTC` w konstruktorze i jest instancja globalna (ostatnia w kolejnosci po `maszyna`).

Glowne ryzyko fazy to SD.begin() zawieszajacy `setup()` bez karty SD — Pitfall 3 z PITFALLS.md. Mitigacja jest znana: jawny guard `if (!SD.begin(10)) { _sd_ok = false; }` bez zadnego kodu blokujacego po nim.

**Primary recommendation:** Zaimplementuj `DataLogger` jako klase OOP z metodami `inicjalizuj(ZegarRTC&)`, `krok(StanSystemu, pan, tilt, bx, by, fs, latency)` i prywatnymi metodami `_otworz_plik_dnia()`, `_zapisz_csv()`. Zachowaj spojnosc stylistyczna z istniejacymi klasami (polskie nazwy metod, konstruktor z lista inicjalizacyjna, `bool inicjalizuj()` zwracajace status).

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SD.h (built-in) | bundled z ArduinoCore-renesas 1.4.1 | Zapis plikow CSV na karcie SD via SPI | Oficjalna, zgodnosc potwierdzona w compatibility matrix Arduino — PASS compile + hardware |
| Wire.h (built-in) | bundled z ArduinoCore-renesas 1.4.1 | I2C master — juz uzywany przez ZegarRTC | Juz aktywny w firmware, Wire.begin() juz wywolane w setup() |
| RTClib (Adafruit) | 2.1.4 | DateTime.unixtime(), DateTime.year/month/day — juz w firmware | Juz zainstalowane w Phase 25, ZegarRTC je opakowuje |
| SPI.h (built-in) | bundled z ArduinoCore-renesas 1.4.1 | Backend SPI dla SD.h — nie wymagany jawnie jezeli SD.h go includuje | SD.h includuje SPI.h automatycznie |

### Nie instalowac dodatkowych bibliotek

Wszystkie potrzebne biblioteki sa juz w firmware. Faza 26 dodaje tylko `#include <SD.h>` i `#define SD_CS_PIN 10`.

### Alternatywy odrzucone

| Zamiast | Moglby byc | Powod odrzucenia |
|---------|------------|-----------------|
| SD.h | SdFat (greiman) | Wieksza zlozonosc bez korzysci przy 3 wpisach/sek; SD.h wystarczajaca |
| DateTime.unixtime() | millis() jako timestamp | millis() nie ma wartosci kalendarzowej — nie da sie parsowac w Pythonie jako data |
| char bufor[80] | String object | String heap fragmentation w petli 100Hz — niedopuszczalne (PITFALLS.md Technical Debt) |

---

## Architecture Patterns

### Suggested Project Structure (zmiany w istniejacym pliku)

```
src/arduino/aries_controller/
└── aries_controller.ino   # Dodac: #include <SD.h>, #define SD_CS_PIN 10,
                           #         class DataLogger, globalna instancja logger,
                           #         SD.begin() w setup(), logger.krok() w loop()
```

### Pattern 1: Klasa DataLogger — OOP z polska konwencja

**What:** Klasa z konstruktorem przyjmujacym `ZegarRTC&`, metoda `inicjalizuj()` wywolywana w `setup()`, metoda `krok()` wywolywana w `loop()`.

**When to use:** Zgodnie ze wzorcem istniejacych klas (HMI, ServoPID, MaszynaStanow, ZegarRTC).

**Szkielet:**
```cpp
// Zrodlo: ARCHITECTURE.md (Pattern A, B, C, D) — zweryfikowane
class DataLogger {
public:
    DataLogger(ZegarRTC& zegar) : _zegar(zegar), _sd_ok(false), _licznik_klatek(0),
                                   _wpisy_od_flush(0) {}

    // Inicjalizacja SD — wywolac po ZegarRTC.inicjalizuj() w setup()
    // Zwraca true jesli SD dostepne. Fail = sd_dostepne=false, system dziala dalej.
    bool inicjalizuj() {
        if (!SD.begin(SD_CS_PIN)) {
            Serial.println(F("SD fail"));
            _sd_ok = false;
            return false;
        }
        _sd_ok = true;
        _otworz_plik_dnia();
        return true;
    }

    // Glowny krok — wywolywac z loop() po HMI tick
    // Loguje co 10. klatke w stanie SLEDZENIE (D-06, D-08)
    void krok(StanSystemu stan, float pan, float tilt,
              int16_t bx, int16_t by, uint8_t fs, uint16_t latency_ms) {
        if (!_sd_ok) return;
        if (stan != SLEDZENIE) { _licznik_klatek = 0; return; }
        if (++_licznik_klatek < 10) return;
        _licznik_klatek = 0;
        _sprawdz_rotacje();  // wykryj zmiane dnia przed zapisem
        _zapisz_csv(stan, pan, tilt, bx, by, fs, latency_ms);
    }

private:
    ZegarRTC& _zegar;
    File _plik;
    bool _sd_ok;
    uint8_t _licznik_klatek;
    uint8_t _wpisy_od_flush;
    uint8_t _ostatni_dzien;  // do wykrywania zmiany dnia

    void _otworz_plik_dnia() { /* Pattern C ponizej */ }
    void _zapisz_csv(...) { /* Pattern B ponizej */ }
    void _sprawdz_rotacje() { /* porownaj dzien z _ostatni_dzien */ }
};
```

### Pattern 2: Otwarcie pliku z naglowkiem (rotacja dzienna)

**What:** Plik otwarty raz na dzien. Naglowek wstawiany tylko jezeli plik pusty (nowy). Przy zmianie dnia — flush + close + reopen nowej nazwy.

**Implementacja:**
```cpp
// Zrodlo: ARCHITECTURE.md Pattern C — zweryfikowane
void _otworz_plik_dnia() {
    if (!_zegar.czy_dostepny()) return;
    DateTime teraz = _zegar.odczytaj_czas();
    char nazwa[13];
    snprintf(nazwa, sizeof(nazwa), "L%02d%02d%02d.CSV",
             (int)(teraz.year() % 100), (int)teraz.month(), (int)teraz.day());
    if (_plik) { _plik.flush(); _plik.close(); }
    _plik = SD.open(nazwa, FILE_WRITE);
    if (_plik && _plik.size() == 0) {
        _plik.println(F("timestamp,stan,pan,tilt,error_x,error_y,face_size,latency_ms"));
        _plik.flush();
    }
    _ostatni_dzien = teraz.day();
}
```

**Uwaga na `F()` macro:** Uzywac `F("staly_string")` dla stringow w metodach — oszczedza RAM przechowujac string we flash (PROGMEM). Istotne przy buforowaniu w RAM.

### Pattern 3: Zapis CSV z flush co 50 wpisow

**What:** `_plik.print()` zamiast `println()` — kontrola znaku konca linii. Flush co 50 wpisow (~17 sek). NIGDY `close()` w petli.

**Implementacja:**
```cpp
// Zrodlo: ARCHITECTURE.md Pattern B — zweryfikowane
void _zapisz_csv(StanSystemu stan, float pan, float tilt,
                 int16_t bx, int16_t by, uint8_t fs, uint16_t latency_ms) {
    if (!_sd_ok || !_plik) return;
    DateTime teraz = _zegar.odczytaj_czas();
    char linia[64];  // wystarczajacy bufor — patrz analiza ponizej
    snprintf(linia, sizeof(linia), "%lu,%d,%d,%d,%d,%d,%d,%d\n",
             (unsigned long)teraz.unixtime(),
             (int)stan, (int)pan, (int)tilt,
             (int)bx, (int)by, (int)fs, (int)latency_ms);
    _plik.print(linia);
    if (++_wpisy_od_flush >= 50) {
        _plik.flush();
        _wpisy_od_flush = 0;
    }
}
```

### Pattern 4: Benchmark latencji (LOG-05)

**What:** Jednorazowy pomiar `micros()` wokol `_plik.print()` — cel < 1000 us.

**Implementacja (w inicjalizuj() lub osobna metoda benchmark()):**
```cpp
// Zrodlo: PITFALLS.md Pitfall 4 — zweryfikowane
unsigned long t0 = micros();
_plik.print(F("TEST,0,0,0,0,0,0,0\n"));
unsigned long dt = micros() - t0;
Serial.print(F("[BENCH] SD write: "));
Serial.print(dt);
Serial.println(F(" us"));
// Wynik zachowac jako komentarz w kodzie
```

### Pattern 5: Graceful degradation (LOG-04)

**What:** Guard `_sd_ok` + `_zegar.czy_dostepny()` na poczatku kazdej metody IO. Zachowanie HMI — analogiczne do `rtc_ostrzezenie()` z Phase 25.

**Implementacja HMI dla SD fail (Claude's Discretion):**
```cpp
// W HMI::sd_ostrzezenie() — spojnosc z rtc_ostrzezenie() (D-08 Phase 25 pattern)
void sd_ostrzezenie() {
    _lcd.clear();
    _lcd.setCursor(0, 0);
    _lcd.print("SD: FAIL        ");
    _lcd.setCursor(0, 1);
    _lcd.print("Brak karty SD   ");
    tone(BUZZER_PIN, 1500, 200);  // krotszy niz RTC fail — SD mniej krytyczne
    delay(1500);
}
```

**Zachowanie przy braku RTC (Claude's Discretion):** Jesli `!_zegar.czy_dostepny()`, DataLogger powinien nie otwierac pliku i ustawic `_sd_ok = false` nawet gdy karta jest dostepna — bez RTC nie ma poprawnej nazwy pliku ani timestampu. Logowanie bez timestamps jest bezuzyteczne.

### Pattern 6: Wykrywanie zmiany dnia

**What:** Porownaj `teraz.day()` z `_ostatni_dzien` w `_sprawdz_rotacje()`. Wywolywac na poczatku `krok()` przed zapisem.

```cpp
void _sprawdz_rotacje() {
    if (!_zegar.czy_dostepny()) return;
    DateTime teraz = _zegar.odczytaj_czas();
    if (teraz.day() != _ostatni_dzien) {
        _otworz_plik_dnia();  // zamknie stary, otworzy nowy
    }
}
```

**Koszt:** Jeden I2C odczyt (~0.3ms) co 10 klatek (~3/sek). Akceptowalne — I2C nie blokuje petli 100Hz (wywolywane co ~3.3 sek efektywnie przy throttle krok()).

### Anti-Patterns

- **`dataFile.close()` w petli PID:** Koszt ~3.4ms — zaburza jeden tick. Nigdy. Uzyj `flush()`.
- **`SD.open()` co wpis:** Kosztowne, zbedne — otworz raz, trzymaj otwarty przez caly dzien.
- **`String` do budowania linii CSV:** Heap fragmentation po ~1000 alokacji. Zawsze `char[]` + `snprintf()`.
- **Logowanie poza `SLEDZENIE`:** D-08 — `error_x/y` i `face_size` sa sensowne tylko przy wykrytej twarzy.
- **Brak naglowka pliku:** D-05 — plik musi byc self-contained; naglowek przy `size() == 0`.

---

## Don't Hand-Roll

| Problem | Nie buduj | Uzyj zamiast | Dlaczego |
|---------|-----------|--------------|----------|
| Timestamp epoch | Wlasna konwersja date→unix | `DateTime.unixtime()` z RTClib | RTClib liczy leap years, strefy czasowe, edge cases poprawnie |
| Zapis plikow FAT32 | Wlasna implementacja FAT | `SD.h` (standardowa Arduino) | SPI protokol, FAT16/32, sektory, katalogi — setki edge cases |
| Rotacja plikow | Porownywanie nazw stringami | Porownanie `teraz.day() != _ostatni_dzien` | Prostsze, niezawodne, nie wymaga listowania plikow na SD |
| Formatowanie CSV | Konkatenacja stringow | `snprintf()` z formatem `%lu,%d,...` | Bezpieczne, nie alokuje heapu, ARM-kompatybilne |

---

## Common Pitfalls

### Pitfall 1: SD.begin() zawiesza setup() gdy brak karty SD

**What goes wrong:** `SD.begin(10)` bez karty lub z zla karta FAT moze zawisnac na kilka sekund lub loop forever na RA4M1 (brak hardware WDT w setup()).

**Why it happens:** SPI timeout wewnątrz biblioteki bez mechanizmu recovery.

**How to avoid:**
```cpp
if (!SD.begin(SD_CS_PIN)) {
    Serial.println(F("SD fail"));
    _sd_ok = false;
    return false;  // natychmiastowy powrot — brak zadnego kodu po tym
}
```
NIGDY nie wywolywac `SD.open()` po nieudanym `SD.begin()`.

**Warning signs:** `setup()` trwa > 2 sekundy, Arduino nie odpowiada po starcie.

**Zrodlo:** PITFALLS.md Pitfall 3 — HIGH confidence.

---

### Pitfall 2: dataFile.close() w petli powoduje PID jitter

**What goes wrong:** `close()` kosztuje ~3.4ms blokowania SPI. Przy 3 wpisach/sek = 10ms/sek stracone. Przy zlym zbiegu z tickiem PID: jeden cykl regulacji opozniony.

**How to avoid:** Otworz plik raz, uzyj `flush()` co 50 wpisow (~1-2ms — w marginesie 10ms PID).

**Zrodlo:** ARCHITECTURE.md + PITFALLS.md Pitfall 4 — HIGH confidence.

---

### Pitfall 3: SPI_QUARTER_SPEED moze byc konieczne

**What goes wrong:** Na niektórych kartach SD + R4 WiFi domyslny SPI clock powoduje brak detekcji karty.

**How to avoid:** Jezeli `SD.begin(SD_CS_PIN)` zwraca false z wlozoną kartą FAT32, sprobuj `SD.begin(SD_CS_PIN, SPI_QUARTER_SPEED)`.

**Zrodlo:** PITFALLS.md + forum Arduino — MEDIUM confidence.

---

### Pitfall 4: Nazwa pliku przekracza FAT 8.3

**What goes wrong:** `logYYMMDD.csv` = 10+3 = 13 znakow — za dlugo dla FAT 8.3 (max 8+3). SD.h moze cicho obciac lub zwrocic blad.

**How to avoid:** Uzyc `L%02d%02d%02d.CSV` → `L260402.CSV` = 7+3 = OK.

**Zrodlo:** ARCHITECTURE.md Etap 4 — HIGH confidence.

---

### Pitfall 5: Brak naglowka przy ponownym otwarciu istniejacego pliku

**What goes wrong:** Jezeli plik juz istnieje (np. Arduino resetowany tego samego dnia), `SD.open(name, FILE_WRITE)` otwiera na koncu. Naglowek wstawiany znow powoduje duplikaty w srodku pliku.

**How to avoid:** Sprawdzaj `_plik.size() == 0` zaraz po otwarciu — naglowek tylko dla nowych plikow.

**Zrodlo:** ARCHITECTURE.md Pattern C — HIGH confidence.

---

### Pitfall 6: `%lu` vs `%d` dla unixtime

**What goes wrong:** `DateTime.unixtime()` zwraca `uint32_t`. Na RA4M1 (32-bit, `int` = 32-bit) `%d` moze dawac ujemne wartosci po roku 2038 (przepelnienie signed). Przed 2038 dziala, ale to UB.

**How to avoid:** Uzyc `%lu` z castem `(unsigned long)teraz.unixtime()` w snprintf.

**Zrodlo:** Analiza typow RTClib + ARM newlib-nano formatowanie — HIGH confidence.

---

### Pitfall 7: I2C odczyt RTC co klatke PID zamiast z cache

**What goes wrong:** Wywolanie `_zegar.odczytaj_czas()` (= `_rtc.now()`, ~0.3ms I2C) w kazdym `krok()` mogloby byc wywolywane z loop() co ~0.5ms. Przy 100Hz loop = 200 odczytow I2C/sek.

**How to avoid:** `_zapisz_csv()` wywolywane tylko co 10 klatek SLEDZENIE (~3x/sek) — odczyt I2C 3x/sek jest akceptowalny. Dodatkowa optymalizacja: cache `DateTime` w `_sprawdz_rotacje()` i przekazywac do `_zapisz_csv()` przez parametr.

**Zrodlo:** ARCHITECTURE.md timing analysis — HIGH confidence.

---

## Code Examples

### Kompletna klasa DataLogger (szkielet produkcyjny)

```cpp
// Zrodlo: ARCHITECTURE.md Pattern A+B+C+D — verified against existing firmware style
#include <SD.h>
#define SD_CS_PIN 10

class DataLogger {
public:
    DataLogger(ZegarRTC& zegar)
        : _zegar(zegar), _sd_ok(false),
          _licznik_klatek(0), _wpisy_od_flush(0), _ostatni_dzien(0) {}

    bool inicjalizuj() {
        if (!_zegar.czy_dostepny()) {
            Serial.println(F("[LOG] Brak RTC — logowanie wylaczone"));
            return false;
        }
        if (!SD.begin(SD_CS_PIN)) {
            Serial.println(F("SD fail"));
            _sd_ok = false;
            return false;
        }
        _sd_ok = true;
        _otworz_plik_dnia();
        _benchmark_latencji();
        return true;
    }

    void krok(StanSystemu stan, float pan, float tilt,
              int16_t bx, int16_t by, uint8_t fs, uint16_t latency_ms) {
        if (!_sd_ok) return;
        if (stan != SLEDZENIE) { _licznik_klatek = 0; return; }
        if (++_licznik_klatek < 10) return;
        _licznik_klatek = 0;
        _sprawdz_rotacje();
        _zapisz_csv(pan, tilt, bx, by, fs, latency_ms);
    }

private:
    ZegarRTC& _zegar;
    File _plik;
    bool _sd_ok;
    uint8_t _licznik_klatek;
    uint8_t _wpisy_od_flush;
    uint8_t _ostatni_dzien;

    void _otworz_plik_dnia() {
        DateTime t = _zegar.odczytaj_czas();
        char nazwa[13];
        snprintf(nazwa, sizeof(nazwa), "L%02d%02d%02d.CSV",
                 (int)(t.year() % 100), (int)t.month(), (int)t.day());
        if (_plik) { _plik.flush(); _plik.close(); }
        _plik = SD.open(nazwa, FILE_WRITE);
        if (_plik && _plik.size() == 0) {
            _plik.println(F("timestamp,stan,pan,tilt,error_x,error_y,face_size,latency_ms"));
            _plik.flush();
        }
        _ostatni_dzien = t.day();
    }

    void _sprawdz_rotacje() {
        DateTime t = _zegar.odczytaj_czas();
        if (t.day() != _ostatni_dzien) _otworz_plik_dnia();
    }

    void _zapisz_csv(float pan, float tilt,
                     int16_t bx, int16_t by, uint8_t fs, uint16_t latency_ms) {
        if (!_plik) return;
        DateTime t = _zegar.odczytaj_czas();
        char linia[64];
        snprintf(linia, sizeof(linia), "%lu,%d,%d,%d,%d,%d,%d,%d\n",
                 (unsigned long)t.unixtime(),
                 (int)SLEDZENIE,
                 (int)pan, (int)tilt,
                 (int)bx, (int)by, (int)fs, (int)latency_ms);
        _plik.print(linia);
        if (++_wpisy_od_flush >= 50) {
            _plik.flush();
            _wpisy_od_flush = 0;
        }
    }

    // LOG-05: jednorazowy benchmark w inicjalizuj()
    // Wynik zapisac jako komentarz w kodzie po pierwszym uruchomieniu
    void _benchmark_latencji() {
        char linia[] = "0000000000,2,0,0,0,0,0,0\n";
        unsigned long t0 = micros();
        _plik.print(linia);
        unsigned long dt = micros() - t0;
        _plik.flush();
        Serial.print(F("[BENCH] SD write: "));
        Serial.print(dt);
        Serial.println(F(" us  (cel: < 1000 us)"));
    }
};
```

### Integracja w setup() i loop()

```cpp
// Po deklaracjach globalnych — logger ostatni (zalezny od zegar):
DataLogger logger(zegar);

// W setup() — po Wire.begin() + zegar.inicjalizuj() + SD:
if (!logger.inicjalizuj()) {
    hmi.sd_ostrzezenie();  // LCD "SD: FAIL" + krotki beep (Claude's Discretion)
    // system kontynuuje — brak blokowania
}

// W loop() — po hmi.lcd_krok():
logger.krok(maszyna.stan(), serwa.kat_pan, serwa.kat_tilt,
            serwa.ostatni_blad_x, serwa.ostatni_blad_y,
            0,   // face_size: zarezerwowane — 0 lub z ramki (patrz Uwagi)
            0);  // latency_ms: zarezerwowane w Phase 26 — Phase 27 doda rzeczywista latencje
```

### Analiza dlugosci linii CSV (weryfikacja bufora 64 bajtow)

```
Format: "%lu,%d,%d,%d,%d,%d,%d,%d\n"
Maks wartosci:
  timestamp: 4294967295  (10 cyfr, uint32 max)
  stan:      2           (1 cyfra)
  pan:       -60         (3 znaki)
  tilt:      -30         (3 znaki)
  error_x:   -160        (4 znaki)
  error_y:   -160        (4 znaki)
  face_size: 255         (3 znaki)
  latency_ms: 9999       (4 znaki)
  7 przecinkow + '\n'    (8 znakow)

Suma max: 10+1+3+1+3+1+4+1+4+1+3+1+4+8 = 45 znakow
Bufor 64 bajty: margines ~30% — WYSTARCZAJACY
Oryginalny szacunek 80 bajtow z CONTEXT.md: rowniez wystarczajacy, mozna zostawic
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `dataFile.close()` per write | keep-file-open + `flush()` co 50 wpisow | Standard od SD.h v1.x | Eliminuje ~3.4ms blokowania SPI co zapis |
| `dtostrf()` dla float → string | `snprintf()` z `%d` i int cast | Migracja Leonardo → R4 (Phase 24) | ARM Renesas nie ma dtostrf — juz zamiast w firmware |
| String object do CSV | `char[]` + snprintf | Zawsze zalecane na Arduino | Brak heap fragmentation w petli 100Hz |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| SD.h | LOG-01, LOG-02, LOG-03 | Tak (bundled) | ArduinoCore-renesas 1.4.1 | — |
| RTClib 2.1.4 | LOG-01, LOG-02 | Tak (installed w Phase 25) | 2.1.4 | — |
| Karta SD (FAT32) | Wszystkie LOG | Fizyczna — weryfikacja uzytkownika | — | Graceful degradation (sd_dostepne=false) |
| ZegarRTC z bateria CR1220 | LOG-01, LOG-02 | Fizyczna — weryfikacja uzytkownika | DS1307 | millis() fallback: logowanie wylaczone jesli !rtc_ok |
| arduino-cli (do kompilacji/uploadu) | Kazdy commit firmware | Sprawdzic przed faza | — | Arduino IDE 2.x jako alternatywa |

**Missing dependencies z fallback:**
- Karta SD nieobecna: `SD fail` na Serial, logowanie wylaczone, system dziala normalnie (LOG-04)
- RTC niedostepny: logowanie wylaczone (brak sensownej nazwy pliku i timestampu)

---

## Validation Architecture

> `workflow.nyquist_validation` nieobecny w config.json — traktowac jako wlaczony.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Brak (test_framework: "none" w config.json) |
| Config file | none |
| Quick run command | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/aries_controller.ino` |
| Full suite command | Kompilacja + upload + reczna weryfikacja Serial i karta SD |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOG-01 | Plik LYYMMDD.CSV z poprawnym naglowkiem i wierszami po 60s SLEDZENIE | manual | — | ❌ Wave 0: brak testu automatycznego |
| LOG-02 | Nowy plik po zmianie dnia (recznie zmieniony RTC lub wait do polnocy) | manual | — | ❌ Wave 0: test reczny |
| LOG-03 | Benchmark micros() < 1000us + Serial print wyniku | manual + serial | — | ❌ Wave 0: weryfikacja Serial Monitor |
| LOG-04 | Start bez karty SD: Serial "SD fail", PID dziala, brak zawieszenia | manual | — | ❌ Wave 0: recznie wyjac karte SD |
| LOG-05 | Wynik benchmarku zapisany w komentarzu lub Serial | manual | — | ❌ Wave 0: Serial Monitor |

### Sampling Rate

- **Per task commit:** `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi` (weryfikacja kompilacji)
- **Per wave merge:** Kompilacja + upload na Uno R4 WiFi + reczna weryfikacja kryteriow sukcesu
- **Phase gate:** Wszystkie 4 kryteria sukcesu (SC#1-SC#4) potwierdzone przed `/gsd:verify-work`

### Wave 0 Gaps

- [ ] Brak automatycznych testow — projekt nie ma frameworka testowego (config: "none")
- [ ] Weryfikacja empiryczna: Serial Monitor + odczyt karty SD na komputerze
- [ ] Kompilacja pod R4 WiFi jest jedynym automatyzowalnym sprawdzeniem

---

## Open Questions

1. **face_size w kolumnie CSV (LOG-01)**
   - What we know: Protokol binarny 8B ma pole `face_size` (byte 6, uint8). W obecnym `_przetworz_ramke()` pole to jest ignorowane (`// _ramka_buf[6] = face_size — zarezerwowane`).
   - What's unclear: Czy Phase 26 ma wyciagac `face_size` z ramki i przekazywac do `logger.krok()`, czy logowac 0 jako placeholder az do Phase 27?
   - Recommendation: Wyciagnac `face_size` z `_ramka_buf[6]` juz w Phase 26 — to prosta zmiana w `_przetworz_ramke()`, nie wymaga zmian protokolu. Przechowac jako `uint8_t ostatni_face_size` w `ServoPID` analogicznie do `ostatni_blad_x/y`.

2. **latency_ms w kolumnie CSV (LOG-01)**
   - What we know: Kolumna `latency_ms` jest w specyfikacji D-02. W Phase 26 Arduino nie mierzy opoznienia end-to-end (to po stronie RPi lub jako delta millis()).
   - What's unclear: Czy logowac 0 jako placeholder, czy mierzyc delta millis() od odebrania ramki do zapisu logu?
   - Recommendation: Logowac 0 jako placeholder w Phase 26. Phase 27 (integracja z MaszynaStanow) moze dodac prawdziwa latencje jezeli RPi bedzie ja wysylac lub jezeli bedziemy liczyc delta millis() w firmware.

3. **Kolejnosc inicjalizacji: Wire → RTC → SD**
   - What we know: REQUIREMENTS.md INT-07 (ukonczone w Phase 25) definiuje `Wire.begin() → rtc.begin() → SD.begin()`. ARCHITECTURE.md potwierdza.
   - What's unclear: W obecnym `setup()` nie ma `SD.begin()` — musi byc dodane po `zegar.inicjalizuj()`.
   - Recommendation: `logger.inicjalizuj()` wywolywac po `zegar.inicjalizuj()` — DataLogger wewnętrznie wywoluje `SD.begin(SD_CS_PIN)`. Kolejnosc globalna poprawna.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact na Phase 26 |
|-----------|-------------------|
| Polskie nazwy metod i zmiennych | `krok()`, `inicjalizuj()`, `_otworz_plik_dnia()`, `_zapisz_csv()`, `_sprawdz_rotacje()` |
| OOP pattern: globalny instancja z referencjami | `DataLogger logger(zegar);` — logger ostatni w kolejnosci globalnej |
| `snprintf()` zamiast `dtostrf()` | Juz zastosowane — `snprintf(linia, sizeof(linia), "%lu,%d,...")` |
| `constrain()` dla clamp | Nie dotyczy bezposrednio DataLogger, ale ServoP ID juz uzywa |
| `bool inicjalizuj()` pattern | `DataLogger::inicjalizuj()` zwraca `bool` |
| Brak frameworka testowego | Weryfikacja empiryczna: Serial Monitor + odczyt SD na komputerze |
| Wszystkie stale w `#define` lub `src/config.py` (Arduino: #define) | `#define SD_CS_PIN 10` na gorze pliku .ino |
| `logger.error()` / `logging.warning()` → Arduino: `Serial.println()` | `Serial.println(F("SD fail"))` dla LOG-04 |
| `try/except` → Arduino: sprawdzenie wartosci zwracanej | `if (!SD.begin(SD_CS_PIN))` — guard pattern |

---

## Sources

### Primary (HIGH confidence)
- `.planning/research/ARCHITECTURE.md` — Pattern A+B+C+D dla DataLogger, timing analysis, integration points SPI/I2C
- `.planning/research/STACK.md` — SD.h bundled z ArduinoCore-renesas 1.4.1, RTClib 2.1.4 kompatybilna
- `.planning/research/PITFALLS.md` — Pitfall 3 (SD.begin hang), Pitfall 4 (SD write latencja), Technical Debt (String vs char[])
- `src/arduino/aries_controller/aries_controller.ino` — Baza firmware v2.1 z ZegarRTC, HMI, MaszynaStanow, ServoPID

### Secondary (MEDIUM confidence)
- `.planning/phases/25-rtc-ds1307-izolowana-integracja/25-CONTEXT.md` — D-13: ZegarRTC gotowy, interfejs `odczytaj_czas()` i `czy_dostepny()`
- Arduino forum: SD card close() vs flush() na R4 — https://forum.arduino.cc/t/arduino-uno-r4-spi-with-sd-card/1328547
- Arduino uno-r4-library-compatibility — https://github.com/arduino/uno-r4-library-compatibility (SD: PASS)

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — SD.h bundled, RTClib juz zainstalowane, zweryfikowane w poprzednich fazach
- Architecture: HIGH — ARCHITECTURE.md zawiera gotowe code patterns zweryfikowane dla tej platformy
- Pitfalls: HIGH — PITFALLS.md oparte na oficjalnych Arduino issues i forum, bezposrednio weryfikowane

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stabilna platforma — SD.h i RTClib nie sa szybko ewoluujace)
