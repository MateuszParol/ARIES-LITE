# Phase 27: Pelna Integracja DataLogger z MaszynaStanow - Research

**Researched:** 2026-04-04
**Domain:** Arduino firmware (Renesas RA4M1) — integracja OOP: DataLogger + MaszynaStanow, logowanie zmian stanow, face_size z ramki binarnej, komenda serialowa zrzutu bufora, E2E z RPi
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Logowac WSZYSTKIE przejscia stanow: BEZCZYNNOSC/SKANOWANIE/SLEDZENIE — pelny audit trail sesji
- **D-06:** Komenda serialowa do zrzutu ostatnich 10 wpisow bufora DataLogger na Serial — umozliwia weryfikacje bez fizycznego dostepu do karty SD

### Claude's Discretion

- **D-02:** Mechanizm powiadamiania DataLogger o zmianie stanu (bezposrednie wywolanie, flaga+poll, lub porownanie w loop). Wybrac najprostszy sposob spojny z istniejaca architektura OOP
- **D-03:** Zrodlo face_size — ramka binarna 8B zawiera face_size jako uint8 (bajt 6). Udostepnic przez MaszynaStanow lub ServoPID i przekazac do logger.krok()
- **D-04:** Definicja latency_ms — czas petli loop(), czas reakcji PID, lub 0 jesli niemierzalne. Wybrac co daje najwiecej wartosci diagnostycznej
- **D-05:** Format wiersza CSV dla zmiany stanu — ten sam format co telemetria (prosty parsing) lub dedykowany marker. Wybrac co latwiej parsowac w Python/pandas
- **D-07:** Trigger komendy zrzutu bufora — wyslanie znaku/sekwencji na Serial (np. bajt 'D' lub dedykowana ramka)

### Deferred Ideas (OUT OF SCOPE)

Brak — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INT-06 | Klasa DataLogger (OOP) zintegrowana z MaszynaStanow — logowanie zmian stanow | Bezposrednie wywolanie `_logger.loguj_zmiane_stanu()` w `_przejdz_do()` po dodaniu referencji `DataLogger&` do konstruktora MaszynaStanow |
| INT-08 | End-to-end: firmware z DataLogger dziala na Uno R4 z pelnym trackingiem RPi | face_size z bajtu 6 ramki 8B, latency_ms z millis() delta petli loop(), komenda serialowa 'D' do weryfikacji bez wyjmowania karty SD |
</phase_requirements>

---

## Summary

Faza 27 domyka integracje DataLogger z MaszynaStanow — to ostatni krok v2.1 milestonu. Infrastruktura jest w pelni gotowa z Phase 26: DataLogger dziala, karta SD i RTC sa zainicjalizowane, `logger.krok()` wywolywany z `loop()`. Pozostaja cztery zmiany: (1) przekazanie referencji `DataLogger&` do konstruktora `MaszynaStanow` i wywolanie `loguj_zmiane_stanu()` w `_przejdz_do()`, (2) wyciagniecie `face_size` z bajtu `_ramka_buf[6]` i zapisanie go jako pole `MaszynaStanow`, (3) uzupelnienie `latency_ms` rzeczywista wartoscia (czas petli loop()), (4) komenda serialowa `'D'` w parserze loop() ktora zrzuca ostatnie 10 wpisow bufora na Serial.

Kluczowe ustalenie architektoniczne (z ARCHITECTURE.md): DataLogger write ~0.35ms, flush ~1-2ms — oba mieszcza sie w marginesie 10ms petli PID. Logowanie zmian stanow jest wywolaniem jednorazowym (nie throttlowanym), takze bezpiecznym. Nowa metoda `loguj_zmiane_stanu()` musi NIEZALEZNIE od filtra `stan != SLEDZENIE` w `krok()` — zmiany stanow logowane zawsze gdy SD dostepne.

**Primary recommendation:** Dodac `DataLogger& _logger` do konstruktora `MaszynaStanow`, wywolac `_logger.loguj_zmiane_stanu()` w `_przejdz_do()`, dodac `uint8_t ostatni_face_size` jako publiczne pole `MaszynaStanow` wypelnianie z `_ramka_buf[6]`, mierzyc `latency_ms` jako `(uint16_t)(millis() - _czas_ostatniej_ramki)` w momencie zapisu — wskazuje na swizosc danych z RPi.

---

## Standard Stack

### Core (bez zmian wzgledem Phase 26)

| Biblioteka | Wersja | Cel | Uwaga |
|-----------|--------|-----|-------|
| SD.h | stdlib Arduino | SPI zapis CSV na karte SD | Juz w firmware, brak zmian |
| RTClib (Adafruit) | 2.1.4 | Timestamps DS1307 | Juz w firmware, brak zmian |
| QuickPID | 3.1.9 | PID 100Hz dual-axis | Juz w firmware, brak zmian |
| Servo | >=1.2.2 | PWM serwa MG-90S | Juz w firmware, brak zmian |
| Wire.h | stdlib Arduino | I2C master dla DS1307 | Juz w firmware, brak zmian |

**Brak nowych bibliotek** — faza 27 to czyste zmiany firmware OOP, bez nowych zaleznosci.

**Platforma:** Arduino Uno R4 WiFi (Renesas RA4M1), ArduinoCore-renesas >=1.4.1

**Flash command:**
```bash
arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/
arduino-cli upload  --fqbn arduino:renesas_uno:unor4wifi --port /dev/ttyACM0 src/arduino/aries_controller/
```

---

## Architecture Patterns

### Istniejaca struktura klas (po Phase 26)

```
aries_controller.ino
├── HMI                    — LCD, buzzer, przycisk (nie zmienia sie)
├── ServoPID               — QuickPID dual-axis, pola publiczne: kat_pan, kat_tilt, ostatni_blad_x/y
├── ZegarRTC               — adapter RTClib (nie zmienia sie)
├── DataLogger(ZegarRTC&)  — krok(), inicjalizuj() (dodajemy: loguj_zmiane_stanu())
├── MaszynaStanow(ServoPID&, HMI&)  — dodajemy: DataLogger& _logger, uint8_t ostatni_face_size
│
└── Kolejnosc globalnych instancji:
    ZegarRTC zegar;
    ServoPID serwa;
    HMI hmi;
    MaszynaStanow maszyna(serwa, hmi);   ← zmiana: maszyna(serwa, hmi, logger)
    DataLogger logger(zegar);            ← ale logger jest po maszyna — kolejnosc problematyczna!
```

**PROBLEM KOLEJNOSCI GLOBALNYCH INSTANCJI (krytyczny):**

Aktualny kod deklaruje `maszyna` PRZED `logger`. Jesli konstruktor `MaszynaStanow` przyjmie `DataLogger& _logger` jako argument, logger musi byc zadeklarowany PRZED maszyna. Wymaga to zmiany kolejnosci globalnych instancji:

```cpp
// PRZED (Phase 26):
ZegarRTC zegar;
ServoPID serwa;
HMI hmi;
MaszynaStanow maszyna(serwa, hmi);
DataLogger logger(zegar);

// PO (Phase 27):
ZegarRTC zegar;
ServoPID serwa;
HMI hmi;
DataLogger logger(zegar);              // logger PRZED maszyna
MaszynaStanow maszyna(serwa, hmi, logger);  // maszyna przyjmuje referencje do logger
```

Alternatywa bez zmiany kolejnosci: wskaznik `DataLogger* _logger` inicjalizowany jako `nullptr` w konstruktorze, ustawiany metoda `ustaw_logger(DataLogger& l)` w `setup()`. Prostsze ale mniej idiomatyczne — preferowac zmiane kolejnosci.

### Pattern 1: Bezposrednie wywolanie w _przejdz_do() (rekomendacja dla D-02)

**Co:** `_logger.loguj_zmiane_stanu(nowy, _serwa.kat_pan, _serwa.kat_tilt)` wywolywane bezposrednio w `_przejdz_do()` zaraz po zmianie `_stan_systemu`.

**Kiedy:** Zawsze gdy nastepuje zmiana stanu — z ramki binarnej, z watchdog, z przycisku abort.

**Dlaczego najlepsze:** Spojne z istniejacym wzorcem `_hmi.buzzer_beep()` i `_serwa.pid_reset()` w `_przejdz_do()`. Brak dodatkowego stanu do pollowania. Wywolanie jednorazowe per przejscie — timing < 0.5ms (nie zaburza PID).

**Przykladowy kod:**
```cpp
void _przejdz_do(StanSystemu nowy) {
    StanSystemu stary = _stan_systemu;  // zachowaj stary stan do logu
    _stan_systemu = nowy;
    _logger.loguj_zmiane_stanu(stary, nowy, _serwa.kat_pan, _serwa.kat_tilt);
    if (nowy == SKANOWANIE) {
        _serwa.resetuj_czas_skanu();
        _serwa.pid_reset();
    } else if (nowy == SLEDZENIE) {
        _hmi.buzzer_beep();
        _serwa.pid_reset();
    }
}
```

### Pattern 2: Nowa metoda DataLogger::loguj_zmiane_stanu()

**Co:** Odrebna metoda logujaca zmiane stanu — NIE filtrowana przez `stan == SLEDZENIE`. Uzywa tego samego formatu CSV co `krok()` dla prosty parsing (D-05).

**Format CSV dla zmiany stanu (decyzja D-05):** Uzywac tego samego formatu co telemetria, z `face_size=0` i `latency_ms=0` — prosty parsing w pandas bez obslugi specjalnych markerow. Stan w kolumnie `stan` juz rozroznia SLEDZENIE (2) od SKANOWANIE (1) i BEZCZYNNOSC (0).

```cpp
// W klasie DataLogger — nowa metoda publiczna
void loguj_zmiane_stanu(StanSystemu stary, StanSystemu nowy,
                        float pan, float tilt) {
    if (!_sd_ok || !_plik) return;
    _sprawdz_rotacje();
    // Ten sam format co _zapisz_csv(), face_size=0, latency_ms=0
    DateTime teraz = _zegar.odczytaj_czas();
    char linia[64];
    snprintf(linia, sizeof(linia), "%lu,%d,%d,%d,0,0,0,0",
             (unsigned long)teraz.unixtime(),
             (int)nowy, (int)pan, (int)tilt);
    _plik.println(linia);
    // flush natychmiastowy — zdarzenie krytyczne, nie czekamy na bufor 50
    _plik.flush();
    _wpisy_od_flush = 0;  // reset licznika bufora
}
```

**Uzasadnienie natychmiastowego flush:** Zmiana stanu to rzadkie zdarzenie (~kilka razy na sesje), nie degraduje PID. Utrata wpisu o zmianie stanu przy power-loss bylaby krytyczna dla analizy — warto flushnac natychmiast.

### Pattern 3: face_size z ramki binarnej (decyzja D-03)

**Co:** `_ramka_buf[6]` zawiera `face_size` (uint8) z protokolu 8B. Aktualnie bajt jest parsowany ale ignorowany (`// _ramka_buf[6] = face_size — zarezerwowane`).

**Rekomendacja:** Dodac publiczne pole `uint8_t ostatni_face_size` do `MaszynaStanow`, wypelniac w `_przetworz_ramke()`, czytac z `loop()` przy wywolaniu `logger.krok()`.

```cpp
// W MaszynaStanow (pole publiczne, jak ostatni_blad_x w ServoPID):
uint8_t ostatni_face_size;

// W _przetworz_ramke():
_serwa.ostatni_blad_x = blad_x;
_serwa.ostatni_blad_y = blad_y;
ostatni_face_size = _ramka_buf[6];  // NOWE

// W loop():
logger.krok(maszyna.stan(), serwa.kat_pan, serwa.kat_tilt,
            serwa.ostatni_blad_x, serwa.ostatni_blad_y,
            maszyna.ostatni_face_size,   // NOWE zamiast 0
            latency_ms);                 // NOWE zamiast 0
```

### Pattern 4: latency_ms — czas od ostatniej ramki (decyzja D-04)

**Rekomendacja:** `latency_ms = (uint16_t)(millis() - maszyna.czas_ostatniej_ramki())`. Wskazuje na "swizosc" danych z RPi — ile czasu minelo od ostatniego pakietu Serial do momentu zapisu. Przy 30Hz normalnie ~33ms. Spike >100ms sygnalizuje utrate pakietow lub opoznienie serial. Ma konkretna wartosc diagnostyczna.

`czas_ostatniej_ramki()` jest juz publicznym getterem w MaszynaStanow (linia 443).

```cpp
// W loop() przed wywolaniem logger.krok():
uint16_t latency_ms = (uint16_t)(millis() - maszyna.czas_ostatniej_ramki());

logger.krok(maszyna.stan(), serwa.kat_pan, serwa.kat_tilt,
            serwa.ostatni_blad_x, serwa.ostatni_blad_y,
            maszyna.ostatni_face_size,
            latency_ms);
```

### Pattern 5: Komenda serialowa zrzutu bufora (D-06, D-07)

**Trigger (rekomendacja dla D-07):** Bajt `'D'` (ASCII 68) — jednoterminowy, nie koliduje z protocolem 8B (startuje od 0xAA). Detekcja w parserze Serial w `loop()` PRZED `maszyna.przetwarzaj_bajt()`.

**Mechanizm zrzutu:** DataLogger przechowuje ostatnie 10 wpisow w krazacym buforze RAM (tablica `char[10][64]`, licznik zapisu). Metoda `zrzuc_ostatnie()` wypisuje je na Serial. Ten bufor jest NIEZALEZNY od ring buffer 50-wpisow SD — sluzy tylko diagnostyce.

```cpp
// W DataLogger — dodatkowy bufor diagnostyczny 10 wpisow
// (10 * 64 = 640 bajtow RAM — akceptowalne przy 32KB)
char _bufor_diagnostyczny[10][64];
uint8_t _idx_diagnostyczny;  // krazacy wskaznik

// Przy kazdym zapisie CSV (w _zapisz_csv() i loguj_zmiane_stanu()):
// skopiuj linie do _bufor_diagnostyczny[_idx_diagnostyczny % 10]
// _idx_diagnostyczny++

// Nowa metoda publiczna:
void zrzuc_ostatnie() {
    Serial.println(F("[DUMP] Ostatnie 10 wpisow DataLogger:"));
    for (uint8_t i = 0; i < 10; i++) {
        uint8_t idx = (_idx_diagnostyczny + i) % 10;
        if (_bufor_diagnostyczny[idx][0] != '\0') {
            Serial.println(_bufor_diagnostyczny[idx]);
        }
    }
    Serial.println(F("[DUMP] Koniec."));
}

// W loop(), PRZED maszyna.przetwarzaj_bajt():
while (Serial.available() > 0) {
    uint8_t bajt = (uint8_t)Serial.read();
    if (bajt == 'D') {
        logger.zrzuc_ostatnie();
        // NIE przekazywac 'D' do maszyna.przetwarzaj_bajt()
    } else {
        maszyna.przetwarzaj_bajt(bajt);
    }
}
```

**Uzasadnienie 'D':** Nie zaczyna sie od 0xAA (protokol 8B marker), wiec parser MaszynaStanow go ignoruje nawet gdy przypadkowo dotrze. Latwiejsze do wyslania z pyserial: `ser.write(b'D')`.

### Anti-Patterns to Avoid

- **Nie uzywac `_logger.loguj_zmiane_stanu()` w `krok()`** — `krok()` ma throttle 10 klatek i filtr SLEDZENIE. Zmiany stanow musza byc w `_przejdz_do()`.
- **Nie flusznac SD co wpis telemetrii** — flush co 50 wpisow (juz zaimplementowane). Loguj_zmiane_stanu flusznac natychmiastowo (jednorazowe zdarzenie).
- **Nie zmieniac kolejnosci `Wire.begin() -> RTC -> SD`** — ustalona w Phase 25 (INT-07).
- **Nie uzywac `String`** — `char[]` + `snprintf()` we wszystkich nowych funkcjach.
- **Nie blokowac parsera Serial** — detekcja 'D' musi byc non-blocking i nie przerywac przetwarzania ramek 8B.

---

## Don't Hand-Roll

| Problem | Nie budowac | Uzyc | Dlaczego |
|---------|-------------|------|----------|
| Formatowanie CSV | Wlasny serializer | `snprintf(linia, sizeof(linia), "%lu,%d,%d,%d,...", ...)` | Juz uzyty w `_zapisz_csv()` — spojnosc |
| Timestamp | millis() jako fallback | `_zegar.odczytaj_czas().unixtime()` | RTC juz dostepny, millis() rollover po 49 dniach |
| Komenda serialowa | Nowy protokol binarny | Pojedynczy bajt 'D' w petli Serial | Prostsze od rozszerzenia protokolu 8B; brak ryzyka kolizji |
| Bufor diagnostyczny | Zewnetrzna klasa bufora | `char[10][64]` + `uint8_t _idx` w DataLogger | KISS — 640B RAM, deterministyczny czas, brak alokacji |

---

## Common Pitfalls

### Pitfall 1: Kolejnosc globalnych instancji — logger przed maszyna

**Co sie psuje:** Kompilator C++ inicjalizuje globalne obiekty w kolejnosci deklaracji. Jesli `maszyna` jest zadeklarowana przed `logger`, a konstruktor `MaszynaStanow` przyjmuje `DataLogger&`, referencja `_logger` wskazuje na nieinicjalizowany obiekt w czasie wywolania konstruktora `maszyna`.

**Dlaczego:** C++ standard nie gwarantuje bezpiecznej inicjalizacji referencji do obiektow zadeklarowanych pozniej.

**Jak unikac:** Zmienic kolejnosc deklaracji globalnych: `logger` PRZED `maszyna`. Sprawdzic po zmianie ze `sizeof(DataLogger)` nie przekracza marginesu RAM.

**Warning signs:** Niespodziewany crash przy starcie (watchdog reset) lub `_sd_ok` false mimo poprawnej karty SD.

### Pitfall 2: loguj_zmiane_stanu() wywolywana przy KAZDEJ iteracji watchdog_krok() gdy stan sie nie zmienia

**Co sie psuje:** `watchdog_krok()` wywoluje `_przejdz_do(SKANOWANIE)` co iteracje jesli timeout, ale tylko przy rzeczywistej zmianie stanu. Sprawdzenie `if (nowy != _stan_systemu)` juz istnieje w `_przetworz_ramke()` ale NIE w `watchdog_krok()` — watchdog wywoluje `_przejdz_do()` bezwarunkowo (moze wielokrotnie logowac ten sam przejscie).

**Jak unikac:** W `_przejdz_do()` dodac guard: `if (nowy == _stan_systemu) return;` jako pierwsza linia — unikamy powtornego logowania tego samego stanu.

### Pitfall 3: Bufor diagnostyczny 10 wpisow — krazacy indeks i wyswietlanie kolejnosci

**Co sie psuje:** Krazacy bufor (circular) bez poprawnego obliczenia poczatku sekwencji pokazuje wpisy w niepoprawnej kolejnosci chronologicznej.

**Jak unikac:** `_idx_diagnostyczny` wskazuje na NASTEPNA pozycje zapisu. Najstarszy wpis = `_idx_diagnostyczny % 10`. Iteracja: `for (i=0; i<10; i++) { idx = (_idx_diagnostyczny + i) % 10; }` — daje chronologicznie od najstarszego do najnowszego.

### Pitfall 4: Bajt 'D' w strumieniu danych 8B od RPi

**Co sie psuje:** Bajt 0x44 ('D' ASCII) moze pojawic sie wewnatrz legalnej ramki 8B jako czesc payload (error_x, error_y, face_size). Parser serial przechwytuje go jako komende zrzutu mimo ze jest czescia ramki.

**Jak unikac:** Detekcja 'D' TYLKO w stanie parsera `CZEKAJ_START` (oczekiwanie na 0xAA). W stanie `CZYTAJ_PAYLOAD` bajty sa przekazywane do `maszyna.przetwarzaj_bajt()` bez filtracji. Lub: modyfikowac logike parsera w `loop()` tak, ze 'D' jest interceptowane TYLKO gdy biezacy stan parsera MaszynaStanow to CZEKAJ_START.

**Prosta implementacja:** Sprawdzac `_stan_parsera == CZEKAJ_START` przed przechwyceniem 'D'. Ale `_stan_parsera` jest prywatny w MaszynaStanow — dodac publiczny getter `StanParsera stan_parsera() const` lub interceptowac bajt przed wywolaniem `maszyna.przetwarzaj_bajt()` tylko gdy ostatni odebrany bajt byl 0xAA (czyli aktualnie w payload) — zbyt skomplikowane.

**Najprostsza bezpieczna implementacja:** Akceptowac falszywy trigger gdy 'D' pojawi sie w payload — zrzut bufora to operacja diagnostyczna, false trigger nie uszkadza danych. Wpisy beda z nazwy pliku widoczne ze to byl trigger a nie koniec sesji. W praktyce przy normalnym uzyciu prawie sie nie zdarza.

### Pitfall 5: SD write latencja przy loguj_zmiane_stanu() + natychmiastowy flush

**Co sie psuje:** Flush SD kosztuje ~1-2ms. Logowanie zmiany stanu wywolywane z `_przejdz_do()` ktore jest czesc `pid_krok()` wywolania — moze wydluzyc jedna iteracje petli.

**Dlaczego nie jest problemem:** `_przejdz_do()` NIE jest wywolywane z `pid_krok()`. Jest wywolywane z `przetwarzaj_bajt()` (parser Serial) lub `watchdog_krok()` — oba sa PRZED `pid_krok()` w kolejnosci loop(). Zmiana stanu to rzadkie zdarzenie (nie co-tick). Worst case: flush ~2ms w jednej iteracji loop() — wciaz w marginesie 10ms PID.

---

## Code Examples

Verified patterns z istniejacego firmware (HIGH confidence — bezposrednie odczytanie z aries_controller.ino):

### Zmiana kolejnosci globalnych instancji

```cpp
// Kolejnosc PRZED Phase 27 (linie 662-666):
ZegarRTC zegar;
ServoPID serwa;
HMI hmi;
MaszynaStanow maszyna(serwa, hmi);
DataLogger logger(zegar);

// Kolejnosc PO Phase 27:
ZegarRTC zegar;
ServoPID serwa;
HMI hmi;
DataLogger logger(zegar);              // PRZESUNIETY przed maszyna
MaszynaStanow maszyna(serwa, hmi, logger);  // nowy parametr
```

### Modyfikacja konstruktora MaszynaStanow

```cpp
// Oryginalny konstruktor (linie 364-371):
class MaszynaStanow {
public:
    MaszynaStanow(ServoPID& serwa, HMI& hmi) :
        _serwa(serwa), _hmi(hmi),
        _stan_systemu(BEZCZYNNOSC),
        _ramka_idx(0), _stan_parsera(CZEKAJ_START),
        _czas_ostatniej_ramki(0) {}

// Po zmianie:
class MaszynaStanow {
public:
    uint8_t ostatni_face_size;  // NOWE pole publiczne

    MaszynaStanow(ServoPID& serwa, HMI& hmi, DataLogger& logger) :
        _serwa(serwa), _hmi(hmi), _logger(logger),
        _stan_systemu(BEZCZYNNOSC),
        _ramka_idx(0), _stan_parsera(CZEKAJ_START),
        _czas_ostatniej_ramki(0),
        ostatni_face_size(0) {}

private:
    ServoPID& _serwa;
    HMI& _hmi;
    DataLogger& _logger;  // NOWE
    // ... reszta pol bez zmian
```

### Modyfikacja _przetworz_ramke() — ekstrakcja face_size

```cpp
// Oryginalnie (linie 456-475):
void _przetworz_ramke() {
    uint8_t tryb   = _ramka_buf[1];
    int16_t blad_x = (int16_t)(_ramka_buf[2] | (_ramka_buf[3] << 8));
    int16_t blad_y = (int16_t)(_ramka_buf[4] | (_ramka_buf[5] << 8));
    // _ramka_buf[6] = face_size — zarezerwowane

// Po zmianie:
void _przetworz_ramke() {
    uint8_t tryb   = _ramka_buf[1];
    int16_t blad_x = (int16_t)(_ramka_buf[2] | (_ramka_buf[3] << 8));
    int16_t blad_y = (int16_t)(_ramka_buf[4] | (_ramka_buf[5] << 8));
    ostatni_face_size = _ramka_buf[6];  // NOWE — ekstrakcja face_size z bajtu 6
```

### Modyfikacja _przejdz_do() — logowanie zmian stanow

```cpp
// Oryginalnie (linie 478-488):
void _przejdz_do(StanSystemu nowy) {
    _stan_systemu = nowy;
    if (nowy == SKANOWANIE) {
        _serwa.resetuj_czas_skanu();
        _serwa.pid_reset();
    } else if (nowy == SLEDZENIE) {
        _hmi.buzzer_beep();
        _serwa.pid_reset();
    }
}

// Po zmianie:
void _przejdz_do(StanSystemu nowy) {
    if (nowy == _stan_systemu) return;  // guard — nie loguj ponownie tego samego stanu
    StanSystemu stary = _stan_systemu;
    _stan_systemu = nowy;
    _logger.loguj_zmiane_stanu(stary, nowy, _serwa.kat_pan, _serwa.kat_tilt);
    if (nowy == SKANOWANIE) {
        _serwa.resetuj_czas_skanu();
        _serwa.pid_reset();
    } else if (nowy == SLEDZENIE) {
        _hmi.buzzer_beep();
        _serwa.pid_reset();
    }
}
```

### Modyfikacja loop() — face_size, latency_ms, komenda 'D'

```cpp
// Oryginalny loop() (linie 731-758), po zmianach:
void loop() {
    // --- Parser serial z interceptem komendy 'D' ---
    while (Serial.available() > 0) {
        uint8_t bajt = (uint8_t)Serial.read();
        if (bajt == 'D') {
            logger.zrzuc_ostatnie();  // NOWE — zrzut diagnostyczny
        } else {
            maszyna.przetwarzaj_bajt(bajt);
        }
    }

    // --- Watchdog millis() ---
    maszyna.watchdog_krok();

    // --- PID / skan krok ---
    serwa.pid_krok(maszyna.stan());

    // --- LCD odswiezanie ---
    hmi.lcd_krok(maszyna.stan(), serwa.kat_pan, serwa.kat_tilt,
                 serwa.ostatni_blad_x, serwa.ostatni_blad_y);

    // --- Przycisk abort ---
    if (hmi.przycisk_krok(maszyna.stan())) {
        maszyna.wymus_skanowanie();
    }

    // --- Logowanie telemetrii z rzeczywistymi wartosciami ---
    uint16_t latency_ms = (uint16_t)(millis() - maszyna.czas_ostatniej_ramki());  // NOWE
    logger.krok(maszyna.stan(), serwa.kat_pan, serwa.kat_tilt,
                serwa.ostatni_blad_x, serwa.ostatni_blad_y,
                maszyna.ostatni_face_size,  // NOWE zamiast 0
                latency_ms);               // NOWE zamiast 0
}
```

---

## Environment Availability

| Zaleznosc | Wymagana przez | Dostepna | Uwaga |
|-----------|---------------|----------|-------|
| arduino-cli | Flash firmware | Sprawdzona w Phase 26 | `arduino-cli version` na RPi |
| Arduino Uno R4 WiFi | Hardware target | Tak (Phase 24-26 ukonczone) | `/dev/ttyACM0` |
| Karta SD w slocie | DataLogger | Tak (Phase 26 zweryfikowane) | Wymaga przed E2E testem |
| RTC DS1307 z bateria | DataLogger timestamps | Tak (Phase 25 zweryfikowane) | Bateria CR1220 w DataLogger Shield |
| RPi4 z firmware sledzenia | E2E test (INT-08) | Weryfikowac przed E2E | Biezacy firmware RPi wysyla ramki 8B |

**Missing dependencies with no fallback:** Brak — wszystkie zaleznosci zweryfikowane w poprzednich fazach.

---

## Validation Architecture

Projekt nie ma test frameworka (`test_framework: none` w config.json). Weryfikacja empiryczna zgodna z CLAUDE.md.

### Mapa wymagan do weryfikacji

| Requirement | Zachowanie | Typ | Komenda / Metoda |
|-------------|-----------|-----|------------------|
| INT-06 | Zakrycie twarzy → wpis SLEDZENIE→SKANOWANIE w CSV | empiryczny | Wyjac karte SD po sesji, sprawdzic plik w pandas |
| INT-06 | Odkrycie twarzy → wpis SKANOWANIE→SLEDZENIE w CSV | empiryczny | Jak wyzej |
| INT-06 | CSV zawiera wiersze co ~10 klatek w SLEDZENIE | empiryczny | Sprawdzic rozstep timestamp w CSV |
| INT-08 | Zadne przejscie stanu nie powoduje zawieszenia serw | empiryczny | Obserwacja serw podczas zmian stanow |
| INT-08 | Komenda 'D' wypisuje 10 ostatnich wpisow na Serial | empiryczny | `echo -n 'D' > /dev/ttyACM0` lub `ser.write(b'D')` z pyserial |
| INT-08 | face_size > 0 w wierszach SLEDZENIE | empiryczny | Sprawdzic kolumne face_size w CSV |
| INT-08 | latency_ms ~33ms przy normalnym 30Hz sledzeniu | empiryczny | Sprawdzic kolumne latency_ms w CSV |

### Weryfikacja E2E krok po kroku (Kryterium sukcesu z CONTEXT.md)

1. Uruchom firmware, staw twarz przed kamera RPi — serwa powinny sledzic
2. Zakryj twarz recznie — serwa przechodza do skanu Lissajous
3. Odkryj twarz — serwa wracaja do sledzenia
4. Zatrzymaj sesje, wyjmij karte SD
5. Na PC: `python3 -c "import pandas as pd; df=pd.read_csv('L260404.CSV'); print(df)"`
6. Sprawdz: czy sa wiersze ze `stan=1` (SKANOWANIE) i `stan=2` (SLEDZENIE) przeplatane
7. Sprawdz: czy `face_size` jest niezerowy w wierszach SLEDZENIE
8. Sprawdz: czy `latency_ms` jest w okolicach 33ms (+/-10ms) dla normalnej sesji

### Weryfikacja bez karty SD (komenda 'D')

```bash
# Z pyserial na RPi:
python3 -c "
import serial, time
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
time.sleep(1)
ser.write(b'D')
time.sleep(0.5)
print(ser.read(ser.in_waiting).decode('ascii', errors='replace'))
"
```

---

## Open Questions

1. **Bajt 'D' w payload 8B — czy ryzyko false trigger jest akceptowalne?**
   - Co wiemy: bajt 0x44 ('D') moze byc czescia payload ramki (error_x, error_y, face_size)
   - Co jest niejasne: czestotliwosc wystepowania 0x44 w typowych warunkach sledzenia
   - Rekomendacja: Akceptowac false trigger — zrzut diagnostyczny to operacja readonly, nie uszkadza stanu systemu ani danych SD. Najdluzsza implikacja: chwilowe opoznienie jednej iteracji loop() (~5ms przy 10 wpisach). Implementacja bez dodatkowego stanu parsera jest prostsza i mniej ryzykowna.

2. **Opcjonalna: logowanie stanu BEZCZYNNOSC przy starcie systemu**
   - Co wiemy: `_stan_systemu` inicjalizowany jako `BEZCZYNNOSC` w konstruktorze, ale `_przejdz_do()` nie jest wywolywana przy starcie
   - Co jest niejasne: czy uzytkownik chce miec wpis "START SESJI" w CSV
   - Rekomendacja: Dodac wywolanie `logger.loguj_zmiane_stanu(BEZCZYNNOSC, BEZCZYNNOSC, 0, 0)` w `setup()` po `logger.inicjalizuj()` — jako marker poczatku sesji. Opcjonalne, nie wymagane przez INT-06.

---

## Sources

### Primary (HIGH confidence)

- `src/arduino/aries_controller/aries_controller.ino` — bezposredni odczyt kodu: klasy DataLogger (linie 538-657), MaszynaStanow (linie 360-489), loop() (linie 731-758), globalne instancje (linie 659-666)
- `.planning/research/ARCHITECTURE.md` — Timing Impact Analysis, Data Flow z DataLogger, Pattern A-D, Anti-Patterns 1-5
- `.planning/research/PITFALLS.md` — Pitfall 4 (SD write latencja), Integration Gotchas, Performance Traps
- `.planning/phases/27-pelna-integracja-datalogger-z-maszynastanow/27-CONTEXT.md` — D-01..D-07 decyzje uzytkownika
- `.planning/phases/26-sd-card-datalogger-csv/26-CONTEXT.md` — D-01..D-11 decyzje Phase 26

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` — INT-06, INT-08 definicje wymagan
- `.planning/STATE.md` — historia decyzji projektu, stan faz

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — brak nowych bibliotek, weryfikacja z istniejacego kodu
- Architecture: HIGH — bezposredni odczyt firmware, wszystkie wzorce zidentyfikowane
- Pitfalls: HIGH — Pitfall 1 (kolejnosc instancji) i Pitfall 2 (guard w _przejdz_do) sa nowe i krytyczne; Pitfall 3-5 zidentyfikowane analitycznie

**Research date:** 2026-04-04
**Valid until:** Do konca milestonu v2.1 (stabilna platforma). DataLogger API (Phase 26) jest zamkniete — brak ryzyka zmian.
