---
phase: 20-firmware-arduino-pid-servo
verified: 2026-03-31T12:00:00Z
status: human_needed
score: 6/6 must-haves verified
human_verification:
  - test: "Upload firmware do Arduino Leonardo i wlacz zasilanie 6V serw. Obserwuj ruch serw w ciagu pierwszej sekundy."
    expected: "Serwa plynnie dochodza do pozycji centralnej (90/90) w ciagu ok. 1 sekundy — bez skoku, bez uderzenia mechanicznego, bez brownoutu zasilacza."
    why_human: "Zachowanie safe_startup() (rampa writeMicroseconds 500→1500us, 50 krokow po 20ms) nie moze byc zweryfikowane bez sprzetu. Ryzyko skoku pradu jest ryzykiem fizycznym."
  - test: "Uruchom firmware, polacz RPi przez UART, wyslij ramke mode=2 (TRACK) z bledem x=+80, y=+40, odczekaj 3 sekundy bez kolejnych ramek."
    expected: "Serwa reaguja na blad PID w ciagu 10ms (100 Hz tick). Po 500ms bez ramki Arduino autonomicznie wraca do trybu SCAN (ruch sinusoidalny Lissajous)."
    why_human: "Zachowanie watchdog millis() i PID servo response wymaga hardware: Arduino Leonardo + serwa MG-90S + UART z RPi."
  - test: "Zmien #define PAN_INVERT z (1) na (-1), skompiluj i uploaduj. Wyslij ramke TRACK z bledem x=+80. Sprawdz kierunek ruchu serwa pan."
    expected: "Kierunek ruchu serwa pan jest odwrocony w porownaniu do wersji PAN_INVERT=(1)."
    why_human: "Kalibracja kierunku serwa (ARD-04) wymaga obserwacji fizycznego ruchu. Nie mozna zweryfikowac programowo."
  - test: "Wyslij kolejno ramki: mode=0 (IDLE), mode=1 (SCAN), mode=2 (TRACK), mode=1 (SCAN). Obserwuj przejscia stanow."
    expected: "Maszyna stanow przechodzi IDLE → SCAN → TRACK → SCAN zgodnie z ramkami. W trybie SCAN widoczny ruch Lissajous 2D (pan i tilt poruszaja sie z rozna czestotliwoscia)."
    why_human: "Weryfikacja maszyny stanow wymaga hardware i mozliwosci obserwacji ruchu serw. Lissajous 2D z f_pan=0.05 Hz i f_tilt=0.073 Hz (irracjonalny stosunek) wymaga kilkudziesieciu sekund obserwacji."
---

# Phase 20: Firmware Arduino PID + Servo — Raport Weryfikacji

**Phase Goal:** Firmware Arduino — PID + sterowanie serwami. Arduino odbiera ramki z RPi przez UART, oblicza PID dual-axis (100 Hz), steruje serwami pan/tilt, skanuje autonomicznie (Lissajous 2D) przy braku komunikacji (watchdog 500ms).
**Verified:** 2026-03-31T12:00:00Z
**Status:** human_needed — wszystkie automatyczne sprawdzenia przeszly; weryfikacja hardware wymagana
**Re-verification:** Nie — weryfikacja inicjalna

## Goal Achievement

### Observable Truths

| #  | Truth                                                                 | Status     | Evidence                                                                                          |
|----|-----------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------------|
| 1  | Serwa plynnie docieraja do 90/90 przy starcie — brak skoku pradu      | ? HUMAN    | safe_startup() implementuje rampe 500→1500us w 50 krokach (20ms kazdy) — logika poprawna, hardware wymagany |
| 2  | Zmiana PAN_INVERT / TILT_INVERT w #define odwraca kierunek serwa      | ? HUMAN    | PAN_INVERT uzyty jako mnoznik: `kat_pan + PAN_INVERT * pan_wyj` (linia 195) — logika poprawna, ruch fizyczny wymagany |
| 3  | Servo.attach() na D9 i D10, PID skonfigurowany 100 Hz z anti-windup   | VERIFIED   | serwo_pan.attach(PAN_PIN=9), SetSampleTimeUs(10000), iAwMode::iAwCondition — wszystkie obecne     |
| 4  | Petla PID wykonuje sie co 10ms — deterministyczny timing via millis()  | VERIFIED   | pid_tick(): `if (teraz - czas_ostatniego_pid < PID_INTERVAL_MS) return` (linia 183) — throttle dziala |
| 5  | Watchdog 500ms bez ramek → Arduino przechodzi do SCAN automatycznie    | VERIFIED   | loop() linia 284-287: sprawdza `stan_systemu != IDLE && != SCAN`, wywoluje przejdz_do(SCAN)       |
| 6  | Maszyna stanow IDLE → SCAN → TRACK sterowana ramkami z RPi            | VERIFIED   | dispatch_ramke() ekstrakcja mode, przejdz_do() z resetem PID — przetwarzaj_bajt() wywoluje dispatch_ramke po poprawnej checksumie |
| 7  | Skan Lissajous 2D pokrywa obie osie jednoczesnie                       | VERIFIED   | skan_tick(): sin(2*pi*SCAN_FREQ_PAN*t) i sin(2*pi*SCAN_FREQ_TILT*t) — irracjonalny stosunek 0.073/0.05=1.46 (linia 171-172) |

**Score:** 5/7 truths verified automatycznie; 2/7 wymagaja human verification (hardware). Wszystkie truths maja poprawna implementacje logiki.

### Required Artifacts

| Artifact                                              | Oczekiwane                                                          | Status     | Details                                                         |
|-------------------------------------------------------|---------------------------------------------------------------------|------------|-----------------------------------------------------------------|
| `src/arduino/aries_controller/aries_controller.ino`   | Pelny firmware: defines, PID, servo, safe_startup, state machine    | VERIFIED   | 293 linie, kompiluje sie: 38% flash, 16% RAM, exit 0            |

### Key Link Verification

| Od                     | Do                      | Via                                           | Status   | Details                                                               |
|------------------------|-------------------------|-----------------------------------------------|----------|-----------------------------------------------------------------------|
| `setup()`              | `serwo_pan.attach(9)`   | Servo.attach PRZED safe_startup()             | WIRED    | Linia 258: serwo_pan.attach(PAN_PIN) — przed safe_startup() (linia 262) |
| `safe_startup()`       | `serwo_pan.writeMicroseconds` | Rampa 500→1500us w 1000ms               | WIRED    | Linia 214-215: writeMicroseconds w petli 50 krokow                    |
| `przetwarzaj_bajt()`   | `dispatch_ramke()`      | Wywolanie po poprawnej checksumie zamiast echo | WIRED    | Linia 113: dispatch_ramke() w bloku if (obliczona == ramka_buf[7])    |
| `dispatch_ramke()`     | `przejdz_do()`          | Zmiana stanu na podstawie mode z ramki        | WIRED    | Linia 161: przejdz_do(nowy) po walidacji tryb <= 2                    |
| `pid_tick()`           | `ustaw_serwa()`         | Po obliczeniu PID lub skan tick               | WIRED    | Linia 176 (via skan_tick), linia 197 (TRACK bezposrednio)             |
| `loop()`               | `pid_tick()`            | Wywolanie w kazdej iteracji                   | WIRED    | Linia 291: pid_tick() na koncu loop()                                 |

### Data-Flow Trace (Level 4)

Nie dotyczy dla firmware Arduino. Dane plyna: UART → przetwarzaj_bajt() → dispatch_ramke() → stan_systemu/ostatni_blad_x/y → pid_tick() → kat_pan/kat_tilt → ustaw_serwa() → Servo.write(). Lancuch kompletny, bez pustych zmiennych ani hardcodowanych pustych wartosci na trasie.

### Behavioral Spot-Checks

| Zachowanie                             | Komenda                                                                                  | Wynik           | Status  |
|----------------------------------------|------------------------------------------------------------------------------------------|-----------------|---------|
| Firmware kompiluje sie bez bledow      | `arduino-cli compile --fqbn arduino:avr:leonardo src/arduino/aries_controller`           | exit 0, 38% flash | PASS  |
| Serial.write (echo) usuniety           | `grep -c 'Serial.write' aries_controller.ino`                                            | 0               | PASS    |
| dispatch_ramke wywolany z parsera      | `grep -c 'dispatch_ramke()' aries_controller.ino`                                        | 2 (def + call)  | PASS    |
| pid_tick wywolany z loop               | `grep -c 'pid_tick()' aries_controller.ino`                                              | 2 (def + call)  | PASS    |
| Watchdog 500ms obecny                  | `grep -c 'WATCHDOG_TIMEOUT_MS' aries_controller.ino`                                     | 2 (def + use)   | PASS    |
| PID Reset przy zmianie stanu           | `grep -c 'pidPan.Reset' aries_controller.ino`                                            | 2 (SCAN + TRACK) | PASS   |
| Lissajous sin() uzyty                  | `grep 'SCAN_FREQ_PAN' aries_controller.ino \| grep -c 'sin'`                             | 1               | PASS    |
| Ruch serw przy safe_startup (hardware) | Upload + pomiar pradowy                                                                   | -               | SKIP (hardware) |

### Requirements Coverage

| Requirement | Plan zrodlowy | Opis                                                                                   | Status       | Evidence                                                                              |
|-------------|--------------|----------------------------------------------------------------------------------------|--------------|---------------------------------------------------------------------------------------|
| ARD-01      | 20-02        | QuickPID dual-axis (pan + tilt) z anti-windup, deterministyczny loop 100Hz via millis() | SATISFIED    | init_pid(): iAwMode::iAwCondition, SetSampleTimeUs(10000); pid_tick(): millis() throttle |
| ARD-02      | 20-01        | Servo safe startup — plynny ruch do 90/90 przy starcie (nie skok)                       | SATISFIED*   | safe_startup(): rampa 500→1500us, 50 krokow, 20ms delay — *efekt fizyczny: human     |
| ARD-03      | 20-02        | Software watchdog (millis()) — powrot do SCAN gdy brak ramek >500ms                    | SATISFIED    | loop() linia 284-287: WATCHDOG_TIMEOUT_MS=500, przejdz_do(SCAN)                       |
| ARD-04      | 20-01        | Konfigurowalny kierunek serw (PAN_INVERT / TILT_INVERT define)                          | SATISFIED*   | #define PAN_INVERT (1), TILT_INVERT (-1); mnoznik w pid_tick() linia 195-196 — *kalibracja: human |
| ARD-05      | 20-02        | Maszyna stanow: IDLE → SCAN → TRACK z przejsciami sterowanymi ramkami z RPi             | SATISFIED    | dispatch_ramke(), przejdz_do(), enum StanSystemu {IDLE, SCAN, TRACK}, stan_systemu=IDLE w setup() |
| ARD-06      | 20-02        | Skanowanie sinusoidalne w trybie SCAN (autonomiczne, bez ramek z RPi)                   | SATISFIED    | skan_tick(): SCAN_AMP_PAN*sin(2*pi*SCAN_FREQ_PAN*t), SCAN_AMP_TILT*sin(2*pi*SCAN_FREQ_TILT*t) |

*Satisfaid logicznie; weryfikacja fizyczna wymagana.

### Anti-Patterns Found

| Plik                       | Linia | Pattern                          | Powaga  | Uwaga                                                                                                         |
|----------------------------|-------|----------------------------------|---------|---------------------------------------------------------------------------------------------------------------|
| aries_controller.ino       | 42    | SCAN_AMP_PAN=70.0f > PAN_MAX=60.0f | Info  | Amplituda skanowania przekracza limit katowy. Clamp w skan_tick() (linia 174) i ustaw_serwa() (linia 241) obsluguje to poprawnie — defense-in-depth per plan. Efektywna amplituda pan to 60 deg, nie 70 deg. |

Brak blokujacych anti-patternow.

### Human Verification Required

#### 1. Safe startup — brak skoku pradu

**Test:** Upload firmware do Arduino Leonardo. Wlacz zasilanie serw 6V. Zmierz prad zasilacza lub obserwuj zachowanie serw w ciagu pierwszej sekundy.
**Oczekiwane:** Serwa plynnie docieraja do pozycji centralnej (90/90) w ciagu ok. 1 sekundy. Brak gwaltownego szarpniecia, brak brownoutu zasilacza. Czas ruchu: ok. 1000ms.
**Dlaczego human:** Ryzyko fizyczne (brownout, skok pradu). Kod jest logicznie poprawny (rampa 500→1500us, 50 krokow), ale efekt moze byc zweryfikowany tylko empirycznie.

#### 2. Watchdog 500ms i PID tracking

**Test:** Podlacz Arduino przez UART do RPi. Uruchom nadajnik z `src/serial_interface.py`. Wyslij ramke TRACK z bledem x=+80, y=+40. Odczekaj ponad 500ms bez wysylania ramek.
**Oczekiwane:** Serwa reaguja na blad PID (ruch w kierunku korekcji). Po 500ms bez komunikacji serwa przechodza do autonomicznego skanu Lissajous.
**Dlaczego human:** Wymaga hardware: Arduino Leonardo + serwa MG-90S + UART z RPi. Czasy millis() nie moga byc zweryfikowane programowo.

#### 3. Konfigurowalny kierunek serw (ARD-04)

**Test:** Zmien `#define PAN_INVERT (1)` na `(-1)`. Skompiluj, uploaduj. Wyslij ramke TRACK z bledem x=+80. Porownaj kierunek ruchu z oryginalnym PAN_INVERT=(1).
**Oczekiwane:** Kierunek ruchu serwa pan jest odwrocony. Zmiana tylko jednego #define powinna zmienic kierunek bez zadnych innych modyfikacji kodu.
**Dlaczego human:** Kalibracja kierunku serwa wymaga fizycznej obserwacji.

#### 4. Lissajous 2D — wizualna weryfikacja

**Test:** Uruchom firmware w trybie SCAN (wyslij ramke mode=1). Obserwuj ruch obu serw przez minimum 30 sekund.
**Oczekiwane:** Pan i tilt poruszaja sie sinusoidalnie z rozna czestotliwoscia (0.05 Hz vs 0.073 Hz). Trajektoria jest figury Lissajous — nigdy nie powtarza sie identycznie. Zakresy: pan do +-60 deg (clamped z 70 deg AMP), tilt do +-25 deg.
**Dlaczego human:** Wizualna weryfikacja trajektorii Lissajous wymaga obserwacji w czasie rzeczywistym.

### Gaps Summary

Brak blokujacych gap'ow. Caly firmware jest zaimplementowany, kompiluje sie (exit 0, 38% flash, 16% RAM), wszystkie kluczowe polaczenia sa weryfikowane. Cztery wymagania wymagaja empirycznej weryfikacji na hardware (zachowanie typowe dla firmware Arduino — nie mozna zweryfikowac programowo bez sprzetu).

Jedyna uwaga techniczna: SCAN_AMP_PAN=70.0f > PAN_MAX=60.0f. Efektywna amplituda skanowania pan to 60 stopni (nie 70 jak zdefiniowane). Jest to zrozumiale i obslugiwane przez clamp (defense-in-depth per plan), ale warto to potwierdzic podczas hardware testing.

---

_Verified: 2026-03-31T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
