#!/usr/bin/env python3
"""Skrypt weryfikacji echo serial link RPi-Arduino.

Wysyla referencyjny TRACK frame, porownuje echo bajt po bajcie.
Raportuje PASS/FAIL + hex dump (D-07, D-09). Exit code 0/1.
"""

import sys
import time
from pathlib import Path

import serial

# Dodaj katalog projektu do sys.path — umozliwia import src.vision.serial_interface
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vision.serial_interface import SerialInterface  # noqa: E402

# Parametry portu
PORT = "/dev/ttyACM0"
TIMEOUT = 2.0
FRAME_SIZE = 8

# Referencyjny TRACK frame z PROTOCOL_SPEC.md (D-08)
# mode=2, error_x=45, error_y=-12, face_size=128
OCZEKIWANA = bytes([0xAA, 0x02, 0x2D, 0x00, 0xF4, 0xFF, 0x80, 0xA4])


def main() -> int:
    """Wysyla referencyjny TRACK frame, czyta echo i porownuje bajt po bajcie.

    Returns:
        0 — echo zgodne z wyslana ramka (PASS).
        1 — echo niezgodne, timeout lub blad portu (FAIL).
    """
    iface = SerialInterface(port=PORT, timeout=TIMEOUT)

    try:
        iface.open()

        # Czekaj na gotowoscc Arduino USB CDC (Pitfall 1 — Leonardo boot delay)
        time.sleep(2.0)

        # Wyczysc bufor wejsciowy przed testem — zapobiega desynchronizacji (Pitfall 3)
        iface._ser.reset_input_buffer()

        # Wyslij referencyjny TRACK frame (D-08)
        iface.send_frame(mode=2, error_x=45, error_y=-12, face_size=128)

        # Wydrukuj wyslana ramke w formacie hex (D-09)
        print(f"sent=[{' '.join(f'{b:02X}' for b in OCZEKIWANA)}]")

        # Odczytaj echo z timeoutem — Arduino powinien odeslac identyczna ramke
        odebrano = iface._ser.read(FRAME_SIZE)

        # Formatuj odebrane bajty lub komunikat o braku odpowiedzi
        hex_recv = (
            ' '.join(f'{b:02X}' for b in odebrano)
            if odebrano
            else '(brak odpowiedzi)'
        )
        print(f"recv=[{hex_recv}]")

        # Porownaj bajt po bajcie i zwroc wynik
        if odebrano == OCZEKIWANA:
            print("PASS")
            return 0
        else:
            print("FAIL")
            return 1

    except serial.SerialException as e:
        print(f"BLAD PORTU: {e}")
        return 1

    finally:
        iface.close()


if __name__ == "__main__":
    sys.exit(main())
