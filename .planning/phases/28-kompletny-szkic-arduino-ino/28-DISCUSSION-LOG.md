# Phase 28: Flash firmware na Uno R4 WiFi - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 28-kompletny-szkic-arduino-ino
**Areas discussed:** Metoda flashowania, Procedura testow, Awarie i rollback, Konfiguracja RPi

---

## Metoda flashowania

| Option | Description | Selected |
|--------|-------------|----------|
| Arduino IDE | GUI — Sketch > Upload. Weryfikacja wizualna kompilacji + upload. | |
| arduino-cli | Komenda: compile + upload. Reprodukowalne, scriptowalne. | |
| Claude zdecyduje | Researcher zbada najlepsza metode. | ✓ |

**User's choice:** Claude zdecyduje
**Notes:** Uzytkownik nie ma preferencji IDE vs CLI.

| Option | Description | Selected |
|--------|-------------|----------|
| Tak, IDE gotowe | Arduino IDE z boardem R4 WiFi skonfigurowane. | |
| Nie wiem | Nie pamietam stanu srodowiska. | |
| Nie, potrzebna instalacja | Potrzebuje instrukcji od zera. | ✓ |

**User's choice:** Potrzebna instalacja od zera
**Notes:** RPi4 nie ma zainstalowanego Arduino IDE ani arduino-cli.

| Option | Description | Selected |
|--------|-------------|----------|
| RPi4 (ten sam co wizja) | Flashowanie z RPi4 ktory uruchamia pi_brain.py. | ✓ |
| PC/laptop | Oddzielny komputer do flashowania. | |
| Oba | Flash z PC, test z RPi. | |

**User's choice:** RPi4
**Notes:** Wszystko na jednym urzadzeniu.

| Option | Description | Selected |
|--------|-------------|----------|
| arduino-cli (Recommended) | Lzejsze na RPi4, brak GUI. | ✓ |
| Arduino IDE | Pelne GUI, ciezsze na RPi4. | |
| Sprawdz co mam | Nie wiem co zainstalowane. | |

**User's choice:** arduino-cli
**Notes:** Preferuje CLI — lzejsze na RPi4.

| Option | Description | Selected |
|--------|-------------|----------|
| SSH only | Brak fizycznego monitora. | |
| Monitor + klawiatura | Desktop na RPi4. | ✓ |
| Oba | Glownie SSH, monitor dostepny. | |

**User's choice:** Monitor + klawiatura
**Notes:** Ma fizyczny dostep do RPi4 — moze obserwowac LCD i serwa bezposrednio.

---

## Procedura testow

| Option | Description | Selected |
|--------|-------------|----------|
| Izolowane po kolei (Recommended) | LCD, serwa, buzzer, przycisk, serial, power cycle. Kazdy niezalezny. | ✓ |
| Szybki smoke test | Wlacz i sprawdz wszystko na raz. | |
| Claude zdecyduje | Researcher dobierze kolejnosc. | |

**User's choice:** Izolowane po kolei
**Notes:** Pasywne najpierw (LCD), aktywne pozniej (serwa).

| Option | Description | Selected |
|--------|-------------|----------|
| Checkpoint w planie (Recommended) | CHECKPOINT po kazdym tescie, PASS/FAIL. Wzorzec Phase 24. | ✓ |
| Lista w terminalu | Proste potwierdzenie w chacie. | |
| Zrzuty ekranu / zdjecia | Dokumentacja wizualna. | |

**User's choice:** Checkpoint w planie
**Notes:** Identyczny wzorzec jak Phase 24.

| Option | Description | Selected |
|--------|-------------|----------|
| Pelny E2E tracking (Recommended) | pi_brain.py, twarz, sledzenie serwami. | ✓ |
| Tylko echo/parsowanie | Testowe ramki bez kamery. | |
| Oba | Echo najpierw, potem E2E. | |

**User's choice:** Pelny E2E tracking
**Notes:** Najsilniejszy dowod poprawnosci systemu.

---

## Awarie i rollback

| Option | Description | Selected |
|--------|-------------|----------|
| Debug in-place (Recommended) | Diagnozuj na R4: polaczenia, piny, Serial output. | ✓ |
| Rollback na R3 | Wroc do R3 jesli R4 nie dziala. | |
| Eskaluj do nowej fazy | Nowa faza debug jesli problem powazny. | |

**User's choice:** Debug in-place
**Notes:** Bez rollbacku.

| Option | Description | Selected |
|--------|-------------|----------|
| Tak, mam zapas | Zapasowe serwa, LCD, kable. | |
| Nie, pojedyncze egzemplarze | Kazdy komponent w jednym egzemplarzu. | ✓ |
| Czesciowo | Niektore w zapasie. | |

**User's choice:** Pojedyncze egzemplarze
**Notes:** Brak zapasowych czesci — plan musi byc ostrozny.

---

## Konfiguracja RPi

| Option | Description | Selected |
|--------|-------------|----------|
| Tak, E2E dzialal z R3 | pi_brain.py + R3 przez /dev/ttyACM0, tracking dzialal. | ✓ |
| Nie, tylko firmware izolowanie | Phase 24 testowala kompilacje i peryferia. | |
| Nie pamietam | Plan zweryfikuje stan. | |

**User's choice:** E2E dzialal z R3
**Notes:** Teraz trzeba powtorzyc z R4.

| Option | Description | Selected |
|--------|-------------|----------|
| Nie wiem — Claude zbada | Researcher sprawdzi DTR na R4 WiFi (ESP32-S3 bridge). | ✓ |
| DTR juz naprawiony | Phase 24 usunela workaround. | |
| Wiem ze trzeba zmienic | Konkretna wiedza o zmianach. | |

**User's choice:** Claude zbada
**Notes:** Phase 24 D-06 usunela CDC workaround Leonardo — trzeba zweryfikowac czy R4 wymaga dodatkowych zmian.

| Option | Description | Selected |
|--------|-------------|----------|
| Juz polaczone | Kabel USB RPi4 ↔ R4 na miejscu. | ✓ |
| Pierwsze polaczenie | R4 nowe, nigdy nie podlaczone. | |
| R3 polaczony, R4 bedzie zamiana | Zamiana R3 na R4 na tym samym USB. | |

**User's choice:** Juz polaczone
**Notes:** R4 WiFi fizycznie podlaczone do RPi4 przez USB.

---

## Claude's Discretion

- Metoda instalacji arduino-cli na RPi4 ARM64
- Board FQBN dla Uno R4 WiFi
- Biblioteki do zainstalowania (QuickPID, Servo, LiquidCrystal)
- DTR behavior R4 WiFi vs Leonardo
- udev rules dla /dev/ttyACM0
- Timeout/retry na flash failure

## Deferred Ideas

None — discussion stayed within phase scope
