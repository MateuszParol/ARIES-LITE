// aries_controller.ino — Firmware ARIES-LITE v2.0
// Architektura rozproszona: Arduino Leonardo (PID + HMI)
// Fazy 19-23: parser serial, PID dual-axis, HMI, klasy OOP

#include <QuickPID.h>       // PID z anti-windup (QuickPID 3.1.9)
#include <Servo.h>           // sterowanie serwami MG-90S
#include <LiquidCrystal.h>   // LCD 1602 w trybie 4-bit

// --- Stale protokolu ---
#define FRAME_SIZE    8       // Stala dlugosc ramki 8 bajtow per PROTOCOL_SPEC.md
#define START_MARKER  0xAA   // Marker poczatku ramki

// --- Konfiguracja PID (D-02) ---
#define KP              2.0f      // Wspolczynnik proporcjonalny
#define KI              0.1f      // Wspolczynnik calkowitowy
#define KD              0.5f      // Wspolczynnik roznicowy
#define OUTPUT_LIMIT    5.0f      // +/-5 stopni/tick — D-02
#define PID_INTERVAL_MS 10        // 100 Hz — D-03

// --- Konfiguracja serw (D-05, D-10) ---
#define PAN_PIN         9         // D9 = TIMER1A
#define TILT_PIN        10        // D10 = TIMER1B
#define PAN_MIN         (-60.0f)  // limit katowy pan
#define PAN_MAX         (60.0f)
#define TILT_MIN        (-30.0f)  // limit katowy tilt
#define TILT_MAX        (30.0f)

// --- Kierunek serw — empiryczna kalibracja (D-04, D-12) ---
#define PAN_INVERT      (1)       // +1 lub -1 — zmien empirycznie
#define TILT_INVERT     (-1)      // -1 potwierdzony w v1.7 legacy

// --- Normalizacja bledu (D-01) ---
#define POLOWA_RAMKI    160.0f    // polowa szerokosci klatki 320px

// --- Watchdog (D-07) ---
#define WATCHDOG_TIMEOUT_MS 500   // 500ms bez ramek → SKANOWANIE

// --- Skan Lissajous (D-09, D-10, D-11) ---
#define SCAN_FREQ_PAN   0.05f    // Hz — czestotliwosc pan
#define SCAN_FREQ_TILT  0.073f   // Hz — irracjonalny stosunek (D-11)
#define SCAN_AMP_PAN    70.0f    // stopnie — D-10
#define SCAN_AMP_TILT   25.0f    // stopnie — D-10

// --- HMI: LCD 1602 (D-04: piny 2,3,4,5,6,11) ---
#define LCD_RS          2
#define LCD_EN          3
#define LCD_D4          4
#define LCD_D5          5
#define LCD_D6          6
#define LCD_D7_PIN     11    // D7_PIN aby unikac konfliktu nazwy
#define LCD_INTERVAL_MS 200  // 5 Hz odswiezanie (D-02, HMI-01)

// --- HMI: Buzzer + Przycisk (D-05, D-07) ---
#define BUZZER_PIN      8     // D8 — tone() uzywa Timer3 na Leonardo (D-06)
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
    // dtostrf() zamiast sprintf("%f") — AVR nie obsluguje %f (Pitfall 1)
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
        dtostrf(kat_pan,  4, 0, pan_buf);   // np. " +12" lub " -60"
        dtostrf(kat_tilt, 4, 0, tilt_buf);
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
        _lcd.print("ARIES-LITE v2.0");
        _lcd.setCursor(0, 1);
        _lcd.print("Inicjalizacja...");
        delay(2000);
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
    void skan_krok(unsigned long teraz) {
        float t = (teraz - _czas_startowy_skanu) / 1000.0f;  // sekundy
        kat_pan  = SCAN_AMP_PAN  * sin(2.0f * M_PI * SCAN_FREQ_PAN  * t);
        kat_tilt = SCAN_AMP_TILT * sin(2.0f * M_PI * SCAN_FREQ_TILT * t);
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

    // Reset czasu skanu — wywolywany przy przejsciu do SKANOWANIE
    void resetuj_czas_skanu() {
        _czas_startowy_skanu = millis();
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

    // Bezpieczny startup — rampa writeMicroseconds() 500→1500us w 1000ms
    // Minimalne obciazenie zasilacza 6V, brak skoku pradu (D-04)
    void _bezpieczny_start() {
        const int US_MIN    = 500;    // minimalny impuls
        const int US_CENTER = 1500;   // centrum = 90 stopni
        const int KROKI     = 50;     // 1000ms / 20ms = 50 krokow
        const int OPOZNIENIE_MS = 20;

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
// class MaszynaStanow — Parser ramek i przejscia miedzy stanami
// Zalezy od ServoPID i HMI (referencje).
// ============================================================
class MaszynaStanow {
public:
    // Konstruktor przyjmuje referencje do istniejacych instancji globalnych
    MaszynaStanow(ServoPID& serwa, HMI& hmi) :
        _serwa(serwa), _hmi(hmi),
        _stan_systemu(BEZCZYNNOSC),
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
        // _ramka_buf[6] = face_size — zarezerwowane

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

    // Przejscie do nowego stanu z resetem PID i scan timer
    void _przejdz_do(StanSystemu nowy) {
        _stan_systemu = nowy;
        if (nowy == SKANOWANIE) {
            _serwa.resetuj_czas_skanu();  // reset czasu skanu
            _serwa.pid_reset();           // reset integratora PID
        } else if (nowy == SLEDZENIE) {
            _hmi.buzzer_beep();           // sygnał "Target Lock" (HMI-02)
            _serwa.pid_reset();           // reset PID przy wejsciu w SLEDZENIE
        }
        // BEZCZYNNOSC: nic dodatkowego
    }
};

// ============================================================
// Globalne instancje — kolejnosc wazna (ServoPID i HMI przed MaszynaStanow)
// ============================================================
ServoPID serwa;
HMI hmi;
MaszynaStanow maszyna(serwa, hmi);

// ============================================================
// setup() — inicjalizacja sprzetu
// ============================================================
void setup() {
    Serial.begin(115200);  // baudrate per PROTOCOL_SPEC.md

    // Leonardo USB CDC — czekaj az host otworzy port, max 3 sekundy
    // (bez timeoutu Leonardo zawiesza sie na while(!Serial))
    uint32_t start = millis();
    while (!Serial && millis() - start < 3000) {
        delay(10);
    }

    // Inicjalizacja HMI: LCD bootscreen + piny buzzer/przycisk
    hmi.inicjalizuj();

    // Inicjalizacja serw: attach + bezpieczny start + parametry PID
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
        maszyna.przetwarzaj_bajt(bajt);
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
}
