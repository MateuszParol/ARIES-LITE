# Phase 19: Serial Link + Echo Test - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 19-serial-link-echo-test
**Areas discussed:** Parser Arduino, Nadajnik RPi, Echo test, Heartbeat

---

## Parser Arduino

### Model parsera

| Option | Description | Selected |
|--------|-------------|----------|
| State-machine | WAIT_START → READ_PAYLOAD → VERIFY_CHECKSUM → DISPATCH, non-blocking, bajt po bajcie | ✓ |
| Bufor 8B z peek() | Serial.available() >= 8, peek() == 0xAA, readBytes(8). Prostszy ale blokujacy | |

**User's choice:** State-machine (Recommended)
**Notes:** Zgodne z wymaganiem SER-02

### Sygnalizacja poprawnego odbioru

| Option | Description | Selected |
|--------|-------------|----------|
| Serial.println() debug log | Arduino wypisuje zdekodowane pola na Serial Monitor | |
| Echo ramki z powrotem | Arduino odsyla cala ramke 8B do RPi | ✓ |
| LED toggle | Wbudowany LED mruga przy poprawnej ramce | |

**User's choice:** Echo ramki z powrotem
**Notes:** Programowa weryfikacja end-to-end — RPi porownuje wyslane vs odebrane

### Echo format

| Option | Description | Selected |
|--------|-------------|----------|
| Identyczna ramka 8B | Arduino odsyla dokladnie te same 8 bajtow | ✓ |
| Tylko payload 6B | Bajty 1-6 bez start marker i checksum | |
| Zdekodowane pola jako tekst | ASCII string z polami | |

**User's choice:** Identyczna ramka 8B (Recommended)
**Notes:** Najprostsze porownanie bajt po bajcie

### Obsluga bledow

| Option | Description | Selected |
|--------|-------------|----------|
| Cichy drop + resync | Odrzuc ramke, wroc do WAIT_START. Brak echo. | ✓ |
| Serial.println() error log | Wypisz "ERR:CHECKSUM" na Serial | |
| Echo z flaga bledu | Start=0xBB zamiast 0xAA | |

**User's choice:** Cichy drop + resync (Recommended)
**Notes:** RPi wykrywa brak odpowiedzi przez timeout

---

## Nadajnik RPi

### Organizacja kodu

| Option | Description | Selected |
|--------|-------------|----------|
| Klasa SerialInterface | OOP wrapper na pyserial w src/vision/serial_interface.py | ✓ |
| Funkcje modulowe | Osobne funkcje na poziomie modulu | |
| Inline w skrypcie testowym | Cala logika w echo_test.py | |

**User's choice:** Klasa SerialInterface (Recommended)
**Notes:** Zgodne z INT-04 (modularny OOP), reusable w pi_brain.py

### low_latency

| Option | Description | Selected |
|--------|-------------|----------|
| Programowo w SerialInterface | subprocess + setserial przy kazdym open() | ✓ |
| Regula udev | /etc/udev/rules.d/99-aries.rules | |
| Pominiecie | Domyslna latency, weryfikacja pozniej | |

**User's choice:** Programowo w SerialInterface (Recommended)
**Notes:** Nie wymaga sudo ani konfiguracji systemu

### Utrata portu USB

| Option | Description | Selected |
|--------|-------------|----------|
| Log + wyjatek | SerialException logowany + podniesiony wyzej | ✓ |
| Auto-reconnect w petli | Ponowne otwarcie co 2s | |
| Cichy no-op | send_frame() zwraca False | |

**User's choice:** Log + wyjatek (Recommended)
**Notes:** Reconnect to odpowiedzialnosc wywolujacego (pi_brain.py)

---

## Echo test

### Format skryptu

| Option | Description | Selected |
|--------|-------------|----------|
| Skrypt jednorazowy | scripts/echo_test.py — wyslij, porownaj, PASS/FAIL | ✓ |
| Tryb ciagly interaktywny | Petla co 200ms z wyswietlaniem na zywo | |
| Pytest test | tests/test_serial.py z pytest | |

**User's choice:** Skrypt jednorazowy (Recommended)
**Notes:** Prosty, weryfikowalny, reusable

### Scenariusze testowe

| Option | Description | Selected |
|--------|-------------|----------|
| Normalna ramka TRACK | mode=2, error_x=45, error_y=-12, face_size=128 | ✓ |
| Ramka IDLE (zerowe bledy) | mode=0, error_x=0, error_y=0, face_size=0 | |
| Skrajne wartosci | error_x=-160, error_y=+160, face_size=255 | |
| USB reconnect | Odlacz/podlacz USB, sprawdz resync | |

**User's choice:** Normalna ramka TRACK
**Notes:** Referencyjny przyklad z PROTOCOL_SPEC.md

### Raportowanie

| Option | Description | Selected |
|--------|-------------|----------|
| Print PASS/FAIL + hex dump | sent=[hex], recv=[hex], PASS/FAIL. Exit code 0/1. | ✓ |
| Verbose z dekodowaniem pol | Hex dump + zdekodowane pola | |
| Claude decyduje | Format do uznania Claude | |

**User's choice:** Print PASS/FAIL + hex dump (Recommended)
**Notes:** Minimalny, czytelny output

---

## Heartbeat

### Format heartbeat

| Option | Description | Selected |
|--------|-------------|----------|
| Normalna ramka mode=IDLE | Zwykla ramka 8B z mode=0, zerowe bledy | ✓ |
| Osobny bajt heartbeat | Pojedynczy bajt 0x55 co 200ms | |
| Ramka z flaga heartbeat | Nowy tryb mode=3 (HEARTBEAT) | |

**User's choice:** Normalna ramka mode=IDLE (Recommended)
**Notes:** Zero specjalnej logiki, spojne z protokolem

### Umiejscowienie w kodzie

| Option | Description | Selected |
|--------|-------------|----------|
| Wbudowany w SerialInterface | Metoda send_heartbeat() jako alias | ✓ |
| Osobny test w echo_test.py | Dedykowany krok z timingiem 200ms | |
| Odlozony do Phase 21 | Tylko weryfikacja ze ramka IDLE przechodzi | |

**User's choice:** Wbudowany w SerialInterface (Recommended)
**Notes:** Timing 200ms dopiero w pi_brain.py (Phase 21)

---

## Claude's Discretion

- Wewnetrzna implementacja state-machine parsera (nazwy stanow, zmienne)
- Dokladna struktura echo_test.py (argumenty CLI, timeout, ilosc powtorzen)
- Czy echo_test.py importuje SerialInterface czy ma wlasna logike

## Deferred Ideas

None — discussion stayed within phase scope
