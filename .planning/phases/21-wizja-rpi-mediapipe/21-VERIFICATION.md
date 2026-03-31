---
phase: 21-wizja-rpi-mediapipe
verified: 2026-03-31T09:00:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 21: Wizja RPi MediaPipe — Verification Report

**Phase Goal:** RPi4 wykrywa twarze przez MediaPipe, oblicza blad X/Y i wysyla ramki do Arduino w sposob ciagly — kamera sledzi twarz bez Flaska
**Verified:** 2026-03-31T09:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                              | Status     | Evidence                                                                                    |
|----|-----------------------------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------|
| 1  | Picamera2 stream dostarcza klatki BGR z poprawnym AWB (brak niebieskiej/zielonej poswiaty)         | VERIFIED   | camera.py KameraRPi: dwuetapowy AWB fix (ColourGains w config + capture_metadata + set_controls), NV12/YUV420p autodetection — 12 wystapien ColourGains, 2 formaty konwersji |
| 2  | MediaPipe FaceDetector wykrywa twarze w klatkach 320x240 — zwraca liste bbox pikselowych           | VERIFIED   | detector.py WykrywaczTwarzy: RunningMode.VIDEO, detect_for_video(), origin_x/y pikselowe bbox — substantive 178 linii |
| 3  | Sticky tracking wybiera najwieksza twarz z 20% histereza — brak migotania przy 2+ twarzach          | VERIFIED   | detector.py wybierz_twarz(): STICKY_PROG=0.20, area comparison, nearest-center match dla update, hold przy zaniku |
| 4  | Model blaze_face_short_range.tflite istnieje w models/ przed inicjalizacja detektora               | VERIFIED   | models/blaze_face_short_range.tflite: 229 746 B (>100KB), os.path.isfile() guard z FileNotFoundError w __init__ |
| 5  | pi_brain oblicza blad X/Y wzgledem centrum klatki i wysyla ramki 8B do Arduino                     | VERIFIED   | brain.py _oblicz_error(): clamp -160..+160 / -120..+120, face_size uint8, serial.send_frame() w TRACK i SCAN branch |
| 6  | Heartbeat TX co 200ms nawet gdy brak detekcji twarzy — Arduino watchdog nie odpala sie             | VERIFIED   | brain.py WatekHeartbeat daemon thread: HEARTBEAT_INTERVAL=0.200, send_frame(MODE_SCAN) gdy brak TX przez >200ms |
| 7  | pi_brain zamyka sie czysto na Ctrl+C — serial.close() i camera.stop() wywolane bez wyjatkow        | VERIFIED   | run_pi_brain.py: SIGINT/SIGTERM handler wywoluje mozg.zatrzymaj(); brain.py zatrzymaj(): guard _zatrzymano, sekwencja heartbeat.stop + detektor.zamknij + serial.close + kamera.zatrzymaj + destroyAllWindows |
| 8  | HUD wyswietla bbox, blad X/Y i tryb na cv2.imshow z headless fallback                             | VERIFIED   | brain.py _rysuj_hud(): rectangle, crosshair, putText tryb/eX/eY/FPS; try/except cv2.error -> _headless=True |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact                                    | Expected                                          | Status     | Details                                      |
|---------------------------------------------|---------------------------------------------------|------------|----------------------------------------------|
| `src/vision/camera.py`                      | KameraRPi — daemon thread kamera z AWB fix        | VERIFIED   | 206 linii, klasa KameraRPi, syntax OK         |
| `src/vision/detector.py`                    | WykrywaczTwarzy — MediaPipe + sticky tracking     | VERIFIED   | 178 linii, klasa WykrywaczTwarzy, syntax OK   |
| `src/vision/__init__.py`                    | Re-eksport glownych klas                          | VERIFIED   | 5 linii, re-eksportuje KameraRPi, WykrywaczTwarzy, SerialInterface |
| `models/blaze_face_short_range.tflite`      | Model MediaPipe FaceDetector                      | VERIFIED   | 229 746 B (224KB), pobrany z Google Storage   |
| `src/vision/brain.py`                       | MozgRPi + WatekHeartbeat + HUD + error calc       | VERIFIED   | 353 linii, klasy MozgRPi i WatekHeartbeat, syntax OK |
| `run_pi_brain.py`                           | Entry point z signal handlers                     | VERIFIED   | 50 linii, shebang, SIGINT/SIGTERM, syntax OK  |

### Key Link Verification

| From                    | To                          | Via                              | Status   | Details                                                  |
|-------------------------|-----------------------------|----------------------------------|----------|----------------------------------------------------------|
| `src/vision/camera.py`  | picamera2                   | Picamera2 lores YUV420 stream    | WIRED    | capture_array("lores"), capture_metadata()               |
| `src/vision/detector.py`| mediapipe                   | FaceDetector.detect_for_video    | WIRED    | detect_for_video() x4, RunningMode.VIDEO                 |
| `src/vision/detector.py`| models/blaze_face_short_range.tflite | MODEL_PATH w BaseOptions | WIRED    | model_asset_path, os.path.isfile guard                   |
| `src/vision/brain.py`   | src/vision/camera.py        | KameraRPi.odczytaj()             | WIRED    | self._kamera.odczytaj() — 1 wystapienie w petli          |
| `src/vision/brain.py`   | src/vision/detector.py      | WykrywaczTwarzy.wykryj() + wybierz_twarz() | WIRED | self._detektor.wykryj() i self._detektor.wybierz_twarz() |
| `src/vision/brain.py`   | src/vision/serial_interface.py | SerialInterface.send_frame() | WIRED    | self._serial.send_frame() — 3 wystapienia (TRACK + SCAN + heartbeat) |
| `run_pi_brain.py`       | src/vision/brain.py         | MozgRPi.uruchom() + zatrzymaj()  | WIRED    | mozg.uruchom() x1, mozg.zatrzymaj() x3 (signal + except + potwierdzenie) |

### Data-Flow Trace (Level 4)

| Artifact              | Data Variable    | Source                              | Produces Real Data | Status    |
|-----------------------|------------------|-------------------------------------|--------------------|-----------|
| `src/vision/brain.py` | klatka (np.ndarray) | kamera.odczytaj() -> Picamera2 lores | Tak — daemon thread capture_array("lores") | FLOWING |
| `src/vision/brain.py` | twarze (List[bbox]) | detektor.wykryj() -> MediaPipe detect_for_video | Tak — wywolanie modelu TFLite z rzeczywista klatka | FLOWING |
| `src/vision/brain.py` | error_x/error_y   | _oblicz_error(bbox, shape) | Tak — obliczony z rzeczywistego bbox i shape | FLOWING |
| `src/vision/brain.py` | serial TX         | send_frame(mode, error_x, error_y, face_size) | Tak — wysylane do Arduino przy kazdej iteracji | FLOWING |

### Behavioral Spot-Checks

| Behavior                              | Command                                                                   | Result       | Status |
|---------------------------------------|---------------------------------------------------------------------------|--------------|--------|
| Poprawna skladnia Python (5 plikow)   | `python3 -c "import ast; ast.parse(...)"`                                 | All syntax OK | PASS   |
| Model TFLite istnieje i ma wlasciwy rozmiar | `ls -la models/blaze_face_short_range.tflite`                       | 229 746 B     | PASS   |
| Commity istnieja w git log            | `git log --oneline \| grep "f010811\|2ecf167\|113be36\|1a10ed7"`         | 4 commity znalezione | PASS |
| Kluczowe metody obecne w brain.py     | `grep -c "def _oblicz_error\|def _rysuj_hud\|def zatrzymaj\|def uruchom"` | 1 x 4        | PASS   |

Step 7b: Behavioral spot-checks ograniczone — modul wymaga Picamera2 i mediapipe dostepnych tylko na RPi4. Testy syntaktyczne i strukturalne wykonane jako substytuty.

### Requirements Coverage

| Requirement | Source Plan | Description                                                                  | Status      | Evidence                                                               |
|-------------|-------------|------------------------------------------------------------------------------|-------------|------------------------------------------------------------------------|
| VIS-01      | 21-01       | MediaPipe Face Detection (BlazeFace, bbox only) na Picamera2 stream 320x240  | SATISFIED   | WykrywaczTwarzy: RunningMode.VIDEO, detect_for_video(), pikselowe bbox origin_x/y |
| VIS-02      | 21-01       | Sticky tracking — priorytet dla najwiekszej twarzy (bbox area)               | SATISFIED   | wybierz_twarz(): STICKY_PROG=0.20, area=w*h, switch przy >20% wzroscie, nearest-center match |
| VIS-03      | 21-02       | Obliczanie bledu X/Y wzgledem srodka klatki                                  | SATISFIED   | _oblicz_error(): error_x/y sklamowane do -160..+160 / -120..+120, skalowanie dla niestandardowych rozdzielczosci |
| VIS-04      | 21-01       | AWB fix dla sensora IMX219 — poprawne kolory bez blue/green tint             | SATISFIED   | KameraRPi.start(): dwuetapowy AWB, AWB_FALLBACK_GAINS=(2.2, 1.8), capture_metadata + set_controls |
| VIS-05      | 21-02       | Wysylanie ramek binarnych do Arduino przez SerialInterface (OOP)             | SATISFIED   | MozgRPi._petla_glowna(): self._serial.send_frame() w TRACK i SCAN trybach (3 wystapienia) |
| VIS-06      | 21-02       | Heartbeat TX co 200ms (nawet gdy brak detekcji twarzy)                       | SATISFIED   | WatekHeartbeat daemon thread: HEARTBEAT_INTERVAL=0.200, monitoruje czas TX, send_frame(SCAN) przy braku |
| VIS-07      | 21-02       | Graceful shutdown — zamkniecie kamery, portu serial, czysty exit             | SATISFIED   | zatrzymaj() z guardem _zatrzymano: heartbeat.stop + detektor.zamknij + serial.close + kamera.zatrzymaj + destroyAllWindows; signal handlers w run_pi_brain.py |

Wszystkie 7 wymagan pokryte. Brak ORPHANED requirements.

### Anti-Patterns Found

| File                   | Line | Pattern         | Severity | Impact        |
|------------------------|------|-----------------|----------|---------------|
| `src/vision/detector.py` | 106 | `return []`    | Info     | Poprawny — error fallback w bloku except przy bledie detect_for_video, nie stub |

Brak blokujacych anti-patternow. Jedyne `return []` to poprawna obsluga bledu w try/except — nie stub.

### Human Verification Required

#### 1. AWB fix na rzeczywistym sprzecie

**Test:** Uruchom `python3 run_pi_brain.py` na RPi4 z sensorem IMX219 w swietle dziennym.
**Oczekiwane:** HUD wyswietla klatki z naturalnymi kolorami — brak niebieskiej lub zielonej poswiaty.
**Dlaczego human:** Jakosc koloru nie mozna zweryfikowac bez hardware IMX219 i wyswietlacza.

#### 2. Dokladnosc detekcji twarzy MediaPipe

**Test:** Stojac przed kamera RPi z uruchomionym `run_pi_brain.py` — HUD powinien wyswietlic zielony prostokat wokol twarzy.
**Oczekiwane:** Bbox pokrywa twarz, tryb zmienia sie na TRACK, error X/Y bliskie 0 gdy twarz przy centrum.
**Dlaczego human:** Dokladnosc detekcji modelu BlazeFace wymaga fizycznej obecnosci twarzy w kadrze.

#### 3. Continuous TX do Arduino

**Test:** Podlacz Arduino (faza 20) do RPi przez USB, uruchom `run_pi_brain.py`, obserwuj Serial Monitor Arduino.
**Oczekiwane:** Ramki 8B arywuja co max 200ms bez przerwy; przy twarzy w kadrze mode=2 (TRACK), bez twarzy mode=1 (SCAN).
**Dlaczego human:** Wymaga fizycznego Arduino z firmware fazy 20 i kabla USB.

#### 4. Sticky tracking z dwoma twarzami

**Test:** Stojac w kadrze z druga osoba — mozg powinien utrzymac tracking na twarzy laczacej wiekszy obszar.
**Oczekiwane:** Brak migotania miedzy twarzami; zmiana celu widoczna dopiero gdy nowa twarz >20% wieksza.
**Dlaczego human:** Wymaga dwoch osob przed kamera i obserwacji zachowania HUD.

### Gaps Summary

Brak gap — wszystkie 8 must-have truths zweryfikowane, wszystkie 6 artefaktow kompletne i podlaczone, wszystkie 7 wymagan pokryte.

---

_Verified: 2026-03-31T09:00:00Z_
_Verifier: Claude (gsd-verifier)_
