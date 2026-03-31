# Phase 20: Firmware Arduino PID + Servo - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 20-firmware-arduino-pid-servo
**Areas discussed:** PID tuning + mapowanie, Safe startup + serwa, Maszyna stanow + watchdog, Skan sinusoidalny

---

## PID tuning + mapowanie

| Option | Description | Selected |
|--------|-------------|----------|
| PID bezposrednio na pikselach | QuickPID Input=error_px, Output=korekta stopni. Prostsze. | |
| Normalizacja do -1.0..+1.0 | error_norm = error_px / 160.0. Bardziej przenosne. | ✓ |
| Claude decyduje | Zostaw wybor do planowania. | |

**User's choice:** Normalizacja do -1.0..+1.0

| Option | Description | Selected |
|--------|-------------|----------|
| Konserwatywne (Kp=2.0, Ki=0.1, Kd=0.5) | Mniejsze gainy, brak overshootu. Output +/-5 deg/tick. | ✓ |
| Umiarkowane (Kp=5.0, Ki=0.3, Kd=1.0) | Szybsza reakcja, mozliwy overshoot. +/-10 deg/tick. | |
| Claude decyduje | Dobierz punkt startowy. | |

**User's choice:** Konserwatywne (Kp=2.0, Ki=0.1, Kd=0.5)

| Option | Description | Selected |
|--------|-------------|----------|
| Tak, neguj pan error | Negative feedback jak w legacy. | |
| Nie, PAN_INVERT zalatwia | #define obsluguje kierunek. | |
| Claude decyduje | Najlepsza strategia znakow. | ✓ |

**User's choice:** Claude decyduje

| Option | Description | Selected |
|--------|-------------|----------|
| Staly setpoint = 0.0 | RPi oblicza error, PID dazy do 0. Proste. | |
| Claude decyduje | Setpoint wynika z architektury. | ✓ |

**User's choice:** Claude decyduje

---

## Safe startup + serwa

| Option | Description | Selected |
|--------|-------------|----------|
| Inkrementalna rampa (1 deg/10ms) | Analogiczny do smooth_move_to() z legacy. ~900ms. | |
| Servo.write(90) z delay | Prostsze ale skok pradu mozliwy. | |
| Servo.writeMicroseconds() rampa | Dokladniejsza kontrola przez mikrsekundy. Precyzyjne. | ✓ |
| Claude decyduje | Najlepsza strategia. | |

**User's choice:** Servo.writeMicroseconds() rampa

| Option | Description | Selected |
|--------|-------------|----------|
| 500ms | Szybkie ale plynne. | |
| 1000ms | Wolniejsze, bezpieczniejsze. Legacy ~1s. | ✓ |
| 2000ms | Bardzo konserwatywne. | |
| Claude decyduje | Dobierz czas. | |

**User's choice:** 1000ms

---

## Maszyna stanow + watchdog

| Option | Description | Selected |
|--------|-------------|----------|
| IDLE (czekaj na RPi) | Po safe startup serwa w 90/90, czeka na ramke. | ✓ |
| SCAN (autonomiczny start) | Od razu skan sinusoidalny. | |
| Claude decyduje | Najlepsza strategia. | |

**User's choice:** IDLE (czekaj na RPi)

| Option | Description | Selected |
|--------|-------------|----------|
| Przejdz do SCAN | Autonomiczny skan. Per ROADMAP criteria #3. | |
| Przejdz do IDLE | Zatrzymaj serwa. Bezpieczniejsze. | |
| Claude decyduje | Najlepsza strategia watchdog. | ✓ |

**User's choice:** Claude decyduje

| Option | Description | Selected |
|--------|-------------|----------|
| Tryb z ramki = stan Arduino | Bezposrednie mapowanie mode na stan. Proste. | |
| Warunkowe przejscia | Arduino moze odrzucic niektorych przejsc. Defensywne. | |
| Claude decyduje | Najlepsza logika dispatchera. | ✓ |

**User's choice:** Claude decyduje

---

## Skan sinusoidalny

| Option | Description | Selected |
|--------|-------------|----------|
| Lissajous 2D (pan + tilt) | Obie osie z roznymi czestotliwosciami. Pelne pokrycie. | ✓ |
| Tylko pan (single-axis) | Prostsze, mniej pokrycia. | |
| Claude decyduje | Najlepsza strategia. | |

**User's choice:** Lissajous 2D (pan + tilt)

**Amplitudy:**
- PAN: 70 stopni (user: "45 stopni bylo za waskim obszarem, zwiekszamy do 70 stopni")
- TILT: 25 stopni

**Czestotliwosci:** Claude decyduje (legacy PAN=0.05, TILT=0.07 jako odniesienie)

---

## Claude's Discretion

- Strategia znakow PID (negacja vs INVERT define)
- Watchdog target state (SCAN vs IDLE)
- Dispatcher logic (bezposredni vs warunkowy)
- Czestotliwosci skanowania Lissajous
- PID setpoint (staly 0.0 vs inny)
- Organizacja wewnetrzna kodu .ino

## Deferred Ideas

None — discussion stayed within phase scope
