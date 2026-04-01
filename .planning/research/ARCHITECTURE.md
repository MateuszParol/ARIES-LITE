# Architecture Research

**Domain:** Distributed embedded vision + real-time servo control (RPi4 Mozg + Arduino Uno R4 WiFi Uklad Wykonawczy)
**Researched:** 2026-03-30 (v2.0 base), 2026-04-01 (v2.1 supplement: SD logging + RTC + pin migration)
**Confidence:** HIGH (validated against official docs, reference implementations, and existing codebase)

---

## v2.1 Supplement: SD Logging + RTC + Pin Migration Integration

**Milestone:** v2.1 Migracja na Uno R4 + DataLogger
**Researched:** 2026-04-01

This section answers the specific question: How do SD card logging and RTC DS1307 integrate with the existing 100Hz PID firmware architecture?

---

### System Overview (v2.1)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Arduino Uno R4 WiFi                             │
│                                                                      │
│  ┌──────────────────────┐  ┌─────────────────────────────────────┐  │
│  │   UART (USB Serial)  │  │         SPI Bus (D11/D12/D13)       │  │
│  │   115200 baud        │  │   CS=D10                            │  │
│  │   8B binary protocol │  │  ┌──────────────────┐               │  │
│  └──────────┬───────────┘  │  │  SD Card (FAT32)  │               │  │
│             │              │  └──────────────────┘               │  │
│  ┌──────────▼───────────┐  └─────────────────────────────────────┘  │
│  │   MaszynaStanow      │                                            │
│  │  (parser + states)   │  ┌─────────────────────────────────────┐  │
│  └──────┬───────┬───────┘  │         I2C Bus (A4/A5)             │  │
│         │       │(NOWE)    │  ┌──────────────────┐               │  │
│  ┌──────▼──┐  ┌─▼────────┐ │  │  RTC DS1307 0x68 │               │  │
│  │ServoPID │  │DataLogger│ │  └──────────────────┘               │  │
│  │100Hz PID│  │CSV + RTC │ │                                      │  │
│  └──────┬──┘  └──────────┘ └─────────────────────────────────────┘  │
│         │                                                            │
│  ┌──────▼───────────────┐                                           │
│  │        HMI            │                                          │
│  │ (LCD + buzzer + btn)  │                                          │
│  └──────────────────────┘                                           │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ loop():  Serial → Maszyna → watchdog → ServoPID → HMI → Logger│  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Nowe vs Zmodyfikowane Komponenty

#### Nowe komponenty

| Komponent | Lokalizacja | Rola |
|-----------|-------------|------|
| `class DataLogger` | `aries_controller.ino` | SD init, RTC odczyt, zapis CSV, rotacja plikow dziennych |
| `#include <SD.h>` | naglowek | SPI SD card — biblioteka standardowa Arduino |
| `#include <Wire.h>` | naglowek | I2C master dla DS1307 |
| `#include <RTClib.h>` | naglowek | Adafruit RTClib — DateTime, RTC_DS1307 |
| `#define SD_CS_PIN 10` | stale | CS pin dla SPI SD |

#### Zmodyfikowane komponenty

| Komponent | Co sie zmienia | Uwaga |
|-----------|---------------|-------|
| `#define PAN_PIN` | `9` → `6` | Nowa mapa pinow v2.1 |
| `#define TILT_PIN` | `10` → `9` | Nowa mapa pinow v2.1; D10 oddany SPI CS |
| `#define LCD_RS/EN/D4-D7` | `2,3,4,5,6,11` → `A0,A1,D2,D3,D4,D5` | Nowa mapa pinow v2.1 |
| `setup()` | dodaje: `Wire.begin()`, `SD.begin(SD_CS_PIN)`, RTC init, DataLogger init | Kolejnosc: Wire → RTC → SD |
| `loop()` | dodaje: `logger.krok(...)` wywolanie | Po HMI tick |
| `MaszynaStanow::_przejdz_do()` | dodaje: `_logger.loguj_zmiane_stanu(...)` | Wymaga referencji do DataLogger |
| `HMI::lcd_krok()` | Wiersz 1 zmienia sie z `Bx/By` na czas RTC `HH:MM:SS` | Czas cache'owany z DataLogger |
| Globalne instancje | Kolejnosc: `serwa` → `hmi` → `maszyna` → `logger` | Logger ostatni (zalezy od SerialParser przez maszyne) |

---

### Integration Points: SPI Bus (SD Card, D10-D13)

| Szczegol | Wartosc | Zrodlo |
|----------|---------|--------|
| CS pin | D10 (`SD_CS_PIN`) | Project.md pin map v2.1 |
| MOSI | D11 (hardware SPI) | Uno R4 WiFi datasheet |
| MISO | D12 (hardware SPI) | Uno R4 WiFi datasheet |
| SCK | D13 (hardware SPI) | Uno R4 WiFi datasheet |
| Biblioteka | `SD.h` (standardowa Arduino) | HIGH confidence |
| Init kolejnosc | `SD.begin(SD_CS_PIN)` PO `Wire.begin()` — Wire zawsze pierwszy | ArduinoCore-renesas best practice |
| Konflikt z Servo D6/D9 | BRAK — Servo uzywa tiimerow GPT, SPI na osobnym peryferialu | HIGH confidence |
| Czas operacji (benchmark) | open: ~0.04ms, write: ~0.17ms, flush: ~1-2ms, close: ~3.4ms | MEDIUM confidence (wielokrotnie potwierdzone na forum) |
| Shield V1.0 kompatybilnosc | DataLogger Shield V1.0 (Adafruit Rev A) uzywa D10-D13 + A4/A5 bezposrednio — fizycznie kompatybilny z Uno R4 WiFi (identyczny pin header R3) | HIGH confidence |

**Kluczowa decyzja architektoniczna: keep-file-open + flush co N wpisow**

Plik CSV otwarty RAZ przy inicjalizacji dnia. `dataFile.flush()` wywolywany co ~50 wpisow zamiast close/reopen co wpis. Uzasadnienie: `close()` kosztuje ~3.4ms blokowania SPI; przy 3 wpisach/sek bez bufforowania = 10ms/sek stracone. Z flushowaniem co 50 wpisow (~17 sekund) — maksymalna utrata przy power-loss to 17 sekund danych, co jest akceptowalne dla telemetrii.

---

### Integration Points: I2C Bus (RTC DS1307, A4/A5)

| Szczegol | Wartosc | Zrodlo |
|----------|---------|--------|
| SDA | A4 (nie uzywac analogRead(A4) gdy Wire aktywne) | Uno R4 WiFi pinout |
| SCL | A5 (jw.) | Uno R4 WiFi pinout |
| Adres DS1307 | 0x68 (staly, niedefiniowalny) | HIGH confidence |
| Biblioteka | `RTClib` Adafruit — klasa `RTC_DS1307` | HIGH confidence |
| Init | `Wire.begin()` (bez argumentu — master only), potem `rtc.begin()` | HIGH confidence |
| Znany issue R4 WiFi | ArduinoCore-renesas issue #180: DS1307 nie dzialal gdy `Wire.begin(adres)` (slave mode). Fix zmergowany PR #191. Aktualne core (>=1.1.0) nie ma problemu. | HIGH confidence — GitHub issue oficjalny |
| Pull-upy | Uno R4 WiFi NIE ma wbudowanych pull-upow. DataLogger Shield V1.0 ma wlasne 10kΩ pull-upy — wystarczajace. | MEDIUM confidence |
| Czas odczytu | ~0.3ms przy domyslnym 100kHz I2C — odczytywac co 200ms (LCD tick), nie co klatke PID | HIGH confidence |
| Odswiezanie cache | `DateTime _teraz` cache'owany w DataLogger, aktualizowany co tick LCD (200ms) | Architektoniczne |

---

### Integration Points: Servo (D6 PAN, D9 TILT)

| Szczegol | Wartosc | Zrodlo |
|----------|---------|--------|
| Biblioteka | `Servo.h` (Arduino) v1.2.2+ | HIGH confidence |
| Znany issue R4 WiFi | Servo library <1.2.2 dawala niepoprawny PWM timing na R4 (zbyt duze kroki). Fix w v1.2.2, czerwiec 2024. WYMAGANA aktualizacja przez Arduino IDE Library Manager. | HIGH confidence — forum post z potwierdzonym fix |
| Konflikt z SPI D10-D13 | BRAK — Servo D6/D9 uzywa tiimerow GPT, SPI na oddzielnym bloku | HIGH confidence |
| Konflikt z I2C A4/A5 | BRAK | HIGH confidence |
| Pin zmiana vs Leonardo | Leonardo: PAN=D9/TILT=D10. Uno R4 v2.1: PAN=D6/TILT=D9 (D10 oddany pod SPI CS) | Project.md decision |

---

### Timing Impact Analysis: 100Hz PID Loop

Kluczowe pytanie: czy DataLogger zaklocI petlę PID?

```
Loop iteration timing (szacunek):
  Serial.read()        ~0.01ms  (non-blocking, 0-1 bajt)
  watchdog_krok()      ~0.001ms (millis() compare)
  ServoPID::pid_krok() ~0.1ms   (QuickPID Compute + servo.write)
  HMI::lcd_krok()      ~0.2ms   (LCD print, 5Hz throttled — co 200ms faktycznie)
  DataLogger::krok()   ~0.001ms (licznik check only, NO IO w wieksz. iteracji)
  DataLogger write     ~0.35ms  (write CSV linia, co 10 klatek SLEDZENIE)

Worst case gdy DataLogger pisze:
  0.1 + 0.35 = 0.45ms aktywne IO w jednej iteracji
  PID timer: pid_krok() sprawdza millis() — jesli 10ms minelo pisze do serwa
  Blokowanie 0.45ms NIE zaburza 100Hz (10ms interval) — margines 9.55ms
```

**Wnioski:** DataLogger write (~0.35ms na CSV linia) nie blokuje PID 100Hz. Jedyny ryzykowny scenariusz to `plik.flush()` co ~50 wpisow (~1-2ms) — rowniez w marginesie 10ms. Brak potrzeby przenoszenia loggera do osobnego watku (Arduino jest single-threaded).

Unikac w DataLogger: operacji `SD.open()` + `SD.close()` w loop — ta para kosztuje ~3.5ms i moze zaburzyc jeden tick PID.

---

### Data Flow (rozszerzony o DataLogger)

```
RPi4 --USB Serial--> MaszynaStanow::przetwarzaj_bajt()
                          |
              _przetworz_ramke() [co poprawna ramka ~30Hz]
                  |               |
         blad_x/y → ServoPID   _licznik_klatek++
                  |               |
         pid_krok() [100Hz]    [co 10. klatka] DataLogger::krok()
                  |                         |
         Servo.write()            _teraz = cached RTC DateTime
                                            |
                                  char linia[80] via snprintf()
                                            |
                                  _plik.print(linia)  [~0.17ms]
                                            |
                                  [co 50 wpisow] _plik.flush() [~1-2ms]

Zmiana stanu w MaszynaStanow::_przejdz_do(nowy):
    ├── DataLogger::loguj_zmiane_stanu(nowy, pan, tilt)  [natychmiastowo]
    ├── (SKANOWANIE) resetuj_czas_skanu() + pid_reset()
    └── (SLEDZENIE)  buzzer_beep() + pid_reset()

RTC cache refresh (co 200ms w HMI::lcd_krok()):
    DateTime _teraz = _rtc.now()  [~0.3ms I2C]
    → cache w DataLogger uzywany przez krok() i loguj_zmiane_stanu()
```

---

### Suggested Build Order (v2.1 milestones)

Kolejnosc respektuje zaleznosci komponentow i minimalizuje jednoczesne debugowanie wielu zmian.

#### Etap 1: Migracja pinow (fundament)

**Co:** Tylko zmiana `#define` — LCD, Servo, Buzzer, Przycisk na nowa mape v2.1. BEZ SD, BEZ RTC.

**Zaleznosci:** Brak — czysta zmiana konfiguracji.

**Zmiany kodu:**
- `PAN_PIN 9` → `6`
- `TILT_PIN 10` → `9`
- `LCD_RS 2` → `A0`, `LCD_EN 3` → `A1`, `LCD_D4 4` → `2`, `LCD_D5 5` → `3`, `LCD_D6 6` → `4`, `LCD_D7_PIN 11` → `5`
- Usunac/ogniczyc `while(!Serial)` — Uno R4 nie potrzebuje (brak USB CDC jak Leonardo)
- Upewnic sie ze Servo library >= 1.2.2 (update przez IDE)

**Weryfikacja:** Serial log + LCD bootscreen + buzzer beep + ruch serw po komendzie RPi.

#### Etap 2: Soft Start 500ms

**Co:** Weryfikacja `_bezpieczny_start()` na Uno R4 — czy obecna rampa (1000ms) dziala, czy wystarczy 500ms.

**Zaleznosci:** Etap 1.

**Weryfikacja empiryczna:** Czy serwa skacza przy starcie? Czy brownout na zasilaczu 6V?

#### Etap 3: RTC DS1307 (Wire + RTClib)

**Co:** Dodanie `Wire.begin()` + `RTC_DS1307 rtc` + `rtc.begin()`. Wyswietlenie `HH:MM:SS` na LCD Row 1. BEZ SD w tym etapie.

**Zaleznosci:** Etap 2. I2C prostsze niz SPI — walidacja izolowana.

**Wymagania wstepne:**
- `Tools > Board > Board Manager`: Arduino UNO R4 Boards >= 1.1.0 (naprawa issue #180)
- `Tools > Manage Libraries`: zainstalowac `RTClib` by Adafruit

**Weryfikacja:** LCD Row 1 pokazuje czas aktualizowany co 200ms. Czas DS1307 ustawiony wstepnie (lub `rtc.adjust(DateTime(F(__DATE__), F(__TIME__)))` przy pierwszym flashowaniu).

#### Etap 4: SD Card + DataLogger CSV

**Co:** Dodanie `SD.begin(SD_CS_PIN)`, tworzenie pliku z data RTC (`L260401.CSV` format 8.3), zapis naglowka CSV, DataLogger::krok() w loop() bez wywolania z MaszynaStanow.

**Zaleznosci:** Etap 3 (nazwa pliku zawiera date z RTC).

**Uwaga nazwy pliku:** FAT32 (SD.h standard) wymaga formatu 8.3. `logYYMMDD.csv` = 10+3 znaków — za dlugo. Uzyc `L%02d%02d%02d.CSV` → np. `L260401.CSV` (7+3, poprawne).

**Weryfikacja:** Po 60 sekundach — wyciagnac karte SD, otworzyc `L260401.CSV` na komputerze, sprawdzic naglowek + timestampy + wartosci PID.

#### Etap 5: Integracja DataLogger z MaszynaStanow

**Co:** Przekazanie referencji `DataLogger& _logger` do konstruktora MaszynaStanow. Wywolanie `_logger.loguj_zmiane_stanu()` w `_przejdz_do()`. Testowanie pelnego przeplywy zmian stanow.

**Zaleznosci:** Etap 4 (DataLogger musi dzialac stabilnie).

**Weryfikacja:** Wyciagnac karte, zobaczyc wpisy o zmianie stanu z timestampem RTC + co-10-klatkowe linie SLEDZENIE.

---

### Architectural Patterns (v2.1 DataLogger)

#### Pattern A: Throttled millis() logging — nie blokuje 100Hz PID

DataLogger::krok() sprawdza licznik klatek (inkrementowany przez parser, nie przez timer). Zapis co 10. klatke SLEDZENIE = ~3 wpisy/sek przy 30Hz wejsciu. Zmiana stanu logowana natychmiastowo przez `loguj_zmiane_stanu()`.

```cpp
// W DataLogger::krok() — wywolywane co iteracje loop()
void krok(StanSystemu stan, float pan, float tilt,
          int16_t blad_x, int16_t blad_y, uint8_t face_size) {
    if (stan != SLEDZENIE) return;
    if (++_licznik_klatek < 10) return;
    _licznik_klatek = 0;
    _zapisz_csv(stan, pan, tilt, blad_x, blad_y, face_size);
}
```

#### Pattern B: Keep-file-open + flush co N wpisow

```cpp
void _zapisz_csv(StanSystemu stan, float pan, float tilt,
                 int16_t bx, int16_t by, uint8_t fs) {
    if (!_sd_ok || !_plik) return;  // cichy skip jesli SD niedostepne
    char linia[80];
    snprintf(linia, sizeof(linia),
             "%lu,%04d-%02d-%02dT%02d:%02d:%02d,%d,%.1f,%.1f,%d,%d,%d\r\n",
             millis(),
             (int)_teraz.year(), (int)_teraz.month(), (int)_teraz.day(),
             (int)_teraz.hour(), (int)_teraz.minute(), (int)_teraz.second(),
             (int)stan, pan, tilt, (int)bx, (int)by, (int)fs);
    _plik.print(linia);
    if (++_wpisy_od_flush >= 50) {
        _plik.flush();
        _wpisy_od_flush = 0;
    }
}
```

#### Pattern C: Rotacja plikow dziennych (8.3 FAT format)

```cpp
void _otworz_plik_dnia() {
    DateTime teraz = _rtc.now();
    char nazwa[13];
    snprintf(nazwa, sizeof(nazwa), "L%02d%02d%02d.CSV",
             (int)(teraz.year() % 100), (int)teraz.month(), (int)teraz.day());
    _plik = SD.open(nazwa, FILE_WRITE);
    if (_plik && _plik.size() == 0) {
        // Nowy plik — wpisz naglowek CSV
        _plik.println("millis,timestamp,stan,pan,tilt,error_x,error_y,face_size");
        _plik.flush();
    }
}
```

#### Pattern D: Graceful degradation — flagi `_sd_ok` i `_rtc_ok`

```cpp
void inicjalizuj() {
    Wire.begin();  // ZAWSZE pierwszy
    _rtc_ok = _rtc.begin();
    if (!_rtc_ok) Serial.println("[LOGGER] RTC brak!");
    _sd_ok = SD.begin(SD_CS_PIN);
    if (!_sd_ok) { Serial.println("[LOGGER] SD brak!"); return; }
    _otworz_plik_dnia();
}
```

Wszystkie metody DataLogger sprawdzaja flagi przed IO. Brak SD/RTC = system dziala normalnie bez logowania.

---

### Anti-Patterns (v2.1 specific)

#### Anti-Pattern 1: SD.open/close co wpis CSV

**Co sie robi:** `SD.open("log.csv", FILE_WRITE)` + `file.close()` przy kazdym wpisie.

**Dlaczego zle:** `close()` = ~3.4ms blokowania SPI. Przy 3 wpisach/sek = 10ms/sek. Przy nieszczesliwym zbiegu z tickiem PID (okno 10ms): opoznienie ~3.4ms moze przesunac timer i zaburzyc jeden cykl regulacji.

**Zamiast tego:** Otworz plik raz, `flush()` co 50 wpisow.

---

#### Anti-Pattern 2: Wire I2C co tick PID (100Hz)

**Co sie robi:** `DateTime teraz = rtc.now()` w `pid_krok()` co 10ms.

**Dlaczego zle:** Odczyt I2C DS1307 = ~0.3ms przy 100kHz. 100 odczytow/sek = 30ms/sek blokowania na I2C. DS1307 zmienia czas raz na sekunde — 100 odczytow/sek to czyste marnotrawstwo.

**Zamiast tego:** Cache `DateTime _teraz` odswiezany co tick LCD (200ms). DataLogger uzywa cache.

---

#### Anti-Pattern 3: String do budowania CSV na Arduino

**Co sie robi:** `String linia = String(millis()) + "," + String(pan) + ...`

**Dlaczego zle:** Klasa `String` na Arduino fragmentuje heap przez dynamiczna alokacje. Na Uno R4 (32KB RAM) mniej dotkliwe niz na 8-bit AVR, ale przy dlugim czasie pracy moze spowodowac niedet. zawieszenie.

**Zamiast tego:** `char linia[80]; snprintf(linia, sizeof(linia), "...", ...)` — alokacja na stosie, deterministyczny czas.

---

#### Anti-Pattern 4: Wire.begin() PO SD.begin()

**Co sie robi:** Inicjalizacja SD przed I2C.

**Dlaczego zle:** ArduinoCore-renesas (Uno R4) wymaga I2C init jako master (`Wire.begin()` bez argumentu) przed innymi peryferiami dla stabilnej pracy. Odwrotna kolejnosc moze powodowac niepewne zachowanie I2C — nawet jesli issue #180 jest naprawiony, kolejnosc Wire → RTC → SD jest zalecanym best-practice.

**Zamiast tego:** `Wire.begin()` jako pierwsze w `setup()` po `Serial.begin()`.

---

#### Anti-Pattern 5: Brak sprawdzenia powrotu SD.begin() i rtc.begin()

**Co sie robi:** Ignorowanie `bool` z funkcji inicjalizacyjnych.

**Dlaczego zle:** Wyjeta karta SD lub niepodlaczony RTC → DataLogger wywoluje `_plik.print()` na uninitialized file object → undefined behavior lub crash.

**Zamiast tego:** Flagi `_sd_ok` i `_rtc_ok` + cichy skip wszystkich operacji IO gdy false.

---

### Sources (v2.1 supplement)

- [ArduinoCore-renesas issue #180: DS1307 I2C master-only fix](https://github.com/arduino/ArduinoCore-renesas/issues/180) — HIGH confidence, official repo
- [Arduino Uno R4 WiFi pinout reference](https://lastminuteengineers.com/arduino-uno-r4-wifi-pinout-reference/) — HIGH confidence, verified against official datasheet
- [Adafruit DataLogger Shield code walkthrough](https://learn.adafruit.com/adafruit-data-logger-shield/using-the-real-time-clock-3) — HIGH confidence, official Adafruit guide
- [Servo library v1.2.2 fix for R4 WiFi](https://forum.arduino.cc/t/trouble-with-servos-on-r4-wifi/1151749) — HIGH confidence, confirmed fix in library release notes
- Arduino forum SD benchmarks: open ~0.04ms, write ~0.17ms, close ~3.4ms — MEDIUM confidence (multiple forum sources agree on order-of-magnitude)
- [SD card write latency forum thread](https://forum.arduino.cc/t/latency-writing-sd-card/605637) — MEDIUM confidence

---

## v2.0 Base Architecture

*(Istniejace dokumenty z 2026-03-30 — zachowane jako referencja)*

---

**Domain:** Distributed embedded vision + real-time servo control (RPi4 Mozg + Arduino Leonardo Uklad Wykonawczy)
**Researched:** 2026-03-30
**Confidence:** HIGH (validated against official docs, reference implementations, and existing codebase)

### System Overview (v2.0 base — Leonardo)

```
┌─────────────────────────────────────────────────────────────────┐
│              MOZG — Raspberry Pi 4 (Python)                     │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │ Picamera2    │   │  MediaPipe   │   │  Serial Sender   │    │
│  │ Stream thread│──▶│  Face Detect │──▶│  (pyserial)      │    │
│  │ (daemon)     │   │  + Error calc│   │  115200 baud     │    │
│  └──────────────┘   └──────────────┘   └────────┬─────────┘    │
│                                                  │ USB /dev/ttyACM0
└──────────────────────────────────────────────────┼──────────────┘
                                                   │ USB Serial
┌──────────────────────────────────────────────────┼──────────────┐
│              UKLAD WYKONAWCZY — Arduino Leonardo │              │
│                                                  ▼              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │ Serial Parser│──▶│  PID Pan+Tilt│──▶│  Servo Library   │    │
│  │ (ISR + buffer│   │  (100+ Hz)   │   │  MG-90S D9/D10   │    │
│  └──────────────┘   └──────────────┘   └──────────────────┘    │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │  Watchdog    │   │  LCD 1602    │   │  Buzzer + Button │    │
│  │  (serial TO) │   │  RS/E/D4–D7  │   │  D8 / D7        │    │
│  └──────────────┘   └──────────────┘   └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Node | Responsibility | Communicates With |
|-----------|------|----------------|-------------------|
| `Picamera2Stream` | RPi4 | YUV420→BGR capture, AWB fix, daemon thread | `pi_brain.py` (frames) |
| `MediaPipe FaceDetector` | RPi4 | Face bounding box detection, largest-face selection | `pi_brain.py` (bbox) |
| `ErrorCalculator` | RPi4 | Normalize error to [-1.0, +1.0] relative to frame centre | Serial sender |
| `SerialSender` | RPi4 | Frame encoding, checksum, pyserial write at ~30 Hz | Arduino parser |
| `SerialParser` | Arduino | ISR-driven byte accumulation, frame validation, checksum | PID controller |
| `PIDController` | Arduino | Dual-axis PID at 100+ Hz (setpoint = 0), angle computation | Servo library |
| `ServoDriver` | Arduino | Arduino `Servo.write()` to MG-90S on D9 (pan), D10 (tilt) | Physical hardware |
| `WatchdogTimer` | Arduino | millis()-based serial timeout, returns to SCAN on silence | State machine |
| `LCD1602` | Arduino | 4-bit mode status display (mode, angles, FPS) | State machine |
| `BuzzerButton` | Arduino | Buzzer feedback on state change; D7 button = abort track | State machine |

---

### Recommended Project Structure

```
ARIES-LITE/
├── src/
│   ├── arduino/
│   │   └── aries_controller/
│   │       └── aries_controller.ino    # caly firmware Arduino
│   ├── vision/
│   │   └── pi_brain.py                 # MediaPipe + serial sender (nowy glowny skrypt)
│   ├── config.py                       # stale — bez zmian (PID gains, limity)
│   └── hardware.py                     # zachowany w legacy/ lub usuniety (servo teraz na Arduino)
├── legacy/                             # v1.x monolityczny kod jako referencja
│   ├── main.py
│   ├── run_test_tracker.py
│   └── src/
├── web/                                # opcjonalnie — Flask UI moze zostac dla podgladu
├── models/                             # DNN weights — mozliwe usuniecie (MediaPipe = bundled)
├── requirements.txt                    # nowe: mediapipe, pyserial; usuniete: gpiozero, pigpio, dlib
└── .planning/
```

### Structure Rationale

- **`src/arduino/`**: Firmware zywi wlasny katalog. Oddzielenie .ino od Python zapobiega
  importowaniu jako modul Python. Arduino IDE / arduino-cli szuka `aries_controller/aries_controller.ino`.
- **`src/vision/pi_brain.py`**: Nowy entry point RPi — zastepuje `run_test_tracker.py`.
  Nie dziedziczy po starym kodzie (rozny stack kamerowy i brak PID po stronie Pi).
- **`legacy/`**: Poprzednie milestony zachowane. Umozliwia rollback bez git bisect.
  Zgodne z decyzja projektowa "Stary monolit zachowany w `legacy/`".

---

### Architectural Patterns (v2.0 base)

#### Pattern 1: Brain-Muscle Split (RPi = wizja, Arduino = sterowanie)

**Co:** RPi4 zajmuje sie wylacznie detekcja i obliczaniem bledu. Arduino zajmuje sie
wylacznie PID i serwami. Zaden wezel nie robi obu rzeczy jednoczesnie.

**Dlaczego:** RPi4 Python ma GIL i nieregularne latencje GC. PID w Pythonie na RPi4
osiaga ~30 Hz z jitterem. Arduino bez OS osiaga >100 Hz z deterministycznym timingiem.
Podział eliminuje single point of failure — Arduino dziala autonomicznie gdy Pi zawiesza sie.

**Trade-off:** Komunikacja przez USB Serial dodaje latencje ~1-5ms na ramke. Akceptowalne
dla sledzenia twarzy (cykl PID = 10ms przy 100 Hz).

**Confidence:** HIGH — wzorzec stosowany w robotyce (ROS: compute node + controller node).
Potwierdzone przez projekt SaraKIT (MediaPipe RPi + BLDC controller).

---

#### Pattern 2: Asymetryczny protokol szeregowy (Pi pisze, Arduino odpowiada)

**Co:** RPi4 wysyla klatki danych do Arduino (dominujacy nadawca). Arduino opcjonalnie
odsyla ACK lub status. Komunikacja nie jest RPC — brak blokujacego oczekiwania na odpowiedz.

**Dlaczego:** Petla wizji na Pi jest niezalezna od czestotliwosci PID na Arduino.
Pi wysyla z ~30 Hz (klatka kamery). Arduino petla PID biegnie z 100+ Hz bez czekania
na kolejna wiadomosc. Blokujacy request/response niszczyloby deterministyczny timing PID.

**Trade-off:** Pi nie ma potwierdzenia ze ramka dotarla. Przy utracie ramki Arduino
kontynuuje PID z ostatnim bledem (hold-last) co jest bezpieczniejsze niz zatrzymanie.

---

#### Pattern 3: Fixed-length binary frame z checksum

**Co:** Kazda wiadomosc Pi→Arduino ma stala dlugosc (8 bajtow). Bez dlugosci w naglowku.
Arduino wie dokładnie ile bajtow czytac po bajcie startowym.

**Format ramki (Pi → Arduino):**
```
Bajt 0:  0xAA           — start marker (stały)
Bajt 1:  tryb           — 0x00=SCAN, 0x01=TRACK, 0x02=IDLE
Bajt 2:  blad_x_high    — error_x jako int16 big-endian, high byte
Bajt 3:  blad_x_low     — error_x jako int16 big-endian, low byte
Bajt 4:  blad_y_high    — error_y jako int16 big-endian, high byte
Bajt 5:  blad_y_low     — error_y jako int16 big-endian, low byte
Bajt 6:  rozmiar_twarzy — face bbox width jako uint8 (0–255 po normalizacji)
Bajt 7:  checksum       — XOR bajtow 1–6 (weryfikacja integralnosci)
```

**Confidence:** MEDIUM-HIGH — pattern z Eli Bendersky (framing article) + todbot blog.
Konkretny format zaprojektowany dla tego projektu, wymaga walidacji na sprzecie.

---

#### Pattern 4: Arduino watchdog via millis() (nie AVR WDT)

**Co:** Arduino sprawdza `millis() - ostatnia_ramka_ms > WATCHDOG_MS` w petli.
Jesli Pi nie wyslalo ramki przez WATCHDOG_MS (500ms), Arduino przechodzi do SKANOWANIE.

**Dlaczego NIE `wdt_reset()` (AVR hardware WDT):** AVR WDT na Leonardo resetuje caly
mikrokontroler. Dla utraty komunikacji z Pi chcemy autonomiczny SCAN — serwa dalej sie
ruszaja. Hardware WDT byłby zbyt drastyczny.

**Confidence:** HIGH — wzorzec aplikacyjny watchdog z Interrupt/Memfault best practices.

---

#### Pattern 5: MediaPipe face_detector API (Tasks API)

**Co:** `mediapipe.tasks.python.vision.FaceDetector` — nie stary `mediapipe.solutions`.
Tasks API jest oficjalnym nastepca (Google, 2023).

**Confidence:** MEDIUM — oficjalne API z Google AI Developers (zweryfikowane). FPS na RPi4
to szacunek — wymaga empirycznej weryfikacji.

---

### Data Flow (v2.0 base)

```
Picamera2 YUV420 (320x240)
    ↓ cvtColor(YUV420p2RGB)              — daemon thread
    ↓
MediaPipe FaceDetector.detect_for_video()
    ↓
Wybor najwyzszej twarzy (max bbox area)
    ↓
Obliczenie bledu:
    error_x = face_cx - frame_cx         — piksele, int16
    error_y = face_cy - frame_cy         — piksele, int16
    tryb = TRACK (twarz znaleziona) lub SCAN (brak twarzy)
    ↓
Enkodowanie ramki 8-bajtowej (binary + XOR checksum)
    ↓
pyserial.write(frame)  →  USB /dev/ttyACM0  →  Arduino Serial
    ↓
[Arduino]
SerialParser: czeka na 0xAA, czyta 7 bajtow, weryfikuje XOR
    ↓
PID(error_x) → delta_pan    |   (100 Hz loop, millis() timing)
PID(error_y) → delta_tilt   |
    ↓
pan_angle  = clamp(pan_angle  + PAN_DIR  * delta_pan,  -60, +60)
tilt_angle = clamp(tilt_angle + TILT_DIR * delta_tilt, -30, +30)
    ↓
servo_pan.write(pan_angle + 90)     — Arduino Servo: 0-180 stopni
servo_tilt.write(tilt_angle + 90)
    ↓
LCD update (tryb, pan, tilt) + buzzer na zmiane trybu
```

---

### Integration Points (v2.0 base)

#### External Hardware

| Interface | Polaczenie | Uwagi |
|-----------|-----------|-------|
| USB Serial | /dev/ttyACM0, 115200 baud | Arduino Leonardo = USB CDC natywny, bez adaptera |
| IMX219 Camera | CSI ribbon cable | Picamera2 + libcamera, ten sam backend co v1.x |
| MG-90S PAN | Arduino D9 (PWM) | Arduino Servo library, 50 Hz PWM |
| MG-90S TILT | Arduino D10 (PWM) | Arduino Servo library, 50 Hz PWM |
| LCD 1602 | RS=12, E=11, D4=5, D5=4, D6=3, D7=2 | 4-bit mode, LiquidCrystal library |
| Buzzer | Arduino D8 | tone() / digitalWrite |
| Button | Arduino D7 (INPUT_PULLUP) | Active LOW, wymaga debounce |
| Servo power | Zewnetrzne 6V | Oddzielone od 5V RPi — zapobiega brownout |

#### Internal Boundaries

| Granica | Komunikacja | Uwagi |
|---------|------------|-------|
| Pi main thread ↔ Picamera2 daemon | `threading.Lock` + shared numpy frame | Identycznie jak v1.x |
| Pi main ↔ Arduino | USB Serial, binary 8B frames, 1-way dominant | Fire-and-forget |
| Arduino Serial ISR ↔ PID loop | Volatile shared state (error_x, error_y, tryb) | Atomic na AVR dla uint8/int16 |
| Arduino PID ↔ Servo | Servo library internal | Servo.write() thread-safe w single-threaded Arduino |

---

### Sources (v2.0 base)

- [MediaPipe Face Detector Python API](https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector/python) — bounding box format, Tasks API (HIGH confidence)
- [MediaPipe for Raspberry Pi](https://www.cnx-software.com/2023/08/21/mediapipe-for-raspberry-pi-released-no-code-low-code-on-device-machine-learning-solutions/) — oficjalne wsparcie RPi, 2023 (HIGH confidence)
- [Arduino Serial Protocol Design Patterns — todbot blog](https://todbot.com/blog/2009/07/30/arduino-serial-protocol-design-patterns/) — fixed-length vs delimiter framing (HIGH confidence)
- [Framing in Serial Communications — Eli Bendersky](https://eli.thegreenplace.net/2009/08/12/framing-in-serial-communications/) — start marker + checksum pattern (HIGH confidence)
- [Firmware Watchdog Best Practices — Interrupt/Memfault](https://interrupt.memfault.com/blog/firmware-watchdog-best-practices) — aplikacyjny watchdog vs hardware WDT (HIGH confidence)
- CLAUDE.md + PROJECT.md — decyzje architektoniczne v2.0 (HIGH confidence — source of truth)

---

*Architecture research for: ARIES-LITE — v2.0 Architektura Rozproszona + v2.1 DataLogger integration*
*Researched: 2026-03-30 (v2.0), 2026-04-01 (v2.1)*
