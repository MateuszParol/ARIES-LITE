---
phase: 1
plan: 1
wave: 1
---

# Plan 1.1: Core System Configuration & Hardware Controller

## Objective
Utworzenie stałych systemowych dla limitów serwomechanizmów, parametrów regulacji PID oraz implementacja sprzętowej obsługi PWM dla eliminacji drgań.

## Context
- .gsd/SPEC.md
- src/config.py
- src/hardware.py

## Tasks

<task type="auto">
  <name>Zdefiniowanie stałych (config.py)</name>
  <files>src/config.py</files>
  <action>
    - Zdefiniuj domyślne stałe PID dla osi Pan/Tilt.
    - Zdefiniuj bezpieczne zakresy stopni (soft limits), aby zapobiec przerwaniu taśmy od kamery RPi.
    - Zdefiniuj globalne flagi stanów maszyny.
  </action>
  <verify>python -c "import src.config; print('Config Valid')"</verify>
  <done>Plik `src/config.py` wystawia zmienne publiczne zapobiegając używaniu 'magicznych liczb'.</done>
</task>

<task type="auto">
  <name>Klasa PanTiltSystem dla serw sprzętowych (hardware.py)</name>
  <files>src/hardware.py</files>
  <action>
    - Skorzystaj z `AngularServo` z biblioteki `gpiozero`
    - Wstrzyknij fabrykę `PiGPIOFactory` wymuszającą sygnał DMA PWM via `pigpiod`
    - Wyklucz wywrócenie aplikacji gdy `pigpiod` wyłączone/system operuje na PC
    - Przygotuj metodę `smooth_move_to` z parametrem kroku i opóźnienia do inkrementalnych ruchów Safe Start.
  </action>
  <verify>python -c "import src.hardware; print('Hardware Valid')"</verify>
  <done>Silnik operuje w trybie hardware PWM a jeśli zawiedzie - wchodzi w tryb mock bez crashu.</done>
</task>

## Success Criteria
- [x] Oprogramowanie nie wiesza się przy braku linuxowego demona I/O na Windows.
- [x] Ostre wpięcia w prąd niwelowane są metodą inkrementalną `smooth_move_to`.
