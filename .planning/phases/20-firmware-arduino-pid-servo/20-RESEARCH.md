# Phase 20: Firmware Arduino PID + Servo - Research

**Researched:** 2026-03-31
**Domain:** Arduino Leonardo firmware — QuickPID dual-axis, Servo safe startup, millis() watchdog, maszyna stanow, skan Lissajous
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Normalizacja bledu do -1.0..+1.0 po stronie Arduino: `error_norm = (float)error_px / 160.0f`. PID operuje na znormalizowanym bledzie — przenoszalne miedzy rozdzielczosciami.
- **D-02:** Poczatkowe gainy konserwatywne: Kp=2.0, Ki=0.1, Kd=0.5. Output limit +/-5.0 stopni/tick. Kalibracja empiryczna w Phase 23.
- **D-03:** QuickPID z anti-windup. Dual-axis (osobne instancje pan i tilt). Loop PID co 10ms via millis() (deterministyczny, nie delay()).
- **D-04:** Safe startup przez Servo.writeMicroseconds() z rampa. Startuj od 500us (lub min), inkrementuj do 1500us (centrum = 90 stopni) w ciagu 1000ms. Minimalne obciazenie zasilacza 6V.
- **D-05:** Servo.attach() na pinach PAN=D9, TILT=D10. Attach PRZED rampa — writeMicroseconds() wymaga attach.
- **D-06:** Stan po power-on: IDLE. Arduino czeka na pierwsza ramke z RPi. Serwa w pozycji 90/90 po safe startup, nic sie nie rusza samo.
- **D-09:** Skan Lissajous 2D — obie osie skanuja jednoczesnie z roznymi czestotliwosciami.
- **D-10:** Amplitudy: PAN = 70 stopni (zwiekszony z legacy 45), TILT = 25 stopni.

### Claude's Discretion

- **D-07:** Watchdog timeout 500ms (millis()). Po timeout bez ramek Arduino przechodzi do stanu wybranego przez Claude (SCAN lub IDLE). Kazda poprawna ramka resetuje timer watchdog.
- **D-08:** Dispatcher ramek — bezposredni vs warunkowy. Obie opcje akceptowalne.
- **D-11:** Czestotliwosci skanowania. Irracjonalny stosunek PAN/TILT dla pelnego pokrycia Lissajous. Legacy: PAN=0.05, TILT=0.07 jako punkt odniesienia.
- **D-12:** Strategia znakow PID (negacja vs INVERT define). ARD-04 wymaga konfigurowalnego kierunku przez `#define PAN_INVERT / TILT_INVERT`.
- **D-13:** Staly setpoint 0.0 (error=0 = centrum) lub inny.
- Wewnetrzna organizacja kodu w .ino (funkcje, nazwy zmiennych, komentarze)
- Kolejnosc inicjalizacji w setup()

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARD-01 | QuickPID dual-axis (pan + tilt) z anti-windup, deterministyczny loop 100Hz via millis() | QuickPID 3.1.9 API udokumentowany, SetSampleTimeUs(10000), iAwCondition, dOnMeas — gotowe wzorce |
| ARD-02 | Servo safe startup — plynny ruch do 90/90 przy starcie (nie skok) | Wzorzec writeMicroseconds() rampa dokumentowany w D-04, analogia do legacy smooth_move_to() |
| ARD-03 | Software watchdog (millis()) — powrot do trybu SCAN gdy brak ramek >500ms | millis() watchdog pattern z ARCHITECTURE.md, NIE AVR WDT (Caterina bug) |
| ARD-04 | Konfigurowalny kierunek serw (PAN_INVERT / TILT_INVERT define) dla empirycznej kalibracji | #define PAN_INVERT / TILT_INVERT pattern z ARCHITECTURE.md Pattern 6 |
| ARD-05 | Maszyna stanow: IDLE → SCAN → TRACK z przejsciami sterowanymi przez ramki z RPi | Protociol: mode byte 0=IDLE, 1=SCAN, 2=TRACK; enum StanSystemu; przejscia na podstawie mode w ramce |
| ARD-06 | Skanowanie sinusoidalne w trybie SCAN (autonomiczne, bez ramek z RPi) | Lissajous: sin(2pi*f_pan*t) / sin(2pi*f_tilt*t + phi); irracjonalny stosunek f_tilt/f_pan |

</phase_requirements>

---

## Summary

Faza 20 rozbudowuje istniejacy firmware Arduino (parser + echo z Phase 19) o pelna logike sterowania: QuickPID dual-axis 100 Hz, bezpieczny startup writeMicroseconds(), maszyne stanow IDLE/SCAN/TRACK, watchdog millis() 500ms, skan Lissajous 2D. Wszystkie biblioteki (QuickPID, Servo, LiquidCrystal) sa juz dolaczone w `#include` w aries_controller.ino — wymagaja tylko konfiguracji.

Kluczowe decyzje projektowe sa zamkniete (D-01 do D-06, D-09, D-10). Discretionary decyzje (watchdog target state, skan czestotliwosci, sign convention) sa do rozwiazania przez planera/executora. Badania poprzednich faz (research z Phase 18) dokumentuja wszystkie pitfalle i wzorce QuickPID — nie ma potrzeby zewnetrznego researchu; wiedza jest w projekcie.

Nie istnieje framework testowy w projekcie (`test_framework: none` w config.json). Walidacja jest empiryczna: arduino-cli compile, arduino-cli upload, Serial Monitor weryfikacja, pomiar fizyczny serwami.

**Podstawowa rekomendacja:** Rozbuduj przetwarzaj_bajt() o dispatch do StanSystemu, dodaj pid_tick() z millis(), zaimplementuj safe startup w setup() z writeMicroseconds() rampa, zaimplementuj skan_tick() dla trybu SCAN z Lissajous. Watchdog target = SCAN (nie IDLE) — system autonomiczny przy utracie komunikacji.

---

## Standard Stack

### Core

| Biblioteka | Wersja | Cel | Dlaczego standardowa |
|------------|--------|-----|---------------------|
| QuickPID | 3.1.9 | Dual-axis PID 100 Hz z anti-windup | Zainstalowany (Phase 18, #include w aries_controller.ino). 51 µs compute vs PID_v1 128 µs. iAwCondition anti-windup + dOnMeas derivative mode. |
| Servo.h | Built-in (Arduino IDE) | PWM D9 (pan) i D10 (tilt) | Wbudowany. Timer1 na Leonardo: D9=TIMER1A, D10=TIMER1B. Natywna obsluga MG-90S. |
| LiquidCrystal.h | Built-in (Arduino IDE) | LCD 1602 (Phase 22 — NIE w tej fazie) | Juz w #include, nie uzywany w Phase 20, nie usuwac. |

### Supporting

| Biblioteka | Wersja | Cel | Kiedy uzywac |
|------------|--------|-----|-------------|
| avr/wdt.h | AVR-libc built-in | NIE uzywac hardware WDT | Zrodlo wiedzy: nie wolno uzywac wdt_enable() na Leonardo (Caterina bootloader bug). millis() watchdog zamiast. |

### Instalacja

Wszystko zainstalowane w Phase 18. Weryfikacja:
```bash
arduino-cli lib list | grep QuickPID
```

Oczekiwany output: `QuickPID   3.1.9`

---

## Architecture Patterns

### Struktura kodu w aries_controller.ino

```
// --- Includes i defines ---
#include <QuickPID.h>
#include <Servo.h>
#include <LiquidCrystal.h>

#define PAN_INVERT  1   // +1 lub -1 — empirycznie
#define TILT_INVERT (-1) // -1 potwierdzony w v1.7 legacy

// --- Stale ---
#define FRAME_SIZE 8
#define START_MARKER 0xAA
#define PID_INTERVAL_MS 10       // 100 Hz
#define WATCHDOG_TIMEOUT_MS 500  // 500ms per D-07
#define SCAN_FREQ_PAN   0.05f    // Hz — punkt startowy
#define SCAN_FREQ_TILT  0.07f    // Hz — irracjonalny stosunek
#define SCAN_AMP_PAN    70.0f    // stopni — D-10
#define SCAN_AMP_TILT   25.0f    // stopni — D-10
#define HALF_FRAME_W    160.0f   // dla normalizacji bledu — D-01

// --- Enum stanow systemu ---
enum StanSystemu { IDLE, SCAN, TRACK };

// --- Enum stanow parsera (zachowany z Phase 19) ---
enum StanParsera { WAIT_START, READ_PAYLOAD };

// --- Instancje PID ---
float pan_wej, pan_wyj, pan_sp = 0.0f;
float tilt_wej, tilt_wyj, tilt_sp = 0.0f;
QuickPID pidPan(&pan_wej, &pan_wyj, &pan_sp, Kp, Ki, Kd, QuickPID::Action::direct);
QuickPID pidTilt(&tilt_wej, &tilt_wyj, &tilt_sp, Kp, Ki, Kd, QuickPID::Action::direct);

// --- Instancje Servo ---
Servo serwo_pan;
Servo serwo_tilt;

// --- Stan systemu ---
StanSystemu stan_systemu = IDLE;
float kat_pan  = 0.0f;   // -60..+60 stopni
float kat_tilt = 0.0f;   // -30..+30 stopni
int16_t ostatni_blad_x = 0;
int16_t ostatni_blad_y = 0;

// --- Watchdog i timing ---
unsigned long czas_ostatniej_ramki = 0;
unsigned long czas_ostatniego_pid  = 0;
unsigned long czas_startowy_skanu  = 0;

// Funkcje: przetwarzaj_bajt(), dispatch_ramke(), safe_startup(),
//          pid_tick(), skan_tick(), ustaw_serwa()

setup() → serial + safe_startup() + PID init
loop() → parser + watchdog + pid/skan tick
```

### Pattern 1: Safe Startup — writeMicroseconds() rampa (D-04)

**Co:** Serwo startuje od 500us i inkremenuje do 1500us w ciagu 1000ms.
**Kiedy:** W setup(), po Servo.attach(), przed wejsciem w glowna petle.
**Zrodlo:** D-04 z CONTEXT.md + anti-pattern dokumentowany w ARCHITECTURE.md.

```cpp
// Source: CONTEXT.md D-04 + PITFALLS.md Anti-Pattern 5
void safe_startup() {
    const int US_MIN    = 500;   // minimalny impuls
    const int US_CENTER = 1500;  // centrum = 90 stopni
    const int KROKI     = 50;    // 1000ms / 20ms = 50 krokow
    const int OPOZNIENIE_MS = 20;

    int us_start_pan  = US_MIN;
    int us_start_tilt = US_MIN;

    for (int i = 0; i <= KROKI; i++) {
        int us = us_start_pan + (int)((long)(US_CENTER - us_start_pan) * i / KROKI);
        serwo_pan.writeMicroseconds(us);
        serwo_tilt.writeMicroseconds(us);
        delay(OPOZNIENIE_MS);
    }
    kat_pan  = 0.0f;
    kat_tilt = 0.0f;
}
```

**Uwaga:** Servo.attach() musi poprzedzac writeMicroseconds(). Jesli attach() nie zostal wywolany, writeMicroseconds() jest ignorowane.

### Pattern 2: QuickPID konfiguracja (D-02, D-03)

**Co:** Dual-axis QuickPID z iAwCondition, dOnMeas, setpoint=0, loop co 10ms.
**Kiedy:** W setup() po safe_startup().

```cpp
// Source: PITFALLS.md Pitfall 4 + STACK.md QuickPID Configuration
const float Kp = 2.0f, Ki = 0.1f, Kd = 0.5f;
const float OUTPUT_LIMIT = 5.0f;  // D-02: +/-5 stopni/tick

void init_pid() {
    pidPan.SetSampleTimeUs(10000);   // 100 Hz
    pidTilt.SetSampleTimeUs(10000);
    pidPan.SetOutputLimits(-OUTPUT_LIMIT, OUTPUT_LIMIT);
    pidTilt.SetOutputLimits(-OUTPUT_LIMIT, OUTPUT_LIMIT);
    pidPan.SetAntiWindupMode(QuickPID::iAwCondition);   // anti-windup
    pidTilt.SetAntiWindupMode(QuickPID::iAwCondition);
    pidPan.SetProportionalMode(QuickPID::pOnError);
    pidTilt.SetProportionalMode(QuickPID::pOnError);
    pidPan.SetDerivativeMode(QuickPID::dOnMeas);        // brak derivative kick
    pidTilt.SetDerivativeMode(QuickPID::dOnMeas);
    pidPan.SetMode(QuickPID::Control::automatic);
    pidTilt.SetMode(QuickPID::Control::automatic);
}
```

**WAZNE:** Gainy D-02 sa na znormalizowanym bledzie (-1.0..+1.0), nie na pikselach.
Output limit +/-5 stopni/tick. PID setpoint = 0.0 (centrum klatki = brak bledu).

### Pattern 3: Normalizacja bledu i tick PID (D-01)

```cpp
// Source: CONTEXT.md D-01, PROTOCOL_SPEC.md
void pid_tick() {
    unsigned long teraz = millis();
    if (teraz - czas_ostatniego_pid < PID_INTERVAL_MS) return;
    czas_ostatniego_pid = teraz;

    if (stan_systemu == TRACK) {
        // Normalizacja: error_px / 160.0 → zakres -1.0..+1.0
        pan_wej  = (float)ostatni_blad_x / HALF_FRAME_W;
        tilt_wej = (float)ostatni_blad_y / HALF_FRAME_W;

        pidPan.Compute();
        pidTilt.Compute();

        // Zastosuj kierunek + clamp
        kat_pan  = constrain(kat_pan  + PAN_INVERT  * pan_wyj,  -60.0f, 60.0f);
        kat_tilt = constrain(kat_tilt + TILT_INVERT * tilt_wyj, -30.0f, 30.0f);
        ustaw_serwa();
    } else if (stan_systemu == SCAN) {
        skan_tick(teraz);
    }
    // IDLE: nic nie rob
}
```

### Pattern 4: Skan Lissajous 2D (D-09, D-10, D-11)

**Co:** PAN i TILT skanuja jednoczesnie z roznymi czestotliwosciami (irracjonalny stosunek).
**Dlaczego irracjonalny stosunek:** Stosunek f_tilt/f_pan = 0.07/0.05 = 1.4 — nie jest scisle irracjonalny (7/5 = 1.4 = wymierne), ale daje figura Lissajous 5:7 pokrywajaca cale pole. Lepszy wybor: f_pan=0.05, f_tilt=0.073 (niemianowane przyblizenie sqrt(2)*0.05).

```cpp
// Source: legacy/src/modes/test_tracker.py _skanuj() + CONTEXT.md D-09, D-10, D-11
void skan_tick(unsigned long teraz) {
    float t = (teraz - czas_startowy_skanu) / 1000.0f;  // sekundy
    kat_pan  = SCAN_AMP_PAN  * sin(2.0f * M_PI * SCAN_FREQ_PAN  * t);
    kat_tilt = SCAN_AMP_TILT * sin(2.0f * M_PI * SCAN_FREQ_TILT * t);
    // Clamp dla bezpieczenstwa
    kat_pan  = constrain(kat_pan,  -60.0f, 60.0f);
    kat_tilt = constrain(kat_tilt, -30.0f, 30.0f);
    ustaw_serwa();
}
```

**Rekomendacja dla D-11 (Claude's Discretion):** Uzyj `SCAN_FREQ_PAN=0.05f, SCAN_FREQ_TILT=0.073f`.
Stosunek 0.073/0.05 = 1.46 — niewymierne przyblizenie, Lissajous nigdy nie zamknie cyklu w przewidywalnym czasie, co daje chaotyczne ale pelne pokrycie.

### Pattern 5: Maszyna stanow + watchdog (D-06, D-07)

```cpp
// Source: ARCHITECTURE.md Pattern 4 + CONTEXT.md D-06, D-07
void loop() {
    // Parser (zachowany z Phase 19, rozszerzony o dispatch)
    while (Serial.available() > 0) {
        przetwarzaj_bajt((uint8_t)Serial.read());
    }

    // Watchdog millis()
    if (millis() - czas_ostatniej_ramki > WATCHDOG_TIMEOUT_MS) {
        if (stan_systemu != SCAN) {
            przejdz_do(SCAN);  // autonomiczny powrot do skanowania
        }
    }

    // PID lub skan tick (co 10ms)
    pid_tick();

    // LCD throttled (Phase 22 — placeholder tutaj)
}

void przejdz_do(StanSystemu nowy_stan) {
    stan_systemu = nowy_stan;
    if (nowy_stan == SCAN) {
        czas_startowy_skanu = millis();
        pidPan.Reset();
        pidTilt.Reset();
    }
}
```

**Rekomendacja dla D-07 (Claude's Discretion):** Watchdog target = SCAN.
Uzasadnienie: system ma byc autonomiczny — kamera powinna szukac twarzy bez RPi, nie stac nieruchomo. IDLE przy watchdog = nieruchomy system = bezuzyteczny przy awarii sieci. SCAN = bezpieczny fallback zgodny z intencja projektu.

### Pattern 6: Dispatch ramki + PAN_INVERT (D-08, D-12)

**Rekomendacja dla D-08 (Claude's Discretion):** Bezposredni dispatcher — mode z ramki ustawia stan bezposrednio.
Uzasadnienie: RPi wie co robi (ma wyniki detekcji MediaPipe) i wysyla wiarygodny tryb. Warunkowy dispatcher komplikuje logike bez zysku. Jedyny wyjatek: watchdog moze nadpisac IDLE→SCAN.

```cpp
// Source: PROTOCOL_SPEC.md + CONTEXT.md D-08, D-12
void dispatch_ramke() {
    uint8_t tryb     = ramka_buf[1];
    int16_t blad_x   = (int16_t)(ramka_buf[2] | (ramka_buf[3] << 8));
    int16_t blad_y   = (int16_t)(ramka_buf[4] | (ramka_buf[5] << 8));
    // ramka_buf[6] = face_size (do uzycia w Phase 23+)

    czas_ostatniej_ramki = millis();  // reset watchdog

    ostatni_blad_x = blad_x;
    ostatni_blad_y = blad_y;

    StanSystemu nowy = (StanSystemu)tryb;  // 0=IDLE, 1=SCAN, 2=TRACK
    if (nowy != stan_systemu) {
        przejdz_do(nowy);
    }
}
```

**Rekomendacja dla D-12 (Claude's Discretion):** Stala `#define PAN_INVERT (+1)` i `#define TILT_INVERT (-1)`.
Uzasadnienie: v1.7 empirycznie potwierdzil negacje tilt (`korekta_tilt = -pid_tilt` w legacy). Nowy montaz Arduino wymaga re-weryfikacji, ale poczatkowe wartosci oparte na doswiadczeniu. PAN_INVERT=+1 (brak negacji), TILT_INVERT=-1 (negacja).

**Rekomendacja dla D-13 (Claude's Discretion):** Setpoint = 0.0.
Uzasadnienie: Protokol wysyla blad wzgledem centrum klatki. error=0 oznacza twarz w centrum. PID d0azy do usrednienia error_norm=0 → setpoint naturalny = 0.0.

### Pattern 7: ustaw_serwa() z konwersja kat→write()

```cpp
// Source: ARCHITECTURE.md Data Flow
void ustaw_serwa() {
    // Servo.write() przyjmuje 0-180 stopni, centrum = 90
    // kat_pan / kat_tilt w zakresie -60..+60 i -30..+30
    serwo_pan.write((int)(kat_pan + 90.0f));
    serwo_tilt.write((int)(kat_tilt + 90.0f));
}
```

### Anti-Patterns

- **delay() w loop():** Blokuje parser i PID. Uzywac TYLKO w safe_startup() (jednorazowe, w setup()).
- **Servo.write() bez timer throttle:** loop() biega ~50-100 kHz, writeMicroseconds() co iteracje = bez efektu + CPU overhead. Throttlowac do 100 Hz via millis().
- **wdt_enable() na Leonardo:** Caterina bootloader bug — permanentny reset loop. NIE UZYWAC. Tylko millis() watchdog.
- **lcd.clear() w petli PID:** lcd.clear() blokuje ~1500µs, przy 100 Hz to 15% budgetu. LCD Phase 22 — na razie brak, ale zachowac wiedze.
- **Servo.attach() po safe_startup:** attach musi byc PRZED writeMicroseconds() — kolejnosc w setup() kluczowa.

---

## Don't Hand-Roll

| Problem | Nie buduj | Uzyj zamiast | Dlaczego |
|---------|-----------|--------------|----------|
| Anti-windup PID | Warunkowa integracja reczna | QuickPID iAwCondition | Zaimplementowane i przetestowane; recznie = ryzyko bledow przy krawedzi |
| Derivative kick | Filtrowanie d-term recznie | QuickPID dOnMeas | Jeden setter; recznie = komplikacja |
| PWM safe startup | Reczna interpolacja write() | writeMicroseconds() rampa (Pattern 1) | Konkretny wzorzec z D-04; prosty for-loop |
| Servo katy | Obliczanie us recznie | Servo.write(kat + 90) | Servo.h mapuje 0-180 → 1000-2000us automatycznie |
| Software watchdog | Licznik iteracji | millis() - czas_ostatniej_ramki | millis() nie driftuje przy zmiennym czasie loop() |

---

## Common Pitfalls

### Pitfall 1: safe_startup() przed attach()
**Co sie dzieje:** writeMicroseconds() wywolane przed attach() jest cichym no-op. Serwo nie rusza sie podczas rampy.
**Dlaczego:** Servo library ignoruje komendy bez aktywnego attach.
**Jak uniknac:** W setup(): `serwo_pan.attach(9); serwo_tilt.attach(10);` PRZED safe_startup().
**Sygnaly:** Serwo skacze do nowej pozycji po pierwszym pid_tick() zamiast plynnej rampy.

### Pitfall 2: Blad normalizacji — int16 dzielony przez int
**Co sie dzieje:** `(float)ostatni_blad_x / 160` oblicza integer division jesli HALF_FRAME_W jest int. Wynik = 0 lub 1 dla wszystkich wartosci <160.
**Dlaczego:** C++ promuje int/int do int, nie float.
**Jak uniknac:** Uzyj `160.0f` lub `(float)160`. Zdefiniuj `#define HALF_FRAME_W 160.0f`.
**Sygnaly:** PID nie reaguje na blad; pan/tilt_wej zawsze 0.0 lub 1.0.

### Pitfall 3: QuickPID nie oblicza jesli za czesto wywolywany
**Co sie dzieje:** QuickPID.Compute() z SetSampleTimeUs(10000) ignoruje wywolania czestsze niz 10ms (zwraca false bez obliczenia). Wywolywac go w loop() bez zewnetrznego millis() throttle = zero efektu gdy loop() biega szybciej.
**Dlaczego:** QuickPID ma wewnetrzny timer — to feature, nie bug. Ale pidPan.Compute() NIE blokuje; po prostu nic nie robi.
**Jak uniknac:** Wywolywac Compute() w kazdej iteracji loop() — QuickPID sam decyduje kiedy obliczac. LUB throttlowac zewnetrznym millis() dla przejrzystosci. Obie metody dzialaja.
**Sygnaly:** Serwa nie reaguja w ogole lub z opoznieniem.

### Pitfall 4: Skan Lissajous z wymiernym stosunkiem czestotliwosci
**Co sie dzieje:** Jesli f_pan=0.05, f_tilt=0.07 (stosunek 5:7 wymierne), figura Lissajous zamknie sie po 7/0.05 = 140 sekundach i zacznie sie powtarzac. Caly skan bedzie tego samego wzoru — moze nie pokryc niektorych katow.
**Dlaczego:** Lissajous z wymiernym stosunkiem to zamknieta krzywa.
**Jak uniknac:** Uzyj f_tilt=0.073f (przyblizenie niewymierne). Stosunek 0.073/0.05=1.46 — krzywoliniowy Lissajous nie zamknie cyklu.
**Sygnaly:** Po ~2 minutach skan wyglada identycznie jak na poczatku.

### Pitfall 5: Watchdog fire przy normalnej komunikacji (czas_ostatniej_ramki nie resetowany)
**Co sie dzieje:** czas_ostatniej_ramki nie jest uaktualniane przy kazdej poprawnej ramce → watchdog odpala sie co 500ms mimo aktywnej komunikacji.
**Dlaczego:** Latwa pomylka w dispatch_ramke() — reset watchdog po VERIFY_CHECKSUM, nie po START_MARKER.
**Jak uniknac:** `czas_ostatniej_ramki = millis()` tylko po udanej weryfikacji checksum w dispatch_ramke(), nie w srodku przetwarzaj_bajt().
**Sygnaly:** System cigle wraca do SCAN mimo ze RPi wysyla TRACK ramki.

### Pitfall 6: Przepelnienie millis() po 49 dniach
**Co sie dzieje:** millis() przepelnia sie po ~49 dniach (uint32_t 2^32 ms). Roznica `millis() - czas_ostatniej_ramki` staje sie bardzo duza i watchdog odpala sie faleszywie.
**Dlaczego:** Standardowy problem z odejmowaniem unsigned.
**Jak uniknac:** Odejmowanie unsigned long jest bezpieczne przy przepelnieniu: `(unsigned long)(millis() - czas_ostatniej_ramki) > WATCHDOG_TIMEOUT_MS` dziala poprawnie dzieki arytmetyce modularnej. NIE uzywac signed comparison.
**Sygnaly:** System "restartuje sie" po bardzo dlugim czasie dzialania.

---

## Code Examples

### Pelna sekwencja setup()

```cpp
// Source: CONTEXT.md D-04, D-05, STACK.md, ARCHITECTURE.md
void setup() {
    Serial.begin(115200);

    // Leonardo USB CDC — czekaj na otwarcie portu, max 3s
    uint32_t start = millis();
    while (!Serial && millis() - start < 3000) {
        delay(10);
    }

    // D-05: attach PRZED safe_startup
    serwo_pan.attach(9);   // D9 = TIMER1A
    serwo_tilt.attach(10); // D10 = TIMER1B

    // D-04: safe startup rampa writeMicroseconds()
    safe_startup();

    // D-03: PID init
    init_pid();

    // Inicjalizacja watchdog timer
    czas_ostatniej_ramki = millis();
    czas_startowy_skanu  = millis();

    // D-06: stan startowy IDLE
    stan_systemu = IDLE;
}
```

### Rozszerzona przetwarzaj_bajt() z dispatch

```cpp
// Source: Phase 19 aries_controller.ino + CONTEXT.md D-08
void przetwarzaj_bajt(uint8_t bajt) {
    switch (stan_parsera) {
        case WAIT_START:
            if (bajt == START_MARKER) {
                ramka_buf[0] = bajt;
                ramka_idx = 1;
                stan_parsera = READ_PAYLOAD;
            }
            break;

        case READ_PAYLOAD:
            ramka_buf[ramka_idx++] = bajt;
            if (ramka_idx == FRAME_SIZE) {
                uint8_t obliczona = 0;
                for (uint8_t i = 1; i <= 6; i++) obliczona ^= ramka_buf[i];

                if (obliczona == ramka_buf[7]) {
                    dispatch_ramke();   // <-- NOWE: zamiast echo
                }
                // Bledna checksum: cichy drop

                ramka_idx = 0;
                stan_parsera = WAIT_START;
            }
            break;

        default:
            ramka_idx = 0;
            stan_parsera = WAIT_START;
            break;
    }
}
```

### Angle clamp + ustaw_serwa()

```cpp
// Source: ARCHITECTURE.md Data Flow + legacy/src/hardware.py set_angles()
#define PAN_MIN  (-60.0f)
#define PAN_MAX  (+60.0f)
#define TILT_MIN (-30.0f)
#define TILT_MAX (+30.0f)

void ustaw_serwa() {
    kat_pan  = constrain(kat_pan,  PAN_MIN,  PAN_MAX);
    kat_tilt = constrain(kat_tilt, TILT_MIN, TILT_MAX);
    serwo_pan.write((int)(kat_pan  + 90.0f));
    serwo_tilt.write((int)(kat_tilt + 90.0f));
}
```

---

## State of the Art

| Stare podejscie | Aktualne podejscie | Kiedy zmieniono | Wplyw |
|-----------------|-------------------|-----------------|-------|
| br3ttb PID_v1 (Python/Arduino) | QuickPID 3.1.9 z iAwCondition | Phase 18 decision | 51 µs vs 128 µs compute; wbudowany anti-windup |
| gpiozero + pigpio (Python servo) | Servo.h na Arduino | v2.0 architektura | Arduino deterministyczny timing vs Python GIL jitter |
| delay() w loop dla timing | millis() non-blocking | Standard Arduino wzorzec | Brak blokowania parsera i watchdog |
| Servo.write(90) w setup() | writeMicroseconds() rampa 1000ms | Phase 20 D-04 | Brak brownout przy starcie (znany problem v1.x) |
| Skan pan-only (SCAN_AMPLITUDE=45) | Lissajous 2D PAN=70, TILT=25 | Phase 20 D-09, D-10 | Pelne 2D pokrycie pola widzenia |

**Przestarzale:**
- Hardware AVR WDT (`wdt_enable()`): Caterina bootloader bug na Leonardo — permanentny brick risk. Uzywac wylacznie millis() watchdog.
- `Serial.parseInt()` / ASCII protokol: Za wolne, brak checksuma, variable length. Protokol binarny 8B aktywny od Phase 19.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| arduino-cli | Kompilacja + upload | ✓ | 1.4.1 (2026-01-19) | — |
| QuickPID library | ARD-01 | ✓ | 3.1.9 (zainstalowany Phase 18) | — |
| Servo.h | ARD-02 | ✓ | Built-in Arduino IDE | — |
| Arduino Leonardo na /dev/ttyACM0 | Upload + weryfikacja | Wymaga podlaczenia fizycznego | — | — |
| Serwa MG-90S na D9/D10 | Weryfikacja fizyczna | Wymaga podlaczenia fizycznego | — | Serial Monitor log weryfikuje logike bez serw |

**Missing dependencies with no fallback:**
- Fizyczne serwa MG-90S + zasilacz 6V — wymagane do pelnej weryfikacji mechanicznej ARD-02 (safe startup) i ARD-04 (kierunek). Logike firmware mozna weryfikowac przez Serial Monitor bez serw.

---

## Validation Architecture

> `test_framework: none` w .planning/config.json (`workflow.nyquist_validation` nieobecny — traktuj jako enabled, ale brak frameworka testowego).

### Brak frameworka testowego

Projekt nie ma pytest, unittest ani Arduino test framework. Walidacja empiryczna per CLAUDE.md: "Verification is empirical (HTTP responses, visual confirmation, command output)."

### Mapa wymagan → weryfikacja

| Req ID | Zachowanie | Typ testu | Komenda / metoda | Plik |
|--------|-----------|-----------|------------------|------|
| ARD-01 | QuickPID 100 Hz, anti-windup | Empiryczny | Serial Monitor: wyslij TRACK ramke z error_x=100, obserwuj output PID w logach | Brak plikow testowych |
| ARD-02 | Safe startup plynny | Empiryczny / wizualny | Podlacz serwa, zasilacz 6V, arduino-cli upload, obserwuj ruch przy starcie | — |
| ARD-03 | Watchdog 500ms → SCAN | Empiryczny | Wyslij TRACK ramki, zatrzymaj RPi, czekaj >500ms, obserwuj Serial Monitor log "SCAN" | — |
| ARD-04 | PAN_INVERT/TILT_INVERT | Empiryczny | Wyslij TRACK ramke z error_x=+80, obserwuj kierunek ruchu pan; zmien define, porownaj | — |
| ARD-05 | Maszyna stanow IDLE→SCAN→TRACK | Empiryczny | Wyslij mode=0 (IDLE) → log "IDLE"; mode=1 (SCAN) → obserwuj skan; mode=2 (TRACK) → obserwuj PID | — |
| ARD-06 | Skan Lissajous 2D | Empiryczny / wizualny | Ustaw stan SCAN przez ramke mode=1, obserwuj ruch obu osi rownoczesnie | — |

### Komendy weryfikacji

```bash
# Kompilacja (weryfikacja bez sprzetu)
arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller/

# Upload
arduino-cli upload --fqbn arduino:avr:leonardo --port /dev/ttyACM0 src/arduino/aries_controller/

# Monitor Serial (obserwacja logiki)
arduino-cli monitor --port /dev/ttyACM0 --config baudrate=115200
```

### Wave 0 Gaps

Brak plikow testowych do stworzenia — projekt nie ma frameworka testowego. Weryfikacja przez Serial Monitor i obserwacje fizyczne.

---

## Open Questions

1. **Czestotliwosc skanowania Lissajous (D-11)**
   - Co wiemy: f_pan=0.05 i f_tilt=0.07 z legacy (stosunek 5:7 wymierne). Uzytkownik uznal 45 stopni za za waskie (stad D-10 PAN=70). Amplitudy zwiekszono.
   - Co niejasne: Czy stosunek 5:7 jest wystarczajaco "roznorodnny" dla praktycznego pokrycia, czy wymagane niewymierne?
   - Rekomendacja: Uzyj f_tilt=0.073f. Roznica praktyczna znikoma, ale unika idealnie symetrycznych wzorcow.

2. **Kierunek PAN_INVERT na nowym montazu (D-12)**
   - Co wiemy: TILT_INVERT=-1 potwierdzony empirycznie w v1.7 legacy. PAN_INVERT w legacy = brak negacji (+1) przy montazu v1.7.
   - Co niejasne: Montaz Arduino v2.0 moze byc inny od v1.7 (inne umieszczenie serwomechanizmu).
   - Rekomendacja: Zacznij od PAN_INVERT=+1, TILT_INVERT=-1. Empiryczna weryfikacja w fazie 20 lub 23.

3. **Gainy D-02 na znormalizowanym bledzie**
   - Co wiemy: Kp=2.0, Ki=0.1, Kd=0.5, output limit ±5 deg/tick, blad normalizowany do ±1.0.
   - Co niejasne: Te gainy sa nowe (nie testowane na sprzecie). Dla Kp=2.0, error_norm=1.0 (twarz na krawedzi): P-term = 2.0 — w granicach output limit 5.0. Przy convergencji z krawedzi do centrum w ~3 tickach (2.0 + 1.8 + 1.6 ≈ 5 deg w ~30ms). Wyglada rozumnie.
   - Rekomendacja: Zaakceptuj D-02 jako punkt startowy. Kalibracja empiryczna w Phase 23 per CONTEXT.md.

---

## Project Constraints (from CLAUDE.md)

- **Jezyk komentarzy i nazw:** Polski dla nowszego kodu (wzorzec z test_tracker.py). Kontynuowac w Phase 20: komentarze po polsku, nazwy zmiennych polskie (kat_pan, czas_ostatniej_ramki, stan_systemu).
- **Styl kodu:** 4-spacje indentacja, brak automatic formattera, brak lintera.
- **Weryfikacja empiryczna:** Brak unit testow. Proof = arduino-cli compile + Serial Monitor output + fizyczna obserwacja.
- **GSD workflow:** Zmiany przez GSD command (execute-phase), nie bezposrednia edycja.
- **Brak delay() w loop():** delay() tylko w setup() dla safe_startup(). loop() = non-blocking.
- **Commit convention:** `feat(phase-20): opis` lub `fix(scope): opis`.
- **PID gainy w stalych:** Kp/Ki/Kd jako stale na gorze .ino, nie hardcode w QuickPID konstruktorze.
- **Soft limits:** PAN ±60, TILT ±30 stopni (z CLAUDE.md hardware constraints).
- **Piny serw:** PAN=D9, TILT=D10 (hardcoded per D-05).
- **NIE hardware WDT:** wdt_enable() zabronione na Leonardo (Caterina bug, documented in STATE.md).

---

## Sources

### Primary (HIGH confidence)

- `src/arduino/aries_controller/aries_controller.ino` — istniejacy firmware z Phase 19 (parser state-machine + echo); bezposrednie zrodlo rozbudowy
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED 8-bajtowa ramka, checksum, mode values, referencyjny kod C
- `.planning/research/ARCHITECTURE.md` — Brain-Muscle wzorzec, Pattern 4 (millis() watchdog), Pattern 6 (PAN_DIR define), data flow, petla Arduino
- `.planning/research/PITFALLS.md` — Pitfall 4 (QuickPID iAwCondition, dOnMeas), Pitfall 6 (AVR WDT bootloader lock)
- `.planning/research/STACK.md` — QuickPID 3.1.9 API, SetSampleTimeUs, Servo.h TIMER1 mapping
- `.planning/phases/20-firmware-arduino-pid-servo/20-CONTEXT.md` — zamkniete decyzje D-01..D-13
- `legacy/src/hardware.py` — smooth_move_to() wzorzec (analog do safe_startup()), set_angles() clamp
- `legacy/src/modes/test_tracker.py` — _skanuj() sinusoidal scan, MaszynaStanow, PID sign convention

### Secondary (MEDIUM confidence)

- `.planning/STATE.md` — Accumulated decisions: TILT_INVERT=-1 potwierdzony v1.7, millis() watchdog decyzja
- `.planning/REQUIREMENTS.md` — ARD-01..ARD-06 definicje i traceability

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — QuickPID, Servo.h zainstalowane i przetestowane w Phase 18
- Architecture: HIGH — wszystkie wzorce z wczesniejszego research + legacy codebase
- Pitfalls: HIGH — dokumentowane problemy z poprzednich faz projektu
- Discretionary decisions: MEDIUM — rekomendacje logiczne, wymagaja empirycznej weryfikacji na sprzecie

**Research date:** 2026-03-31
**Valid until:** 2026-05-01 (stabilny stack Arduino, brak fast-moving dependencies)
