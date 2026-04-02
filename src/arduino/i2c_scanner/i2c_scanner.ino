// i2c_scanner.ino — Diagnostyka I2C dla ARIES-LITE v2.1
// Skanuje magistrale I2C (A4/A5) i wypisuje znalezione adresy.
// Oczekiwany wynik: DS1307 pod adresem 0x68 (DataLogger Shield)

#include <Wire.h>

void setup() {
    Serial.begin(115200);
    uint32_t start = millis();
    while (!Serial && millis() - start < 500) { delay(10); }

    Wire.begin();  // I2C master — BEZ argumentu (Pitfall 5: Wire.begin(addr) = slave!)
    Serial.println("=== ARIES-LITE I2C Scanner ===");
    Serial.println("Skanowanie adresow 0x01 - 0x7F...");

    uint8_t znalezione = 0;
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        uint8_t wynik = Wire.endTransmission();
        if (wynik == 0) {
            Serial.print("I2C znaleziony: 0x");
            if (addr < 16) Serial.print("0");
            Serial.println(addr, HEX);
            znalezione++;
        }
    }

    Serial.print("Znalezione urzadzenia: ");
    Serial.println(znalezione);

    if (znalezione == 0) {
        Serial.println("BLAD: Brak urzadzen I2C! Sprawdz osadzenie DataLogger Shield.");
    }
    Serial.println("Skan zakonczony.");
}

void loop() {}
