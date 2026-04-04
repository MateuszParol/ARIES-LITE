# Phase 14: PID Sign Fix - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Kalibracja PAN_INVERT/TILT_INVERT na Arduino Uno R4 WiFi — eliminacja positive feedback (serwa uciekaja od twarzy zamiast sledzic). Po tej fazie serwa poruszaja sie W KIERUNKU twarzy (negative feedback) na docelowym hardware R4.

Faza NIE obejmuje: zmian w logice PID (gainy, anti-windup), zmian w protokole binarnym 8B, zmian w MediaPipe/detekcji, nowych funkcji HMI, zmian w pi_brain.py (chyba ze researcher uzna za konieczne).

</domain>

<decisions>
## Implementation Decisions

### Procedura kalibracji
- **D-01:** Uzyj istniejacego skryptu `scripts/kalibracja_serw.py` do empirycznej weryfikacji kierunku serw. Claude zweryfikuje stan skryptu (istnienie, aktualnosc) i zaktualizuje jesli trzeba.
- **D-02:** Kolejnosc kalibracji: najpierw pan (bardziej widoczny lewo-prawo), potem tilt.
- **D-03:** Fizyczny montaz identyczny jak w v1.7/v2.0 — pan+=prawo, tilt+=dol. Nie wymaga zmiany orientacji.
- **D-04:** Claude's Discretion — szczegoly skryptu: amplituda testowa, czas obserwacji, zabezpieczenia (smooth_move, male katy), auto vs manual feedback.

### Zapis wyniku
- **D-05:** Wynik kalibracji utrwalony jako `#define PAN_INVERT` i `#define TILT_INVERT` w firmware .ino — zmiana wymaga rekompilacji. Akceptowalne bo kalibracja jednorazowa. (Potwierdzenie Phase 23 D-02)

### Weryfikacja negative feedback
- **D-06:** Weryfikacja przez skrypt kalibracyjny + obserwacja wizualna: error_x=+50 → serwo jedzie w prawo, error_y=+30 → serwo pochyla w dol. Deterministyczne, powtarzalne.
- **D-07:** Claude's Discretion — czas obserwacji do potwierdzenia negative feedback (kontekst: Success Criteria mowi o konwergencji PID w 1-3s).

### Obsluga bledu error_x/y
- **D-08:** Claude's Discretion — researcher zweryfikuje pelny lancuch znaku: _oblicz_error() w brain.py → serial TX → parser Arduino → PID → INVERT → servo. Ustali konwencje obu osi (error_x: +160 = twarz po prawej?, error_y: +120 = twarz ponizej srodka?).
- **D-09:** Claude's Discretion — gdzie naprawic kierunek (tylko Arduino INVERT vs zmiana po stronie RPi). Researcher przeanalizuje najczystsze rozwiazanie.

### Claude's Discretion
- Stan skryptu kalibracja_serw.py — D-04
- Czas obserwacji weryfikacji — D-07
- Konwencja znakow error_x/y — D-08
- Lokalizacja fixa (Arduino INVERT vs RPi) — D-09
- Amplituda i bezpieczenstwo testow kalibracyjnych

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Firmware Arduino
- `src/arduino/aries_controller/aries_controller.ino` — Pelny firmware: #define PAN_INVERT (+1) i TILT_INVERT (-1) na liniach 37-38, zastosowanie w pid_krok() linia 269-271

### Kod RPi (lancuch bledu)
- `src/vision/brain.py` — MozgRPi: _oblicz_error() oblicza error_x/error_y z bbox, wyslanie przez serial
- `src/vision/serial_interface.py` — send_frame(): pakowanie error_x/error_y jako int16 LE

### Skrypt kalibracyjny
- `scripts/kalibracja_serw.py` — Skrypt kalibracyjny z Phase 23 (researcher zweryfikuje istnienie i stan)

### Protokol binarny
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja ramki 8B: error_x (int16, bajty 2-3), error_y (int16, bajty 4-5)

### Kontekst wczesniejszych faz
- `.planning/phases/23-integracja-kalibracja/23-CONTEXT.md` — D-01/D-02: procedura kalibracji i zapis INVERT
- `.planning/phases/24-migracja-pinow-i-kompilacja-bazowa/24-CONTEXT.md` — D-02: mapa pinow PAN=D6, TILT=D9

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/kalibracja_serw.py` — skrypt kalibracyjny z Phase 23 (do weryfikacji stanu)
- `src/vision/serial_interface.py` — SerialInterface.send_frame() gotowy do uzycia przez skrypt testowy

### Established Patterns
- PAN_INVERT/TILT_INVERT jako #define w firmware — mnoznik +1 lub -1 stosowany w pid_krok()
- Error normalizowany do zakresu -160..+160 (error_x) i -120..+120 (error_y) na RPi
- PID wejscie: `_pan_wejscie = (float)ostatni_blad_x / POLOWA_RAMKI` — normalizacja do -1..+1

### Integration Points
- Zmiana #define PAN_INVERT/TILT_INVERT w aries_controller.ino linia 37-38
- Ewentualnie zmiana znaku w brain.py _oblicz_error() jesli researcher uzna to za czystsze

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-pid-sign-fix*
*Context gathered: 2026-04-04*
