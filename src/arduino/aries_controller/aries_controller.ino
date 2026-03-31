// aries_controller.ino — parser state-machine + echo
// Faza 19: serial link — odbior ramki 8B i echo identycznej ramki
// Implementacja PID, serw, LCD, HMI w fazach 20-22

#include <QuickPID.h>       // PID z anti-windup (QuickPID 3.1.9)
#include <Servo.h>           // sterowanie serwami MG-90S
#include <LiquidCrystal.h>   // LCD 1602 w trybie 4-bit

// --- Stale protokolu ---
#define FRAME_SIZE    8       // Stala dlugosc ramki 8 bajtow per PROTOCOL_SPEC.md
#define START_MARKER  0xAA   // Marker poczatku ramki

// --- Stan parsera ---
enum StanParsera {
    WAIT_START,   // Oczekiwanie na bajt 0xAA
    READ_PAYLOAD  // Zbieranie pozostalych 7 bajtow ramki
};

// --- Zmienne globalne parsera ---
uint8_t ramka_buf[FRAME_SIZE];  // Bufor zebranej ramki
uint8_t ramka_idx = 0;          // Aktualny indeks w buforze
StanParsera stan_parsera = WAIT_START;  // Stan startowy: czekaj na marker

// --- Funkcja parsera bajt po bajcie ---
// Przetwarza pojedynczy bajt odebrany z Serial.
// Non-blocking — wywolywana z loop() dla kazdego dostepnego bajtu.
// Po zebraniu pelnej ramki (8B) weryfikuje checksum XOR bajtow 1-6.
// Poprawna checksum: echo identycznej ramki (Serial.write).
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
                    // Checksum poprawna — echo identycznej ramki 8B (D-02)
                    Serial.write(ramka_buf, FRAME_SIZE);
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

void setup() {
    Serial.begin(115200);  // baudrate per PROTOCOL_SPEC.md

    // Leonardo USB CDC — czekaj az host otworzy port, max 3 sekundy
    // (Pitfall 4: bez timeoutu Leonardo zawiesza sie na while(!Serial))
    uint32_t start = millis();
    while (!Serial && millis() - start < 3000) {
        delay(10);
    }
}

void loop() {
    // Przetworz wszystkie dostepne bajty — non-blocking, bajt po bajcie
    while (Serial.available() > 0) {
        uint8_t bajt = (uint8_t)Serial.read();
        przetwarzaj_bajt(bajt);
    }
}
