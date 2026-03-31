// aries_controller.ino — parser state-machine + echo
// Faza 19: serial link — odbior ramki 8B i echo identycznej ramki
// Faza 20: fundament sterowania — PID dual-axis, safe startup, maszyna stanow
// Faza 22: HMI — LCD 1602, buzzer, przycisk

#include <QuickPID.h>       // PID z anti-windup (QuickPID 3.1.9)
#include <Servo.h>           // sterowanie serwami MG-90S
#include <LiquidCrystal.h>   // LCD 1602 w trybie 4-bit

// --- Stale protokolu ---
#define FRAME_SIZE    8       // Stala dlugosc ramki 8 bajtow per PROTOCOL_SPEC.md
#define START_MARKER  0xAA   // Marker poczatku ramki

// --- Konfiguracja PID (D-02) ---
#define KP              2.0f      // Proporcjonalny gain
#define KI              0.1f      // Calkowitowy gain
#define KD              0.5f      // Roznicowy gain
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
#define HALF_FRAME_W    160.0f    // polowa szerokosci klatki 320px

// --- Watchdog (D-07) ---
#define WATCHDOG_TIMEOUT_MS 500   // 500ms bez ramek → SCAN

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

// --- Stan parsera ---
enum StanParsera {
    WAIT_START,   // Oczekiwanie na bajt 0xAA
    READ_PAYLOAD  // Zbieranie pozostalych 7 bajtow ramki
};

// --- Stan systemu (D-06) ---
enum StanSystemu { IDLE, SCAN, TRACK };

// --- Zmienne globalne parsera ---
uint8_t ramka_buf[FRAME_SIZE];  // Bufor zebranej ramki
uint8_t ramka_idx = 0;          // Aktualny indeks w buforze
StanParsera stan_parsera = WAIT_START;  // Stan startowy: czekaj na marker

// --- LCD 1602 (4-bit) ---
LiquidCrystal lcd(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7_PIN);
unsigned long czas_ostatniego_lcd = 0;

// --- Instancje Servo ---
Servo serwo_pan;
Servo serwo_tilt;

// --- Zmienne PID (QuickPID wymaga float*) ---
float pan_wej = 0.0f, pan_wyj = 0.0f, pan_sp = 0.0f;
float tilt_wej = 0.0f, tilt_wyj = 0.0f, tilt_sp = 0.0f;
QuickPID pidPan(&pan_wej, &pan_wyj, &pan_sp, KP, KI, KD, QuickPID::Action::direct);
QuickPID pidTilt(&tilt_wej, &tilt_wyj, &tilt_sp, KP, KI, KD, QuickPID::Action::direct);

// --- Stan systemu ---
StanSystemu stan_systemu = IDLE;   // D-06: startowy IDLE
float kat_pan  = 0.0f;             // aktualny kat pan (-60..+60)
float kat_tilt = 0.0f;             // aktualny kat tilt (-30..+30)
int16_t ostatni_blad_x = 0;        // ostatni blad X z ramki
int16_t ostatni_blad_y = 0;        // ostatni blad Y z ramki

// --- Timing ---
unsigned long czas_ostatniej_ramki = 0;  // watchdog timer
unsigned long czas_ostatniego_pid  = 0;  // PID tick timer
unsigned long czas_startowy_skanu  = 0;  // czas wejscia w SCAN

// --- Funkcja parsera bajt po bajcie ---
// Przetwarza pojedynczy bajt odebrany z Serial.
// Non-blocking — wywolywana z loop() dla kazdego dostepnego bajtu.
// Po zebraniu pelnej ramki (8B) weryfikuje checksum XOR bajtow 1-6.
// Poprawna checksum: dispatch do maszyny stanow (dispatch_ramke).
// Bledna checksum lub nieoczekiwany bajt: cichy drop + resync do WAIT_START.
void przetwarzaj_bajt(uint8_t bajt) {
    switch (stan_parsera) {

        case WAIT_START:
            // Czekaj na marker poczatku ramki 0xAA
            if (bajt == START_MARKER) {
                ramka_buf[0] = bajt;
                ramka_idx = 1;
                stan_parsera = READ_PAYLOAD;
            }
            // Inny bajt: cichy drop, resync (D-03) — brak akcji
            break;

        case READ_PAYLOAD:
            // Zbieraj kolejne bajty do bufora
            ramka_buf[ramka_idx++] = bajt;

            if (ramka_idx == FRAME_SIZE) {
                // Zebrano pelna ramke — weryfikuj checksum XOR bajtow 1-6
                uint8_t obliczona = 0;
                for (uint8_t i = 1; i <= 6; i++) {
                    obliczona ^= ramka_buf[i];
                }

                if (obliczona == ramka_buf[7]) {
                    // Checksum poprawna — dispatch do maszyny stanow (Phase 20)
                    dispatch_ramke();
                }
                // Bledna checksum: cichy drop (D-03) — brak echo, RPi wykrywa timeout

                // Resync do stanu poczatkowego
                ramka_idx = 0;
                stan_parsera = WAIT_START;
            }
            break;

        default:
            // Nieznany stan — resync
            ramka_idx = 0;
            stan_parsera = WAIT_START;
            break;
    }
}

// Przejscie do nowego stanu z resetem PID i scan timer
void przejdz_do(StanSystemu nowy_stan) {
    stan_systemu = nowy_stan;
    if (nowy_stan == SCAN) {
        czas_startowy_skanu = millis();  // reset czasu skanu
        pidPan.Reset();                   // reset integratora PID
        pidTilt.Reset();
    } else if (nowy_stan == TRACK) {
        pidPan.Reset();                   // reset PID przy wejsciu w TRACK
        pidTilt.Reset();
    }
    // IDLE: nic dodatkowego
}

// Ekstrakcja pol z ramki i dispatch do maszyny stanow (D-08: bezposredni)
void dispatch_ramke() {
    uint8_t tryb     = ramka_buf[1];
    int16_t blad_x   = (int16_t)(ramka_buf[2] | (ramka_buf[3] << 8));
    int16_t blad_y   = (int16_t)(ramka_buf[4] | (ramka_buf[5] << 8));
    // ramka_buf[6] = face_size — zarezerwowane na Phase 23

    czas_ostatniej_ramki = millis();  // reset watchdog (D-07, Pitfall 5)

    ostatni_blad_x = blad_x;
    ostatni_blad_y = blad_y;

    // Bezposredni dispatch — mode z ramki ustawia stan (D-08)
    if (tryb <= 2) {  // walidacja zakresu mode: 0=IDLE, 1=SCAN, 2=TRACK
        StanSystemu nowy = (StanSystemu)tryb;
        if (nowy != stan_systemu) {
            przejdz_do(nowy);
        }
    }
}

// Skan sinusoidalny Lissajous 2D — autonomiczne skanowanie (D-09)
// f_pan=0.05 Hz, f_tilt=0.073 Hz — irracjonalny stosunek (D-11)
// PAN=70 deg, TILT=25 deg (D-10)
void skan_tick(unsigned long teraz) {
    float t = (teraz - czas_startowy_skanu) / 1000.0f;  // sekundy
    kat_pan  = SCAN_AMP_PAN  * sin(2.0f * M_PI * SCAN_FREQ_PAN  * t);
    kat_tilt = SCAN_AMP_TILT * sin(2.0f * M_PI * SCAN_FREQ_TILT * t);
    // Clamp dla bezpieczenstwa (powinien byc zbedny przy AMP < MAX, ale defense-in-depth)
    kat_pan  = constrain(kat_pan,  PAN_MIN,  PAN_MAX);
    kat_tilt = constrain(kat_tilt, TILT_MIN, TILT_MAX);
    ustaw_serwa();
}

// Petla PID 100 Hz z millis() throttle (D-03)
// Normalizacja bledu error_px / 160.0f → -1.0..+1.0 (D-01)
void pid_tick() {
    unsigned long teraz = millis();
    if (teraz - czas_ostatniego_pid < PID_INTERVAL_MS) return;
    czas_ostatniego_pid = teraz;

    if (stan_systemu == TRACK) {
        // D-01: normalizacja bledu — piksel / polowa_ramki
        pan_wej  = (float)ostatni_blad_x / HALF_FRAME_W;
        tilt_wej = (float)ostatni_blad_y / HALF_FRAME_W;

        pidPan.Compute();
        pidTilt.Compute();

        // Zastosuj kierunek (D-12: PAN_INVERT / TILT_INVERT) + clamp
        kat_pan  = constrain(kat_pan  + PAN_INVERT  * pan_wyj,  PAN_MIN,  PAN_MAX);
        kat_tilt = constrain(kat_tilt + TILT_INVERT * tilt_wyj, TILT_MIN, TILT_MAX);
        ustaw_serwa();
    } else if (stan_systemu == SCAN) {
        skan_tick(teraz);
    }
    // IDLE: nic nie rob — serwa nieruchome
}

// Bezpieczny startup — rampa writeMicroseconds() 500→1500us w 1000ms
// Minimalne obciazenie zasilacza 6V, brak skoku pradu (D-04)
void safe_startup() {
    const int US_MIN    = 500;    // minimalny impuls
    const int US_CENTER = 1500;   // centrum = 90 stopni
    const int KROKI     = 50;     // 1000ms / 20ms = 50 krokow
    const int OPOZNIENIE_MS = 20;

    for (int i = 0; i <= KROKI; i++) {
        int us = US_MIN + (int)((long)(US_CENTER - US_MIN) * i / KROKI);
        serwo_pan.writeMicroseconds(us);
        serwo_tilt.writeMicroseconds(us);
        delay(OPOZNIENIE_MS);
    }
    kat_pan  = 0.0f;
    kat_tilt = 0.0f;
}

// Konfiguracja QuickPID dual-axis (D-02, D-03)
void init_pid() {
    pidPan.SetSampleTimeUs(10000);   // 100 Hz
    pidTilt.SetSampleTimeUs(10000);
    pidPan.SetOutputLimits(-OUTPUT_LIMIT, OUTPUT_LIMIT);
    pidTilt.SetOutputLimits(-OUTPUT_LIMIT, OUTPUT_LIMIT);
    pidPan.SetAntiWindupMode(QuickPID::iAwMode::iAwCondition);
    pidTilt.SetAntiWindupMode(QuickPID::iAwMode::iAwCondition);
    pidPan.SetProportionalMode(QuickPID::pMode::pOnError);
    pidTilt.SetProportionalMode(QuickPID::pMode::pOnError);
    pidPan.SetDerivativeMode(QuickPID::dMode::dOnMeas);
    pidTilt.SetDerivativeMode(QuickPID::dMode::dOnMeas);
    pidPan.SetMode(QuickPID::Control::automatic);
    pidTilt.SetMode(QuickPID::Control::automatic);
}

// Konwersja kat (-60..+60 / -30..+30) na Servo.write(0-180)
// Centrum serwa = 90 stopni = pozycja 0 w naszym ukladzie
void ustaw_serwa() {
    kat_pan  = constrain(kat_pan,  PAN_MIN,  PAN_MAX);
    kat_tilt = constrain(kat_tilt, TILT_MIN, TILT_MAX);
    serwo_pan.write((int)(kat_pan  + 90.0f));
    serwo_tilt.write((int)(kat_tilt + 90.0f));
}

// Odswiezanie LCD co 200ms — Row 0: tryb + katy, Row 1: bledy X/Y
// setCursor + overwrite zamiast LCD.clear() — brak migotania (Pitfall 3)
// dtostrf() zamiast sprintf("%f") — AVR nie obsluguje %f (Pitfall 1)
void lcd_tick() {
    unsigned long teraz = millis();
    if (teraz - czas_ostatniego_lcd < LCD_INTERVAL_MS) return;
    czas_ostatniego_lcd = teraz;

    // Row 0: tryb (5 znakow) + katy pan/tilt
    lcd.setCursor(0, 0);
    const char* tryb_str;
    switch (stan_systemu) {
        case TRACK: tryb_str = "SLEDZ"; break;
        case SCAN:  tryb_str = "SKAN "; break;
        default:    tryb_str = "IDLE "; break;
    }
    char pan_buf[5], tilt_buf[5];
    dtostrf(kat_pan,  4, 0, pan_buf);    // np. " +12" lub " -60"
    dtostrf(kat_tilt, 4, 0, tilt_buf);
    char linia0[17];
    snprintf(linia0, sizeof(linia0), "%sP:%-4sT:%-4s", tryb_str, pan_buf, tilt_buf);
    lcd.print(linia0);

    // Row 1: bledy X/Y z ostatniej ramki
    lcd.setCursor(0, 1);
    char linia1[17];
    snprintf(linia1, sizeof(linia1), "Bx:%-5dBy:%-5d", (int)ostatni_blad_x, (int)ostatni_blad_y);
    lcd.print(linia1);
}

void setup() {
    Serial.begin(115200);  // baudrate per PROTOCOL_SPEC.md

    // Leonardo USB CDC — czekaj az host otworzy port, max 3 sekundy
    // (Pitfall 4: bez timeoutu Leonardo zawiesza sie na while(!Serial))
    uint32_t start = millis();
    while (!Serial && millis() - start < 3000) {
        delay(10);
    }

    // --- LCD bootscreen (HMI-04, D-03) ---
    lcd.begin(16, 2);
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("ARIES-LITE v2.0");
    lcd.setCursor(0, 1);
    lcd.print("Inicjalizacja...");
    delay(2000);

    // Podlacz serwa do pinow PWM — attach PRZED safe_startup() (D-05, Pitfall 1)
    serwo_pan.attach(PAN_PIN);
    serwo_tilt.attach(TILT_PIN);

    // Bezpieczny startup — rampa do pozycji centralnej 90/90 (D-04)
    safe_startup();

    // Inicjalizacja kontrolerow PID (D-02, D-03)
    init_pid();

    // Inicjalizacja timerow
    czas_ostatniej_ramki = millis();
    czas_startowy_skanu  = millis();

    // Stan startowy — Arduino czeka na pierwsza ramke z RPi (D-06)
    stan_systemu = IDLE;
}

void loop() {
    // --- Parser serial (zachowany z Phase 19) ---
    while (Serial.available() > 0) {
        uint8_t bajt = (uint8_t)Serial.read();
        przetwarzaj_bajt(bajt);
    }

    // --- Watchdog millis() (D-07) ---
    // Po 500ms bez poprawnej ramki → autonomiczny powrot do SCAN
    if (stan_systemu != IDLE && stan_systemu != SCAN) {
        if (millis() - czas_ostatniej_ramki > WATCHDOG_TIMEOUT_MS) {
            przejdz_do(SCAN);
        }
    }

    // --- PID / skan tick (D-03) ---
    pid_tick();

    // --- LCD odswiezanie (HMI-01) ---
    lcd_tick();
}
