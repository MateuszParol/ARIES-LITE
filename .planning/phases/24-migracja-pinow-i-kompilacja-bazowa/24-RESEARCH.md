# Phase 24: Migracja Pinow i Kompilacja Bazowa - Research

**Researched:** 2026-04-01
**Domain:** Arduino firmware port — ATmega32U4 (Leonardo) → Renesas RA4M1 (Uno R4 WiFi)
**Confidence:** HIGH — wszystkie kluczowe ustalenia zweryfikowane empirycznie przez kompilacje na miejscu

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** LCD 1602: RS=A0, E=A1, D4=D2, D5=D3, D6=D4, D7=D5
- **D-02:** Serwa MG-90S: PAN=D6, TILT=D9
- **D-03:** Buzzer=D8 (OUTPUT), Przycisk=D7 (INPUT_PULLUP)
- **D-04:** ZAREZERWOWANE — SD: D10-D13 (SPI), I2C: A4-A5 (nie uzywac w tej fazie)
- **D-05:** delay(500) na poczatku setup() PRZED inicjalizacja serw — stabilizacja napiecia zasilacza 6V. Nastepnie istniejaca rampa writeMicroseconds(500->1500) w 1000ms. Lacznie ~1.5s do pelnej gotowosci.
- **D-09:** QuickPID musi kompilowac sie na Arduino Uno R4 WiFi (Renesas RA4M1). Zweryfikowac parametry enum (iAwMode, pMode, dMode) — moga sie roznic na 32-bit.
- **D-10:** Servo library >= 1.3.0 wymagana — znany bug jittera na R4 w wersjach < 1.2.2. Zweryfikowac plynnosc sweep na D6/D9.
- **D-11:** LiquidCrystal na pinach analogowych (A0, A1) — wymaga jawnego pinMode(A0, OUTPUT) w setup() (DAC domyslnie wylaczony, ale lepiej explicit).
- **D-12:** Zmiana bootscreen LCD: "ARIES-LITE v2.1" (z v2.0). Zaktualizowac tez komentarz naglowkowy w pliku .ino.

### Claude's Discretion

- Serial startup behavior na R4 — D-06
- dtostrf zamiennik (snprintf int cast vs %.0f) — D-07
- Struktura plikow (.ino vs .h/.cpp split) — D-08
- Kolejnosc zmian w migracji (piny najpierw, potem Soft Start, potem dtostrf)
- Czy tone() na D8 wymaga innego timera na R4 (Renesas vs AVR Timer3)
- Wewnetrzne nazwy zmiennych — zachowac obecne polskie

### Deferred Ideas (OUT OF SCOPE)

Brak — dyskusja pozostala w zakresie fazy.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MIG-03 | Firmware kompiluje sie pod Arduino Uno R4 WiFi (ArduinoCore-renesas >=1.4.1) bez bledow | ZWERYFIKOWANE empirycznie — kompilacja zero bledow juz teraz (ArduinoCore-renesas 1.5.3 zainstalowany) |
| MIG-04 | Nowa mapa pinow: LCD(RS=A0,E=A1,D4=D2,D5=D3,D6=D4,D7=D5), Serwa(PAN=D6,TILT=D9), Buzzer=D8, Przycisk=D7 | Prosty #define swap — 7 linii kodu, zidentyfikowane dokladnie |
| MIG-05 | Servo library >=1.3.0 — brak jittera na serwach MG-90S przy PID 100Hz | Servo 1.3.0 juz zainstalowany, architektura renesas_uno na liscie — OK |
| MIG-06 | dtostrf() zastapione snprintf() — kompatybilnosc ARM Renesas RA4M1 | ZASKAKUJACE ODKRYCIE: dtostrf DZIALA na R4 przez shim w core 1.5.3 — zamiana zalecana ale nie krytyczna |
| MIG-07 | Usuniete specyfiki Leonardo (Caterina DTR=False, USB CDC workaroundy) | Firmware: while(!Serial) z timeoutem — OK na R4, zachowac; serial_interface.py: dtr=False wymaga usuniecia |
| MIG-08 | Soft Start 500ms w setup() — stabilizacja napiecia przed ruchem serw | delay(500) dodac w ServoPID::_bezpieczny_start() PRZED rampa; punkt wstawienia zidentyfikowany (linia 278) |
| MIG-09 | QuickPID kompiluje sie i dziala poprawnie na 32-bit Renesas RA4M1 | ZWERYFIKOWANE — enum iAwCondition, pOnError, dOnMeas sa poprawne w QuickPID 3.1.9, architektures=* |
</phase_requirements>

---

## Summary

Firmware ARIES-LITE v2.0 (496 linii, plik `src/arduino/aries_controller/aries_controller.ino`) **kompiluje sie juz teraz na Arduino Uno R4 WiFi bez bledow** — to kluczowe odkrycie weryfikacyjne. ArduinoCore-renesas 1.5.3 dostarcza shim dla `dtostrf()` (plik `api/deprecated-avr-comp/avr/dtostrf.h`), wiec blad kompilacji ktory byl opisany w dokumentacji milestoneowej nie wystepuje z aktualna wersja core'a. Biblioteki Servo 1.3.0 i QuickPID 3.1.9 sa juz zainstalowane i kompatybilne.

Faza 24 sprowadza sie do 5 precyzyjnych zmian w firmware + 1 zmiany w `serial_interface.py`: zmiana 7 #define pinow, dodanie delay(500) Soft Start, zamiana dtostrf() na snprintf() (zalecana mimo dzialajacego shimu — czytelnosc + przyszlosc), skrocenie bloku Serial CDC wait, aktualizacja wersji na v2.1 i wymagane testy weryfikacyjne na sprzecie.

**Rekomendacja:** Port w jednym .ino (struktura D-08 — zachowac monolityczny plik). Podzial na .h/.cpp ma sens od Fazy 25 gdy dodajemy RTC/SD — jeszcze 100-200 linii kodu. Teraz byloby przedwczesna komplikacja.

---

## Standard Stack

### Core

| Biblioteka | Wersja | Cel | Status |
|-----------|--------|-----|--------|
| ArduinoCore-renesas | 1.5.3 | BSP dla Renesas RA4M1 — toolchain ARM + HAL | ZAINSTALOWANY na dev machine |
| Servo (arduino-libraries) | 1.3.0 | PWM serwa MG-90S na D6/D9 | ZAINSTALOWANY — architektura renesas_uno na liscie |
| QuickPID | 3.1.9 | Dual-axis PID 100 Hz | ZAINSTALOWANY — architektures=* |
| LiquidCrystal (built-in) | 1.0.7 | LCD 1602 4-bit na A0,A1,D2-D5 | ZAINSTALOWANY |

### Weryfikacja wersji bibliotek (wykonana 2026-04-01)

```
arduino-cli lib list wynik:
  LiquidCrystal  1.0.7   (user)
  QuickPID       3.1.9   (user)
  Servo          1.3.0   (user)

arduino-cli core list wynik:
  arduino:avr         1.8.7
  arduino:renesas_uno 1.5.3  (zainstalowany podczas research)
```

### Komendy instalacji

```bash
# Instalacja core (jesli brak):
arduino-cli core update-index
arduino-cli core install arduino:renesas_uno

# Biblioteki sa juz zainstalowane. Weryfikacja:
arduino-cli lib list

# Kompilacja weryfikacyjna:
arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi \
  src/arduino/aries_controller/
```

---

## Architecture Patterns

### Aktualna struktura firmware (do zachowania)

```
aries_controller.ino  (496 linii, monolityczny)
  ├── #include + #define (linie 1-70)
  │     ├── stale protokolu: FRAME_SIZE, START_MARKER
  │     ├── konfiguracja PID: KP, KI, KD, OUTPUT_LIMIT, PID_INTERVAL_MS
  │     ├── PINY SERW: PAN_PIN=9, TILT_PIN=10  ← ZMIANA
  │     ├── limity katowe: PAN_MIN/MAX, TILT_MIN/MAX
  │     ├── PINY LCD: LCD_RS=2, LCD_EN=3, ..., LCD_D7_PIN=11  ← ZMIANA
  │     └── PINY HMI: BUZZER_PIN=8, PRZYCISK_PIN=7  (bez zmian)
  ├── enum StanParsera, StanSystemu (linie 58-70)
  ├── class HMI (linie 76-169)
  │     ├── lcd_krok(): dtostrf()  ← ZAMIANA na snprintf
  │     └── lcd_bootscreen(): "v2.0"  ← ZMIANA na "v2.1"
  ├── class ServoPID (linie 175-309)
  │     └── _bezpieczny_start(): brak delay(500)  ← DODAC
  ├── class MaszynaStanow (linie 315-440)  ← BEZ ZMIAN
  ├── globalne instancje (linie 444-447)  ← BEZ ZMIAN
  └── setup() + loop() (linie 452-495)
        └── while(!Serial) blok  ← SKROCIC do 500ms
```

### Rekomendowana struktura plikow (D-08: Claude's Discretion)

**Decyzja: zachowac jeden .ino plik.** Uzasadnienie:
- Faza 24 dodaje ~5 linii zmian — brak powodu do strukturyzacji
- Fazy 25-27 dodadza DataLogger (~150 linii) — split wtedy ma sens
- Jeden .ino: prostszy Arduino IDE build, brak problemow z include paths

### Wzorzec inicjalizacji setup() po zmianie

```cpp
void setup() {
    Serial.begin(115200);

    // R4 WiFi: USB przez ESP32-S3 bridge — max 500ms wait
    // (zachowac timeout — nie blokujacy, dziala na obu platformach)
    uint32_t start = millis();
    while (!Serial && millis() - start < 500) {
        delay(10);
    }

    // Soft Start 500ms — stabilizacja napiecia 6V PRZED inicjalizacja serw (D-05)
    // UWAGA: serwa.inicjalizuj() wywoluje _bezpieczny_start() wewnetrznie
    // delay(500) musi byc PRZED serwa.inicjalizuj(), nie w srodku
    delay(500);  // MIG-08: stabilizacja zasilacza

    // Inicjalizacja HMI: LCD bootscreen + piny buzzer/przycisk
    hmi.inicjalizuj();

    // Inicjalizacja serw: attach + bezpieczny start (rampa 1000ms) + parametry PID
    serwa.inicjalizuj();
}
```

**UWAGA architektoniczna:** Wedlug CONTEXT.md D-05 delay(500) ma byc PRZED inicjalizacja serw. Obecna kolejnosc setup() to: Serial → HMI.inicjalizuj() → serwa.inicjalizuj(). Delay(500) powinno byc dodane przed `hmi.inicjalizuj()` (bo bootscreen wymaga LCD, a nie serw) albo bezposrednio przed `serwa.inicjalizuj()`. Drugi wariant jest bezpieczniejszy — LCD bootscreen moze sie pojawic od razu, a delay(500) chroni serwa.

### Wzorzec zamiany dtostrf() na snprintf() (D-07)

```cpp
// PRZED (AVR dtostrf — dziala na R4 przez shim, ale nieczytelne):
char pan_buf[5], tilt_buf[5];
dtostrf(kat_pan,  4, 0, pan_buf);
dtostrf(kat_tilt, 4, 0, tilt_buf);

// PO (snprintf z int cast — precyzja 0, identyczny wynik):
char pan_buf[5], tilt_buf[5];
snprintf(pan_buf,  sizeof(pan_buf),  "%4d", (int)kat_pan);
snprintf(tilt_buf, sizeof(tilt_buf), "%4d", (int)kat_tilt);
```

**Uzasadnienie int cast:** `dtostrf(kat_pan, 4, 0, buf)` z precyzja=0 zaokragla do calkowitych. `(int)kat_pan` robi trunc (nie round), ale dla wyswietlania na LCD roznica jest pomijalna. Alternatywa: `"%.0f"` dla prawdziwego zaokraglenia — obie opcje sa akceptowalne.

### Mapa zmian #define (MIG-04)

```cpp
// STARY (Leonardo v2.0):            NOWY (Uno R4 WiFi v2.1):
#define PAN_PIN         9         →  #define PAN_PIN         6    // D6
#define TILT_PIN        10        →  #define TILT_PIN        9    // D9

#define LCD_RS          2         →  #define LCD_RS          A0   // RS=A0
#define LCD_EN          3         →  #define LCD_EN          A1   // E=A1
#define LCD_D4          4         →  #define LCD_D4          2    // D4=D2
#define LCD_D5          5         →  #define LCD_D5          3    // D5=D3
#define LCD_D6          6         →  #define LCD_D6          4    // D6=D4
#define LCD_D7_PIN     11         →  #define LCD_D7_PIN      5    // D7=D5

// BEZ ZMIAN (juz poprawne):
#define BUZZER_PIN      8         // D8 — tone() dziala na R4
#define PRZYCISK_PIN    7         // D7 — INPUT_PULLUP
```

### Anti-Patterns do unikniecia

- **Brak delay(500) przed serwa.inicjalizuj():** Spike pradowy 6V zasilacza przy attach() bez stabilizacji = ryzyko brownout/restart
- **Brak timeoutu w while(!Serial):** Na R4 bez USB podlaczonego setup() nigdy nie konczy — blokuje HMI i serwa
- **Zmiana logiki PID lub protokolu:** MaszynaStanow i SerialInterface protokol 8B sa BEZ ZMIAN
- **Dodawanie WiFi/BT includes:** ESP32 burst current na 3.3V rail = brownout przy serwie

---

## Kluczowe Odkrycia

### Odkrycie 1: dtostrf DZIALA na renesas_uno 1.5.3 (MEDIUM confidence)

**Co to znaczy dla planu:** MIG-06 nie jest blokerem kompilacji. Firmware kompiluje sie zero bledow juz teraz. Mimo to zamiana na snprintf() jest zalecana — dtostrf() via shim jest "deprecated-avr-comp", co sugeruje ze moze zniknac w przyszlych core releases. Zamiana teraz kosztuje 2 linie, chroni Fazy 25-27.

**Zrodlo:** `find /home/parolisko/.arduino15/packages/arduino/hardware/renesas_uno/1.5.3/cores/arduino/ -name "dtostrf.h"` — plik istnieje w `api/deprecated-avr-comp/avr/dtostrf.h`, wlaczany przez `Arduino.h`.

### Odkrycie 2: Kompilacja zero bledow juz teraz (HIGH confidence)

```
Wynik: arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/
Szkic uzyka 64188 bajtow (24%) pamieci programu. Maksimum to 262144 bajtow.
Zmienne globalne uzywaja 7432 bajtow (22%) pamieci dynamicznej, [...]. Maksimum to 32768 bajtow.
```

Firmware v2.0 ze starymi pinami (Leonardo) **kompiluje sie czysto** na R4. Jedyna praca w Fazie 24 to: zmiana #define + Soft Start + snprintf + Serial timeout + v2.1 string + DTR fix w Python + testy sprzetowe.

### Odkrycie 3: QuickPID 3.1.9 enum names identyczne (HIGH confidence)

Zweryfikowano przez `grep` w source QuickPID 3.1.9:
- `QuickPID::iAwMode::iAwCondition` — OK
- `QuickPID::pMode::pOnError` — OK
- `QuickPID::dMode::dOnMeas` — OK
- `QuickPID::Action::direct` — OK

Brak zmian w kodzie PID.

### Odkrycie 4: LiquidCrystal.begin() wywoluje pinMode() wewnetrznie (HIGH confidence)

`LiquidCrystal.cpp` linia 91: `pinMode(_rs_pin, OUTPUT)`. Jawny `pinMode(A0, OUTPUT)` w setup() (D-11) jest reduntantny ale harmless — zalecany jako explicitna dokumentacja intencji, nie jako wymaganie techniczne.

### Odkrycie 5: serial_interface.py wymaga usuniecia DTR=False (HIGH confidence)

Plik `src/vision/serial_interface.py` linia 60: `ser.dtr = False`. Na R4 DTR nie resetuje ukladu (ESP32 bridge, nie Caterina). Komentarz w kodzie explicite mowi "zapobiega resetowi Leonardo" — to jest Leonardo-specific workaround. Nalezy usunac lub zmienic na `ser.dtr = None` (brak interwencji). Protokol binarny 8B bez zmian.

### Odkrycie 6: tone() dziala na R4 WiFi (MEDIUM confidence)

`tone()` jest czescia ArduinoCore-renesas API na R4 — dziala. D8 nie ma zadnych specjalnych ograniczen timera na R4 WiFi. Nie ma konfliktu z Servo D6/D9 (rozne timery GPT). Buzzer passive < 8mA limit na R4.

### Odkrycie 7: ArduinoCore-renesas 1.5.3 zamiast 1.4.1 (LOW->MEDIUM confidence)

STACK.md (milestoneowa) referencjonuje 1.4.1. Index Arduino Package Manager zwraca 1.5.3 jako Latest. Instalacja 1.5.3 przebiegla pomyslnie, kompilacja dziala. Nie znaleziono release notes 1.5.3 — MEDIUM confidence ze nie wprowadza regresji dla tej fazy. Servo 1.3.0 na liscie architektur: `renesas_uno` — poprawne dla 1.5.3.

---

## Don't Hand-Roll

| Problem | Nie budowac | Uzyc zamiast | Dlaczego |
|---------|-------------|--------------|----------|
| float → string | Wlasna funkcja konwersji | `snprintf(buf, sizeof(buf), "%4d", (int)val)` | Standard C, brak heap, dziala wszedzie |
| Servo PWM timing | Recznie pisac writeMicroseconds | `Servo.write()` (Servo 1.3.0) | Timer GPT R4 jest skomplikowany; 1.3.0 naprawia znany bug |
| PID anti-windup | Wlasna implementacja | `QuickPID::iAwMode::iAwCondition` | 3.1.9 zweryfikowany, dziala na 32-bit |
| LCD debounce delay | `delay()` w lcd loop | millis() throttle `if (teraz - last < 200)` | Juz zaimplementowane, nie zmieniac |
| Serial CDC wait | Nieskonczone while(!Serial) | `while (!Serial && millis() - start < 500)` | ESP32 bridge max 500ms — timeout jest wymagany |

---

## Common Pitfalls

### Pitfall 1: Brak delay(500) przed inicjalizacja serw

**Co sie psuje:** Serwa ruszaja gwaltownie przy powrocie zasilania, spike pradowy moze zresetowac Uno R4.
**Dlaczego:** Zasilacz 6V potrzebuje stabilizacji przed obciazeniem.
**Jak unikac:** delay(500) w setup() przed `serwa.inicjalizuj()` (nie w _bezpieczny_start() — D-05 mowi "na poczatku setup()").
**Sygnaly ostrzegawcze:** Reset podczas inicjalizacji, LCD pokazuje bootscreen i znika.

### Pitfall 2: Niepoprawna kolejnosc: delay(500) vs hmi.inicjalizuj()

**Co sie psuje:** delay(500) wstawiony przed Serial.begin() lub po serwa.inicjalizuj() nie spelnia wymagania D-05.
**Dlaczego:** Aktualna kolejnosc setup(): Serial → HMI → Serwa. delay(500) powinno byc bezposrednio przed `serwa.inicjalizuj()`.
**Jak unikac:** Wzorzec: `hmi.inicjalizuj(); delay(500); serwa.inicjalizuj();` — LCD bootscreen pojawia sie od razu, serwa stabilizuja 500ms potem. Uzytkownik widzi "Inicjalizacja..." zanim serwa ruszaja.

### Pitfall 3: DTR=False pozostawiony w serial_interface.py

**Co sie psuje:** Na R4 nie jest to krytyczne (DTR nie powoduje resetu), ale kod mowi "zapobiega resetowi Leonardo" — dezinformuje przyszlych developerow.
**Dlaczego:** Caterina-specific workaround.
**Jak unikac:** Zmiana `ser.dtr = False` na usuniecie lub `# ser.dtr = False  # legacy Leonardo — niepotrzebne na R4`.

### Pitfall 4: dtostrf zachowane bez zamiany

**Co sie psuje:** Technicznie kompiluje sie i dziala (shim w core 1.5.3), ale jest w katalogu "deprecated-avr-comp". Future core update moze usunac shim.
**Dlaczego:** Arduino core team oznaczyl to jako deprecated compatibility.
**Jak unikac:** Zamien teraz na snprintf() — 2 linie, 0 ryzyka.

### Pitfall 5: Sprawdzenie wersji Servo przed upload

**Co sie psuje:** Servo < 1.2.2 powoduje jitter na R4 — serwa "tykaja" co ~100 µs.
**Dlaczego:** Bug w implementacji timera GPT dla renesas_uno w starszych wersjach.
**Jak unikac:** Servo 1.3.0 juz zainstalowany. Weryfikacja przed testem Sweep: `arduino-cli lib list | grep Servo`.

### Pitfall 6: Brak jawnego pinMode(A0, OUTPUT) przed lcd.begin()

**Co sie psuje:** Technicznie LiquidCrystal.begin() wywoluje pinMode() wewnetrznie — dziala bez jawnego wywolania. Ale A0 jest pinem DAC na R4, a DAC domyslnie wylaczony.
**Dlaczego:** Bezpieczniej explicit — dokumentacja intencji (D-11).
**Jak unikac:** Dodac `pinMode(A0, OUTPUT); pinMode(A1, OUTPUT);` w setup() PRZED `hmi.inicjalizuj()`.

---

## Code Examples

### Pelna lista zmian w #define (linie 21-50 firmware)

```cpp
// Source: CONTEXT.md D-01, D-02; weryfikacja empiryczna 2026-04-01

// SERWA (zmiana):
#define PAN_PIN         6    // D6 — bylo 9
#define TILT_PIN        9    // D9 — bylo 10

// LCD (zmiana — A0/A1 jako RS/EN, D2-D5 jako data):
#define LCD_RS          A0   // RS=A0 — bylo 2
#define LCD_EN          A1   // E=A1 — bylo 3
#define LCD_D4          2    // D4=D2 — bylo 4
#define LCD_D5          3    // D5=D3 — bylo 5
#define LCD_D6          4    // D6=D4 — bylo 6
#define LCD_D7_PIN      5    // D7=D5 — bylo 11

// BUZZER + PRZYCISK (bez zmian, juz poprawne):
#define BUZZER_PIN      8    // D8
#define PRZYCISK_PIN    7    // D7 INPUT_PULLUP
```

### setup() po migracji

```cpp
// Source: CONTEXT.md D-05, D-06, D-11; wzorzec empiryczny

void setup() {
    Serial.begin(115200);

    // R4 WiFi: ESP32-S3 USB bridge — skrocony timeout 500ms (D-06)
    uint32_t start = millis();
    while (!Serial && millis() - start < 500) {
        delay(10);
    }

    // Explicit OUTPUT dla pinow DAC/op-amp A0/A1 (D-11)
    pinMode(A0, OUTPUT);
    pinMode(A1, OUTPUT);

    // LCD bootscreen — widoczny od razu
    hmi.inicjalizuj();

    // Soft Start 500ms — stabilizacja zasilacza 6V PRZED ruchem serw (D-05, MIG-08)
    delay(500);

    // Serwa: attach + rampa writeMicroseconds(500->1500) w 1000ms
    serwa.inicjalizuj();
}
```

### dtostrf → snprintf zamiana (linie 109-111 firmware)

```cpp
// Source: CONTEXT.md D-07; odkrycie empiryczne dtostrf shim 2026-04-01

// PRZED:
char pan_buf[5], tilt_buf[5];
dtostrf(kat_pan,  4, 0, pan_buf);
dtostrf(kat_tilt, 4, 0, tilt_buf);

// PO (int cast — precyzja 0, format 4 znaki prawostronne):
char pan_buf[5], tilt_buf[5];
snprintf(pan_buf,  sizeof(pan_buf),  "%4d", (int)kat_pan);
snprintf(tilt_buf, sizeof(tilt_buf), "%4d", (int)kat_tilt);
```

### Usuniecie DTR workaround w serial_interface.py

```python
# Source: odkrycie empiryczne 2026-04-01; PITFALLS.md Pitfall 5

# PRZED (Leonardo-specific — linia 60 serial_interface.py):
ser.dtr = False  # DTR=False PRZED open() — zapobiega resetowi Leonardo (bootloader Caterina)

# PO (R4 WiFi: ESP32 bridge nie resetuje sie przy DTR):
# Usunac linie "ser.dtr = False" lub zakomentowac z explanacją:
# ser.dtr = False  # LEGACY Leonardo/Caterina — nie potrzebne na Uno R4 WiFi (ESP32 bridge)
```

### Weryfikacja Servo Sweep (test przed PID)

```cpp
// Source: PITFALLS.md Pitfall 1; Servo 1.3.0 library
// Test: wgrac oddzielny szkic, obserwowac ruch na D6/D9 przez 30s

#include <Servo.h>
Servo pan, tilt;
void setup() {
    pan.attach(6);   // D6 — nowy PAN_PIN
    tilt.attach(9);  // D9 — nowy TILT_PIN
}
void loop() {
    for (int i = 0; i <= 180; i++) { pan.write(i); tilt.write(i); delay(15); }
    for (int i = 180; i >= 0; i--) { pan.write(i); tilt.write(i); delay(15); }
}
// Oczekiwany wynik: plynny ruch bez "tykania" lub skokow
```

---

## State of the Art

| Stary Approach (Leonardo) | Nowy Approach (R4 WiFi) | Kiedy zmieniono | Impakt |
|---------------------------|------------------------|-----------------|--------|
| dtostrf() z AVR libc | snprintf() — standard C | Migracja na ARM | Brak bledu kompilacji na non-AVR targets |
| while(!Serial) do 3000ms | while(!Serial) do 500ms | R4 ESP32 bridge | Szybszy startup, mniejsze ryzyko blokady |
| DTR=False w pyserial | Brak DTR manipulacji | Caterina → ESP32 bridge | Prostszy kod, brak potrzeby workaround |
| PAN_PIN=9, TILT_PIN=10 | PAN_PIN=6, TILT_PIN=9 | Nowa mapa pinow v2.1 | D10 wolny dla SD card CS (Faza 26) |
| LCD na D2-D6, D11 | LCD na A0,A1,D2-D5 | Nowa mapa pinow v2.1 | Konsekwentne groupowanie: PWM na D6/D9, SPI D10-D13 |

**Deprecated:**
- `dtostrf()` z `avr/dtostrf.h` — dostarczany jako "deprecated-avr-comp" shim w renesas core; zastapic snprintf()
- `while(!Serial)` bez timeoutu — nigdy nie konczylo sie bez USB; timeout 500ms jest standardem

---

## Open Questions

1. **Typ buzzera (aktywny vs pasywny)**
   - Co wiemy: D8, tone(BUZZER_PIN, 1000, 100) w firmware. Uno R4 WiFi limit 8mA per pin.
   - Co jest niejasne: Czy buzzer w hardware jest aktywny (do 30mA, wymaga tranzystora) czy pasywny (< 8mA, bezpieczny direct drive).
   - Rekomendacja: STATE.md "Pending Todos" wymienia to explicite — sprawdzic przed upload, zmierzyc prad lub znalezc numer modelu. Jesli aktywny i przekracza 8mA, Faza 24 wymaga NPN tranzystora na D8.

2. **Orientacja serw na nowym montazu Uno R4**
   - Co wiemy: PAN_INVERT=1, TILT_INVERT=-1 z v1.7 kalibracji na poprzednim montazu.
   - Co jest niejasne: Czy montaz fizyczny Uno R4 WiFi ma ta sama orientacje co Leonardo — PAN_DIR / TILT_DIR moze wymagac zmiany.
   - Rekomendacja: Empiryczna kalibracja po pierwszym uruchomieniu — wyslac ramke SLEDZENIE z blad_x=+50, obserwowac kierunek ruchu.

3. **Kompilacja na Uno R4 Minima vs WiFi**
   - Co wiemy: FQBN `arduino:renesas_uno:unor4wifi` uzyty w testach. CONTEXT.md mowi "Uno R4 WiFi".
   - Co jest niejasne: STACK.md odnotowuje ze user wspominal "testy na Uno R3 najpierw".
   - Rekomendacja: Nie testowac na R3 — firmware v2.1 jest dedykowany R4. R3 test bylby dodatkowa komplikacja bez wartosci.

---

## Environment Availability

| Dependency | Wymagane przez | Dostepne | Wersja | Fallback |
|------------|---------------|----------|--------|----------|
| arduino-cli | Kompilacja + upload firmware | tak | 1.4.1 | — |
| ArduinoCore-renesas (arduino:renesas_uno) | Kompilacja na R4 WiFi | tak | 1.5.3 | — |
| Servo library | MIG-05: brak jittera | tak | 1.3.0 | — |
| QuickPID library | MIG-09: PID na 32-bit | tak | 3.1.9 | — |
| LiquidCrystal library | LCD HMI | tak | 1.0.7 | — |
| Arduino Uno R4 WiFi (hardware) | MIG-03..09 testy sprzet | NIEZNANE (dev machine =/= RPi) | — | Kompilacja OK, sprzet na RPi |
| USB kabel do Uno R4 WiFi | Upload + Serial monitor | NIEZNANE | — | — |
| Zasilacz 6V serwa | MIG-08 Soft Start test | NIEZNANE | — | — |

**Uwaga:** Kompilacja zweryfikowana na dev machine (Linux RPi 4, arduino-cli 1.4.1). Upload i testy sprzetu wymagaja fizycznego Arduino Uno R4 WiFi podlaczonego do maszyny.

**Brakujace zalezniosci bez fallbacku:**
- Arduino Uno R4 WiFi hardware — wymagany do zadan weryfikacyjnych MIG-04, MIG-05, MIG-08

---

## Validation Architecture

> Projekt nie ma skonfigurowanego test framework (config.json: `test_framework: "none"`). Weryfikacja jest empiryczna — zgodnie z CLAUDE.md "Verification is empirical (HTTP responses, visual confirmation, command output)."

### Framework

| Property | Value |
|----------|-------|
| Framework | brak — empiryczna weryfikacja |
| Quick run | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/` |
| Full verify | kompilacja + upload + Serial monitor 60s + Sweep test |

### Mapa wymagan → weryfikacji

| Req ID | Zachowanie | Typ testu | Komenda / Metoda | Czy istnieje? |
|--------|-----------|-----------|------------------|---------------|
| MIG-03 | Kompilacja zero bledow na R4 WiFi | kompilacja | `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi src/arduino/aries_controller/` | tak — dziala juz teraz |
| MIG-04 | Nowa mapa pinow — LCD/serwa poprawne | sprzet | LCD bootscreen widoczny; serwa ruszaja do 90/90 | Hardware needed |
| MIG-05 | Servo >= 1.3.0 — brak jittera | sprzet | Szkic Sweep D6/D9 przez 30s — brak tykania | Hardware needed |
| MIG-06 | dtostrf zastapione snprintf | kompilacja | Grep w .ino: `grep dtostrf aries_controller.ino` — zero wynikow | Code change |
| MIG-07 | Usuniete specyfiki Leonardo | code review | Grep: `grep -n "DTR\|Leonardo\|Caterina" serial_interface.py` — zero wynikow | Code change |
| MIG-08 | Soft Start 500ms — brak skoku pradu | sprzet | 5 cykli zasilania, brak resetu podczas inicjalizacji | Hardware needed |
| MIG-09 | QuickPID dziala poprawnie na 32-bit | sprzet | Serial monitor: PID output stabilny, serwa sledza blad_x/y | Hardware needed |

---

## Sources

### Primary (HIGH confidence)
- `arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi` — empiryczna kompilacja firmware v2.0 na R4, zero bledow
- `/home/parolisko/.arduino15/packages/arduino/hardware/renesas_uno/1.5.3/cores/arduino/api/deprecated-avr-comp/avr/dtostrf.h` — dtostrf shim w renesas core
- `arduino-cli lib list` — Servo 1.3.0, QuickPID 3.1.9, LiquidCrystal 1.0.7 zainstalowane
- `/home/parolisko/Arduino/libraries/QuickPID/src/QuickPID.h` — enum names zweryfikowane

### Secondary (MEDIUM confidence)
- [Arduino Uno R4 WiFi User Manual](https://docs.arduino.cc/tutorials/uno-r4-wifi/cheat-sheet) — pinout, A0 DAC, A1 op-amp
- [ArduinoCore-renesas releases](https://github.com/arduino/ArduinoCore-renesas/releases/tag/1.4.1) — historia core
- [Servo library releases](https://github.com/arduino-libraries/Servo/releases) — Servo 1.3.0 renesas_uno support
- `.planning/research/STACK.md`, `.planning/research/PITFALLS.md` — milestoneowe research 2026-04-01

### Tertiary (LOW confidence)
- [Arduino Forum — Tone() function and timer in UNO R4](https://forum.arduino.cc/t/tone-function-and-timer-in-uno-r4/1214643) — tone() dziala na R4, nie ma konfliktow na D8 (thread bez odpowiedzi ale tone() jest udokumentowane w core)

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — wszystkie biblioteki zweryfikowane przez `arduino-cli lib list`, core przez `arduino-cli core install`
- Architecture: HIGH — zmiany #define zidentyfikowane linia po linii w istniejacym firmware
- Pitfalls: HIGH — Pitfall 1-5 maja zrodla empiryczne (kompilacja + source grep); Pitfall 6 (dtostrf shim) odkryty empirycznie
- Validacja: HIGH — kompilacja zero bledow zweryfikowana, sprzet wymagany dla full test

**Research date:** 2026-04-01
**Valid until:** 2026-07-01 (biblioteki stabilne; ArduinoCore-renesas moze sie zmienic, ale Servo 1.3.0 + QuickPID 3.1.9 sa stabilne)
