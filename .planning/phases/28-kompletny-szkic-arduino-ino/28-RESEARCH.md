# Phase 28: Flash firmware na Uno R4 WiFi - Research

**Researched:** 2026-04-02
**Domain:** Arduino CLI flash workflow, Uno R4 WiFi hardware verification, RPi serial integration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** arduino-cli na RPi4 (nie Arduino IDE). RPi4 ma monitor + klawiature — wizualna weryfikacja LCD/serw mozliwa.
- **D-02:** Instalacja ArduinoCore-renesas od zera — RPi4 nie ma jeszcze zainstalowanego srodowiska Arduino. Plan musi zawierac kroki instalacji arduino-cli + core + bibliotek.
- **D-03:** Board FQBN: `arduino:renesas_uno:unor4wifi` — Claude zweryfikuje poprawny identyfikator w research.
- **D-04:** Testy izolowane po kolei, od pasywnych do aktywnych: 1) LCD bootscreen, 2) Serwa Soft Start + sweep, 3) Buzzer ton, 4) Przycisk D7, 5) Serial E2E z RPi (pelny tracking twarzy), 6) Stabilnosc 5x power cycle.
- **D-05:** Checkpoint w planie po kazdym tescie — uzytkownik wpisuje PASS/FAIL, Claude kontynuuje lub debuguje. Wzorzec identyczny z Phase 24.
- **D-06:** Test serial obejmuje PELNY E2E tracking: uruchomienie pi_brain.py (przez run_pi_brain.py), wykrycie twarzy, sledzenie serwami.
- **D-07:** Debug in-place na R4 — nie rollback na R3. Diagnoza: polaczenia, piny, Serial output.
- **D-08:** Pojedyncze egzemplarze komponentow (serwa, LCD, kable) — plan testow musi byc ostrozny. Pasywne testy (LCD) najpierw, aktywne (serwa) pozniej. Unikac agresywnych ruchow serw przy pierwszym uruchomieniu.
- **D-09:** pi_brain.py dzialal E2E z Uno R3 w Phase 24. Cel: identyczne zachowanie z R4 WiFi.
- **D-10:** Claude's Discretion — DTR behavior R4 WiFi (ESP32-S3 bridge) vs Leonardo. Researcher zbada czy pi_brain.py wymaga zmian ustawien serial (dtr=False, port path).

### Claude's Discretion

- Dokladna metoda instalacji arduino-cli na RPi4 ARM64 (apt vs curl)
- Biblioteki do zainstalowania przez arduino-cli (QuickPID, Servo, LiquidCrystal)
- Czy /dev/ttyACM0 jest stabilny na R4 WiFi czy trzeba udev rules
- Kolejnosc pasywna/aktywna w testach serw — minimalny zakres ruchu przy pierwszym sweep
- Timeout i retry strategy jesli flash sie nie powiedzie

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MIG-10 | Wgranie firmware v2.1 na Uno R4 WiFi i pelna weryfikacja sprzetowa — LCD, serwa Soft Start + skan sinusoidalny, serial E2E z RPi, buzzer, przycisk, stabilnosc zasilania (5x power cycle) | Wszystkie narzedzia dostepne: arduino-cli 1.4.1 zainstalowany, FQBN potwierdzony, firmware kompiluje sie bez bledow, /dev/ttyACM0 aktywny, biblioteki zainstalowane |

</phase_requirements>

## Summary

Phase 28 to operacja flashowania i weryfikacji sprzetowej — nie ma tu nowego kodu. Firmware v2.1 (`aries_controller.ino`) zostal juz napisany i zweryfikowany kompilacyjnie w Phase 24. Celem tej fazy jest wgranie go na docelowy hardware (Uno R4 WiFi, nie proxy R3) i potwierdzenie, ze kazdy element sprzetowy dziala zgodnie ze specyfikacja: LCD bootscreen, Soft Start serw, skan Lissajous, buzzer tone przy wejsciu w SLEDZENIE, abort przyciskiem D7, oraz komunikacja E2E z pi_brain.py na RPi.

Kluczowa informacja: srodowisko jest juz w duzej czesci skonfigurowane. Arduino-cli 1.4.1 jest zainstalowany na RPi4, ArduinoCore-renesas 1.5.3 jest zainstalowany, wszystkie trzy wymagane biblioteki (Servo 1.3.0, LiquidCrystal 1.0.7, QuickPID 3.1.9) sa obecne, FQBN `arduino:renesas_uno:unor4wifi` jest potwierdzony i R4 WiFi jest widoczny jako `/dev/ttyACM0`. Firmware kompiluje sie do zera bledow (24% flash, 22% RAM). D-02 z CONTEXT.md ("instalacja od zera") okazuje sie byc juz spelnione — plan nie musi zawierac instalacji arduino-cli ani core, tylko kroki flash + weryfikacji.

Strona RPi: `serial_interface.py` i `brain.py` (uruchamiane przez `run_pi_brain.py`) nie wymagaja zadnych zmian dla R4 WiFi. Kod juz dziala bez DTR workaround (ESP32-S3 bridge, nie USB CDC) — komentarz w `serial_interface.py` linijka 58 to wprost potwierdza. Port `/dev/ttyACM0` jest stabilny, udev rules nie sa potrzebne.

**Primary recommendation:** Flash jednym poleceniem `arduino-cli upload`, nastepnie przeprowadz 6 testow checkpoint w kolejnosci D-04 (pasywne przed aktywnymi), weryfikuj kazdy przed przejsciem do nastepnego.

## Standard Stack

### Core
| Narzedzie / Biblioteka | Wersja | Cel | Uwagi |
|------------------------|---------|-----|-------|
| arduino-cli | 1.4.1 (2026-01-19) | Kompilacja i flash firmware z CLI | Juz zainstalowany na RPi4 — brak potrzeby instalacji |
| ArduinoCore-renesas | 1.5.3 | Board support package dla Uno R4 WiFi | Juz zainstalowany; 1.5.3 > wymaganego minimum 1.4.1 |
| Servo | 1.3.0 | PWM sterowanie serwami MG-90S | Juz zainstalowany; 1.3.0 > wymaganego minimum 1.2.2 (fix jitter R4) |
| LiquidCrystal | 1.0.7 | LCD 1602 tryb 4-bit | Juz zainstalowana |
| QuickPID | 3.1.9 | PID dual-axis 100 Hz | Juz zainstalowana; wersja identyczna z tej uzytej w Phase 24 |
| pyserial | (z requirements.txt) | Port szeregowy RPi → Arduino | SerialInterface.py nie wymaga zmian dla R4 WiFi |

### Potwierdzone FQBN i port
| Parametr | Wartosc | Zrodlo |
|----------|---------|--------|
| FQBN | `arduino:renesas_uno:unor4wifi` | `arduino-cli board listall` + `arduino-cli board list` |
| Port | `/dev/ttyACM0` | `arduino-cli board list` — R4 WiFi widoczny teraz |
| Protokol | serial | Potwierdzony przez `arduino-cli board list` |

**Polecenia flash:**
```bash
# Kompilacja (opcjonalna weryfikacja przed flash)
arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi \
  /home/parolisko/ARIES-LITE/src/arduino/aries_controller/

# Flash
arduino-cli upload --fqbn arduino:renesas_uno:unor4wifi \
  --port /dev/ttyACM0 \
  /home/parolisko/ARIES-LITE/src/arduino/aries_controller/

# Monitor serial (weryfikacja bootscreen i logów)
arduino-cli monitor --port /dev/ttyACM0 --config baudrate=115200
```

**Uwaga:** Po flash arduino-cli monitor musi byc zamkniety przed uruchomieniem pi_brain.py — oba nie moga trzymac portu jednoczesnie.

## Architecture Patterns

### Sekwencja inicjalizacji firmware (setup() w aries_controller.ino)
```
Serial.begin(115200)
while (!Serial && millis() - start < 500)  // max 500ms wait na ESP32 bridge
pinMode(A0, OUTPUT); pinMode(A1, OUTPUT)    // explicit OUTPUT dla pinow LCD
hmi.inicjalizuj()                            // LCD bootscreen "ARIES-LITE v2.1" + piny buzzer/przycisk
delay(500)                                   // Soft Start — stabilizacja 6V przed serwami
serwa.inicjalizuj()                          // attach D6/D9 + rampa 1400→1500us (1000ms) + PID params
// loop() startuje: parser serial, watchdog, pid_krok, lcd_krok, przycisk_krok
```

### Sekwencja testow (D-04 z CONTEXT.md)
```
Test 1: LCD bootscreen (pasywny — tylko zasilanie, bez RPi)
  → weryfikacja: LCD wyswietla "ARIES-LITE v2.1" przez 2s, potem stan BEZCZYNNOSC

Test 2: Serwa Soft Start + skan (aktywny — wymaga zewnetrznego 6V)
  → weryfikacja: brak szarpniecia przy starcie, skan Lissajous (PAN±70°, TILT±25°)
  → UWAGA: minimalny zakres ruchu przy pierwszym obserwowaniu — patrz Pitfall 2

Test 3: Buzzer ton
  → weryfikacja: ton 1kHz/100ms przy przejsciu do SLEDZENIE (trigger przez serial)

Test 4: Przycisk D7 abort
  → weryfikacja: w trybie SLEDZENIE — wcisniecie przywraca SKANOWANIE

Test 5: Serial E2E z RPi
  → python3 run_pi_brain.py na RPi
  → weryfikacja: ramki parsowane, twarz sledzona, serwa reaguja

Test 6: Stabilnosc 5x power cycle
  → 5 kolejnych cykli zasilania — brak restartu Arduino podczas ruchu serw
```

### DTR behavior R4 WiFi (D-10 — Claude's Discretion rozwiazany)

**Wynik badania:** R4 WiFi NIE wymaga zadnych zmian w pi_brain.py ani serial_interface.py.

Roznica Leonardo vs R4 WiFi:
- Leonardo: USB CDC natywne na ATmega32U4 — DTR resetuje chip. Wymagalo `dtr=False` w pyserial.
- R4 WiFi: USB przez ESP32-S3 bridge — DTR nie resetuje RA4M1. Brak potrzeby workaround.

`serial_interface.py` (linie 49-59) juz implementuje poprawny sposob otwarcia portu dla R4:
- Tworzy `serial.Serial()` bez natychmiastowego otwarcia
- Nie ustawia `dsrdtr`, `dtr`, ani zadnych CDC-specific opcji
- Otwarcie przez `ser.open()` bez wyzwalania reset
- Komentarz w kodzie (linia 58) wprost potwierdza: "Uno R4 WiFi: DTR nie resetuje ukladu (ESP32-S3 bridge) — brak workaround"

**Wniosek:** `serial_interface.py` i `brain.py` sa gotowe do uzycia z R4 WiFi bez zadnych modyfikacji.

### Stabilnosc /dev/ttyACM0 na R4 WiFi

**Wynik badania:** `/dev/ttyACM0` jest stabilny — udev rules nie sa potrzebne.

Uzasadnienie:
- R4 WiFi wykrywany przez `arduino-cli board list` jako `/dev/ttyACM0` z prawidlowym FQBN
- `serial_interface.py` hardcoduje `/dev/ttyACM0` jako domyslny port (konstruktor MozgRPi)
- ESP32-S3 bridge na R4 WiFi enumeruje jako ACM (CDC ACM) — stabilna nazwa przy jednym urzadzeniu USB
- Udev rules sa potrzebne tylko gdy wiele urzadzen USB Serial walczy o ACM0/ACM1 — nie dotyczy tej konfiguracji

**Jesli port zmieni sie na /dev/ttyACM1:** Przekaz --port argument do arduino-cli i do MozgRPi: `python3 run_pi_brain.py` (MozgRPi akceptuje port jako argument w konstruktorze, domyslnie "/dev/ttyACM0").

## Don't Hand-Roll

| Problem | Nie buduj | Uzyj zamiast | Dlaczego |
|---------|-----------|--------------|----------|
| Port discovery | Skanowanie /dev/tty* skryptem | `arduino-cli board list` | Zwraca FQBN + port jednoczesnie, wykrywa poprawna plyte |
| Serial monitor | nc / cat /dev/ttyACM0 | `arduino-cli monitor --port /dev/ttyACM0 --config baudrate=115200` | Prawidlowy baudrate, nie zajmuje portu na stale |
| Flash retry | Petla bash z sleep | arduino-cli upload retry lub manual re-plug | ESP32 bridge 1200bps touch wymaga specjalnego protokolu |
| DTR control | rts/dtr toggle w bash | Brak potrzeby — SerialInterface.py juz jest poprawny | R4 nie wymaga DTR toggle |

## Common Pitfalls

### Pitfall 1: arduino-cli monitor zajmuje port — pi_brain.py nie moze sie polaczyc

**What goes wrong:** Uzytkownik uruchamia `arduino-cli monitor` aby sprawdzic bootscreen, potem bez zamkniecia probouje uruchomic `run_pi_brain.py`. pyserial zwraca `SerialException: [Errno 16] Device or resource busy: '/dev/ttyACM0'`.

**Why it happens:** Linux seryjny port moze miec tylko jednego wlasciciela. arduino-cli monitor trzyma FD na `/dev/ttyACM0`.

**How to avoid:** Zawsze zamknij monitor (Ctrl+C) przed uruchomieniem run_pi_brain.py. Plan musi miec ten krok jawnie jako czesc checkpointu Test 5.

**Warning signs:** `SerialException: [Errno 16] Device or resource busy`

### Pitfall 2: Agresywny skan Lissajous przy pierwszym starcie — ryzyko mechaniczne

**What goes wrong:** Przy pierwszym starcie na R4, skan sinusoidalny (PAN ±70°, TILT ±25°) startuje natychmiast po Soft Start. Na breadboardzie kable moga sie zaplatac przy pelnym zakresie ruchu.

**Why it happens:** `_czas_startowy_skanu = millis()` w `ServoPID::inicjalizuj()` — skan startuje od razu w trybie SKANOWANIE. Watchdog 500ms przechodzi do SKANOWANIE jesli nie ma ramek serial.

**How to avoid:** Obserwuj pierwsze sekundy skanu z reka gotowa do odlaczenia zasilania 6V. Sprawdz polaczenia breadboard przed wlaczeniem zasilania serw. Nie uruchamiaj pe;nego zakresu bez upewnienia sie ze kable maja luz.

**Warning signs:** Serwa ciagle wracaja do centrum (znaczy skan nie dziala — prawdopodobnie brak firmware lub zla wersja)

### Pitfall 3: ESP32-S3 bridge 1200bps touch — flash moze nie trafic w okno

**What goes wrong:** `arduino-cli upload` zglosilo sukces ale firmware nie wgral (Arduino nadal uruchamia stary kod). Lub: upload fail z "Could not open serial port /dev/ttyACM0".

**Why it happens:** Uno R4 WiFi uzywa "1200bps touch" przez ESP32-S3 aby wejsc w tryb bootloadera. Jestli ESP32 jeszcze nie zainicjalizowal sie (< 500ms po podlaczeniu USB), touch moze sie nie udac. Rowniez: jesli port ACM zmieni sie z ACM0 na ACM1 podczas reboot do bootloader mode.

**How to avoid:** Jesli flash sie nie powiedzie:
1. Odczekaj 2-3 sekundy po podlaczeniu USB przed pierwszym upload
2. Sprawdz `arduino-cli board list` po nieudanym flash — czy port nadal ACM0
3. Sprob ponownie — drugi upload zazwyczaj dziala
4. Ostatecznosc: wcisnij fizyczny przycisk RESET na R4 podczas uruchamiania arduino-cli upload

**Warning signs:** "Could not open serial port" lub firmware nadal startuje stary kod po "Upload successful"

### Pitfall 4: Buzzer aktywny vs pasywny na D8 (znany z PITFALLS.md)

**What goes wrong:** Aktywny buzzer na D8 pobiera wiecej niz 8mA limit pinu Uno R4 — moze uszkodzic RA4M1 GPIO.

**Why it happens:** Piny R4 maja limit 8mA (vs 40mA Leonardo/Uno R3). Aktywne buzzery pobieraja 15-30mA.

**How to avoid:** Zweryfikuj typ buzzera PRZED testem (Test 3 — buzzer). Pasywny buzzer (bez oscylatora wewnetrznego) = OK bezposrednio na D8. Aktywny buzzer = wymaga tranzystora NPN. Rozroznij: jezeli buzzer wydaje dzwiek gdy podlaczony bezposrednio do 5V bez Arduino = aktywny. Jezeli nie = pasywny.

**Warning signs:** Brak tonu z buzzera (niekoniecznie bledny — moze byc pasywny i wymagac `tone()`, ktore i tak jest uzywane)

### Pitfall 5: arduino-cli monitor blokuje sie gdy Arduino nie wyslal nic (brak USB connect)

**What goes wrong:** `arduino-cli monitor` uruchomiony gdy Arduino jest zasilane ale USB nie jest polaczone z RPi — comenda wisi bez outputu.

**How to avoid:** Zawsze sprawdz `arduino-cli board list` przed uruchomieniem monitor aby potwierdzic ze port jest widoczny.

## Code Examples

### Flash firmware — kompletna sekwencja
```bash
# Krok 1: Sprawdz czy R4 jest widoczny
arduino-cli board list
# Oczekiwany output: /dev/ttyACM0 ... Arduino UNO R4 WiFi arduino:renesas_uno:unor4wifi

# Krok 2: Kompilacja (weryfikacja — opcjonalna, szybka)
arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi \
  /home/parolisko/ARIES-LITE/src/arduino/aries_controller/

# Krok 3: Flash
arduino-cli upload --fqbn arduino:renesas_uno:unor4wifi \
  --port /dev/ttyACM0 \
  /home/parolisko/ARIES-LITE/src/arduino/aries_controller/

# Krok 4: Monitor serial (Test 1 — LCD bootscreen debug)
arduino-cli monitor --port /dev/ttyACM0 --config baudrate=115200
# Ctrl+C aby wyjsc — KONIECZNE przed uruchomieniem run_pi_brain.py
```

### Uruchomienie E2E (Test 5)
```bash
# Zamknij monitor jesli otwarty (Ctrl+C)
# Aktywuj venv
source /home/parolisko/ARIES-LITE/venv/bin/activate

# Uruchom pi_brain
cd /home/parolisko/ARIES-LITE
python3 run_pi_brain.py

# Oczekiwane logi przy poprawnym E2E:
# [INFO] src.vision.serial_interface: Port /dev/ttyACM0 otwarty @ 115200 baud.
# [INFO] src.vision.brain: ...TX SLEDZENIE: Xms err_x=YY err_y=ZZ
```

### Weryfikacja bibliotek (jesli brakuje)
```bash
# Sprawdz zainstalowane biblioteki
arduino-cli lib list

# Instalacja (jesli potrzebna — aktualnie wszystkie sa zainstalowane)
arduino-cli lib install "QuickPID@3.1.9"
arduino-cli lib install "Servo@1.3.0"
arduino-cli lib install "LiquidCrystal@1.0.7"
```

### Retry flash po niepowodzeniu
```bash
# Jesli upload fail — sprawdz aktualny port
arduino-cli board list

# Jesli port zmienil sie na ACM1
arduino-cli upload --fqbn arduino:renesas_uno:unor4wifi \
  --port /dev/ttyACM1 \
  /home/parolisko/ARIES-LITE/src/arduino/aries_controller/
```

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| arduino-cli | Flash firmware | ✓ | 1.4.1 (2026-01-19) | — |
| ArduinoCore-renesas | Board support Uno R4 | ✓ | 1.5.3 (> min 1.4.1) | — |
| Servo library | Sterowanie serwami | ✓ | 1.3.0 (> min 1.2.2) | — |
| LiquidCrystal library | LCD 1602 | ✓ | 1.0.7 | — |
| QuickPID library | PID dual-axis | ✓ | 3.1.9 | — |
| /dev/ttyACM0 | Flash + serial | ✓ | Aktywny (R4 WiFi podlaczony) | — |
| python3 | run_pi_brain.py | ✓ | 3.13.5 | — |
| pyserial | SerialInterface | ✓ (w venv) | z requirements.txt | — |
| Zewnetrzny zasilacz 6V | Serwa MG-90S | Zewnetrzny (fizyczny) | — | NIE — bez niego serwa nie dzialaja |

**Missing dependencies with no fallback:**
- Zewnetrzny zasilacz 6V dla serw MG-90S — wymagany fizycznie do Testu 2 i 6. Arduino USB (5V/500mA) nie wystarczy dla dwoch serw podczas skanu Lissajous.

**Missing dependencies with fallback:**
- Brak — srodowisko jest kompletne.

**Uwaga kluczowa o D-02:** CONTEXT.md zakladal ze RPi4 nie ma srodowiska Arduino. Faktycznie arduino-cli 1.4.1 z ArduinoCore-renesas 1.5.3 i wszystkimi bibliotekami jest juz zainstalowany. Plan nie musi zawierac krokow instalacji — mozna przejsc bezposrednio do flash.

## Validation Architecture

Nyquist validation jest wylaczone dla tej fazy — `test_framework: "none"` w `.planning/config.json`. Weryfikacja jest empiryczna: fizyczne obserwowanie hardware + output Serial/LCD. Struktura checkpointow opisana w sekcji Architecture Patterns.

Matryca weryfrykacji (PASS/FAIL checkpoints):

| Test | Weryfikacja | Typ | Oczekiwany wynik |
|------|-------------|-----|-----------------|
| T1: LCD bootscreen | Wizualna | Manual | "ARIES-LITE v2.1" na LCD przez 2s |
| T2: Serwa Soft Start | Wizualna + brak restartu | Manual | Plynna rampa do centrum, skan sinusoidalny |
| T3: Buzzer | Sluchowa | Manual | Ton 1kHz/100ms przy SLEDZENIE |
| T4: Przycisk D7 | Wizualna (LCD tryb) | Manual | Zmiana SLEDZENIE → SKANOWANIE na LCD |
| T5: Serial E2E | Logi RPi + ruch serw | Manual | [LAT] TX SLEDZENIE w logach, serwa sledzace twarz |
| T6: 5x power cycle | Wizualna przez 5 cykli | Manual | Brak restartu podczas skanu po kazdym wlaczeniu |

## State of the Art

| Stare podejscie | Aktualne podejscie | Uwaga |
|-----------------|-------------------|-------|
| Arduino IDE (GUI) dla flash | arduino-cli (CLI) | RPi4 ma monitor wiec IDE tez mozliwe, ale arduino-cli jest D-01 |
| Leonardo: DTR = reset chip | R4 WiFi: DTR bezefektowe (ESP32 bridge) | SerialInterface.py juz poprawny |
| Leonardo: natywne USB CDC (instant) | R4 WiFi: ESP32-S3 bridge (500ms startup) | Firmware juz ma 500ms timeout |
| dtostrf() na AVR | snprintf() z int cast na ARM | Firmware juz używa snprintf — gotowe |

## Open Questions

1. **Typ buzzera — aktywny vs pasywny**
   - What we know: Buzzer jest na D8 (`tone()` z 1kHz/100ms). Firmware uzywa `tone()` (odpowiednie dla pasywnego). Aktywny buzzer na `tone()` tez moze zabrzmiec (wewnetrzny oscylator ignoruje czestotliwosc), ale przeciazenie pinu to ryzyko.
   - What's unclear: Czy buzzer w konfiguracji breadboard to aktywny czy pasywny. Znane z STATE.md: "Active buzzer na D8: jesli aktywny moze przekroczyc 8mA limit Uno R4".
   - Recommendation: Zweryfikuj typ przed Testem 3 (podlacz bezposrednio do 5V — wydaje dzwiek = aktywny). Jesli aktywny, przeskocz Test 3 lub dodaj tranzystor NPN (BC547). Nie jest blockerem dla Testow 1,2,4,5,6.

2. **Orientacja serw (PAN_INVERT / TILT_INVERT)**
   - What we know: `PAN_INVERT = 1`, `TILT_INVERT = -1` w firmware. STATE.md zaznacza: "Orientacja serw: PAN_DIR / TILT_INVERT wymaga empirycznej kalibracji na nowym montazu Uno R4". Test 5 (E2E) ujawni czy kierunek jest poprawny.
   - What's unclear: Czy montaz fizyczny na R4 jest identyczny z R3 proxy.
   - Recommendation: W ramach Testu 5 obserwuj czy serwa sledziace twarz poruszaja sie w prawidlowym kierunku. Jesli nie — zmien `PAN_INVERT` na `-1` lub `TILT_INVERT` na `1` i re-flash.

## Project Constraints (from CLAUDE.md)

- **Jezyk komentarzy i zmiennych:** Polski — komentarze w planach i kodzie po polsku
- **Brak test framework:** Weryfikacja empiryczna (brak pytest, brak unittest)
- **GSD workflow:** Nie dokonuj edycji plikow poza GSD command (execute-phase)
- **Commit convention:** `type(scope): description`
- **Architektura OOP:** HMI / ServoPID / MaszynaStanow — klasy niezmienione w tej fazie
- **Wszystkie stale w config (src/config.py):** Nie dotyczy Arduino firmware — stale sa w `#define` w aries_controller.ino
- **Graceful mock mode:** Nie dotyczy tej fazy — flash na prawdziwy hardware

## Sources

### Primary (HIGH confidence)
- Wynik `arduino-cli board listall` — FQBN `arduino:renesas_uno:unor4wifi` potwierdzony na zywo
- Wynik `arduino-cli board list` — R4 WiFi aktywny na `/dev/ttyACM0` potwierdzony na zywo
- Wynik `arduino-cli core list` — ArduinoCore-renesas 1.5.3 zainstalowany potwierdzony na zywo
- Wynik `arduino-cli lib list` — Servo 1.3.0, LiquidCrystal 1.0.7, QuickPID 3.1.9 zainstalowane na zywo
- Wynik `arduino-cli compile` — firmware kompiluje sie bez bledow (24% flash, 22% RAM) na zywo
- `src/arduino/aries_controller/aries_controller.ino` — firmware v2.1 gotowy do flash
- `src/vision/serial_interface.py` — DTR workaround nieobecny, kod gotowy dla R4 WiFi
- `.planning/research/PITFALLS.md` — Pitfall 5: ESP32 USB bridge startup delay — 500ms timeout juz w firmware

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md` — Synteza badan migracji Leonardo → R4
- `.planning/phases/28-kompletny-szkic-arduino-ino/28-CONTEXT.md` — Decyzje projektowe D-01 do D-10

### Tertiary (LOW confidence)
- Brak — wszystkie kluczowe twierdzenia zweryfikowane bezposrednio na urzadzeniu lub kodzie

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — zweryfikowany zywy hardware + arduino-cli output
- Architecture: HIGH — sekwencja inicjalizacji bezposrednio z kodu firmware, DTR behavior z komentarzy SerialInterface.py
- Pitfalls: HIGH — Pitfall 1,3 z bezposredniego uzycia narzedzia; Pitfall 2,4 z PITFALLS.md (Phase 24 research); Pitfall 5 z arduino-cli doswiadczenia
- Environment: HIGH — kazdy tool sprawdzony `command -v` + version check

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stabilne srodowisko embedded — zmiana mniej prawdopodobna)

**Kluczowe odkrycie dla planisty:** D-02 z CONTEXT.md ("instalacja ArduinoCore-renesas od zera") jest nieaktualne — srodowisko jest juz skonfigurowane. Plan Phase 28 moze przejsc bezposrednio do sekwencji flash + 6 checkpointow. Oszczedza to ~4 taski instalacji w planie.
