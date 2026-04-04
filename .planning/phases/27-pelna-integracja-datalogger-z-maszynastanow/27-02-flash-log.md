# Flash Log — 27-02 Task 1

**Data:** 2026-04-04T07:53:07Z
**Port:** /dev/ttyACM0
**Target:** Arduino Uno R4 WiFi (arduino:renesas_uno:unor4wifi)
**Firmware:** src/arduino/aries_controller/aries_controller.ino (commit 4154edc)

## Wynik kompilacji

```
Szkic używa 83596 bajtów (31%) pamięci programu. Maksimum to 262144 bajtów.
Zmienne globalne używają 11268 bajtów (34%) pamięci dynamicznej, pozostawiając 21500 bajtów dla zmiennych lokalnych. Maksimum to 32768 bajtów.
```

## Wynik uploadu

```
Erase flash — Done in 0.004 seconds
Write 83604 bytes to flash (21 pages) — Done in 5.085 seconds
New upload port: /dev/ttyACM0 (serial)
```

## Weryfikacja komendy 'D'

```
=== STARTUP ===
(brak — Uno R4 WiFi ESP32-S3 bridge nie wysyla DTR reset, zgodnie z decyzja Phase 25)

=== KOMENDA D ===
[DUMP] Ostatnie 10 wpisow DataLogger:
[DUMP] Koniec.
```

## Weryfikacja stabilnosci (10s monitoring)

Brak watchdog reset, brak powtarzajacych sie bootscreen — firmware dziala stabilnie.

## Acceptance criteria — PASS

- [x] arduino-cli upload konczy sie bez bledow
- [x] Komenda 'D' zwraca `[DUMP] Ostatnie 10 wpisow DataLogger:` i `[DUMP] Koniec.`
- [x] Brak watchdog reset w ciagu 10s
- [ ] Serial output po starcie zawiera `[RTC]` lub `[SD]` — nie widoczny (ESP32-S3 bridge, brak DTR reset — zgodne z Phase 25)
