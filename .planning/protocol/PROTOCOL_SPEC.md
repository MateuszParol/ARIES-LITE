# ARIES-LITE Serial Protocol v1.0

**Status:** LOCKED
**Data zatwierdzenia:** 2026-03-30
**Wersja:** 1.0

---

## Ramka — 8 bajtow

Kazda ramka ma stala dlugosc 8 bajtow. Bajty sa numerowane od 0.

| Offset | Nazwa      | Typ    | Kodowanie                    | Zakres           | Opis                                           |
|--------|------------|--------|------------------------------|------------------|------------------------------------------------|
| 0      | `start`    | uint8  | staly `0xAA`                 | `0xAA`           | Marker poczatku ramki — synchronizacja strumienia |
| 1      | `mode`     | uint8  | `0=IDLE, 1=SCAN, 2=TRACK`    | `0..2`           | Aktualny tryb pracy systemu                    |
| 2      | `error_x`  | int16  | little-endian (bajt mlodszy) | `-160..+160 px`  | Blad poziomy — odchylenie srodka twarzy od centrum kadru (os X) |
| 3      | `error_x`  | int16  | little-endian (bajt starszy) | `-160..+160 px`  | Drugi bajt error_x (little-endian)             |
| 4      | `error_y`  | int16  | little-endian (bajt mlodszy) | `-160..+160 px`  | Blad pionowy — odchylenie srodka twarzy od centrum kadru (os Y) |
| 5      | `error_y`  | int16  | little-endian (bajt starszy) | `-160..+160 px`  | Drugi bajt error_y (little-endian)             |
| 6      | `face_size`| uint8  | `percent * 255 / 100`        | `0..255`         | Rozmiar twarzy jako procent kadru przeskalowany do 0-255 |
| 7      | `checksum` | uint8  | XOR bajtow 1-6               | `0..255`         | Suma kontrolna — XOR wszystkich bajtow z wyjatkiem start markera |

---

## Obliczanie checksum

Checksum obliczana jest jako XOR kolejnych bajtow od offsetu 1 do 6 (wlacznie). Bajt 0 (`0xAA`, start marker) **NIE wchodzi** do obliczenia checksumy.

```
checksum = mode XOR error_x_lo XOR error_x_hi XOR error_y_lo XOR error_y_hi XOR face_size
```

Gdzie:
- `error_x_lo` = bajt na offset 2 (mlodszy bajt error_x)
- `error_x_hi` = bajt na offset 3 (starszy bajt error_x)
- `error_y_lo` = bajt na offset 4 (mlodszy bajt error_y)
- `error_y_hi` = bajt na offset 5 (starszy bajt error_y)

---

## Przyklad referencyjny (Python)

Parametry przykladu: `mode=2` (TRACK), `error_x=45`, `error_y=-12`, `face_size=128`.

```python
import struct

def build_frame(mode: int, error_x: int, error_y: int, face_size: int) -> bytes:
    """Buduje 8-bajtowa ramke protokolu ARIES-LITE."""
    # Pakuj payload jako: mode (uint8), error_x (int16 LE), error_y (int16 LE), face_size (uint8)
    payload = struct.pack('<BhhB', mode, error_x, error_y, face_size)
    # Oblicz XOR checksum bajtow payload (bajty 1-6 ramki)
    checksum = 0
    for b in payload:
        checksum ^= b
    # Pelna ramka: start marker + payload + checksum
    return bytes([0xAA]) + payload + bytes([checksum])

# Przyklad
frame = build_frame(mode=2, error_x=45, error_y=-12, face_size=128)
# Oczekiwana ramka:
# Offset 0: 0xAA (start)
# Offset 1: 0x02 (mode=TRACK)
# Offset 2: 0x2D (error_x lo = 45)
# Offset 3: 0x00 (error_x hi = 0)
# Offset 4: 0xF4 (error_y lo = 244, bo -12 w int16 LE = [0xF4, 0xFF])
# Offset 5: 0xFF (error_y hi = 255)
# Offset 6: 0x80 (face_size = 128)
# Offset 7: 0xA4 (checksum = 164 = 0x02^0x2D^0x00^0xF4^0xFF^0x80)
# => [0xAA, 0x02, 0x2D, 0x00, 0xF4, 0xFF, 0x80, 0xA4]
print([hex(b) for b in frame])
# ['0xaa', '0x2', '0x2d', '0x0', '0xf4', '0xff', '0x80', '0xa4']
```

Obliczenie checksum krok po kroku:
- `mode = 0x02`
- `error_x_lo = 0x2D`, `error_x_hi = 0x00`
- `error_y_lo = 0xF4`, `error_y_hi = 0xFF` (bo `-12` w int16 little-endian = `[0xF4, 0xFF]`)
- `face_size = 0x80`
- `checksum = 0x02 ^ 0x2D ^ 0x00 ^ 0xF4 ^ 0xFF ^ 0x80 = 0xA4 (164)`

---

## Przyklad referencyjny (Arduino C)

```cpp
// Odbiorca — parsowanie ramki po stronie Arduino Leonardo
uint8_t buf[8];

// Oczekiwanie na start marker i odczyt calej ramki
void parse_frame(uint8_t *buf) {
    uint8_t mode      = buf[1];
    // Little-endian int16: bajt mlodszy + (bajt starszy << 8)
    int16_t error_x   = (int16_t)(buf[2] | (buf[3] << 8));
    int16_t error_y   = (int16_t)(buf[4] | (buf[5] << 8));
    uint8_t face_size = buf[6];
    uint8_t checksum  = buf[7];

    // Weryfikacja checksum
    uint8_t calc = buf[1] ^ buf[2] ^ buf[3] ^ buf[4] ^ buf[5] ^ buf[6];
    if (calc != checksum) {
        // Blad checksumy — odrzuc ramke
        return;
    }

    // Uzyj wartosci
    // error_x, error_y -> wejscie PID (w pikselach, zakres -160..+160)
    // face_size -> opcjonalnie (zoom, distance estimation)
}

// Petla nasluchiwania
void loop() {
    if (Serial.available() >= 8) {
        if (Serial.peek() == 0xAA) {
            Serial.readBytes(buf, 8);
            parse_frame(buf);
        } else {
            Serial.read();  // Wyrzuc nieznany bajt, synchronizuj
        }
    }
}
```

---

## Tryby pracy

| Wartosc (uint8) | Nazwa  | Opis                                                              |
|-----------------|--------|-------------------------------------------------------------------|
| `0`             | `IDLE` | Brak akcji — serwomechanizmy nieruchome, PID zatrzymany           |
| `1`             | `SCAN` | Skanowanie sinusoidalne — autonomiczne poszukiwanie twarzy        |
| `2`             | `TRACK`| Sledzenie twarzy — PID dual-axis aktywny, serwomechanizmy koryguja|

---

## Parametry transmisji

| Parametr      | Wartosc           | Opis                                              |
|---------------|-------------------|---------------------------------------------------|
| Baudrate      | `115200`          | Zgodne z arduino-cli default i Serial.begin()     |
| Format        | `8N1`             | 8 bitow danych, brak parzystosci, 1 bit stopu     |
| DTR           | `False`           | Wylaczony reset DTR — Leonardo nie resetuje sie przy polaczeniu (Caterina bootloader) |
| Port (RPi)    | `/dev/ttyACM0`    | USB CDC — Arduino Leonardo jako Virtual COM Port  |
| Kierunek      | RPi → Arduino     | Jednostronny: RPi nadaje, Arduino odbiera i steruje serwami |

---

*Specyfikacja zamknieta: 2026-03-30. Zmiany wymagaja aktualizacji wersji protokolu.*
