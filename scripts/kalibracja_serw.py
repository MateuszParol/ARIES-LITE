#!/usr/bin/env python3
"""Deterministyczny skrypt kalibracji kierunkow serw ARIES-LITE v2.0.

Wysyla 4 sekwencje testowe (PAN prawo, PAN lewo, TILT dol, TILT gora)
przez SerialInterface i pyta uzytkownika o potwierdzenie kierunku ruchu
per krok. Raportuje PASS/FAIL dla kazdego kroku i dla calej kalibracji.

Cel: Weryfikacja ze PAN_INVERT i TILT_INVERT w firmware Arduino sa poprawne
(montaz standardowy: pan+=prawo, tilt+=dol). Jezeli krok FAIL — zmien
#define PAN_INVERT / TILT_INVERT w src/arduino/aries_controller/aries_controller.ino,
rekompiluj i wgraj firmware, a nastepnie powtorz kalibracje.

Wymaga: Arduino Leonardo z firmware Phase 22, polaczone przez USB Serial.
"""

import sys
import time
from pathlib import Path

# Dodaj katalog projektu do sys.path — umozliwia import src.vision
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vision.serial_interface import SerialInterface  # noqa: E402

# --- Stale modulowe ---
PORT = "/dev/ttyACM0"          # Domyslny port Arduino Leonardo na RPi
TIMEOUT = 2.0                   # Timeout odczytu TX w sekundach
OPOZNIENIE_BOOT = 4.0          # Leonardo boot delay: 2s LCD bootscreen + 1s safe_startup + 1s margines
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


def main() -> int:
    """Przeprowadza 4-krokowa kalibracje kierunkow serw.

    Kroki:
    1. PAN prawo (error_x=+50) — oczekiwany ruch: kamera w PRAWO
    2. PAN lewo (error_x=-50) — oczekiwany ruch: kamera w LEWO
    3. TILT dol (error_y=+30) — oczekiwany ruch: kamera kompensuje DOL
    4. TILT gora (error_y=-30) — oczekiwany ruch: kamera kompensuje GORA

    Returns:
        0 — wszystkie kroki PASS (PAN_INVERT i TILT_INVERT poprawne).
        1 — co najmniej jeden krok FAIL (wymaga zmiany firmware).
    """
    iface = SerialInterface(port=PORT, timeout=TIMEOUT)

    print("=== ARIES-LITE Kalibracja kierunkow serw ===")
    print(f"Port: {PORT}, Baudrate: 115200")
    print(f"Czas testu per krok: {CZAS_TESTU_S}s, TX: {1/OPOZNIENIE_TX:.0f} Hz\n")

    try:
        # Otworz port szeregowy (DTR=False zapobiega resetowi Leonardo per D-19)
        iface.open()

        # Czekaj na peny rozruch Arduino — LCD bootscreen 2s + safe_startup 1s + margines 1s
        print(f"Czekam {OPOZNIENIE_BOOT:.0f}s na rozruch Arduino (LCD bootscreen + safe_startup)...")
        time.sleep(OPOZNIENIE_BOOT)

        # Wyczysc bufor wejsciowy przed testem — zapobiega desynchronizacji
        iface._ser.reset_input_buffer()

        print("Arduino gotowe. Rozpoczynam kalibracje.\n")

        # --- KROK 1: PAN prawo ---
        print("=== KROK 1: PAN — error_x=+50 (twarz po prawej) ===")
        print("Oczekiwany ruch: serwo PAN przesuwa kamere w PRAWO")
        print(f"Wysylam ramki TRACK error_x=+50 przez {CZAS_TESTU_S}s...")
        wysylaj_petla(iface, error_x=50, error_y=0, czas_s=CZAS_TESTU_S)
        wynik_1 = input("Serwo pan poruszylo sie w PRAWO? [t/n]: ").strip().lower()

        # Krotka przerwa miedzy krokami — Arduino wroci do SCAN (watchdog)
        time.sleep(1.0)

        # --- KROK 2: PAN lewo ---
        print("\n=== KROK 2: PAN — error_x=-50 (twarz po lewej) ===")
        print("Oczekiwany ruch: serwo PAN przesuwa kamere w LEWO")
        print(f"Wysylam ramki TRACK error_x=-50 przez {CZAS_TESTU_S}s...")
        wysylaj_petla(iface, error_x=-50, error_y=0, czas_s=CZAS_TESTU_S)
        wynik_2 = input("Serwo pan poruszylo sie w LEWO? [t/n]: ").strip().lower()

        time.sleep(1.0)

        # --- KROK 3: TILT dol ---
        print("\n=== KROK 3: TILT — error_y=+30 (twarz ponizej centrum) ===")
        print("Oczekiwany ruch: serwo TILT kompensuje DOL (kamera opada)")
        print(f"Wysylam ramki TRACK error_y=+30 przez {CZAS_TESTU_S}s...")
        wysylaj_petla(iface, error_x=0, error_y=30, czas_s=CZAS_TESTU_S)
        wynik_3 = input("Serwo tilt poruszylo sie w DOL? [t/n]: ").strip().lower()

        time.sleep(1.0)

        # --- KROK 4: TILT gora ---
        print("\n=== KROK 4: TILT — error_y=-30 (twarz powyzej centrum) ===")
        print("Oczekiwany ruch: serwo TILT kompensuje GORA (kamera unosi sie)")
        print(f"Wysylam ramki TRACK error_y=-30 przez {CZAS_TESTU_S}s...")
        wysylaj_petla(iface, error_x=0, error_y=-30, czas_s=CZAS_TESTU_S)
        wynik_4 = input("Serwo tilt poruszylo sie w GORA? [t/n]: ").strip().lower()

        # --- PODSUMOWANIE ---
        wyniki = [
            ("PAN prawo", wynik_1),
            ("PAN lewo",  wynik_2),
            ("TILT dol",  wynik_3),
            ("TILT gora", wynik_4),
        ]

        print("\n=== PODSUMOWANIE ===")
        wszystkie_ok = True
        for nazwa, wynik in wyniki:
            status = "PASS" if wynik == "t" else "FAIL"
            print(f"  {nazwa}: {status}")
            if wynik != "t":
                wszystkie_ok = False

        if wszystkie_ok:
            print("\nKalibracja PASS — PAN_INVERT i TILT_INVERT poprawne.")
            return 0
        else:
            print("\nKalibracja FAIL — zmien #define PAN_INVERT/TILT_INVERT w firmware i rekompiluj.")
            print("  Plik: src/arduino/aries_controller/aries_controller.ino (linia 30-31)")
            return 1

    finally:
        iface.close()


if __name__ == "__main__":
    sys.exit(main())
