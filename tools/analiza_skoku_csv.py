#!/usr/bin/env python3
"""Analiza skoku serw przy przejsciu SLEDZENIE→SKANOWANIE z logow CSV DataLogger.

Uzycie:
    python3 tools/analiza_skoku_csv.py LYYMMDD.CSV

Sprawdza czy skok pan i tilt przy kazdym przejsciu SLEDZENIE→SKANOWANIE
nie przekracza progu 5 stopni (per D-11).

Kolumny CSV: timestamp, stan, pan, tilt, error_x, error_y, face_size, latency_ms
"""
import csv
import sys

PROG_SKOKU = 5.0  # stopnie — max akceptowalny skok (D-11)


def analizuj(sciezka_csv: str) -> bool:
    with open(sciezka_csv) as f:
        wiersze = list(csv.DictReader(f))

    przejscia = []
    for i in range(1, len(wiersze)):
        poprz, akt = wiersze[i - 1], wiersze[i]
        if poprz['stan'] == 'SLEDZENIE' and akt['stan'] == 'SKANOWANIE':
            delta_pan = abs(float(akt['pan']) - float(poprz['pan']))
            delta_tilt = abs(float(akt['tilt']) - float(poprz['tilt']))
            przejscia.append({
                'wiersz': i + 1,
                'delta_pan': delta_pan,
                'delta_tilt': delta_tilt,
            })

    if not przejscia:
        print("BRAK przejsc SLEDZENIE→SKANOWANIE w logu.")
        return True

    wszystkie_ok = True
    for p in przejscia:
        ok = p['delta_pan'] <= PROG_SKOKU and p['delta_tilt'] <= PROG_SKOKU
        status = 'PASS' if ok else 'FAIL'
        if not ok:
            wszystkie_ok = False
        print(f"Wiersz {p['wiersz']}: skok_pan={p['delta_pan']:.1f}\u00b0, "
              f"skok_tilt={p['delta_tilt']:.1f}\u00b0 \u2014 {status}")

    print(f"\nWynik: {'PASS' if wszystkie_ok else 'FAIL'} "
          f"({len(przejscia)} przejsc, prog={PROG_SKOKU}\u00b0)")
    return wszystkie_ok


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Uzycie: {sys.argv[0]} <sciezka_do_csv>")
        sys.exit(1)
    ok = analizuj(sys.argv[1])
    sys.exit(0 if ok else 1)
