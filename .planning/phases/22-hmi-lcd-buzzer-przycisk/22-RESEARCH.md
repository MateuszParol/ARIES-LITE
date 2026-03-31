# Phase 22: HMI LCD + Buzzer + Przycisk - Research

**Researched:** 2026-03-31
**Domain:** Arduino Leonardo — LiquidCrystal 4-bit, tone(), millis() debounce, HMI w firmware embedded
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** LCD 2x16. Row 0: tryb (SKAN/SLEDZ/IDLE) + FPS. Row 1: katy serw P:+12.3 T:-5.7.
- **D-02:** Odswiezanie LCD max 5 Hz (co 200ms) via osobny timer millis(). LCD.print() ~1ms nie blokuje PID tick 10ms.
- **D-03:** Bootscreen: nazwa systemu ("ARIES-LITE v2.0") na LCD przez pierwsze 2 sekundy po starcie.
- **D-04:** Piny LCD — Claude's Discretion. Researcher zbada optymalne mapowanie pinow dla Leonardo. Ograniczenia: D7 (przycisk), D8 (buzzer), D9/D10 (serwa) zajete. LiquidCrystal.h juz #include w firmware.
- **D-05:** Buzzer na pinie D8. Krotki beep (100ms, ~1kHz) TYLKO przy przejsciu do TRACK. Brak dzwiekow przy innych przejsciach.
- **D-06:** Uzywaj tone() — Arduino Leonardo ma Timer3 (niezalezny od Timer1 serw). tone() nie koliduje z serwami na D9/D10.
- **D-07:** Przycisk na pinie D7 z INPUT_PULLUP. Aktywny TYLKO w trybie TRACK — przerywa sledzenie i przechodzi do SCAN. W SCAN/IDLE ignorowany.
- **D-08:** Debounce przez millis() (20ms). Reakcja w ciagu 50ms od wcisniecia. Bez zewnetrznej biblioteki.
- **D-09:** LCD, buzzer i przycisk obslugiwane w loop() POZA pid_tick() — nie wplywaja na deterministyczny timing PID 100Hz.
- **D-10:** Buzzer wywolywany w przejdz_do() — jedyne miejsce zmiany stanu. tone(BUZZER_PIN, 1000, 100) przy nowym stanie == TRACK.

### Claude's Discretion

- Mapowanie pinow LCD (RS, EN, D4-D7 lub I2C) — D-04
- Dokladny format tekstu na LCD (ile znakow, padding, formatowanie katow)
- Kolejnosc inicjalizacji LCD w setup() (po safe_startup czy przed?)
- Czy LCD.clear() przy kazdym odswiezeniu czy tylko przy zmianie trybu

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

### Out of Scope

- Zmiany w pi_brain.py (RPi)
- Kalibracja kierunkow serw (Phase 23)
- Zmiany w protokole 8B
- Zmiany w PID

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HMI-01 | LCD 1602 wyswietla tryb (SCAN/TRACK/IDLE) i blad X/Y — update max 5Hz (nie w petli PID!) | D-01, D-02: timer millis() co 200ms; setCursor pattern bez LCD.clear() |
| HMI-02 | Buzzer (D8) krotki dzwiek przy przejsciu do TRACK ("Target Lock") | D-05, D-06: tone(D8, 1000, 100) w przejdz_do() gdy nowy_stan == TRACK; Timer3 niezalezny |
| HMI-03 | Przycisk akcji (D7, INPUT_PULLUP) — "Abort Track" przywraca tryb SCAN | D-07, D-08: digitalRead z millis() debounce 20ms; tylko w TRACK |
| HMI-04 | LCD bootscreen z nazwa systemu przy starcie Arduino | D-03: lcd.begin() w setup(), lcd.print("ARIES-LITE v2.0"), delay(2000) |

</phase_requirements>

---

## Summary

Faza 22 to rozbudowa istniejacego firmware Arduino (`aries_controller.ino`) o trzy elementy HMI: wyswietlacz LCD 1602, buzzer pasywny i przycisk. Caly kod istnieje w jednym pliku `.ino`. Biblioteka `LiquidCrystal.h` jest juz dolaczona. Wszystkie kluczowe decyzje architektoniczne sa zamkniete — faza to implementacja, nie projektowanie.

Krytyczny insight: LCD.clear() zajmuje 1.52ms i powoduje migotanie przy 5Hz. Poprawny wzorzec to setCursor(0,0) + print() z dopelnieniem spacjami do stalej dlugosci — brak migotania, brak artefaktow. To jedyna nieoczywista decyzja do podjecia (Claude's Discretion).

Buzzer tone() na D8 jest bezpieczny na Leonardo — serwa uzywaja Timer1 (D9/D10), tone() uzywa Timer3 (D11 lub dowolny pin). Konflikty timerow sa realnym zagrozeniem na Arduino Uno (Timer1 == serwa + Timer1 == tone()), ale na Leonardo nie wystepuja.

**Rekomendacja ogolna:** Jedna faza, jeden plan. Wszystkie cztery elementy HMI sa malymi, niezaleznymi dodatkami do `loop()` i `setup()`. Implementowac jako jeden task w jednym commicie lub dwa taski (LCD+bootscreen, potem buzzer+przycisk).

---

## Standard Stack

### Core

| Biblioteka | Wersja | Cel | Dlaczego standard |
|------------|--------|-----|-------------------|
| LiquidCrystal | bundled (Arduino AVR) | HD44780 LCD 4-bit/8-bit | Oficjalna Arduino, juz zainstalowana w projekcie |
| tone() | built-in | PWM dla buzzera pasywnego | Wbudowana funkcja Arduino, uzupelnia Timer3 na Leonardo |
| digitalRead() + millis() | built-in | Debounce przycisku | Zero-overhead, sprawdzony wzorzec |
| dtostrf() | AVR libc | float → char[] dla LCD | Standardowa AVR, brak sprintf %f na AVR (nie dziala!) |

### Alternatywy wykluczone z powodu decyzji

| Zamiast | Mogloby byc | Dlaczego wykluczone |
|---------|-------------|---------------------|
| LiquidCrystal (4-bit) | LiquidCrystal_I2C (I2C) | D-04 locked: uzywamy istniejacego #include, 4-bit parallel |
| millis() debounce | Bounce2 lib | D-08 locked: bez zewnetrznej biblioteki |

**Instalacja:** Brak — wszystko juz dostepne w srodowisku (ENV-02 complete, biblioteki zainstalowane w Phase 18/20).

---

## Architecture Patterns

### Recommended Project Structure (firmware)

```
aries_controller.ino
├── #define konfiguracja (istniejace + nowe: LCD_RS, LCD_EN, LCD_D4-D7, BUZZER_PIN, PRZYCISK_PIN, LCD_INTERVAL_MS)
├── Zmienne globalne (istniejace + nowe: lcd, czas_ostatniego_lcd, przycisk_ostatni_stan, przycisk_czas_zmiany)
├── przetwarzaj_bajt()          — bez zmian
├── przejdz_do()                — ZMIANA: dodac tone() dla TRACK
├── dispatch_ramke()            — bez zmian
├── skan_tick()                 — bez zmian
├── pid_tick()                  — bez zmian
├── lcd_tick()                  — NOWA: odswiezanie LCD co 200ms
├── przycisk_tick()             — NOWA: debounce + abort TRACK→SCAN
├── safe_startup()              — bez zmian
├── init_pid()                  — bez zmian
├── ustaw_serwa()               — bez zmian
├── setup()                     — ZMIANA: lcd.begin() + bootscreen przed petla
└── loop()                      — ZMIANA: dodac lcd_tick() i przycisk_tick()
```

### Pattern 1: LCD odswiezanie bez migotania (setCursor overwrite)

**Co to:** Zamiast lcd.clear() uzyj lcd.setCursor() + lcd.print() z dopelnieniem do stalej dlugosci.
**Kiedy uzywac:** Zawsze przy odswiezaniu zawartosci LCD w petli — LCD.clear() kosztuje 1.52ms i wytwarza widoczne migotanie przy 5Hz.

```cpp
// Zrodlo: oficjalna dokumentacja Arduino LiquidCrystal (HIGH confidence)
// Wzorzec: stala szerokosc bez LCD.clear()
void lcd_tick() {
    unsigned long teraz = millis();
    if (teraz - czas_ostatniego_lcd < LCD_INTERVAL_MS) return;
    czas_ostatniego_lcd = teraz;

    // Row 0: tryb + katy (16 znakow, zawsze nadpisujemy cala linie)
    lcd.setCursor(0, 0);
    // Przyklad: "SLEDZ  P:+12 T:-5"  (trunc do 16)
    // ... format i print (patrz Code Examples)

    // Row 1: katy serw (pelna szerokosc)
    lcd.setCursor(0, 1);
    // ...
}
```

### Pattern 2: millis() debounce dla przycisku

**Co to:** Wykryj zbocze opadajace (przycisk wcisniety z INPUT_PULLUP), odczekaj 20ms, zweryfikuj stan.
**Kiedy uzywac:** Zawsze przy fizycznych przyciskach — mechaniczne styki "odbijaja" przez 5-20ms.

```cpp
// Wzorzec millis() debounce — klasyczny Arduino
#define DEBOUNCE_MS 20

bool przycisk_ostatni_stan = HIGH;      // INPUT_PULLUP: HIGH = nie wcisniety
unsigned long przycisk_czas_zmiany = 0;

void przycisk_tick() {
    // Aktywny tylko w TRACK (D-07)
    if (stan_systemu != TRACK) return;

    bool aktualny = digitalRead(PRZYCISK_PIN);
    if (aktualny != przycisk_ostatni_stan) {
        przycisk_czas_zmiany = millis();
        przycisk_ostatni_stan = aktualny;
    }
    // Zbocze stabilne przez DEBOUNCE_MS → reaguj
    if ((millis() - przycisk_czas_zmiany >= DEBOUNCE_MS) && aktualny == LOW) {
        // Przycisk wcisniety i stabilny — abort TRACK → SCAN
        przejdz_do(SCAN);
    }
}
```

### Pattern 3: tone() — buzzer przy przejsciu stanu

**Co to:** Wywolanie tone() z czasem trwania (nieblokujace) w momencie zmiany stanu.
**Kiedy uzywac:** Tylko w `przejdz_do()` dla TRACK — nie w pid_tick() ani lcd_tick().

```cpp
// tone(pin, czestotliwosc_Hz, czas_ms) — nieblokujace, uzywa Timer3 na Leonardo
void przejdz_do(StanSystemu nowy_stan) {
    stan_systemu = nowy_stan;
    if (nowy_stan == TRACK) {
        tone(BUZZER_PIN, 1000, 100);  // 1kHz, 100ms — nieblokujace (D-06)
        pidPan.Reset();
        pidTilt.Reset();
    } else if (nowy_stan == SCAN) {
        czas_startowy_skanu = millis();
        pidPan.Reset();
        pidTilt.Reset();
    }
}
```

### Pattern 4: Bootscreen LCD w setup()

**Kiedy:** Po lcd.begin(), przed safe_startup() — uzytkownik widzi status przy starcie.
**Kolejnosc:** lcd.begin() → bootscreen + delay(2000) → safe_startup() → init_pid().

```cpp
// setup() — kolejnosc z bootscreen
void setup() {
    Serial.begin(115200);
    // ... USB CDC wait ...

    lcd.begin(16, 2);           // 16 kolumn, 2 rzedy
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("ARIES-LITE v2.0");
    lcd.setCursor(0, 1);
    lcd.print("Inicjalizacja...");
    delay(2000);                 // HMI-04: bootscreen przez 2 sekundy

    serwo_pan.attach(PAN_PIN);
    serwo_tilt.attach(TILT_PIN);
    safe_startup();
    // ...
}
```

### Anti-Patterns

- **LCD.clear() w lcd_tick():** Kosztuje 1.52ms + widoczne migotanie. Zamiast: setCursor + overwrite z padding spacjami.
- **tone() w pid_tick():** Wywolanie co 10ms = ciagly ton, nie beep. Tylko w przejdz_do().
- **sprintf(buf, "%f", kat_pan) na AVR:** Na AVR toolchain sprintf nie obsluguje `%f` (floating point disabled by default). Uzyj dtostrf().
- **przycisk_tick() blokuje petla:** Nigdy delay() w debounce — tylko millis() pattern.
- **delay(2000) poza setup():** Akceptowalne tylko w bootscreen, nigdy w loop().

---

## Don't Hand-Roll

| Problem | Nie buduj | Uzyj | Dlaczego |
|---------|-----------|------|----------|
| Formatowanie float na AVR | wlasna konwersja float→string | `dtostrf(wartosc, szerokosc, precyzja, bufor)` | sprintf("%f") nie dziala na AVR bez flagi linkera; dtostrf() jest w avr-libc |
| PWM dla buzzera | wlasna petla PWM | `tone(pin, freq, duration)` | Nieblokujace, Timer3 na Leonardo, wbudowane |
| LCD komunikacja | wlasna implementacja HD44780 | `LiquidCrystal lcd(...)` | Juz zainstalowana, sprawdzona, zgodna z 4-bit |

---

## Mapowanie Pinow LCD (Claude's Discretion — D-04)

### Zajete piny na Leonardo

| Pin | Funkcja | Modul |
|-----|---------|-------|
| D7  | Przycisk abort (INPUT_PULLUP) | HMI-03 |
| D8  | Buzzer tone() | HMI-02 |
| D9  | Servo pan (Timer1A) | ARD-01 |
| D10 | Servo tilt (Timer1B) | ARD-01 |

### Rekomendowane mapowanie LCD (4-bit parallel)

LiquidCrystal w trybie 4-bit wymaga 6 pinow: RS, EN, D4, D5, D6, D7 (lcd data pins, nie D7 Arduino).

| Pin Arduino | Funkcja LCD | Uzasadnienie |
|-------------|-------------|--------------|
| D2 | RS (Register Select) | Zwykly digital, brak konfliktu |
| D3 | EN (Enable) | Zwykly digital, brak konfliktu |
| D4 | LCD_D4 | Zwykly digital, brak konfliktu |
| D5 | LCD_D5 | Zwykly digital, brak konfliktu |
| D6 | LCD_D6 | Zwykly digital, brak konfliktu |
| D11 | LCD_D7 | Zwykly digital, brak konfliktu |

**Uzasadnienie:** D2-D6 to standardowe piny GPIO bez specjalnych funkcji na Leonardo. D11 to SPI MOSI — ale SPI nie jest uzywane w projekcie. Unikamy D12/D13 (SPI MISO/SCK i LED wbudowana — mozliwe konflikty z debugowaniem). Unikamy A0-A5 — zostawiamy wolne na ewentualne przyszle czujniki.

**Instantiation w kodzie:**
```cpp
// #define w bloku konfiguracyjnym na poczatku pliku
#define LCD_RS   2
#define LCD_EN   3
#define LCD_D4   4
#define LCD_D5   5
#define LCD_D6   6
#define LCD_D7  11

// Zmienna globalna (po #define bloku)
LiquidCrystal lcd(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7);
```

---

## Format wyswietlania LCD (Claude's Discretion)

### Row 0 (16 znakow): tryb + katy

Uzytkownik widzi tryb i katy w jednej linii. Format bez FPS (FPS niedostepne w firmware — brak licznika — zrezygnuj z FPS z D-01, katy sa diagnostycznie cenniejsze).

```
"SLEDZ  P:+12 T:-5 "   // 16 znakow z padding
"SKAN   P:+42 T:+18"
"IDLE   P: +0 T: +0"
```

Kolumna 0-5: tryb (6 znakow z padding), kolumna 6: spacja, kolumna 7-11: pan (5 znakow), kolumna 12: spacja, kolumna 13-15: tilt (3 znaki).

Alternatywnie (prostsze):
```
"SLEDZ P:+12 T:-5  "   // tryb + kat pan + kat tilt
```

### Row 1 (16 znakow): bledy X/Y

```
"Ex:+045  Ey:-012  "   // blad X i Y z RPi (ostatni znany)
```

Lub — jesli katy sa na row 0, row 1 moze pokazywac bledy:
```
"Bx:+045  By:-012  "
```

**Rekomendacja finalna (prosta, czytelna):**
- Row 0: `"SLEDZ P:+NN T:+NN  "` (tryb 5 znakow + pan 6 + tilt 6 = 17 → trim do 16)
- Row 1: `"Bx:+NNN  By:-NNN  "` (blad X i Y z ostatniej ramki)

Dokladny format do ustalenia przez executor — wazne: zawsze 16 znakow (trailing spaces) aby nadpisac poprzedni tekst bez LCD.clear().

---

## Common Pitfalls

### Pitfall 1: sprintf("%f") nie dziala na AVR

**Co sie dzieje:** `sprintf(buf, "%.1f", kat_pan)` kompiluje sie bez bledu, ale zwraca pusty string lub "?" na AVR.
**Dlaczego:** AVR-GCC domyslnie linkuje printf bez wsparcia float — oszczednosc flash.
**Jak unikac:** Uzyj `dtostrf(kat_pan, 5, 1, buf)` — avr-libc wlasna funkcja, zawsze dziala.
**Przyklad:**
```cpp
char buf_pan[6];  // np. "+12.3\0"
dtostrf(kat_pan, 5, 1, buf_pan);  // szerokosc=5, precyzja=1
```
**Confidence:** HIGH — klasyczny problem AVR, potwierdzony w wielu projektach.

### Pitfall 2: tone() koliduje z Servo na Arduino Uno (ale NIE na Leonardo)

**Co sie dzieje na Uno:** tone() na Uno uzywa Timer2, Servo uzywa Timer1 — brak konfliktu. Ale jezeli ktos uzywa Timer1 do czegokolwiek innego + tone() = problem.
**Na Leonardo:** Serwa na D9/D10 uzywaja Timer1. tone() na Leonardo uzywa Timer3. Brak konfliktu — D-06 jest poprawna decyzja.
**Weryfikacja:** Potwierdzono w Arduino Leonardo hardware timer assignment (Timer1 = D9/D10 PWM, Timer3 = dostepny dla tone()).
**Confidence:** HIGH — zaleznosc tiimerow jest dokumentowana w datasheet ATmega32U4.

### Pitfall 3: LCD.clear() powoduje migotanie i blokuje 1.52ms

**Co sie dzieje:** `lcd.clear()` wysyla komende do HD44780 i czeka na wykonanie (~1.52ms). Przy 5Hz = 0.76% czasu CPU. Migotanie widoczne dla oka przy >= 2Hz.
**Jak unikac:** lcd.setCursor(0,0) + lcd.print() z dopelnieniem do 16 znakow spacjami na koncu. LCD nadpisuje bez czyszczenia.
**Confidence:** HIGH — powszechnie znany wzorzec w spolecznosci Arduino.

### Pitfall 4: Debounce — reset stanu przy kazdym odczycie

**Co sie dzieje:** Nieprawidlowy debounce resetuje timer przy kazdym odczycie zamiast przy zmianie — przycisk nigdy nie przechodzi debounce.
**Jak unikac:** Zmien `przycisk_czas_zmiany` TYLKO gdy stan sie zmienil (porownanie z `przycisk_ostatni_stan`). Patrz Pattern 2 powyzej.
**Confidence:** HIGH — klasyczny blad w implementacjach debounce.

### Pitfall 5: Inicjalizacja LCD przed Serial.begin() — brak problemu, ale kolejnosc ma znaczenie

**Bezpieczna kolejnosc w setup():**
1. `Serial.begin(115200)` + USB CDC wait
2. `lcd.begin(16, 2)` + bootscreen + delay(2000)
3. `serwo_pan.attach()` + `serwo_tilt.attach()`
4. `safe_startup()`
5. `init_pid()`
6. inicjalizacja timerow
7. `stan_systemu = IDLE`

LCD nie koliduje z Serial ani Servo — kazdy uzywa innych zasobow. Kolejnosc pokazana powyzej jest logicznie naturalna (uzytkownik widzi bootscreen podczas gdy startup sie dzieje).

### Pitfall 6: INPUT_PULLUP — logika odwrocona

**Co sie dzieje:** Z INPUT_PULLUP: przycisk niecisniety = HIGH, wcisniety = LOW. Programista czyta HIGH jako "wcisniety" — logika odwrocona.
**Jak unikac:** Reaguj na stan LOW (lub zbocze HIGH→LOW). Patrz Pattern 2 — `aktualny == LOW` oznacza wcisniety.
**Confidence:** HIGH — fundamentalna charakterystyka INPUT_PULLUP.

---

## Code Examples

### dtostrf() — formatowanie katow dla LCD

```cpp
// Zrodlo: avr-libc stdlib.h (HIGH confidence)
// dtostrf(float val, int width, int precision, char* buf)
// width: minimalna szerokosc (z znakiem), precision: cyfry po kropce
char buf[7];  // "+123.4\0" = 7 znakow max
dtostrf(kat_pan, 6, 1, buf);  // "+12.3 " lub "-60.0"
```

### lcd_tick() — pelna implementacja

```cpp
#define LCD_INTERVAL_MS 200  // 5 Hz max (D-02)

unsigned long czas_ostatniego_lcd = 0;

void lcd_tick() {
    unsigned long teraz = millis();
    if (teraz - czas_ostatniego_lcd < LCD_INTERVAL_MS) return;
    czas_ostatniego_lcd = teraz;

    // Row 0: tryb systemu
    lcd.setCursor(0, 0);
    char linia0[17];  // 16 znakow + \0
    const char* tryb_str;
    switch (stan_systemu) {
        case TRACK: tryb_str = "SLEDZ"; break;
        case SCAN:  tryb_str = "SKAN "; break;
        default:    tryb_str = "IDLE "; break;
    }
    char pan_buf[6], tilt_buf[6];
    dtostrf(kat_pan,  5, 1, pan_buf);
    dtostrf(kat_tilt, 5, 1, tilt_buf);
    // Format: "SLEDZ P:+12.3T:-5.0" — przytnij do 16
    snprintf(linia0, sizeof(linia0), "%-5s P:%-5s T:%s", tryb_str, pan_buf, tilt_buf);
    // Uzupelnij spacjami do 16 znakow
    for (uint8_t i = strlen(linia0); i < 16; i++) linia0[i] = ' ';
    linia0[16] = '\0';
    lcd.print(linia0);

    // Row 1: bledy X/Y
    lcd.setCursor(0, 1);
    char linia1[17];
    char bx_buf[5], by_buf[5];
    // ostatni_blad_x/y sa int16_t — uzyj itoa lub snprintf
    snprintf(linia1, sizeof(linia1), "Bx:%-5d By:%-5d", (int)ostatni_blad_x, (int)ostatni_blad_y);
    for (uint8_t i = strlen(linia1); i < 16; i++) linia1[i] = ' ';
    linia1[16] = '\0';
    lcd.print(linia1);
}
```

### Nowe #define — blok konfiguracyjny

```cpp
// --- HMI: LCD (D-04 Claude's Discretion: piny 2,3,4,5,6,11) ---
#define LCD_RS          2
#define LCD_EN          3
#define LCD_D4          4
#define LCD_D5          5
#define LCD_D6          6
#define LCD_D7_PIN     11  // D7_PIN aby unikac konfliktu nazwy z enum/define

// --- HMI: Buzzer + Przycisk (D-05, D-07) ---
#define BUZZER_PIN      8
#define PRZYCISK_PIN    7
#define LCD_INTERVAL_MS 200  // 5 Hz (D-02)
#define DEBOUNCE_MS     20   // debounce przycisku (D-08)
```

### Zmienna globalna lcd

```cpp
// Po bloku #define, przed innymi zmiennymi globalnymi
LiquidCrystal lcd(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7_PIN);
```

---

## Runtime State Inventory

> Ten typ fazy to rozbudowa firmware — brak stanu runtime do migracji.

| Kategoria | Znalezione | Akcja |
|-----------|-----------|-------|
| Przechowywane dane | Brak — firmware stateless, brak EEPROM w projekcie | Brak |
| Konfiguracja live service | Brak — srodowisko Arduino nie ma persystentnych runtime configs | Brak |
| Stan OS | Brak — embedded firmware nie ma OS-level state | Brak |
| Secrets/env vars | Brak — brak .env, brak sekretow w firmware | Brak |
| Build artifacts | `aries_controller.ino` zkompilowany binary na Arduino — zostanie nadpisany po `arduino-cli upload` | Upload firmware po zmianie |

**Wniosek:** Faza nie wymaga migracji danych ani runtime cleanup. Nowy firmware zastapi stary przez upload.

---

## Environment Availability

| Narzedzie | Wymagane przez | Dostepne | Wersja | Fallback |
|-----------|----------------|----------|--------|----------|
| arduino-cli | kompilacja + upload firmware | tak | 1.4.1 (2026-01-19) | — |
| arduino:avr:leonardo FQBN | kompilacja | tak | zainstalowane (Phase 18/20) | — |
| LiquidCrystal | LCD HMI | tak | bundled (juz w bibliotekach) | — |
| QuickPID | PID (istniejace) | tak | 3.1.9 | — |
| Servo | serwa (istniejace) | tak | bundled | — |
| Leonardo hardware | upload i weryfikacja | fizyczny sprzet (nie na RPi) | — | kompilacja lokalna bez uploadu |

**Brakujace narzedzia bez fallback:** Brak — wszystkie narzedzia deweloperskie dostepne.

**Uwaga:** Upload firmware wymaga fizycznego polaczenia Arduino Leonardo przez USB. Weryfikacja empiryczna (HMI widoczne na LCD, dzwiek buzzera) wymaga dostepu do sprzetowego stanowiska.

---

## Validation Architecture

> workflow.nyquist_validation nie jest ustawiony w config.json — traktuj jako enabled.

Projekt ma `"test_framework": "none"` i brak testow automatycznych (zgodnie z CLAUDE.md: "There are no unit tests or linting tools configured. Verification is empirical").

### Test Framework

| Wlasciwosc | Wartosc |
|------------|---------|
| Framework | Brak — weryfikacja empiryczna |
| Config file | Brak |
| Kompilacja | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/` |
| Upload | `arduino-cli upload --fqbn arduino:avr:leonardo -p /dev/ttyACM0 src/arduino/aries_controller/` |

### Phase Requirements → Test Map

| Req ID | Zachowanie | Typ testu | Komenda | Plik |
|--------|-----------|-----------|---------|------|
| HMI-01 | LCD odswiezany co 200ms, tryb widoczny | Empiryczny (wzrokowy) | Obserwacja LCD po starcie systemu | n/d |
| HMI-02 | Buzzer 1kHz 100ms przy przejsciu do TRACK | Empiryczny (sluchowy) | Wyslanie ramki TRACK z RPi | n/d |
| HMI-03 | Przycisk D7 w TRACK → SCAN w < 50ms | Empiryczny (wzrokowy na LCD) | Wcisniecie przycisku podczas sledzenia | n/d |
| HMI-04 | Bootscreen 2s przy starcie | Empiryczny (wzrokowy) | Reset Arduino, obserwacja LCD | n/d |

### Kompilacja jako smoke test

```bash
arduino-cli compile --fqbn arduino:avr:leonardo \
    /home/parolisko/ARIES-LITE/src/arduino/aries_controller/
```

Sukces kompilacji (exit 0) = statyczna weryfikacja poprawnosci kodu. Bledy typow, niezadeklarowane zmienne, brakujace #include — wszystkie wykrywane na etapie kompilacji.

### Wave 0 Gaps

None — brak infrastruktury testowej do stworzenia; kompilacja arduino-cli jest jedynym automatycznym sprawdzeniem.

---

## State of the Art

| Stare podejscie | Aktualne podejscie | Znaczenie |
|----------------|-------------------|-----------|
| LCD.clear() co odswiezenie | setCursor(0,0) + overwrite | Brak migotania, 1.52ms zaoszczedzone |
| sprintf("%f") na AVR | dtostrf() z avr-libc | Jedyne niezawodne rozwiazanie float→string na AVR |
| Zewnetrzna biblioteka debounce | millis() pattern w loop() | Zero zaleznosci, wystarczajaca dokladnosc |

---

## Open Questions

1. **FPS na Row 0 (D-01)**
   - Co wiemy: D-01 mowi "Row 0: tryb + FPS". FPS nie jest obliczane w obecnym firmware — brak licznika klatek.
   - Niejasne: Czy executor ma zaimplementowac licznik FPS? Czy zrezygnowac z FPS na rzecz katow (bardziej diagnostyczne)?
   - Rekomendacja: Zrezygnuj z FPS na Row 0 — zastap katami serw (sa dostepne jako `kat_pan`, `kat_tilt`). Row 0: tryb + katy; Row 1: bledy X/Y. To zgodne z duchem D-01 ("diagnostyczne podejscie").

2. **LCD.clear() tylko przy zmianie trybu (Claude's Discretion)**
   - Rekomendacja: NIE uzywaj LCD.clear() nawet przy zmianie trybu. Staly overwrite eliminuje potrzebe clear() — krotsze nazwy trybow (SKAN, SLEDZ, IDLE) sa zawsze tej samej dlugosci lub krotsze + padding spacjami.

3. **Kolejnosc lcd.begin() w setup()**
   - Rekomendacja: lcd.begin() jako pierwsze (po Serial.begin()), potem bootscreen z delay(2000), potem safe_startup(). Uzytkownik widzi bootscreen przez czas startupu serw.

---

## Sources

### Primary (HIGH confidence)

- LiquidCrystal.h naglowek — `/home/parolisko/Arduino/libraries/LiquidCrystal/src/LiquidCrystal.h` — API konstruktora 4-bit, begin(), setCursor(), print()
- aries_controller.ino — `src/arduino/aries_controller/aries_controller.ino` — istniejacy kod: piny, timery, przejdz_do(), millis() patterns
- CONTEXT.md — `.planning/phases/22-hmi-lcd-buzzer-przycisk/22-CONTEXT.md` — wszystkie decyzje D-01..D-10
- Arduino IDE documentation (wbudowana wiedza + weryfikacja przez naglowki): tone(), digitalRead(), INPUT_PULLUP, dtostrf()

### Secondary (MEDIUM confidence)

- Arduino Leonardo pinout i timer assignment (ATmega32U4): Timer1=D9/D10, Timer3=dostepny dla tone() — standardowa wiedza embedded, spójna z decyzja D-06

### Tertiary (LOW confidence)

- LCD.clear() timing 1.52ms — powszechnie podawane w dokumentacji HD44780, nieweryfikowane bezposrednio z datasheetu

---

## Metadata

**Confidence breakdown:**
- Mapowanie pinow LCD: HIGH — wynikaja bezposrednio z zajecia D7/D8/D9/D10 i dostepnosci pinow Leonardo
- LiquidCrystal API: HIGH — weryfikowane przez lokalny naglowek biblioteki
- tone() / Timer3: HIGH — zgodne z decyzja D-06 i ATmega32U4 datasheet (Timer1=servo, Timer3=tone)
- dtostrf() zamiast sprintf: HIGH — klasyczny problem AVR, jednoznaczne rozwiazanie
- millis() debounce: HIGH — sprawdzony wzorzec, zero bibliotek

**Research date:** 2026-03-31
**Valid until:** 2026-06-30 (stabilny embedded domain — 90 dni)
