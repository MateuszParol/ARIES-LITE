---
phase: 21-wizja-rpi-mediapipe
plan: 02
subsystem: vision
tags: [brain, mediapipe, serial-tx, heartbeat, hud, signal-handler, pid-loop]

# Dependency graph
requires:
  - phase: 21-01
    provides: KameraRPi + WykrywaczTwarzy — kamera Picamera2 i detektor MediaPipe
  - phase: 19-serial-link-echo-test
    provides: SerialInterface — wyslanie ramek 8B do Arduino

provides:
  - MozgRPi — synchroniczna petla kamera->detekcja->error->serial TX z heartbeat 200ms
  - run_pi_brain.py — entry point z SIGINT/SIGTERM graceful shutdown

affects:
  - Zamkniecie petli sterowania RPi→Arduino dla calej fazy 21
  - run_pi_brain.py jako glowny punkt wejscia systemu v2.0

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Mutowalny ref (lista [float]) jako wspoldzielony zegar TX miedzy petla glowna a WatekHeartbeat
    - Guard _zatrzymano przeciw podwojnemu wywolaniu zatrzymaj() z signal handlera + uruchom()
    - Monotoniczny timestamp time.monotonic_ns()//1_000_000 dla detect_for_video() (Pitfall 3)
    - Headless fallback: try cv2.imshow except cv2.error -> _headless=True (D-03)

key-files:
  created:
    - src/vision/brain.py
    - run_pi_brain.py
  modified: []

key-decisions:
  - "Mutowalny ref [float] zamiast threading.Event dla czasu TX — prostszy mechanizm synchronizacji miedzy petla glowna a WatekHeartbeat"
  - "Heartbeat wysyla MODE_SCAN (nie MODE_IDLE) — per D-07, Arduino interpretuje kazda ramke jako dowod zywotnosci i skanuje gdy brak twarzy"
  - "Serial open non-fatal — brak portu szeregowego loguje warning i system dziala bez TX (developerski mock mode)"

# Metrics
duration: ~4 min
completed: 2026-03-31
---

# Phase 21 Plan 02: MozgRPi + run_pi_brain.py — SUMMARY

**MozgRPi — synchroniczna petla kamera->detekcja->error->serial TX z daemon WatekHeartbeat 200ms, HUD z headless fallback i graceful shutdown przez SIGINT/SIGTERM**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-31T07:59:19Z
- **Completed:** 2026-03-31T08:03:09Z
- **Tasks:** 2/2
- **Files modified:** 2 created

## Accomplishments

- MozgRPi w `src/vision/brain.py`: synchroniczna petla sterowania `kamera.odczytaj()` -> `detektor.wykryj()` -> `detektor.wybierz_twarz()` -> `_oblicz_error()` -> `serial.send_frame()` z trybami TRACK i SCAN
- WatekHeartbeat: daemon thread wysylajacy `send_frame(mode=SCAN)` co 200ms gdy petla glowna nie wysyla ramek (brak twarzy lub duzy processing time)
- `_oblicz_error()`: blad X/Y sklamowany do -160..+160 / -120..+120 z skalowaniem dla niestandardowych rozdzielczosci, face_size jako uint8 area_ratio*255
- `_rysuj_hud()`: bbox, crosshair, tryb/error X/Y/FPS z headless fallback przy `cv2.error` (brak wyswietlacza)
- `zatrzymaj()`: thread-safe pod GIL, guard `_zatrzymano` przeciw podwojnemu wywolaniu (signal handler + `uruchom()`)
- `run_pi_brain.py`: entry point z SIGINT/SIGTERM handlerem wywolujacym `mozg.zatrzymaj()`, z komentarzem dokumentujacym wzorzec thread-safety

## Task Commits

Kazde zadanie zatwierdzone atomicznie:

1. **Task 1: MozgRPi — glowna petla sterowania + heartbeat + HUD** - `113be36` (feat)
2. **Task 2: Entry point run_pi_brain.py z signal handlers** - `1a10ed7` (feat)

## Files Created/Modified

- `/home/parolisko/ARIES-LITE/src/vision/brain.py` — MozgRPi: petla glowna, WatekHeartbeat, _oblicz_error, _rysuj_hud, zatrzymaj() z guardem
- `/home/parolisko/ARIES-LITE/run_pi_brain.py` — Entry point: MozgRPi + SIGINT/SIGTERM + logging

## Decisions Made

- **Mutowalny ref [float] dla czasu TX:** Lista jednoelemntowa `[0.0]` wspodzielona miedzy MozgRPi a WatekHeartbeat — prostszy mechanizm niz Event/Condition, thread-safe dla odczytu float pod GIL
- **Heartbeat wysyla MODE_SCAN:** Per D-07 — Arduino interpretuje kazda poprawna ramke jako dowod zywotnosci RPi. Gdy brak twarzy, RPi poprawnie sygnalizuje tryb skanowania zamiast IDLE
- **Serial open non-fatal:** Blad otwarcia portu szeregowego jest logowany jako warning, system kontynuuje bez TX — umozliwia testowanie wizji na desktopie bez Arduino

## Deviations from Plan

Brak odchylen — plan wykonany dokladnie zgodnie ze specyfikacja.

## Known Stubs

Brak. `MozgRPi` jest kompletna implementacja petli sterowania — integruje KameraRPi, WykrywaczTwarzy i SerialInterface z pelna logiką TX.

## Self-Check: PASSED

- `src/vision/brain.py` — istnieje, 353 linii
- `run_pi_brain.py` — istnieje, 50 linii
- Commit `113be36` — zweryfikowany w git log
- Commit `1a10ed7` — zweryfikowany w git log
