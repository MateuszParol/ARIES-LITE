# Phase 6: Diagnostics & Camera - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Dwie chirurgiczne poprawki:
1. Dodanie logowania WARNING w `set_angles()` (`src/hardware.py`) gdy wartość jest obcinana do soft-limitu
2. Dodanie warm-up AWB + lock ColourGains w `Picamera2Stream.start()` (`src/modes/test_tracker.py`)

Faza NIE zmienia logiki PID, stanu maszyny, detekcji HAAR ani żadnego innego zachowania systemu. Tylko diagnostyka i kalibracja koloru.

</domain>

<decisions>
## Implementation Decisions

### Clamp logging (DIAG-01)
- Loguj **każde** przekroczenie limitu — bez rate-limitowania, bez dodatkowego stanu
- Format: **osobne linie per oś** — np.:
  - `WARNING: Clamp pan: 75.0 → 60.0 (limit)`
  - `WARNING: Clamp tilt: -35.0 → -30.0 (limit)`
- Log aktywny **zawsze** — niezależnie od trybu mock/hardware
- Loguj tylko osie, które faktycznie zostały obcięte (nie obie jeśli tylko jedna przekroczyła limit)

### AWB warm-up (CAM-01)
- Warm-up żyje w **`Picamera2Stream.start()`** — metoda blokuje ~2 sekundy zanim zwróci
- Kamera startuje od razu i **pokazuje klatki podczas oczekiwania** (nieokalibrowane przez pierwsze ~2 sekundy — akceptowalne)
- Dwa komunikaty w terminalu:
  - INFO przed: `"Czekam na stabilizację AWB (2s)..."`
  - INFO po: `"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})"` (z faktycznymi wartościami)
- `set_controls({"ColourGains": gains})` wywoływane PO `picam2.start()` + `time.sleep(2.0)` — NIE przed startem

### Fallback ColourGains (CAM-02)
- Gdy `capture_metadata()["ColourGains"]` zwróci `None` — użyj wartości fallback
- Fallback jako **stała modułowa** na górze `test_tracker.py` obok innych stałych:
  ```python
  AWB_FALLBACK_GAINS = (2.5, 1.9)  # (Red, Blue) — fallback gdy sensor nie zwróci gains
  ```
- Log: **WARNING** (nie INFO) — `"ColourGains niedostępne, używam fallback (2.5, 1.9)"`
- NIE dodawać `AwbEnable: False` do `set_controls()` — powoduje konflikt sekwencjonowania ISP

### Claude's Discretion
- Dokładna kolejność operacji wewnątrz `Picamera2Stream.start()` (start → sleep → metadata → set_controls vs inne warianty)
- Nazewnictwo zmiennych dla wartości gains

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PanTiltSystem.set_angles()` (`src/hardware.py:41`): Metoda do modyfikacji — dodać logging przed/po obcięciu wartości
- `Picamera2Stream.start()` (`src/modes/test_tracker.py:63`): Metoda do rozszerzenia — warm-up AWB po `self._picam2.start()`
- Stałe modułowe w `test_tracker.py:24-34`: Wzorzec dla nowej stałej `AWB_FALLBACK_GAINS`

### Established Patterns
- Logging WARNING: `logger.warning(f"...")` — używane w projekcie dla degraded operation
- Logging INFO: `logger.info(f"...")` — używane dla state transitions i inicjalizacji
- Stałe modułowe UPPER_SNAKE_CASE na górze pliku przed klasami
- Mock mode: `set_angles()` woła `self.pan_servo.angle = ...` tylko gdy `not self._mock_mode` — ale obcięcie i logowanie odbywa się przed tym sprawdzeniem, więc WARNING pojawi się zawsze

### Integration Points
- `set_angles()` wywoływane przez `MaszynaStanow._sledz()` i `smooth_move_to()` — obie ścieżki skorzystają automatycznie z nowego logowania
- `Picamera2Stream.start()` wywoływane z `TestTracker.uruchom()` — warm-up jest transparentny dla wywołującego

</code_context>

<specifics>
## Specific Ideas

- Fallback gains (2.5, 1.9) mogą wymagać empirycznej korekty dla konkretnego oświetlenia — stała modułowa ułatwia dostrojenie
- Clamp WARNING per oś pozwala łatwo grep'ować: `grep "Clamp pan"` vs `grep "Clamp tilt"`

</specifics>

<deferred>
## Deferred Ideas

Brak — dyskusja pozostała w granicach fazy.

</deferred>

---

*Phase: 06-diagnostics-camera*
*Context gathered: 2026-03-27*
