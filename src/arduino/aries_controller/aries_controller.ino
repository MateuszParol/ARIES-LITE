// aries_controller.ino — Firmware ARIES-LITE v2.1
// Architektura rozproszona: Arduino Uno R4 WiFi (Renesas RA4M1)
// Fazy 19-23: parser serial, PID dual-axis, HMI, klasy OOP
// Faza 25: integracja RTC DS1307 — ZegarRTC, Wire->RTC kolejnosc, bootscreen z czasem
// Faza 26: DataLogger CSV na karcie SD — rotacja dobowa, ring buffer 50 wpisow, benchmark
// Faza 27: integracja DataLogger z MaszynaStanow — logowanie zmian stanow, face_size, latency_ms, komenda 'D'

#include <math.h>            // asin(), M_PI — phase-offset continuity (D-05, D-06)
#include <Wire.h>            // I2C master — magistrala dla DS1307 (A4/A5)
#include <RTClib.h>          // Adafruit RTClib 2.1.4 — DS1307 (D-16)
#include <SD.h>              // Zapis CSV na karte SD via SPI (D10-D13)
#include <QuickPID.h>       // PID z anti-windup (QuickPID 3.1.9)
#include <Servo.h>           // sterowanie serwami MG-90S
#include <LiquidCrystal.h>   // LCD 1602 w trybie 4-bit

#define SD_CS_PIN       10  // Chip Select karty SD na DataLogger Shield V1.0

// --- Stale protokolu ---
#define FRAME_SIZE    8       // Stala dlugosc ramki 8 bajtow per PROTOCOL_SPEC.md
#define START_MARKER  0xAA   // Marker poczatku ramki

// --- Konfiguracja PID (D-02) ---
#define KP              2.0f      // Wspolczynnik proporcjonalny
#define KI              0.1f      // Wspolczynnik calkowitowy
#define KD              0.5f      // Wspolczynnik roznicowy
#define OUTPUT_LIMIT    3.0f      // +/-3 stopni/tick — redukcja agresji PID (D-01, TRK-01)
#define PID_INTERVAL_MS 10        // 100 Hz — D-03

// --- Konfiguracja serw (D-02, D-10) ---
#define PAN_PIN         6         // D6 — serwo pan (per D-02)
#define TILT_PIN        9         // D9 — serwo tilt (per D-02)
#define PAN_MIN         (-60.0f)  // limit katowy pan
#define PAN_MAX         (60.0f)
#define TILT_MIN        (-30.0f)  // limit katowy tilt
#define TILT_MAX        (30.0f)

// --- Kierunek serw — empiryczna kalibracja (D-04, D-12) ---
#define PAN_INVERT      (1)       // +1 skalibrowany empirycznie R4 WiFi v2.1.1
#define TILT_INVERT     (-1)      // -1 skalibrowany empirycznie R4 WiFi v2.1.1

// --- Normalizacja bledu (D-01) ---
#define POLOWA_RAMKI    160.0f    // polowa szerokosci klatki 320px

// --- Watchdog (D-07) ---
#define WATCHDOG_TIMEOUT_MS 500   // 500ms bez ramek → SKANOWANIE

// --- Skan Lissajous (D-09, D-10, D-11) ---
#define SCAN_FREQ_PAN   0.05f    // Hz — czestotliwosc pan
#define SCAN_FREQ_TILT  0.073f   // Hz — irracjonalny stosunek (D-11)
#define SCAN_AMP_PAN    70.0f    // stopnie — D-10
#define SCAN_AMP_TILT   25.0f    // stopnie — D-10

// --- HMI: LCD 1602 (D-01: piny A0,A1,D2-D5) ---
#define LCD_RS          A0        // RS=A0 (per D-01)
#define LCD_EN          A1        // E=A1 (per D-01)
#define LCD_D4          2         // D4=D2 (per D-01)
#define LCD_D5          3         // D5=D3 (per D-01)
#define LCD_D6          4         // D6=D4 (per D-01)
#define LCD_D7_PIN      5         // D7=D5 (per D-01)
#define LCD_INTERVAL_MS 200  // 5 Hz odswiezanie (D-02, HMI-01)

// --- HMI: Buzzer + Przycisk (D-05, D-07) ---
#define BUZZER_PIN      8     // D8 — bez zmian (per D-03)
#define PRZYCISK_PIN    7     // D7 — INPUT_PULLUP, abort SLEDZENIE (D-07)
#define DEBOUNCE_MS     20    // debounce przycisku (D-08)

// --- Spolonizowany enum stanu parsera ---
enum StanParsera {
    CZEKAJ_START,  // Oczekiwanie na bajt 0xAA
    CZYTAJ_PAYLOAD // Zbieranie pozostalych 7 bajtow ramki
};

// --- Spolonizowany enum stanu systemu (D-06) ---
// Wartosci explicite — cast z trybu ramki (uint8) musi dzialac (Pitfall 2)
enum StanSystemu {
    BEZCZYNNOSC = 0,  // Spoczynek — Arduino czeka na polecenie z RPi
    SKANOWANIE  = 1,  // Autonomiczny skan Lissajous
    SLEDZENIE   = 2   // Sledzenie twarzy przez PID
};

// ============================================================
// class HMI — Interfejs czlowiek-maszyna (LCD, buzzer, przycisk)
// Nie zalezy od ServoPID ani MaszynaStanow.
// ============================================================
class HMI {
public:
    // Konstruktor — inicjalizacja pol z lista inicjalizacyjna
    HMI() : _lcd(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7_PIN),
             _czas_ostatniego_lcd(0),
             _przycisk_ostatni_stan(HIGH),
             _przycisk_czas_zmiany(0) {}

    // Inicjalizacja HMI — LCD bootscreen + konfiguracja pinow
    void inicjalizuj() {
        lcd_begin();
        lcd_bootscreen();
        pinMode(BUZZER_PIN, OUTPUT);
        pinMode(PRZYCISK_PIN, INPUT_PULLUP);
    }

    // Odswiezanie LCD co LCD_INTERVAL_MS — wiersz 0: tryb+katy, wiersz 1: bledy X/Y
    // setCursor + overwrite zamiast lcd.clear() — brak migotania (Pitfall 3)
    // snprintf z int cast — ARM Renesas RA4M1 nie obsluguje AVR-only float konwersji (D-07)
    void lcd_krok(StanSystemu stan, float kat_pan, float kat_tilt,
                  int16_t blad_x, int16_t blad_y) {
        unsigned long teraz = millis();
        if (teraz - _czas_ostatniego_lcd < LCD_INTERVAL_MS) return;
        _czas_ostatniego_lcd = teraz;

        // Wiersz 0: tryb (5 znakow) + katy pan/tilt
        _lcd.setCursor(0, 0);
        const char* tryb_str;
        switch (stan) {
            case SLEDZENIE:    tryb_str = "SLEDZ"; break;
            case SKANOWANIE:   tryb_str = "SKAN "; break;
            default:           tryb_str = "BEZCZ"; break;
        }
        char pan_buf[5], tilt_buf[5];
        snprintf(pan_buf,  sizeof(pan_buf),  "%4d", (int)kat_pan);   // np. "  12" lub " -60"
        snprintf(tilt_buf, sizeof(tilt_buf), "%4d", (int)kat_tilt);
        char linia0[17];
        snprintf(linia0, sizeof(linia0), "%sP:%-4sT:%-4s", tryb_str, pan_buf, tilt_buf);
        _lcd.print(linia0);

        // Wiersz 1: bledy X/Y z ostatniej ramki
        _lcd.setCursor(0, 1);
        char linia1[17];
        snprintf(linia1, sizeof(linia1), "Bx:%-5dBy:%-5d", (int)blad_x, (int)blad_y);
        _lcd.print(linia1);
    }

    // Obsluga przycisku abort — debounce millis() (D-08)
    // Aktywny TYLKO w trybie SLEDZENIE — przerywa sledzenie (D-07, HMI-03)
    // INPUT_PULLUP: LOW = wcisniety, HIGH = nie wcisniety (Pitfall 6)
    // Zwraca true gdy przycisk wcisniety i abort wymagany — loop wywoluje przejscie
    bool przycisk_krok(StanSystemu stan) {
        if (stan != SLEDZENIE) return false;  // D-07: ignoruj poza SLEDZENIE

        bool aktualny = digitalRead(PRZYCISK_PIN);
        if (aktualny != _przycisk_ostatni_stan) {
            _przycisk_czas_zmiany = millis();
        }
        bool abort_wymagany = false;
        // Zbocze stabilne przez DEBOUNCE_MS i przycisk wcisniety (LOW)
        if ((millis() - _przycisk_czas_zmiany >= DEBOUNCE_MS) &&
            aktualny == LOW && _przycisk_ostatni_stan == HIGH) {
            abort_wymagany = true;  // Zglos abort — loop wywola wymus_skanowanie()
        }
        _przycisk_ostatni_stan = aktualny;
        return abort_wymagany;
    }

    // Krotki sygnał dzwiekowy — "Target Lock" przy przejsciu do SLEDZENIE (HMI-02)
    void buzzer_beep() {
        tone(BUZZER_PIN, 1000, 100);  // 1kHz, 100ms
    }

    // Aktualizacja bootscreen z czasem RTC (D-04)
    // Wywolywana po udanej inicjalizacji ZegarRTC
    void bootscreen_z_czasem(DateTime t) {
        char buf[17];
        snprintf(buf, sizeof(buf), "v2.1  %02d:%02d:%02d",
                 t.hour(), t.minute(), t.second());
        _lcd.setCursor(0, 0);
        _lcd.print(buf);
        _lcd.setCursor(0, 1);
        _lcd.print("RTC OK          ");
        delay(1500);  // Czas na przeczytanie — lacznie z bootscreen ~2s
    }

    // Ostrzezenie RTC — RTC niedostepny (HYBRID: ostrzezenie + kontynuacja)
    // LCD: "RTC: FAIL" przez ~2s + krotki alarm buzzer
    // System kontynuuje startup normalnie po zakonczeniu tej metody
    void rtc_ostrzezenie() {
        _lcd.clear();
        _lcd.setCursor(0, 0);
        _lcd.print("RTC: FAIL       ");
        _lcd.setCursor(0, 1);
        _lcd.print("Brak zegara RTC ");
        // Krotki alarm buzzer — 3x beep (nie ciagly ton!)
        for (uint8_t i = 0; i < 3; i++) {
            tone(BUZZER_PIN, 2000, 150);  // 2kHz, 150ms
            delay(250);
        }
        delay(1000);  // Lacznie ~1.75s na ekranie FAIL — czas na przeczytanie
    }

    // Ostrzezenie SD — karta SD niedostepna (HYBRID: ostrzezenie + kontynuacja)
    // LCD: "SD: FAIL" przez ~1.5s + krotki alarm buzzer
    void sd_ostrzezenie() {
        _lcd.clear();
        _lcd.setCursor(0, 0);
        _lcd.print("SD: FAIL        ");
        _lcd.setCursor(0, 1);
        _lcd.print("Brak karty SD   ");
        tone(BUZZER_PIN, 1500, 200);  // 1.5kHz, 200ms — krotszy niz RTC fail
        delay(1500);
    }

private:
    LiquidCrystal _lcd;
    unsigned long _czas_ostatniego_lcd;
    bool _przycisk_ostatni_stan;
    unsigned long _przycisk_czas_zmiany;

    // Uruchomienie LCD
    void lcd_begin() {
        _lcd.begin(16, 2);
        _lcd.clear();
    }

    // Bootscreen LCD przed inicjalizacja serw — uzytkownik widzi status (D-03)
    void lcd_bootscreen() {
        _lcd.setCursor(0, 0);
        _lcd.print("ARIES-LITE v2.1");
        _lcd.setCursor(0, 1);
        _lcd.print("Inicjalizacja...");
        delay(500);  // skrocone z 2000ms — reszta czasu na ekranie z czasem RTC
    }
};

// ============================================================
// class ServoPID — Sterowanie serwami z regulatorem PID dual-axis
// Nie zalezy od HMI.
// ============================================================
class ServoPID {
public:
    // Publiczne pola odczytywane przez MaszynaStanow i HMI
    float kat_pan;
    float kat_tilt;
    int16_t ostatni_blad_x;
    int16_t ostatni_blad_y;

    // Konstruktor — inicjalizacja przez liste inicjalizacyjna
    // KLUCZOWE per Pitfall 4: QuickPID przyjmuje wskazniki do pol klasy.
    // Obiekt globalny — wskazniki stabilne przez caly czas zycia programu.
    ServoPID() :
        kat_pan(0.0f), kat_tilt(0.0f),
        ostatni_blad_x(0), ostatni_blad_y(0),
        _pan_wejscie(0.0f), _pan_wyjscie(0.0f), _pan_setpoint(0.0f),
        _tilt_wejscie(0.0f), _tilt_wyjscie(0.0f), _tilt_setpoint(0.0f),
        _pid_pan(&_pan_wejscie, &_pan_wyjscie, &_pan_setpoint, KP, KI, KD, QuickPID::Action::direct),
        _pid_tilt(&_tilt_wejscie, &_tilt_wyjscie, &_tilt_setpoint, KP, KI, KD, QuickPID::Action::direct),
        _czas_ostatniego_pid(0), _czas_startowy_skanu(0) {}

    // Inicjalizacja: attach serw + bezpieczny start + parametry PID
    void inicjalizuj() {
        _serwo_pan.attach(PAN_PIN);
        _serwo_tilt.attach(TILT_PIN);
        _bezpieczny_start();
        _inicjalizuj_pid_parametry();
        _czas_startowy_skanu = millis();
    }

    // Petla PID 100 Hz z millis() throttle (D-03)
    // SLEDZENIE: PID, SKANOWANIE: skan Lissajous, BEZCZYNNOSC: brak akcji
    void pid_krok(StanSystemu stan) {
        unsigned long teraz = millis();
        if (teraz - _czas_ostatniego_pid < PID_INTERVAL_MS) return;
        _czas_ostatniego_pid = teraz;

        if (stan == SLEDZENIE) {
            // D-01: normalizacja bledu — piksel / polowa_ramki
            _pan_wejscie  = (float)ostatni_blad_x / POLOWA_RAMKI;
            _tilt_wejscie = (float)ostatni_blad_y / POLOWA_RAMKI;

            _pid_pan.Compute();
            _pid_tilt.Compute();

            // Zastosuj kierunek (D-12: PAN_INVERT / TILT_INVERT) + clamp
            kat_pan  = constrain(kat_pan  + PAN_INVERT  * _pan_wyjscie,  PAN_MIN,  PAN_MAX);
            kat_tilt = constrain(kat_tilt + TILT_INVERT * _tilt_wyjscie, TILT_MIN, TILT_MAX);
            ustaw_serwa();
        } else if (stan == SKANOWANIE) {
            skan_krok(teraz);
        }
        // BEZCZYNNOSC: nic nie rob — serwa nieruchome
    }

    // Skan sinusoidalny Lissajous 2D — autonomiczne skanowanie (D-09)
    // f_pan=0.05 Hz, f_tilt=0.073 Hz — irracjonalny stosunek (D-11)
    // PAN=70 deg, TILT=25 deg (D-10)
    // Phase-offset continuity: t + _t_offset_pan/tilt zapewnia plynna kontynuacje z aktualnej pozycji (D-05, D-06)
    void skan_krok(unsigned long teraz) {
        float t = (teraz - _czas_startowy_skanu) / 1000.0f;  // sekundy
        kat_pan  = SCAN_AMP_PAN  * sin(2.0f * (float)M_PI * SCAN_FREQ_PAN  * (t + _t_offset_pan));
        kat_tilt = SCAN_AMP_TILT * sin(2.0f * (float)M_PI * SCAN_FREQ_TILT * (t + _t_offset_tilt));
        // Clamp dla bezpieczenstwa (obrona w glab)
        kat_pan  = constrain(kat_pan,  PAN_MIN,  PAN_MAX);
        kat_tilt = constrain(kat_tilt, TILT_MIN, TILT_MAX);
        ustaw_serwa();
    }

    // Konwersja kat (-60..+60 / -30..+30) na Servo.write(0-180)
    // Centrum serwa = 90 stopni = pozycja 0 w naszym ukladzie
    void ustaw_serwa() {
        kat_pan  = constrain(kat_pan,  PAN_MIN,  PAN_MAX);
        kat_tilt = constrain(kat_tilt, TILT_MIN, TILT_MAX);
        _serwo_pan.write((int)(kat_pan  + 90.0f));
        _serwo_tilt.write((int)(kat_tilt + 90.0f));
    }

    // Reset regulatora PID — integrator i historia pochodnej
    void pid_reset() {
        _pid_pan.Reset();
        _pid_tilt.Reset();
    }

    // Reset czasu skanu z phase-offset continuity (D-05, D-06, D-07)
    // Oblicza t_offset z aktualnej pozycji serwa przez arcsin — eliminacja skoku przy SLEDZENIE→SKANOWANIE
    // asin() zwraca [-pi/2, +pi/2] — pozycyjnie poprawne, moze odwrocic kierunek predkosci (RESEARCH.md)
    // constrain ratio do [-1,1] zapobiega NaN (Pitfall 1 z RESEARCH.md)
    void resetuj_czas_skanu(float aktualny_pan, float aktualny_tilt) {
        _czas_startowy_skanu = millis();
        float ratio_pan  = constrain(aktualny_pan  / SCAN_AMP_PAN,  -1.0f, 1.0f);
        float ratio_tilt = constrain(aktualny_tilt / SCAN_AMP_TILT, -1.0f, 1.0f);
        _t_offset_pan  = asin(ratio_pan)  / (2.0f * (float)M_PI * SCAN_FREQ_PAN);
        _t_offset_tilt = asin(ratio_tilt) / (2.0f * (float)M_PI * SCAN_FREQ_TILT);
    }

private:
    Servo _serwo_pan;
    Servo _serwo_tilt;

    // Zmienne PID — QuickPID wymaga float* (Pitfall 4: pola, nie lokalne)
    float _pan_wejscie, _pan_wyjscie, _pan_setpoint;
    float _tilt_wejscie, _tilt_wyjscie, _tilt_setpoint;
    QuickPID _pid_pan;
    QuickPID _pid_tilt;

    // Liczniki czasu
    unsigned long _czas_ostatniego_pid;
    unsigned long _czas_startowy_skanu;
    // Phase-offset continuity — offsety fazowe dla plynnej kontynuacji skanu (D-05, D-06)
    float _t_offset_pan  = 0.0f;   // sekundy — offset fazowy pan
    float _t_offset_tilt = 0.0f;   // sekundy — offset fazowy tilt

    // Bezpieczny startup — lagodna rampa writeMicroseconds() 1400→1500us w 1000ms
    // Start blisko centrum — brak szarpniecia serw (D-04)
    void _bezpieczny_start() {
        const int US_MIN    = 1400;   // blisko centrum — lagodny start
        const int US_CENTER = 1500;   // centrum = 90 stopni
        const int KROKI     = 20;     // 20 krokow
        const int OPOZNIENIE_MS = 50; // wolne kroki

        for (int i = 0; i <= KROKI; i++) {
            int us = US_MIN + (int)((long)(US_CENTER - US_MIN) * i / KROKI);
            _serwo_pan.writeMicroseconds(us);
            _serwo_tilt.writeMicroseconds(us);
            delay(OPOZNIENIE_MS);
        }
        kat_pan  = 0.0f;
        kat_tilt = 0.0f;
    }

    // Konfiguracja QuickPID dual-axis (D-02, D-03)
    void _inicjalizuj_pid_parametry() {
        _pid_pan.SetSampleTimeUs(10000);   // 100 Hz
        _pid_tilt.SetSampleTimeUs(10000);
        _pid_pan.SetOutputLimits(-OUTPUT_LIMIT, OUTPUT_LIMIT);
        _pid_tilt.SetOutputLimits(-OUTPUT_LIMIT, OUTPUT_LIMIT);
        _pid_pan.SetAntiWindupMode(QuickPID::iAwMode::iAwCondition);
        _pid_tilt.SetAntiWindupMode(QuickPID::iAwMode::iAwCondition);
        _pid_pan.SetProportionalMode(QuickPID::pMode::pOnError);
        _pid_tilt.SetProportionalMode(QuickPID::pMode::pOnError);
        _pid_pan.SetDerivativeMode(QuickPID::dMode::dOnMeas);
        _pid_tilt.SetDerivativeMode(QuickPID::dMode::dOnMeas);
        _pid_pan.SetMode(QuickPID::Control::automatic);
        _pid_tilt.SetMode(QuickPID::Control::automatic);
    }
};

// ============================================================
// class ZegarRTC — Obsluga zegara DS1307 via I2C (D-10)
// Adapter RTClib z polskim interfejsem.
// Wire.begin() MUSI byc wywolane PRZED inicjalizuj() (D-15).
// ============================================================
class ZegarRTC {
public:
    ZegarRTC() : _dostepny(false) {}

    // Inicjalizacja DS1307 — Wire.begin() musi byc wczesniej (D-15)
    // Zwraca false jesli RTC nie odpowiada LUB rok < 2025 (D-07)
    // Przy pierwszym uruchomieniu (oscylator nie biegnie) ustawia czas kompilacji
    bool inicjalizuj() {
        if (!_rtc.begin()) {
            _dostepny = false;
            return false;
        }
        // Ustaw czas kompilacji TYLKO gdy oscylator nie biegnie (swiezutka bateria)
        // Pitfall 4: NIE bezwarunkowo — nadpisaloby czas przy kazdym resecie
        if (!_rtc.isrunning()) {
            _rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
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

// ============================================================
// class DataLogger — Zapis telemetrii CSV na karte SD z RTC timestamps (Faza 26)
// Rotacja dobowa LYYMMDD.CSV (FAT 8.3), ring buffer 50 wpisow, graceful degradation.
// Zalezy od ZegarRTC (referencja) — Wire+RTC+SD kolejnosc inicjalizacji (INT-07).
// ============================================================
class DataLogger {
public:
    // Konstruktor z referencja do ZegarRTC — logger nie inicjalizuje Wire/RTC samodzielnie
    DataLogger(ZegarRTC& zegar) :
        _zegar(zegar), _sd_ok(false),
        _licznik_klatek(0), _wpisy_od_flush(0), _ostatni_dzien(0),
        _idx_diagnostyczny(0) {
        memset(_bufor_diagnostyczny, 0, sizeof(_bufor_diagnostyczny));
    }

    // Inicjalizacja SD — wywolac PO Wire.begin() i zegar.inicjalizuj() (INT-07)
    // Bez RTC logging wymagalby millis() timestamps — mniej uzyteczne (Claude's Discretion)
    // Benchmark LOG-05: micros() wokol pierwszego file.print() — wynik na Serial
    bool inicjalizuj() {
        if (!SD.begin(SD_CS_PIN)) {
            Serial.println(F("SD fail"));
            _sd_ok = false;
            return false;
        }
        // Bez poprawnego RTC timestamps sa bezuzyteczne — wylacz logowanie
        if (!_zegar.czy_dostepny()) {
            Serial.println(F("[SD] Brak RTC — logowanie wymagajace timestamps wylaczone."));
            _sd_ok = false;
            return false;
        }
        _sd_ok = true;
        _otworz_plik_dnia();

        // Benchmark latencji zapisu (LOG-05) — micros() wokol file.print()
        unsigned long t0 = micros();
        _plik.print(F("TEST,0,0,0,0,0,0,0\n"));
        unsigned long t1 = micros();
        char bench_buf[32];
        snprintf(bench_buf, sizeof(bench_buf), "[BENCH] SD write: %lu us", (unsigned long)(t1 - t0));
        Serial.println(bench_buf);
        _plik.flush();  // Upewniamy sie, ze benchmark i naglowek sa zapisane

        return true;
    }

    // Krok logowania — wywolywac z loop() po HMI tick
    // Loguje TYLKO w stanie SLEDZENIE (D-08), co 10 klatek (D-06, LOG-01)
    void krok(StanSystemu stan, float pan, float tilt,
              int16_t bx, int16_t by, uint8_t fs, uint16_t latency_ms) {
        if (!_sd_ok) return;
        if (stan != SLEDZENIE) {
            _licznik_klatek = 0;  // Reset licznika przy wyjsciu z SLEDZENIE
            return;
        }
        if (++_licznik_klatek < 10) return;  // Throttle — co 10 klatek
        _licznik_klatek = 0;

        _sprawdz_rotacje();
        _zapisz_csv(stan, pan, tilt, bx, by, fs, latency_ms);
    }

    // Getter dostepnosci SD — uzywane przez HMI lub diagnostyke
    bool czy_dostepne() const {
        return _sd_ok;
    }

    // Logowanie zmiany stanu — wywolywane z MaszynaStanow::_przejdz_do()
    // Natychmiastowy flush — zdarzenie krytyczne, rzadkie (nie degraduje PID)
    // Ten sam format CSV co _zapisz_csv() per D-05 — prosty parsing pandas
    void loguj_zmiane_stanu(StanSystemu stary, StanSystemu nowy,
                            float pan, float tilt) {
        if (!_sd_ok || !_plik) return;
        _sprawdz_rotacje();
        DateTime teraz = _zegar.odczytaj_czas();
        char linia[64];
        snprintf(linia, sizeof(linia), "%lu,%d,%d,%d,0,0,0,0",
                 (unsigned long)teraz.unixtime(),
                 (int)nowy, (int)pan, (int)tilt);
        _plik.println(linia);
        _plik.flush();          // natychmiastowy flush — zdarzenie krytyczne
        _wpisy_od_flush = 0;    // reset licznika bufora
        // Kopiuj do bufora diagnostycznego
        strncpy(_bufor_diagnostyczny[_idx_diagnostyczny % 10], linia, 63);
        _bufor_diagnostyczny[_idx_diagnostyczny % 10][63] = '\0';
        _idx_diagnostyczny++;
        (void)stary;  // unikamy warning unused — stary stan moze byc uzyteczny pozniej
    }

    // Zrzut 10 ostatnich wpisow na Serial — diagnostyka bez wyjmowania karty SD (D-06)
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

private:
    ZegarRTC& _zegar;
    File _plik;
    bool _sd_ok;
    uint8_t _licznik_klatek;
    uint8_t _wpisy_od_flush;
    uint8_t _ostatni_dzien;
    char _bufor_diagnostyczny[10][64];  // krazacy bufor 10 ostatnich wpisow (640B RAM)
    uint8_t _idx_diagnostyczny;         // wskaznik zapisu do bufora krazacego

    // Otworz (lub stworz) plik dnia LYYMMDD.CSV (D-11: FAT 8.3)
    // Jesli plik nowy (size==0): zapisz naglowek CSV (D-05)
    void _otworz_plik_dnia() {
        if (!_zegar.czy_dostepny()) return;
        DateTime teraz = _zegar.odczytaj_czas();
        char nazwa[13];
        snprintf(nazwa, sizeof(nazwa), "L%02d%02d%02d.CSV",
                 (int)(teraz.year() % 100), (int)teraz.month(), (int)teraz.day());
        if (_plik) {
            _plik.flush();
            _plik.close();
        }
        _plik = SD.open(nazwa, FILE_WRITE);
        if (_plik && _plik.size() == 0) {
            // Nowy plik — zapisz naglowek per D-02/D-05
            _plik.println(F("timestamp,stan,pan,tilt,error_x,error_y,face_size,latency_ms"));
            _plik.flush();
        }
        _ostatni_dzien = teraz.day();
    }

    // Zapisz wiersz CSV do otwartego pliku (D-01, D-03, D-04)
    // snprintf z %d i int cast — ARM Renesas RA4M1, bez float formatting (D-03)
    // Flush co 50 wpisow — ring buffer per D-07/LOG-03
    void _zapisz_csv(StanSystemu stan, float pan, float tilt,
                     int16_t bx, int16_t by, uint8_t fs, uint16_t latency_ms) {
        if (!_sd_ok || !_plik) return;
        DateTime teraz = _zegar.odczytaj_czas();
        char linia[64];
        snprintf(linia, sizeof(linia), "%lu,%d,%d,%d,%d,%d,%d,%d",
                 (unsigned long)teraz.unixtime(),
                 (int)stan, (int)pan, (int)tilt,
                 (int)bx, (int)by, (int)fs, (int)latency_ms);
        _plik.println(linia);
        // Kopiuj do bufora diagnostycznego
        strncpy(_bufor_diagnostyczny[_idx_diagnostyczny % 10], linia, 63);
        _bufor_diagnostyczny[_idx_diagnostyczny % 10][63] = '\0';
        _idx_diagnostyczny++;
        if (++_wpisy_od_flush >= 50) {
            _plik.flush();
            _wpisy_od_flush = 0;
        }
    }

    // Sprawdz rotacje dobowa — jesli dzien sie zmienil, otworz nowy plik (LOG-02)
    void _sprawdz_rotacje() {
        if (!_zegar.czy_dostepny()) return;
        DateTime teraz = _zegar.odczytaj_czas();
        if (teraz.day() != _ostatni_dzien) {
            _otworz_plik_dnia();
        }
    }
};

// ============================================================
// class MaszynaStanow — Parser ramek i przejscia miedzy stanami
// Zalezy od ServoPID, HMI i DataLogger (referencje).
// ============================================================
class MaszynaStanow {
public:
    // Publiczne pole face_size — wypelniane z bajtu 6 ramki 8B (INT-06)
    uint8_t ostatni_face_size;

    // Konstruktor przyjmuje referencje do istniejacych instancji globalnych
    MaszynaStanow(ServoPID& serwa, HMI& hmi, DataLogger& logger) :
        _serwa(serwa), _hmi(hmi), _logger(logger),
        _stan_systemu(BEZCZYNNOSC),
        ostatni_face_size(0),
        _ramka_idx(0), _stan_parsera(CZEKAJ_START),
        _czas_ostatniej_ramki(0) {}

    // Przetwarzanie bajtu z Serial — parser state-machine (non-blocking)
    // Po zebraniu pelnej ramki (8B) weryfikuje checksum XOR bajtow 1-6.
    // Poprawna checksum: wywoluje _przetworz_ramke().
    // Bledna checksum lub nieoczekiwany bajt: cichy drop + resync do CZEKAJ_START.
    void przetwarzaj_bajt(uint8_t bajt) {
        switch (_stan_parsera) {

            case CZEKAJ_START:
                // Czekaj na marker poczatku ramki 0xAA
                if (bajt == START_MARKER) {
                    _ramka_buf[0] = bajt;
                    _ramka_idx = 1;
                    _stan_parsera = CZYTAJ_PAYLOAD;
                }
                // Inny bajt: cichy drop, resync (D-03) — brak akcji
                break;

            case CZYTAJ_PAYLOAD:
                // Zbieraj kolejne bajty do bufora
                _ramka_buf[_ramka_idx++] = bajt;

                if (_ramka_idx == FRAME_SIZE) {
                    // Zebrano pelna ramke — weryfikuj checksum XOR bajtow 1-6
                    uint8_t obliczona = 0;
                    for (uint8_t i = 1; i <= 6; i++) {
                        obliczona ^= _ramka_buf[i];
                    }

                    if (obliczona == _ramka_buf[7]) {
                        // Checksum poprawna — dispatch do maszyny stanow
                        _przetworz_ramke();
                    }
                    // Bledna checksum: cichy drop (D-03) — RPi wykrywa timeout

                    // Resync do stanu poczatkowego
                    _ramka_idx = 0;
                    _stan_parsera = CZEKAJ_START;
                }
                break;

            default:
                // Nieznany stan — resync
                _ramka_idx = 0;
                _stan_parsera = CZEKAJ_START;
                break;
        }
    }

    // Watchdog millis() (D-07) — po 500ms bez ramek → SKANOWANIE
    // Wywolywany z loop() co iteracje
    void watchdog_krok() {
        if (_stan_systemu != BEZCZYNNOSC && _stan_systemu != SKANOWANIE) {
            if (millis() - _czas_ostatniej_ramki > WATCHDOG_TIMEOUT_MS) {
                _przejdz_do(SKANOWANIE);
            }
        }
    }

    // Wymuszone przejscie do SKANOWANIE — uzywane przez abort przycisku
    void wymus_skanowanie() {
        _przejdz_do(SKANOWANIE);
    }

    // Getter aktualnego stanu — uzywany przez loop() do pid_krok() i lcd_krok()
    StanSystemu stan() const {
        return _stan_systemu;
    }

    // Getter czasu ostatniej ramki — do ewentualnego debugowania
    unsigned long czas_ostatniej_ramki() const {
        return _czas_ostatniej_ramki;
    }

private:
    ServoPID& _serwa;
    HMI& _hmi;
    DataLogger& _logger;  // Referencja do loggera — INT-06: logowanie zmian stanow
    StanSystemu _stan_systemu;
    uint8_t _ramka_buf[FRAME_SIZE];
    uint8_t _ramka_idx;
    StanParsera _stan_parsera;
    unsigned long _czas_ostatniej_ramki;

    // Ekstrakcja pol z ramki i dispatch do maszyny stanow (D-08: bezposredni)
    // Resetuje watchdog po poprawnej checksumie (nie w przetwarzaj_bajt — Pitfall 5)
    void _przetworz_ramke() {
        uint8_t tryb   = _ramka_buf[1];
        int16_t blad_x = (int16_t)(_ramka_buf[2] | (_ramka_buf[3] << 8));
        int16_t blad_y = (int16_t)(_ramka_buf[4] | (_ramka_buf[5] << 8));
        ostatni_face_size = _ramka_buf[6];  // Ekstrakcja face_size z bajtu 6 ramki 8B (INT-06)

        _czas_ostatniej_ramki = millis();  // reset watchdog (D-07, Pitfall 5)

        _serwa.ostatni_blad_x = blad_x;
        _serwa.ostatni_blad_y = blad_y;

        // Bezposredni dispatch — mode z ramki ustawia stan (D-08)
        if (tryb <= 2) {  // walidacja zakresu trybu: 0=BEZCZYNNOSC, 1=SKANOWANIE, 2=SLEDZENIE
            StanSystemu nowy = (StanSystemu)tryb;
            if (nowy != _stan_systemu) {
                _przejdz_do(nowy);
            }
        }
    }

    // Przejscie do nowego stanu z resetem PID i scan timer oraz logowaniem (INT-06)
    void _przejdz_do(StanSystemu nowy) {
        if (nowy == _stan_systemu) return;  // Guard — nie loguj ponownie tego samego stanu (Pitfall 2)
        StanSystemu stary = _stan_systemu;
        _stan_systemu = nowy;
        _logger.loguj_zmiane_stanu(stary, nowy, _serwa.kat_pan, _serwa.kat_tilt);  // INT-06: logowanie zmiany stanu
        if (nowy == SKANOWANIE) {
            _serwa.resetuj_czas_skanu(_serwa.kat_pan, _serwa.kat_tilt);  // phase-offset continuity (D-05, D-06)
            _serwa.pid_reset();           // reset integratora PID
        } else if (nowy == SLEDZENIE) {
            _hmi.buzzer_beep();           // sygnał "Target Lock" (HMI-02)
            _serwa.pid_reset();           // reset PID przy wejsciu w SLEDZENIE
        }
        // BEZCZYNNOSC: nic dodatkowego
    }
};

// ============================================================
// Globalne instancje — kolejnosc wazna (DataLogger PRZED MaszynaStanow — referencja)
// ============================================================
ZegarRTC zegar;
ServoPID serwa;
HMI hmi;
DataLogger logger(zegar);              // PRZED maszyna — referencja musi byc wazna (Pitfall 1)
MaszynaStanow maszyna(serwa, hmi, logger);  // Nowy parametr: DataLogger& (INT-06)

// ============================================================
// setup() — inicjalizacja sprzetu
// ============================================================
void setup() {
    Serial.begin(115200);  // baudrate per PROTOCOL_SPEC.md

    // R4 WiFi: USB przez ESP32-S3 bridge — max 500ms wait
    // (zachowac timeout — nie blokujacy, dziala na obu platformach)
    uint32_t start = millis();
    while (!Serial && millis() - start < 500) {
        delay(10);
    }

    // Jawny pinMode dla pinow analogowych LCD (RS=A0, E=A1) — per D-11
    // DAC domyslnie wylaczony na R4, ale explicit OUTPUT zapobiega nieoczekiwanemu zachowaniu
    pinMode(A0, OUTPUT);
    pinMode(A1, OUTPUT);

    // Inicjalizacja HMI: LCD bootscreen + piny buzzer/przycisk
    hmi.inicjalizuj();

    // I2C + RTC po bootscreen (D-14: kolejnosc Wire -> RTC)
    Wire.begin();  // D-15: Wire PRZED rtc.begin()
    if (!zegar.inicjalizuj()) {
        // HYBRID: ostrzezenie + kontynuacja — system startuje BEZ RTC
        Serial.println("[RTC] OSTRZEZENIE: RTC niedostepny lub czas niepoprawny!");
        Serial.println("[RTC] System kontynuuje bez timestampow RTC.");
        hmi.rtc_ostrzezenie();  // LCD "RTC: FAIL" + 3x beep, potem wraca
    } else {
        // RTC OK — wyswietl czas na bootscreen (D-04)
        DateTime teraz = zegar.odczytaj_czas();
        hmi.bootscreen_z_czasem(teraz);

        // Serial debug — timestamp RTC (RTC-03: interfejs gotowy dla Phase 26)
        Serial.print("[RTC] ");
        Serial.print(teraz.year()); Serial.print('-');
        Serial.print(teraz.month()); Serial.print('-');
        Serial.print(teraz.day()); Serial.print(' ');
        Serial.print(teraz.hour()); Serial.print(':');
        Serial.print(teraz.minute()); Serial.print(':');
        Serial.println(teraz.second());
    }

    // Inicjalizacja SD — po RTC, przed serwami (INT-07 kolejnosc: Wire->RTC->SD)
    if (!logger.inicjalizuj()) {
        Serial.println(F("[SD] OSTRZEZENIE: Karta SD niedostepna!"));
        Serial.println(F("[SD] System kontynuuje bez logowania telemetrii."));
        hmi.sd_ostrzezenie();  // LCD "SD: FAIL" + buzzer, potem wraca
    } else {
        Serial.println(F("[SD] Karta SD zainicjalizowana pomyslnie."));
    }

    // Soft Start 500ms — stabilizacja napiecia zasilacza 6V PRZED ruchem serw (MIG-08, D-05)
    delay(500);

    // Inicjalizacja serw: attach + bezpieczny start (rampa 1000ms) + parametry PID
    // maszyna juz zainicjalizowana jako global z referencjami do serwa i hmi
    serwa.inicjalizuj();
}

// ============================================================
// loop() — glowna petla sterowania (nieblokujaca)
// ============================================================
void loop() {
    // --- Parser serial (zachowany z Phase 19) ---
    while (Serial.available() > 0) {
        uint8_t bajt = (uint8_t)Serial.read();
        if (bajt == 'D') {
            logger.zrzuc_ostatnie();  // Zrzut diagnostyczny (D-06)
        } else {
            maszyna.przetwarzaj_bajt(bajt);
        }
    }

    // --- Watchdog millis() (D-07) ---
    maszyna.watchdog_krok();

    // --- PID / skan krok (D-03) ---
    serwa.pid_krok(maszyna.stan());

    // --- LCD odswiezanie (HMI-01) ---
    hmi.lcd_krok(maszyna.stan(), serwa.kat_pan, serwa.kat_tilt,
                 serwa.ostatni_blad_x, serwa.ostatni_blad_y);

    // --- Przycisk abort (HMI-03) ---
    // przycisk_krok() zwraca true gdy wcisniety w trybie SLEDZENIE
    if (hmi.przycisk_krok(maszyna.stan())) {
        maszyna.wymus_skanowanie();  // Abort SLEDZENIE → SKANOWANIE
    }

    // --- Logowanie telemetrii (LOG-01, co 10 klatek w SLEDZENIE) ---
    uint16_t latency_ms = (uint16_t)(millis() - maszyna.czas_ostatniej_ramki());  // D-04: czas od ostatniej ramki
    logger.krok(maszyna.stan(), serwa.kat_pan, serwa.kat_tilt,
                serwa.ostatni_blad_x, serwa.ostatni_blad_y,
                maszyna.ostatni_face_size,  // D-03: face_size z bajtu 6 ramki 8B
                latency_ms);               // D-04: latency od ostatniej ramki RPi
}
