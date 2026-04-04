#!/usr/bin/env python3
"""Deterministyczny skrypt kalibracji kierunkow serw ARIES-LITE v2.0.

Wysyla 4 sekwencje testowe (PAN prawo, PAN lewo, TILT dol, TILT gora)
przez SerialInterface i pyta uzytkownika o potwierdzenie kierunku ruchu
per krok. Raportuje PASS/FAIL dla kazdego kroku i dla calej kalibracji.

Cel: Weryfikacja ze PAN_INVERT i TILT_INVERT w firmware Arduino sa poprawne
(montaz standardowy: pan+=prawo, tilt+=dol). Jezeli krok FAIL — zmien
#define PAN_INVERT / TILT_INVERT w src/arduino/aries_controller/aries_controller.ino,
rekompiluj i wgraj firmware, a nastepnie powtorz kalibracje.

Wymaga: Arduino Uno R4 WiFi z firmware v2.1+, polaczone przez USB Serial.
"""

import sys
import time
from pathlib import Path

# Dodaj katalog projektu do sys.path — umozliwia import src.vision
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vision.serial_interface import SerialInterface  # noqa: E402

# --- Stale modulowe ---
PORT = "/dev/ttyACM0"          # Domyslny port Arduino Uno R4 WiFi na RPi
TIMEOUT = 2.0                   # Timeout odczytu TX w sekundach
OPOZNIENIE_BOOT = 5.0          # R4 WiFi boot delay: LCD bootscreen 500ms + Soft Start rampa 1000ms + CDC enum ~500ms + DataLogger/RTC init + margines
CZAS_TESTU_S = 3.0             # Czas wysylania ramek w kazdym kroku kalibracji
OPOZNIENIE_TX = 0.05           # 50ms = 20 Hz — utrzymuje Arduino w trybie TRACK, watchdog (500ms) nie odpali
TRYB_TRACK = 2                  # MODE_TRACK per PROTOCOL_SPEC.md


def wysylaj_petla(
    iface: SerialInterface, error_x: int, error_y: int, czas_s: float
) -> None:
    """Wysyla ramki TRACK w petli 20 Hz przez czas_s sekund.

    Wysylanie w petli (nie jednorazowe) jest kluczowe — watchdog Arduino
    odpala sie gdy brak ramki przez >500ms i resetuje stan do SCAN
    (Pitfall 1 z Research). Petla 20 Hz (50ms) zapewnia ze watchdog
    nie odpali sie podczas calego kroku kalibracji.

    Args:
        iface: Otwarty interfejs szeregowy do wysylania ramek.
        error_x: Blad poziomy do wyslania (int16, -160..+160 px).
        error_y: Blad pionowy do wyslania (int16, -120..+120 px).
        czas_s: Czas wysylania ramek w sekundach.
    """
    koniec = time.monotonic() + czas_s
    while time.monotonic() < koniec:
        iface.send_frame(mode=TRYB_TRACK, error_x=error_x, error_y=error_y, face_size=128)
        time.sleep(OPOZNIENIE_TX)


def krok_kalibracji(
    iface: SerialInterface, numer: int, opis: str, oczekiwany: str,
    error_x: int, error_y: int
) -> None:
    """Wykonuje pojedynczy krok kalibracji — wysyla ramki i czeka na obserwacje.

    Tryb nieinteraktywny: nie pyta o wynik, uzytkownik raportuje po zakonczeniu.
    """
    print(f"\n=== KROK {numer}: {opis} ===")
    print(f"Oczekiwany ruch: {oczekiwany}")
    print(f"Wysylam ramki TRACK error_x={error_x}, error_y={error_y} przez {CZAS_TESTU_S}s...")
    wysylaj_petla(iface, error_x=error_x, error_y=error_y, czas_s=CZAS_TESTU_S)
    print(f"--- KROK {numer} ZAKONCZONY --- Obserwuj ruch serwa.\n")


def main() -> int:
    """Przeprowadza 4-krokowa kalibracje kierunkow serw.

    Tryb nieinteraktywny: wysyla wszystkie 4 sekwencje testowe z 3s przerwa
    miedzy krokami. Uzytkownik obserwuje i raportuje wynik po zakonczeniu.

    Kroki:
    1. PAN prawo (error_x=+50) — oczekiwany ruch: kamera w PRAWO
    2. PAN lewo (error_x=-50) — oczekiwany ruch: kamera w LEWO
    3. TILT dol (error_y=+30) — oczekiwany ruch: kamera kompensuje DOL
    4. TILT gora (error_y=-30) — oczekiwany ruch: kamera kompensuje GORA

    Returns:
        0 — zawsze (tryb nieinteraktywny, wynik raportowany zewnetrznie).
    """
    # Parsuj argument --krok N (opcjonalny — uruchamia tylko jeden krok)
    pojedynczy_krok = None
    if len(sys.argv) > 1 and sys.argv[1] == "--krok" and len(sys.argv) > 2:
        pojedynczy_krok = int(sys.argv[2])

    iface = SerialInterface(port=PORT, timeout=TIMEOUT)

    print("=== ARIES-LITE Kalibracja kierunkow serw (tryb nieinteraktywny) ===")
    print(f"Port: {PORT}, Baudrate: 115200")
    print(f"Czas testu per krok: {CZAS_TESTU_S}s, TX: {1/OPOZNIENIE_TX:.0f} Hz")
    if pojedynczy_krok:
        print(f"Tryb: tylko krok {pojedynczy_krok}")
    print()

    kroki = [
        (1, "PAN prawo (error_x=+50)", "serwo PAN przesuwa kamere w PRAWO", 50, 0),
        (2, "PAN lewo (error_x=-50)", "serwo PAN przesuwa kamere w LEWO", -50, 0),
        (3, "TILT dol (error_y=+30)", "serwo TILT kompensuje DOL (kamera opada)", 0, 30),
        (4, "TILT gora (error_y=-30)", "serwo TILT kompensuje GORA (kamera unosi sie)", 0, -30),
    ]

    try:
        iface.open()

        print(f"Czekam {OPOZNIENIE_BOOT:.0f}s na rozruch Arduino (LCD bootscreen + safe_startup)...")
        time.sleep(OPOZNIENIE_BOOT)
        iface._ser.reset_input_buffer()
        print("Arduino gotowe. Rozpoczynam kalibracje.\n")

        for numer, opis, oczekiwany, ex, ey in kroki:
            if pojedynczy_krok and numer != pojedynczy_krok:
                continue
            krok_kalibracji(iface, numer, opis, oczekiwany, error_x=ex, error_y=ey)
            # Przerwa miedzy krokami — Arduino wroci do SCAN (watchdog 500ms)
            time.sleep(3.0)

        print("=== KALIBRACJA ZAKONCZONA ===")
        print("Zaraportuj wynik per krok: PASS jesli ruch zgodny z oczekiwanym, FAIL jesli odwrotny.")
        print("  Krok 1: PAN prawo  — czy serwo poszlo w PRAWO?")
        print("  Krok 2: PAN lewo   — czy serwo poszlo w LEWO?")
        print("  Krok 3: TILT dol   — czy serwo poszlo w DOL?")
        print("  Krok 4: TILT gora  — czy serwo poszlo w GORE?")
        return 0

    finally:
        iface.close()


if __name__ == "__main__":
    sys.exit(main())
