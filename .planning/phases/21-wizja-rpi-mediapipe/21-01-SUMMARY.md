---
phase: 21-wizja-rpi-mediapipe
plan: 01
subsystem: vision
tags: [mediapipe, picamera2, blazeface, tflite, awb, sticky-tracking, yuv420, imx219]

# Dependency graph
requires:
  - phase: 19-serial-link-echo-test
    provides: SerialInterface — gotowy modul do wysylania ramek binarnych do Arduino
  - phase: 20-firmware-arduino-pid-servo
    provides: Firmware Arduino gotowe — odbiera ramki binarnie przez USB Serial

provides:
  - KameraRPi — Picamera2 daemon thread lores 320x240, dwuetapowy AWB fix dla IMX219, NV12/YUV420p autodetection
  - WykrywaczTwarzy — MediaPipe FaceDetector Tasks API VIDEO mode, wykryj() z BGR->RGB, wybierz_twarz() z 20% sticky histereza
  - models/blaze_face_short_range.tflite — model BlazeFace (225KB, Google Storage)
  - src/vision/__init__.py — re-eksport KameraRPi, WykrywaczTwarzy, SerialInterface

affects:
  - 21-02 (brain.py uzywa KameraRPi i WykrywaczTwarzy z tego planu)
  - run_pi_brain.py (entry point fazy 21)

# Tech tracking
tech-stack:
  added:
    - mediapipe (BlazeFace FaceDetector, Tasks API, MODEL blaze_face_short_range.tflite 225KB)
  patterns:
    - Picamera2 daemon thread z AWB fix (dwuetapowy: ColourGains w konfiguracji + re-lock po 2s warmup)
    - NV12/YUV420p autodetection (cv2.COLOR_YUV2BGR_NV12 probe first, fallback COLOR_YUV420p2BGR)
    - MediaPipe Tasks API VIDEO mode (synchroniczny detect_for_video() z monotonicznym timestamp_ms)
    - Sticky tracking z 20% histereza (area = w*h, switch tylko gdy nowy cel >20% wiekszy)
    - FileNotFoundError z instrukcja wget przy braku modelu TFLite

key-files:
  created:
    - src/vision/camera.py
    - src/vision/detector.py
    - src/vision/__init__.py
    - models/blaze_face_short_range.tflite
  modified: []

key-decisions:
  - "NV12 probe first zamiast YUV420p: Bookworm Picamera2 moze zwracac NV12 format — try COLOR_YUV2BGR_NV12, fallback COLOR_YUV420p2BGR przy cv2.error"
  - "AWB_FALLBACK_GAINS=(2.2, 1.8) — empiryczne dla IMX219 w swietle dziennym (per legacy test_tracker)"
  - "Sticky tracking w WykrywaczTwarzy (nie MozgRPi) — detector jest odpowiednim miejscem dla selekcji celu"
  - "STICKY_PROG=0.20 — 20% histereza rekomendowana przez Research D-06"

patterns-established:
  - "Pattern: Picamera2 AWB fix — create_video_configuration z ColourGains + sleep(2) + capture_metadata + set_controls"
  - "Pattern: MediaPipe Tasks API VIDEO — FaceDetectorOptions z RunningMode.VIDEO, detect_for_video() z rosnacym timestamp_ms"
  - "Pattern: Sticky tracking — area=(w*h), switch przy area_max > area_sticky*(1+STICKY_PROG), nearest-center match dla update"
  - "Pattern: Model walidacja w __init__ — FileNotFoundError z instrukcja pobrania przed inicjalizacja detektora"

requirements-completed: [VIS-01, VIS-02, VIS-04]

# Metrics
duration: 43min
completed: 2026-03-31
---

# Phase 21 Plan 01: Modul kamery i detektora twarzy — SUMMARY

**Picamera2 daemon thread z dwuetapowym AWB fix i MediaPipe BlazeFace FaceDetector (Tasks API VIDEO) ze sticky tracking 20% histereza — fundament wizji RPi4 dla architektury rozproszonej**

## Performance

- **Duration:** ~43 min
- **Started:** 2026-03-31T07:13:16Z
- **Completed:** 2026-03-31T07:55:53Z
- **Tasks:** 2/2
- **Files modified:** 4 created

## Accomplishments

- KameraRPi: Picamera2 daemon thread lores 320x240 z dwuetapowym AWB fix (ColourGains w konfiguracji + re-lock po 2s warmup) i NV12/YUV420p autodetection
- WykrywaczTwarzy: MediaPipe FaceDetector Tasks API VIDEO mode — wykryj() z BGR->RGB konwersja, pikselowe bbox z bounding_box.origin_x/y, wybierz_twarz() z 20% sticky histereza
- Model blaze_face_short_range.tflite (225KB) pobrany do models/ z Google Storage — walidacja istnienia przed inicjalizacja detektora
- src/vision/__init__.py re-eksportuje KameraRPi, WykrywaczTwarzy, SerialInterface jako unified API modulu wizji

## Task Commits

Kazde zadanie zatwierdzone atomicznie:

1. **Task 1: Modul kamery Picamera2 z AWB fix** - `f010811` (feat)
2. **Task 2: Pobranie modelu MediaPipe + modul detektora + sticky tracking** - `2ecf167` (feat)

## Files Created/Modified

- `/home/parolisko/ARIES-LITE/src/vision/camera.py` — KameraRPi: daemon thread Picamera2, dwuetapowy AWB fix, NV12/YUV420p, odczytaj()/zatrzymaj()
- `/home/parolisko/ARIES-LITE/src/vision/detector.py` — WykrywaczTwarzy: MediaPipe Tasks API VIDEO, wykryj(), wybierz_twarz() sticky, zamknij()
- `/home/parolisko/ARIES-LITE/src/vision/__init__.py` — Re-eksport KameraRPi, WykrywaczTwarzy, SerialInterface
- `/home/parolisko/ARIES-LITE/models/blaze_face_short_range.tflite` — Model BlazeFace 225KB (pobrany z Google Storage)

## Decisions Made

- **NV12/YUV420p autodetection:** Uzywamy try/except na cv2.COLOR_YUV2BGR_NV12 i fallback na cv2.COLOR_YUV420p2BGR — Bookworm + nowsze wersje Picamera2 moga zwracac NV12 zamiast YUV420p, kod musi obsluzyc oba formaty bez konfiguracji
- **Sticky tracking w WykrywaczTwarzy:** Selekcja celu logicznie nalezy do detektora (nie do brain.py) — bardziej modularny design, brain.py po prostu wywoluje wybierz_twarz()
- **FileNotFoundError z instrukcja wget:** Zamiast cichego fail lub ogolnego bledu — podajemy dokladna komende wget do uruchomienia, co przyspiesza debug na RPi

## Deviations from Plan

Brak odchylen — plan wykonany dokladnie zgodnie ze specyfikacja.

## Issues Encountered

Brak. Model pobrany bez problemow (225KB), wzorzec AWB i API MediaPipe zgodne z Research.

## Known Stubs

Brak. Moduly sa kompletne — KameraRPi dostarcza klatki BGR, WykrywaczTwarzy wykrywa twarze. Integracja z brain.py (Plan 02) bedzie uzywala tych modulow bez mockowania.

## User Setup Required

Przed uruchomieniem na RPi4 wymagane:
1. `pip install mediapipe` (lub wheel z PINTO0309 dla aarch64)
2. `sudo apt install python3-picamera2` (system package)
3. Model juz pobrany: `models/blaze_face_short_range.tflite` (225KB)
4. Venv z `--system-site-packages` dla dostepnosci picamera2

## Next Phase Readiness

- src/vision/camera.py i src/vision/detector.py gotowe — Plan 02 (brain.py) moze je importowac bezposrednio
- src/vision/__init__.py: `from src.vision import KameraRPi, WykrywaczTwarzy, SerialInterface`
- Brak blokow dla fazy 21 Plan 02

---
*Phase: 21-wizja-rpi-mediapipe*
*Completed: 2026-03-31*
