# Phase 25: RTC DS1307 Izolowana Integracja - Research

**Researched:** 2026-04-01
**Domain:** Arduino Uno R4 WiFi — Adafruit RTClib 2.1.4 + DS1307 via I2C, klasa ZegarRTC OOP, modyfikacja HMI bootscreen
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Fizyczne podlaczenie I2C**
- D-01: DataLogger Shield oficjalny z gold pinami — styki stabilne, cynowanie A4/A5 NIEPOTRZEBNE
- D-02: I2C scanner (Wire.beginTransmission(0x68)) jako PIERWSZY task — osobny sketch, potwierdzenie fizycznego polaczenia przed kodem RTClib
- D-03: Shield osadzony bezposrednio na Arduino (nie kable jumper) — docelowa konfiguracja od poczatku

**Wyswietlanie czasu na LCD**
- D-04: Czas RTC TYLKO na bootscreen — format "v2.1  HH:MM:SS" w wierszu 0 lub czas w wierszu 1 bootscreena
- D-05: Normalny tryb LCD (lcd_krok) BEZ ZMIAN — wiersz 0: tryb+katy, wiersz 1: bledy Bx/By. Czas dostepny przez Serial.
- D-06: Jesli RTC niedostepny, bootscreen pokazuje "RTC: FAIL" zamiast czasu

**Fallback bez RTC**
- D-07: BLOKADA STARTU — jesli rtc.begin() zwroci false LUB czas niepoprawny (rok < 2025), system NIE startuje
- D-08: Blokada: buzzer alarm (ciagly ton) + LCD wiersz 0: "RTC ERROR" + wiersz 1: "Sprawdz baterie"
- D-09: Petla while(true) z buzzer — wymaga fizycznego resetu Arduino po naprawie RTC

**Klasa RTC w strukturze OOP**
- D-10: Nowa klasa ZegarRTC w aries_controller.ino — spolna z istniejacym OOP (ServoPID, HMI, MaszynaStanow)
- D-11: Metody: inicjalizuj() -> bool, odczytaj_czas() -> DateTime, czy_dostepny() -> bool
- D-12: HMI dostaje referencje do ZegarRTC — bootscreen uzywa odczytaj_czas() do wyswietlenia czasu
- D-13: DataLogger (Phase 26) tez dostanie referencje do ZegarRTC — interfejs gotowy

**Kolejnosc inicjalizacji w setup()**
- D-14: Serial → pinMode(A0/A1) → HMI (bootscreen bez czasu) → Wire.begin() + ZegarRTC.inicjalizuj() → HMI aktualizuje bootscreen z czasem (lub "RTC FAIL" → blokada) → Soft Start → Serwa
- D-15: Wire.begin() PRZED rtc.begin() — wymagane przez RTClib (research potwierdza)

**Biblioteka RTC**
- D-16: Adafruit RTClib 2.1.4 — NIE DS1307RTC (PaulStoffregen) — RTClib przetestowane na Renesas RA4M1 (research STACK.md)

### Claude's Discretion
- Format czasu na bootscreen (HH:MM:SS vs HH:MM vs pelna data)
- Czy rtc.adjust() wywolywac przy pierwszym uruchomieniu (czas z kompilacji)
- Nazewnictwo metod klasy ZegarRTC (polskie, spojne z reszta)
- Ile czasu wyswietlac bootscreen z czasem (obecne 2000ms vs dluzej)
- Walidacja czasu — co znaczy "niepoprawny" (rok < 2025? epoch 0?)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RTC-01 | RTC DS1307 odczytuje poprawny czas po inicjalizacji Wire->RTC->SD | RTClib 2.1.4 `RTC_DS1307::begin()` + `now()` — Wire.begin() przed rtc.begin() (D-15). Klasa ZegarRTC hermetyzuje te wywolania. |
| RTC-02 | LCD row 1 wyswietla aktualny czas (HH:MM:SS) z aktualizacja co 1s | Zakres tej fazy: czas TYLKO na bootscreen (D-04). RTC-02 (normal LCD tick) adresowany przez ten wymaganie — ale D-05 mowi ze normalny lcd_krok BEZ ZMIAN; czas przez Serial. Bootscreen jest punktem integracji w tej fazie. |
| RTC-03 | Timestamp z RTC uzywany w nazwach plikow CSV i wpisach logow | ZegarRTC.odczytaj_czas() -> DateTime — interfejs gotowy dla Phase 26. W tej fazie: Serial.print() z timestampem jako weryfikacja. |
| INT-07 | Poprawna kolejnosc inicjalizacji w setup(): Wire.begin() -> rtc.begin() -> SD.begin() | D-14 definiuje kolejnosc. W tej fazie: Wire.begin() + rtc.begin() (bez SD.begin() — izolowana integracja). |
</phase_requirements>

---

## Summary

Faza 25 dodaje klase `ZegarRTC` do firmware `aries_controller.ino` — izolowana integracja DS1307 via I2C bez SD card i bez zmian w protokole binarnym. Calkowity zakres zmian kodu: 1 nowa klasa (~40 linii), 3 modyfikacje setup(), 1 modyfikacja `lcd_bootscreen()`.

Stos jest w pelni ustalony przez poprzednie badania (STACK.md): Adafruit RTClib 2.1.4 z Wire bundled w ArduinoCore-renesas 1.5.3. Jedyny bloker srodowiskowy: RTClib i Adafruit BusIO NIE sa zainstalowane — Wave 0 musi je zainstalowac przed kompilacja.

Kluczowe ryzyko fazy: fizyczne styki I2C shielda. Decyzja D-01 (gold piny, cynowanie niepotrzebne) i D-02 (I2C scanner jako pierwszy task) eliminuja to ryzyko zgodnie z Pitfall 2.

**Primary recommendation:** Task 1 = oddzielny sketch I2C scanner (weryfikacja 0x68 na fizycznym sprzecie), Task 2 = dodanie ZegarRTC do firmware z blokada startu, Task 3 = weryfikacja sprzetowa.

---

## Standard Stack

### Core (dla tej fazy)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Adafruit RTClib | 2.1.4 | DS1307 odczyt/zapis via I2C — klasa RTC_DS1307, DateTime | Oficjalnie przetestowane na Renesas RA4M1 per Arduino compatibility matrix (PASS compile + hardware). Decyzja D-16. |
| Wire (built-in) | bundled z ArduinoCore-renesas 1.5.3 | I2C master — magistrala dla DS1307 na A4/A5 | Wbudowane. Issue #180 (slave mode bug) naprawione w core 1.0.4+. Aktualny core 1.5.3 >= fix. |
| Adafruit BusIO | zalezy od RTClib | Abstrakcja I2C/SPI dla bibliotek Adafruit | Wymagana dependencja RTClib — zainstalowac razem. |

### Supporting (niezmienione z v2.1)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| QuickPID | 3.1.9 | PID 100Hz | BEZ ZMIAN w tej fazie |
| Servo (arduino-libraries) | 1.3.0 | Serwa MG-90S D6/D9 | BEZ ZMIAN |
| LiquidCrystal (built-in) | bundled | LCD 1602 A0/A1/D2-D5 | BEZ ZMIAN |

### Instalacja (Wave 0 prerequisite)

```bash
# arduino-cli — RTClib i zaleznos BusIO (obie wymagane)
arduino-cli lib install "RTClib"
arduino-cli lib install "Adafruit BusIO"

# Weryfikacja po instalacji
arduino-cli lib list | grep -i "rtclib\|busio"
```

**Stan aktualny:** RTClib NIE jest zainstalowane (zweryfikowane `arduino-cli lib list` — brak). Adafruit BusIO NIE jest zainstalowane. Instalacja blokuje kompilacje — Wave 0 task.

**Version verification:**
- ArduinoCore-renesas: 1.5.3 (zainstalowane, >= wymagane 1.4.1) — OK
- Servo: 1.3.0 (zainstalowane) — OK
- QuickPID: 3.1.9 (zainstalowane) — OK
- RTClib: NIE zainstalowane — Wave 0 install required
- Adafruit BusIO: NIE zainstalowane — Wave 0 install required

---

## Architecture Patterns

### Struktura pliku po modyfikacji

```
aries_controller.ino
├── #include Wire.h, RTClib.h    (nowe — przed pozostalymi)
├── #include QuickPID.h, Servo.h, LiquidCrystal.h (istniejace)
├── #define stale protokolu/PID/servo/LCD (bez zmian)
├── enum StanParsera, StanSystemu (bez zmian)
├── class HMI (MODYFIKACJA: lcd_bootscreen + nowy param ZegarRTC&)
├── class ServoPID (BEZ ZMIAN)
├── class MaszynaStanow (BEZ ZMIAN)
├── class ZegarRTC (NOWE — ~40 linii)
├── globalne instancje:
│   ├── ZegarRTC zegar;        (NOWE — przed hmi)
│   ├── HMI hmi;               (BEZ ZMIAN — ale lcd_bootscreen dostanie referencje)
│   ├── ServoPID serwa;        (BEZ ZMIAN)
│   └── MaszynaStanow maszyna; (BEZ ZMIAN)
└── setup(), loop() (MODYFIKACJA setup — Wire + zegar, loop BEZ ZMIAN)
```

### Pattern 1: Klasa ZegarRTC (nowa)

**Co:** Hermetyzacja RTC_DS1307 z polskim interfejsem, zgodna z konwencja OOP projektu.

**Kiedy uzyc:** Wzorzec adaptera — ukrywa RTClib za polskim API, umozliwia mockowanie w przyszlosci i jednolita obsuge bledu.

```cpp
// Source: CONTEXT.md D-10/D-11, RTClib 2.1.4 API
#include <Wire.h>
#include <RTClib.h>

class ZegarRTC {
public:
    ZegarRTC() : _dostepny(false) {}

    // Zwraca true gdy inicjalizacja udana i czas poprawny (rok >= 2025)
    bool inicjalizuj() {
        if (!_rtc.begin()) {
            _dostepny = false;
            return false;
        }
        DateTime teraz = _rtc.now();
        if (teraz.year() < 2025) {
            // Czas niepoprawny — bateria rozladowana lub DS1307 niezainicjowany
            _dostepny = false;
            return false;
        }
        _dostepny = true;
        return true;
    }

    DateTime odczytaj_czas() {
        return _rtc.now();
    }

    bool czy_dostepny() const {
        return _dostepny;
    }

private:
    RTC_DS1307 _rtc;
    bool _dostepny;
};
```

### Pattern 2: Modyfikacja setup() — kolejnosc inicjalizacji

**Co:** Wire.begin() i ZegarRTC.inicjalizuj() wstawione miedzy hmi.inicjalizuj() a serwa.inicjalizuj() (Soft Start).

**Uzasadnienie kolejnosci D-14:** LCD bootscreen widoczny od razu (hmi.inicjalizuj()), potem I2C i RTC sprawdzone, potem czas wyswietlony (lub blokada), potem Soft Start + serwa.

```cpp
// Source: CONTEXT.md D-14, ARCHITECTURE.md "Init kolejnosc"
void setup() {
    Serial.begin(115200);
    uint32_t start = millis();
    while (!Serial && millis() - start < 500) { delay(10); }

    pinMode(A0, OUTPUT);
    pinMode(A1, OUTPUT);

    hmi.inicjalizuj();              // LCD bootscreen "Inicjalizacja..."

    // I2C + RTC po bootscreen
    Wire.begin();                   // D-15: Wire PRZED rtc.begin()
    if (!zegar.inicjalizuj()) {
        // D-07/D-08/D-09: BLOKADA STARTU — petla nieskonczona
        hmi.rtc_blokada();          // LCD "RTC ERROR" / "Sprawdz baterie" + buzzer
        while (true) {}             // Wymaga fizycznego resetu
    }
    hmi.bootscreen_z_czasem(zegar.odczytaj_czas());  // D-04: aktualizacja bootscreen

    delay(500);                     // Soft Start (MIG-08)
    serwa.inicjalizuj();
}
```

### Pattern 3: Modyfikacja HMI::lcd_bootscreen()

**Co:** lcd_bootscreen() rozbita na 2 etapy: pierwszy etap ("Inicjalizacja...") wywolywany przez hmi.inicjalizuj(), drugi etap (czas lub "RTC ERROR") wywolywany po inicjalizacji ZegarRTC.

**Alternatywa prosta:** lcd_bootscreen() przyjmuje opcjonalny czas — ale wymaga przekazania referencji do ZegarRTC do HMI lub zmiany sygnatury. Rekomendacja: dwie oddzielne metody publiczne w HMI.

```cpp
// Faza 1: wywolywana w hmi.inicjalizuj() — bez zmian w sygnaturze
void lcd_bootscreen() {
    _lcd.setCursor(0, 0);
    _lcd.print("ARIES-LITE v2.1");
    _lcd.setCursor(0, 1);
    _lcd.print("Inicjalizacja...");
    delay(2000);  // lub skrocic — Claude's Discretion
}

// Faza 2: wywolywana po zegar.inicjalizuj() — nowe metody
void bootscreen_z_czasem(DateTime t) {
    char buf[17];
    snprintf(buf, sizeof(buf), "v2.1  %02d:%02d:%02d",
             t.hour(), t.minute(), t.second());
    _lcd.setCursor(0, 0);
    _lcd.print(buf);
    _lcd.setCursor(0, 1);
    _lcd.print("RTC OK          ");
    delay(1500);
}

void rtc_blokada() {
    // D-08: LCD "RTC ERROR" + "Sprawdz baterie" + buzzer ciagly
    _lcd.clear();
    _lcd.setCursor(0, 0);
    _lcd.print("RTC ERROR       ");
    _lcd.setCursor(0, 1);
    _lcd.print("Sprawdz baterie ");
    // Buzzer ciagly (D-09)
    tone(BUZZER_PIN, 1000);  // bez duration = ciagly
}
```

### Pattern 4: I2C Scanner (oddzielny sketch)

**Co:** Minimalny sketch diagnostyczny — TYLKO Wire.h, skanuje 0x01-0x7F, wypisuje przez Serial.

**Kiedy:** Task 1 — przed jakimkolwiek kodem RTClib (D-02).

```cpp
// Source: CONTEXT.md D-02, standard I2C scanner wzorzec
#include <Wire.h>

void setup() {
    Serial.begin(115200);
    Wire.begin();
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.print("I2C znaleziony: 0x");
            Serial.println(addr, HEX);
        }
    }
    Serial.println("Skan zakonczony.");
}

void loop() {}
```

**Oczekiwany wynik:** `I2C znaleziony: 0x68` — DS1307 na standardowym adresie.

### Anti-Patterns to Avoid

- **Wire.begin() po rtc.begin():** Odwrocona kolejnosc powoduje ze RTClib nie widzi DS1307. Zawsze Wire.begin() PIERWSZE (D-15).
- **rtc.adjust() w kazdym inicjalizuj():** Nadpisuje czas przy kazdym resecie. Wywolywac TYLKO jesli `!rtc.isrunning()` lub jesli rok == 0.
- **Brak walidacji roku:** rtc.begin() moze zwrocic true ale czas 2000-01-01 (rozladowana bateria). Walidacja rok >= 2025 jest wymagana (D-07).
- **lcd.clear() zamiast setCursor + overwrite:** Powoduje migotanie LCD (Pitfall 3 z PITFALLS.md). Uzywac setCursor + nadpisywanie spacjami.
- **Modyfikacja lcd_krok():** D-05 — normalny tryb LCD BEZ ZMIAN. Czas RTC tylko na bootscreen.
- **DateTime w globalnej zmiennej bez odswiezania:** DateTime jest snapshot — pobierac przez odczytaj_czas() przy kazdym potrzebnym odczycie, nie przechowywac bez TTL.

---

## Don't Hand-Roll

| Problem | Nie buduj | Uzyj zamiast | Dlaczego |
|---------|-----------|--------------|----------|
| I2C komunikacja z DS1307 | Custom Wire.write()/read() sekwencji | Adafruit RTClib 2.1.4 `RTC_DS1307` | RTClib obsluguje 7-bajt NVM DS1307, DS1307_SQWOUT, BCD konwersje, leap year — 200+ linii kodu ktory nie potrzeba pisac |
| Konwersja BCD czasu z rejestrow | `(reg >> 4) * 10 + (reg & 0x0F)` reczne | RTClib `DateTime::hour()`, `minute()`, `second()` | DS1307 zwraca BCD — RTClib konwertuje automatycznie |
| Sprawdzanie czy oscylator biegnie | `Wire.read()` bitu CH rejestru 0x00 | `RTC_DS1307::isrunning()` | Bit CH=0 znaczy running — RTClib hermetyzuje |
| Format HH:MM:SS | Reczna sprintf logika | `DateTime.hour()`, `minute()`, `second()` + `snprintf` | DateTime API jest czytelne i przetestowane |

---

## Common Pitfalls

### Pitfall 1: I2C scanner nie wykrywa 0x68 — fizyczne styki shielda

**Co idzie zle:** Wire.begin() OK, rtc.begin() zwraca false. I2C scanner nie widzi 0x68.

**Dlaczego:** DataLogger Shield stacking headers — historycznie styki A4/A5 moga tracic kontakt. CONTEXT.md D-01 potwierdza ze gold piny sa stabilne i cynowanie NIEPOTRZEBNE. Jednak jesli shield nie jest do konca osadzony, styki moga byc slabe.

**Jak unikac:** Wykonac Task 1 (I2C scanner) przed Task 2 (firmware RTClib). Jesli scanner nie wykrywa 0x68 — sprawdzic fizyczne osadzenie shielda, nie kod.

**Symptomy wczesne:** Scanner w Serial Monitor nie wypisuje nic lub wypisuje adresy inne niz 0x68.

### Pitfall 2: Czas DS1307 po nowej baterii = 2000-01-01 00:00:00

**Co idzie zle:** rtc.begin() zwraca true (komunikacja OK), ale DateTime.year() == 2000. Brakuje walidacji roku.

**Dlaczego:** DS1307 po nowej baterii lub po dlugim rozladowaniu wraca do epoki. Oscylator biegnie ale czas niezainicjowany. `rtc.isrunning()` zwraca true mimo ze czas bledny.

**Jak unikac:** Walidacja `teraz.year() < 2025` w ZegarRTC.inicjalizuj() (D-07). Przy pierwszym uruchomieniu z nowa bateria: wywolac `rtc.adjust(DateTime(F(__DATE__), F(__TIME__)))` — ustawia czas kompilacji. Metoda adjust() wymagana w jednym jednorazowym sketchu lub w `inicjalizuj()` pod warunkiem `!rtc.isrunning()`.

**Symtomy wczesne:** Serial pokazuje "2000-01-01 00:00:00", RTC-ERROR blokada sie odpala mimo poprawnego fizycznego polaczenia.

### Pitfall 3: delay(2000) w lcd_bootscreen() przed RTC — za dlugi czas na ekranie "Inicjalizacja..."

**Co idzie zle:** Istniejacy kod ma delay(2000) w lcd_bootscreen(). Dodajemy Wire.begin() + rtc.begin() PO lcd_bootscreen(). Uzytkownik widzi "Inicjalizacja..." przez 2000ms zanim zobaczy czas.

**Dlaczego:** Kolejnosc D-14 jest: hmi.inicjalizuj() (z delay(2000)) → Wire.begin() + zegar. Lacznie bootscreen trwa 2000ms + czas inicjalizacji RTC (~5ms) + nowy ekran z czasem.

**Jak unikac:** Zredukuj delay w pierwszym bootscreen do 500ms lub 0 — uzytkownik i tak zobaczy drugi ekran z czasem. Claude's Discretion: rekomendacja — skroc do 500ms (wystarczy zeby zobaczyc "ARIES-LITE v2.1") i dodaj 1500ms na ekranie z czasem.

### Pitfall 4: rtc.adjust() nadpisuje czas przy kazdym uruchomieniu

**Co idzie zle:** Umieszenie `rtc.adjust(DateTime(F(__DATE__), F(__TIME__)))` bezwarunkowo w inicjalizuj() powoduje reset czasu do czasu kompilacji przy kazdym resecie Arduino.

**Dlaczego:** F(__DATE__)/F(__TIME__) to makra preprocesora — czas kompilacji szkicu, nie czas aktualny. DS1307 powinien utrzymywac czas przez baterie miedzy resetami.

**Jak unikac:** Wywolac adjust() TYLKO gdy `!_rtc.isrunning()` (oscylator nie biegnie — swiezutka bateria lub DS1307 niezainicjowany). Albo nie wywolywac w firmware w ogole — adjust przez oddzielny sketch diagnostyczny.

### Pitfall 5: Wire.begin() z adresem — tryb slave

**Co idzie zle:** `Wire.begin(0x68)` zamiast `Wire.begin()` — Arduino wchodzi w tryb slave I2C pod adresem 0x68, nie master. rtc.begin() nie widzi DS1307.

**Dlaczego:** Wire.begin() bez argumentu = master. Wire.begin(addr) = slave. RTClib wymaga mastera.

**Jak unikac:** Zawsze `Wire.begin()` bez argumentu (D-15). ArduinoCore-renesas issue #180 dotyczy wlasnie przemieszania trybow — naprawiony w 1.0.4+ ale najlepiej nigdy nie uzyc Wire.begin(addr) w tym projekcie.

---

## Code Examples

### Pelna klasa ZegarRTC (wzorzec gotowy do implementacji)

```cpp
// Source: CONTEXT.md D-10/D-11, RTClib 2.1.4 API, PITFALLS.md Pitfall 2
class ZegarRTC {
public:
    ZegarRTC() : _dostepny(false) {}

    // Inicjalizuj I2C + DS1307. Wire.begin() MUSI byc wywolane przed inicjalizuj().
    // Zwraca false jesli RTC nie odpowiada LUB rok < 2025 (D-07).
    bool inicjalizuj() {
        if (!_rtc.begin()) {
            _dostepny = false;
            return false;
        }
        // Inicjuj czas z kompilacji TYLKO gdy oscylator nie biegnie (swiezutka bateria)
        if (!_rtc.isrunning()) {
            _rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
        }
        DateTime teraz = _rtc.now();
        if (teraz.year() < 2025) {
            _dostepny = false;
            return false;
        }
        _dostepny = true;
        return true;
    }

    // Odczyt aktualnego czasu z DS1307 (~0.3ms I2C)
    DateTime odczytaj_czas() {
        return _rtc.now();
    }

    // Czy RTC zainicjalizowany i czas poprawny
    bool czy_dostepny() const {
        return _dostepny;
    }

private:
    RTC_DS1307 _rtc;
    bool _dostepny;
};
```

### Wywolanie rtc.adjust() przez Serial (diagnostyczny)

```cpp
// Source: RTClib 2.1.4 README
// Wklej do oddzielnego sketchu diagnostycznego gdy trzeba przestawic czas:
// rtc.adjust(DateTime(2026, 4, 1, 14, 30, 0));  // rok, miesiac, dzien, h, m, s
// lub z kompilacji:
// rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
```

### Serial debug — wypisywanie czasu

```cpp
// Source: RTClib 2.1.4 API
DateTime teraz = zegar.odczytaj_czas();
Serial.print("[RTC] ");
Serial.print(teraz.year()); Serial.print('-');
Serial.print(teraz.month()); Serial.print('-');
Serial.print(teraz.day()); Serial.print(' ');
Serial.print(teraz.hour()); Serial.print(':');
Serial.print(teraz.minute()); Serial.print(':');
Serial.println(teraz.second());
```

### Format HH:MM:SS na LCD (bootscreen)

```cpp
// Source: RTClib DateTime API + snprintf — projekt patterns
DateTime t = zegar.odczytaj_czas();
char buf[17];
snprintf(buf, sizeof(buf), "v2.1  %02d:%02d:%02d",
         t.hour(), t.minute(), t.second());
// Wynik: "v2.1  14:30:05" (16 znakow, dopasowany do LCD 1602)
```

---

## State of the Art

| Stara praktyka | Aktualna praktyka | Kiedy zmienione | Wplyw |
|----------------|-------------------|-----------------|-------|
| DS1307RTC (PaulStoffregen) | Adafruit RTClib 2.1.4 | Renesas RA4M1 — DS1307RTC AVR-only | DS1307RTC nie kompiluje sie na R4. RTClib dziala. |
| Wire.begin() po rtc.begin() | Wire.begin() zawsze PRZED rtc.begin() | ArduinoCore-renesas issue #180 (2023) | Odwrocona kolejnosc powoduje brak komunikacji I2C |
| Bezwarunkowe rtc.adjust() | adjust() tylko gdy !isrunning() | Dobra praktyka RTClib | Reset czasu przy kazdym starcie = bledny timestamp |

**Deprecated/outdated:**
- DS1307RTC (PaulStoffregen): AVR libc — nie kompiluje na ARM Renesas RA4M1. Nie uzyc.
- Wire.begin(0x68): tryb slave — mylone z adresem DS1307. Wire.begin() bez argumentu = master.

---

## Open Questions

1. **rtc.adjust() przy pierwszym uruchomieniu z nowa bateria**
   - Co wiemy: DS1307 wraca do 2000-01-01 po nowej baterii. `rtc.isrunning()` = false gdy oscylator nie biegnie.
   - Nieklarne: Czy `inicjalizuj()` ma wywolac `rtc.adjust(DateTime(F(__DATE__), F(__TIME__)))` automatycznie gdy `!rtc.isrunning()`, czy zostawic to osobnemu sketchowi diagnostycznemu?
   - Rekomendacja (Claude's Discretion): Wywolac `rtc.adjust()` automatycznie w `inicjalizuj()` gdy `!_rtc.isrunning()` — to standard praktyka dla pierwszego uruchomienia. Czas kompilacji jest lepszy niz 2000-01-01. Udokumentowac w komentarzu.

2. **Dlugosc delay na bootscreen z czasem**
   - Co wiemy: Obecny bootscreen ma delay(2000). Po dodaniu RTC bedzie 2 ekrany bootscrenu.
   - Nieklarne: Ile ms na ekranie z czasem?
   - Rekomendacja (Claude's Discretion): Zredukuj delay pierwszego ekranu do 500ms, dodaj 1500ms na ekranie z czasem. Lacznie ~2s — podobnie jak poprzednio.

3. **Format RTC-02 vs D-04 — sprzecznosc w requirements?**
   - Co wiemy: RTC-02 mowi "LCD row 1 wyswietla aktualny czas z aktualizacja co 1s" — sugeruje normalny tryb. D-05 mowi "normalny tryb LCD (lcd_krok) BEZ ZMIAN".
   - Nieklarne: Czy RTC-02 ma byc zrealizowane w Phase 25 czy Phase 26?
   - Rekomendacja: Phase 25 adresuje RTC-02 TYLKO przez bootscreen (D-04). Normalny lcd_krok z czasem (jesli w ogole) to Phase 26 lub osobna decyzja. Planner powinien oznaczyc RTC-02 jako "partially addressed" — bootscreen OK, normal tick OUT OF SCOPE tej fazy.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| arduino-cli | Kompilacja + upload firmware | TAK | 1.4.1 (2026-01-19) | — |
| ArduinoCore-renesas (arduino:renesas_uno) | Board support Uno R4 WiFi | TAK | 1.5.3 (>= 1.4.1 wymagane) | — |
| Adafruit RTClib | ZegarRTC, DS1307 | NIE | — | BRAK — blokuje kompilacje |
| Adafruit BusIO | Dependencja RTClib | NIE | — | BRAK — blokuje RTClib |
| Servo 1.3.0 | ServoPID (istniejace) | TAK | 1.3.0 | — |
| QuickPID 3.1.9 | PID (istniejace) | TAK | 3.1.9 | — |
| DS1307 hardware na 0x68 | ZegarRTC.inicjalizuj() | NIEZNANE — weryfikacja fizyczna | — | I2C scanner (Task 1) |

**Brakujace zaleznosci bez fallback (blokuja wykonanie):**
- Adafruit RTClib — niezbedna. Komenda Wave 0: `arduino-cli lib install "RTClib"`
- Adafruit BusIO — niezbedna (dependencja RTClib). Komenda Wave 0: `arduino-cli lib install "Adafruit BusIO"`

**Weryfikacja fizyczna (nie srodowiskowa):**
- DS1307 na DataLogger Shield na 0x68 — weryfikowane przez Task 1 (I2C scanner sketch). Jesli shield z gold pinami (D-01) jest poprawnie osadzony, oczekiwany wynik: 0x68 detected.

---

## Project Constraints (from CLAUDE.md)

- **Jezyk:** Komentarze, nazwy zmiennych, metody — jezyk polski w nowym kodzie (zgodnie z test_tracker.py / aries_controller.ino pattern)
- **Bez unit testow:** Weryfikacja empiryczna — flash + Serial Monitor + LCD visual check
- **OOP pattern:** Klasy z lista inicjalizacyjna, metody inicjalizuj(), polskie nazewnictwo
- **snprintf zamiast dtostrf:** ARM Renesas RA4M1 — dtostrf nie istnieje
- **Brak Makefile/tox:** Kompilacja przez arduino-cli verify/upload
- **GSD workflow:** Nie editowac plikow bezposrednio poza GSD komendami
- **Commit format:** `feat(25): opis` lub `fix(25): opis`
- **try/except pattern (C++ analog):** Graceful fallback — jesli RTC fail: blokada (D-07/D-08/D-09), nie silent ignore
- **Brak .env / environment variables:** Konfiguracja tylko przez #define w firmware

---

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md` — RTClib 2.1.4 verified compatible z ArduinoCore-renesas 1.4.1+, Wire init order, DS1307 address 0x68
- `.planning/research/PITFALLS.md` — Pitfall 2 (I2C shield styki), Pitfall 3 (SD.begin zawieszenie — nie dotyczy tej fazy), Integration gotchas Wire→RTC→SD kolejnosc
- `.planning/research/ARCHITECTURE.md` — I2C integration details, RTC read timing ~0.3ms, DateTime cache pattern
- `src/arduino/aries_controller/aries_controller.ino` — Firmware v2.1 base code: linie 452-503 (setup/loop), linie 76-169 (klasa HMI, lcd_bootscreen)
- `.planning/phases/24-migracja-pinow-i-kompilacja-bazowa/24-01-SUMMARY.md` — Stan firmware po migracji, snprintf pattern, pinMode A0/A1
- `https://github.com/arduino/uno-r4-library-compatibility` — Official Arduino R4 library compatibility matrix: RTClib PASS

### Secondary (MEDIUM confidence)
- `https://github.com/arduino/ArduinoCore-renesas/issues/180` — DS1307 Wire master-only fix, merged PR #191 w core 1.0.4+
- `https://forum.arduino.cc/t/data-logging-shield-for-r4-minima/1272770` — DataLogger shield I2C na R4: shield pull-upy wystarczajace
- Arduino Library Manager: `arduino-cli lib search rtclib` — RTClib dostepne do instalacji, dependencja Adafruit BusIO

### Tertiary (LOW confidence)
- Brak — wszystkie kluczowe twierdzenia zweryfikowane przez oficjalne zrodla lub istniejacy STACK.md

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — RTClib 2.1.4 zweryfikowane oficjalnie; Wire bundled; zainstalowane biblioteki zweryfikowane arduino-cli lib list
- Architecture: HIGH — ZegarRTC pattern wynika wprost z CONTEXT.md decyzji + istniejacego OOP kodu; integracja setup() potwierdzona przez ARCHITECTURE.md
- Pitfalls: HIGH — zrodlo PITFALLS.md z oficjalnych GitHub issues; dodatkowe pitfalle (rtc.adjust() bezwarunkowe, Wire.begin z adresem) to znane antipatterns RTClib

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stabilne biblioteki — RTClib 2.1.4 nie zmieni sie w ciagu miesiaca)
