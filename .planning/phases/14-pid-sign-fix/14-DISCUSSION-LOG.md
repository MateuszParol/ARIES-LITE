# Phase 14: PID Sign Fix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 14-pid-sign-fix
**Areas discussed:** Procedura kalibracji, Zapis wyniku, Weryfikacja negative feedback, Obsluga bledu error_x/y

---

## Procedura kalibracji

| Option | Description | Selected |
|--------|-------------|----------|
| Skrypt kalibracyjny | Uzyj istniejacego scripts/kalibracja_serw.py — deterministyczne, powtarzalne (Phase 23) | ✓ |
| Reczny test z twarza | Uruchom pi_brain.py, stan po prawej stronie kamery, obserwuj kierunek serwa | |
| Oba — skrypt + weryfikacja na zywo | Najpierw skrypt ustala INVERT, potem pi_brain.py weryfikuje z prawdziwa twarza | |

**User's choice:** Skrypt kalibracyjny (Recommended)
**Notes:** Zgodne z decyzja Phase 23 D-01

| Option | Description | Selected |
|--------|-------------|----------|
| Istnieje i dziala | Skrypt z Phase 23 jest gotowy | |
| Trzeba stworzyc/zweryfikowac | Skrypt moze nie istniec lub wymagac aktualizacji | |
| Claude zdecyduje | Researcher sprawdzi stan skryptu | ✓ |

**User's choice:** Claude zdecyduje

| Option | Description | Selected |
|--------|-------------|----------|
| Ten sam montaz | Orientacja identyczna jak w v1.7/v2.0 | ✓ |
| Inny montaz / nie wiem | Montaz mogl sie zmienic | |
| Jeszcze nie zmontowane | Montaz hardware bedzie czescia tej fazy | |

**User's choice:** Ten sam montaz

| Option | Description | Selected |
|--------|-------------|----------|
| Pan najpierw, potem tilt | Pan bardziej widoczny (lewo-prawo) — latwiej zweryfikowac | ✓ |
| Oba naraz | Wysylaj error_x i error_y jednoczesnie | |
| Claude zdecyduje | Researcher oceni najlepsza kolejnosc | |

**User's choice:** Pan najpierw, potem tilt (Recommended)

Dodatkowe pytania (amplituda, safety, auto/manual): Claude zdecyduje

---

## Zapis wyniku

| Option | Description | Selected |
|--------|-------------|----------|
| #define + rekompilacja | Zmiana #define PAN_INVERT/TILT_INVERT w .ino i reupload. Kalibracja jednorazowa. | ✓ |
| EEPROM runtime | Zapis do EEPROM na R4, odczyt w setup(). Bez rekompilacji. | |
| Komenda serial | Nowa komenda z RPi do ustawiania INVERT w runtime. Wymaga zmian protokolu. | |

**User's choice:** #define + rekompilacja (Recommended)
**Notes:** Potwierdzenie Phase 23 D-02

---

## Weryfikacja negative feedback

| Option | Description | Selected |
|--------|-------------|----------|
| Skrypt + obserwacja | Skrypt wyslaje error_x=+50, potwierdzasz wizualnie ze serwo jedzie w prawo. Deterministyczne. | ✓ |
| Pelny E2E z pi_brain.py | Uruchom tracking z prawdziwa twarza i potwierdz konwergencje PID | |
| Oba sekwencyjnie | Najpierw skrypt, potem krotki test E2E jako potwierdzenie | |

**User's choice:** Skrypt + obserwacja (Recommended)

Czas obserwacji: Claude zdecyduje (kontekst: Success Criteria mowi o konwergencji 1-3s)

---

## Obsluga bledu error_x/y

| Option | Description | Selected |
|--------|-------------|----------|
| Tylko Arduino INVERT | RPi wysyla error_x=+160 gdy twarz po prawej. Arduino odwraca przez INVERT. | |
| Zmiana po stronie RPi | Odwroc znak error_x/y w pi_brain.py przed serial TX | |
| Claude zdecyduje | Researcher przeanalizuje pelny lancuch znaku i zaproponuje najczystszy fix | ✓ |

**User's choice:** Claude zdecyduje

Konwencja error_x/y (RPi): Claude zweryfikuje oba — researcher przeczyta _oblicz_error() i potwierdzi konwencje obu osi
Konwencja error_y: Claude zweryfikuje

---

## Claude's Discretion

- Stan skryptu kalibracja_serw.py (istnienie, aktualnosc)
- Amplituda testowa, czas obserwacji, zabezpieczenia
- Konwencja znakow error_x/error_y (pelny lancuch)
- Lokalizacja fixa (Arduino INVERT vs RPi)
- Czas obserwacji dla potwierdzenia negative feedback

## Deferred Ideas

None — discussion stayed within phase scope
