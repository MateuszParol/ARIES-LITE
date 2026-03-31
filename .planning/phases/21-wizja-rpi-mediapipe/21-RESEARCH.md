# Phase 21: Wizja RPi MediaPipe - Research

**Researched:** 2026-03-31
**Domain:** MediaPipe FaceDetector + Picamera2 + SerialInterface na RPi4 aarch64
**Confidence:** MEDIUM (instalacja MediaPipe na aarch64 wymaga weryfikacji empirycznej na RPi; wzorce kamery i serial HIGH)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Kod podzielony na moduly w `src/vision/`: osobne pliki dla kamery (Picamera2), detektora (MediaPipe), i glownej logiki (brain). SerialInterface juz istnieje w `src/vision/serial_interface.py`.
- **D-03:** Podglad wideo z HUD (cv2.imshow) jak w legacy test_tracker: bbox, blad X/Y, tryb. Headless fallback gdy brak monitora.
- **D-07:** Brak detekcji twarzy = wysylanie ramki z mode=SCAN (1). Arduino skanuje autonomicznie (Lissajous). Heartbeat utrzymywany co 200ms nawet bez twarzy — watchdog Arduino nie odpala sie.

### Claude's Discretion

- **D-02:** Glowna petla sterowania (synchroniczna while-loop vs callback Picamera2 vs asyncio)
- **D-04:** Strategia AWB fix (sleep+metadata vs stale ColourGains vs inne podejscie)
- **D-05:** Rozdzielczosc Picamera2 (domyslnie 320x240 — jezeli inna, przeskalowac blad do zakresu -160..+160)
- **D-06:** Strategia sticky tracking (najwieksza bbox area vs centrum vs hybryda z histereza)
- **D-08:** Mechanizm heartbeat (millis check w glownej petli vs osobny watek)

### Deferred Ideas (OUT OF SCOPE)

- Flask/web UI (v2.1 WEB-01)
- LCD/buzzer/przycisk HMI (Phase 22)
- Kalibracja kierunkow serw (Phase 23)
- Zmiany w firmware Arduino (Phase 20 complete)

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VIS-01 | MediaPipe Face Detection (BlazeFace, bbox only) na Picamera2 stream 320x240 | Wzorzec Tasks API + Picamera2 Stream z legacy — sekcja Architecture Patterns |
| VIS-02 | Sticky tracking — priorytet dla najwiekszej twarzy (bbox area), stabilne sledzenie przy wielu twarzach | Strategia sticky z histereza — sekcja Claude's Discretion Recommendations |
| VIS-03 | Obliczanie bledu X/Y wzgledem srodka klatki (znormalizowane do zakresu ramki) | Wzor bledu + skalowanie do int16 -160..+160 — sekcja Code Examples |
| VIS-04 | AWB fix dla sensora IMX219 — poprawne kolory bez blue/green tint | Dwuetapowa strategia ColourGains — sekcja Architecture Patterns |
| VIS-05 | Wysylanie ramek binarnych do Arduino przez SerialInterface (OOP) | SerialInterface gotowy — sekcja Standard Stack + Code Examples |
| VIS-06 | Heartbeat TX co 200ms (nawet gdy brak detekcji twarzy) | Osobny watek daemon z Event stop — sekcja Claude's Discretion Recommendations |
| VIS-07 | Graceful shutdown — zamkniecie kamery, portu serial, czysty exit | SIGINT/SIGTERM pattern z legacy test_tracker — sekcja Architecture Patterns |

</phase_requirements>

---

## Summary

Phase 21 buduje `pi_brain.py` — glowny modul wizji RPi4 laczącej Picamera2, MediaPipe FaceDetector i SerialInterface w jeden potok sterowania. Architektura jest celowo wzorowana na legacy `test_tracker.py`: kamera jako daemon thread z lockiem, synchroniczna petla glowna, HUD przez cv2.imshow z headless fallback, graceful shutdown przez SIGINT/SIGTERM.

Glowne ryzyko fazy to instalacja MediaPipe na RPi4 aarch64 z Python 3.11 — oficjalne kola PyPI nie publikuja linux_aarch64 wheeli, ale instalacja przez piwheels lub pip z platform tag negotiation dziala empirycznie na Bookworm + Python 3.11 (weryfikacja konieczna jako krok 0). Kluczowe decyzje pozostawione Claude: petla synchroniczna (zalecana dla prostoty), osobny watek heartbeat (gwarantowany interwal 200ms niezalezny od FPS detekcji), strategia sticky tracking przez pole bbox z histereza 20%.

Wzorzec API MediaPipe to Tasks API (`mp.tasks.vision.FaceDetector`) w trybie VIDEO — synchroniczny `detect_for_video()` z monotonicznym timestamp_ms. Bounding box wychodzi w koordynatach znormalizowanych [0,1]; error X/Y obliczany jako `int((center_norm - 0.5) * frame_width)` i clampowany do -160..+160 dla protokolu 8B.

**Primary recommendation:** Synchroniczna while-loop + daemon thread heartbeat. MediaPipe VIDEO mode z `detect_for_video()`. Sticky tracking przez area z 20% histereza. AWB: ColourGains w `create_video_configuration()` + re-lock po 2s.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mediapipe | 0.10.x (najnowszy) | BlazeFace FaceDetector — bbox detection | Google oficjalny, 12-30 FPS na RPi4 CPU. Zastepczo szybszy od res10_300x300 Caffe SSD. Tasks API (nie legacy solutions) |
| picamera2 | system package | Strumien klatki z sensora IMX219 | System apt — nie pip. Daemon thread z frame lock (wzorzec z legacy test_tracker) |
| pyserial | 3.5 | Wysylanie ramek 8B do Arduino via /dev/ttyACM0 | Juz zainstalowany w venv. DTR=False + low_latency — zachowane z SerialInterface |
| numpy | >=1.24,<2.0 (pinned) | Operacje na tablicach klatek | KRYTYCZNE: mediapipe 0.10.x ma hard dependency `numpy <2.0`. Nie podnosic do 2.x |
| opencv-python-headless | 4.8.x | cvtColor YUV→BGR, cv2.imshow HUD, cv2.rectangle | Juz zainstalowany. Headless variant — imshow dziala o ile DISPLAY dostepny |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| simple-pid | >=2.0.1 | PID na RPi (jezeli pi_brain steruje serwami bezposrednio) | NIE w Phase 21 — PID jest na Arduino. Nie importowac w pi_brain |
| threading | stdlib | Daemon thread kamery + heartbeat thread | Zawsze — pattern z legacy |
| signal | stdlib | SIGINT/SIGTERM graceful shutdown | Zawsze — pattern z legacy zatrzymaj() |
| time | stdlib | sleep AWB warmup, millis dla timestamp_ms | Zawsze |
| struct | stdlib | SerialInterface wewnetrznie uzywa struct.pack | Nie importowac bezposrednio w brain — SerialInterface to opakowuje |
| logging | stdlib | logger = logging.getLogger(__name__) w kazdym module | Zawsze — projekt standard |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| MediaPipe Tasks API VIDEO mode | LIVE_STREAM mode (async callback) | LIVE_STREAM wymaga callback + osobnego watku wyniku — znacznie bardziej skomplikowane. VIDEO sync jest prostszy i wystarczajacy |
| Osobny watek heartbeat | millis check w glownej petli | Glowna petla moze trwac >200ms gdy MediaPipe wolny (12 FPS = 83ms/klatka + overhead). Watek gwarantuje interwal bez wzgledu na FPS |
| Picamera2 lores + main | Tylko lores | lores YUV420 wystarczy do detekcji. main stream niepotrzebny — oszczednosc pamieci i latencji |

**Installation (RPi4 — Python 3.11 venv z --system-site-packages):**

```bash
# Krok 0: weryfikacja Python 3.11 w venv (mediapipe nie dziala na 3.13)
python3 --version  # musi byc 3.11.x

# Krok 1: standardowe pip (Bookworm + Python 3.11 + piwheels = czesto dziala)
pip install mediapipe

# Krok 1b (fallback jesli pip fail): PINTO0309 community wheel aarch64
pip install https://github.com/PINTO0309/mediapipe-bin/releases/download/v0.10.x/mediapipe-0.10.x-cp311-...-linux_aarch64.whl

# Weryfikacja po instalacji:
python3 -c "import mediapipe as mp; print('mediapipe', mp.__version__)"

# Krok 2: numpy pin (mediapipe wymaga <2.0)
python3 -c "import numpy; print(numpy.__version__)"
# Jezeli >=2.0: pip install "numpy<2.0"

# Pobierz model (wymagany przez Tasks API):
wget -O models/blaze_face_short_range.tflite \
  https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite
```

**Version verification (na RPi):**

```bash
pip show mediapipe | grep Version
pip show numpy | grep Version
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/vision/
├── __init__.py             # pusty lub re-eksport glownej klasy
├── serial_interface.py     # ISTNIEJACY — nie modyfikowac
├── camera.py               # Picamera2Stream (adapter z test_tracker)
├── detector.py             # WykrywaczTwarzy — MediaPipe FaceDetector wrapper
└── brain.py                # MozgRPi — glowna petla + sticky tracking + SerialTX
run_pi_brain.py             # entry point (root, wzorzec run_test_tracker.py)
models/
└── blaze_face_short_range.tflite   # model MediaPipe (nie w git jesli duzy)
```

### Pattern 1: Synchroniczna petla glowna (zalecana dla D-02)

**What:** Prosta while-loop: grab klatke → detect → sticky select → oblicz error → wyslij ramke serial. Brak asyncio, brak callbackow.

**When to use:** Zawsze — ProstaD-02 rekomendacja. Jedyny watek z logika to main thread. Heartbeat w osobnym daemon thread (patrz Pattern 4).

**Example:**

```python
# Wzorzec petli glownej (src/vision/brain.py)
# Source: adaptacja z legacy/src/modes/test_tracker.py:TestTracker.uruchom()

def _petla_glowna(self) -> None:
    """Glowna petla sterowania — kamera → detekcja → serial TX."""
    self._kamera.start()
    self._heartbeat.start()  # daemon thread

    logger.info("MozgRPi uruchomiony. Ctrl+C aby zatrzymac.")
    timestamp_ms: int = 0

    while self._running:
        klatka = self._kamera.odczytaj()
        if klatka is None:
            time.sleep(0.01)
            continue

        timestamp_ms += 33  # ~30 FPS monotoniczny (nie real time.time())

        # Detekcja MediaPipe — synchroniczna
        wykryte = self._detektor.wykryj(klatka, timestamp_ms)

        # Sticky tracking — wybor najwiekszej twarzy
        bbox = self._wybierz_twarz(wykryte)

        # Oblicz error i wyslij
        if bbox is not None:
            ex, ey, fs = self._oblicz_error(bbox, klatka.shape)
            self._serial.send_frame(mode=2, error_x=ex, error_y=ey, face_size=fs)
        else:
            self._serial.send_frame(mode=1, error_x=0, error_y=0, face_size=0)

        # HUD z headless fallback (D-03)
        self._rysuj_hud(klatka, bbox)
```

### Pattern 2: MediaPipe Tasks API — VIDEO mode (VIS-01)

**What:** FaceDetector w trybie VIDEO z monotonicznym timestamp_ms. Synchroniczny `detect_for_video()` — blokuje do uzyskania wyniku. Bounding box w koordynatach znormalizowanych [0,1].

**When to use:** W WykrywaczTwarzy.wykryj() — wywolywane z glownej petli.

**Example:**

```python
# src/vision/detector.py
# Source: https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector/python

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from typing import List, Optional, Tuple
import numpy as np

MODEL_PATH = "models/blaze_face_short_range.tflite"
MIN_CONFIDENCE = 0.5

class WykrywaczTwarzy:
    """Wrapper MediaPipe FaceDetector — Tasks API, tryb VIDEO."""

    def __init__(self, model_path: str = MODEL_PATH) -> None:
        opcje = mp_vision.FaceDetectorOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=mp_vision.RunningMode.VIDEO,
            min_detection_confidence=MIN_CONFIDENCE,
        )
        self._detektor = mp_vision.FaceDetector.create_from_options(opcje)
        logger.info(f"MediaPipe FaceDetector zaladowany: {model_path}")

    def wykryj(
        self, klatka_bgr: np.ndarray, timestamp_ms: int
    ) -> List[Tuple[int, int, int, int]]:
        """Wykrywa twarze w klatce BGR. Zwraca liste bbox (x,y,w,h) w pikselach.

        Args:
            klatka_bgr: Klatka OpenCV BGR (nie RGB).
            timestamp_ms: Monotoniczny timestamp w ms (musi rosnac).

        Returns:
            Lista (x, y, w, h) w pikselach dla kazdej wykrytej twarzy.
        """
        h, w = klatka_bgr.shape[:2]

        # MediaPipe wymaga RGB — konwersja z BGR
        klatka_rgb = cv2.cvtColor(klatka_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=klatka_rgb)

        wynik = self._detektor.detect_for_video(mp_image, timestamp_ms)

        twarze = []
        for det in wynik.detections:
            bb = det.bounding_box
            # bb.origin_x/y, bb.width, bb.height — wspolrzedne pikselowe (nie normalizowane)
            twarze.append((bb.origin_x, bb.origin_y, bb.width, bb.height))
        return twarze

    def zamknij(self) -> None:
        """Zamyka detektor (zwalnia zasoby TFLite)."""
        self._detektor.close()
```

**UWAGA:** W MediaPipe Tasks API bounding_box jest w pikselach (nie normalizowany), obliczone wzgledem oryginalnego rozmiaru obrazu.

### Pattern 3: Sticky tracking z histereza (VIS-02, D-06)

**What:** Wybor "najwiekszej twarzy" (area = w * h). Sticky selection: raz wybrany cel trzymany dopoki nie pojawi sie twarz >20% wieksza. Brak migotania przy 2+ twarzach w kadrze.

**When to use:** W metodzie `_wybierz_twarz()` w brain.py.

**Example:**

```python
# Strategia sticky tracking (w MozgRPi)
STICKY_PROG = 0.20  # 20% — wymagany wzrost obszaru do przeskoku celu

def _wybierz_twarz(
    self,
    twarze: List[Tuple[int, int, int, int]]
) -> Optional[Tuple[int, int, int, int]]:
    """Sticky selection — wybiera najwieksza twarz z histereza.

    Przeskakuje na nowy cel tylko gdy jest o STICKY_PROG% wiekszy.
    """
    if not twarze:
        self._sticky_id = None
        return None

    # Oblicz area kazdej twarzy
    obszary = [w * h for (x, y, w, h) in twarze]
    idx_max = obszary.index(max(obszary))
    twarz_max = twarze[idx_max]

    if self._sticky_bbox is None:
        # Brak poprzedniego celu — wybierz natychmiast
        self._sticky_bbox = twarz_max
        return twarz_max

    area_sticky = self._sticky_bbox[2] * self._sticky_bbox[3]
    area_max = obszary[idx_max]

    if area_max > area_sticky * (1.0 + STICKY_PROG):
        # Nowy cel wyraznie wiekszy — przeskocz
        logger.debug(f"Sticky switch: {area_sticky} → {area_max}")
        self._sticky_bbox = twarz_max

    # Szukaj sticky bbox wsrod aktualnych twarzy (update wspolrzednych)
    # Jezeli sticky zniknal — pozostan przy ostatniej pozycji (hold)
    return self._sticky_bbox
```

### Pattern 4: Heartbeat daemon thread (VIS-06, D-08)

**What:** Osobny daemon thread co 200ms wysyla send_frame(mode=SCAN) jezeli glowna petla nie wyslala. Gwarantuje interwal <=200ms nawet gdy MediaPipe wolny (12 FPS = 83ms/klatka).

**When to use:** Zawsze — watchdog Arduino wymaga ramek co maks 500ms.

**Example:**

```python
# src/vision/brain.py — heartbeat thread
# Source: threading.Event pattern dla daemon threads

import threading
import time

HEARTBEAT_INTERVAL = 0.200  # 200ms

class WatekHeartbeat(threading.Thread):
    """Daemon thread wysylajacy heartbeat SCAN co 200ms.

    Wysyla ramke SCAN jesli od ostatniej TX minely >= HEARTBEAT_INTERVAL.
    Glowna petla moze wysylac czesciej (kazda klatka z wykryta twarzą).
    """

    def __init__(self, serial_iface, czas_ostatniej_tx_ref: list) -> None:
        super().__init__(daemon=True, name="heartbeat")
        self._serial = serial_iface
        self._czas_ref = czas_ostatniej_tx_ref  # lista [float] — mutowalny ref
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            teraz = time.time()
            if teraz - self._czas_ref[0] >= HEARTBEAT_INTERVAL:
                try:
                    self._serial.send_frame(mode=1, error_x=0, error_y=0, face_size=0)
                    self._czas_ref[0] = teraz
                except Exception as e:
                    logger.error(f"Heartbeat TX blad: {e}")
            time.sleep(0.050)  # 50ms poll — narzut minimalny
```

### Pattern 5: AWB fix — dwuetapowy ColourGains (VIS-04, D-04)

**What:** Identyczny z legacy `Picamera2Stream.start()` w test_tracker.py. Etap 1: ColourGains w `create_video_configuration()` — neutralne od klatki 0. Etap 2: po 2s sleep `capture_metadata()` + `set_controls()` z rzeczywistymi gains sensora.

**When to use:** W KameraRPi.start() — bez wyjatkow.

**Example:**

```python
# src/vision/camera.py — AWB fix (identyczny z legacy test_tracker.py)
# Source: legacy/src/modes/test_tracker.py:Picamera2Stream.start() + Phase 11 CONTEXT.md

AWB_FALLBACK_GAINS = (1.0, 1.0)  # neutralne (0.0, 0.0) = re-enable AWB — NIGDY nie uzywac

def start(self) -> None:
    self._picam2 = Picamera2()
    konfiguracja = self._picam2.create_video_configuration(
        lores={"size": (self._szerokosc, self._wysokosc), "format": "YUV420"},
        controls={"ColourGains": AWB_FALLBACK_GAINS}  # neutralne od klatki 0
    )
    self._picam2.configure(konfiguracja)
    self._picam2.start()

    # Warmup AWB
    logger.info("Czekam na stabilizacje AWB (2s)...")
    time.sleep(2.0)
    metadata = self._picam2.capture_metadata()
    gains = metadata.get("ColourGains")
    if gains is None or gains == (0.0, 0.0):
        logger.warning("AWB still running, uzywam fallback (1.0, 1.0)")
        gains = AWB_FALLBACK_GAINS
    self._picam2.set_controls({"ColourGains": (float(gains[0]), float(gains[1]))})
    r, b = gains
    logger.info(f"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})")
```

### Pattern 6: Graceful shutdown (VIS-07)

**What:** SIGINT/SIGTERM handler wywoluje metodę `zatrzymaj()` ktora: zatrzymuje main loop, czeka na daemon threads (join z timeout), zamyka SerialInterface i Picamera2.

**When to use:** W entry point `run_pi_brain.py` — signal.signal() na SIGINT i SIGTERM.

**Example:**

```python
# run_pi_brain.py — signal handling
# Source: adaptacja z legacy test_tracker.py:zatrzymaj()

import signal

def _shutdown(mozg, sig, frame):
    logger.info(f"Sygnal {sig} — zatrzymuję system...")
    mozg.zatrzymaj()  # sets _running = False, closes serial + camera

mozg = MozgRPi()
signal.signal(signal.SIGINT, lambda s, f: _shutdown(mozg, s, f))
signal.signal(signal.SIGTERM, lambda s, f: _shutdown(mozg, s, f))
mozg.uruchom()  # blokuje do zatrzymaj()
```

### Anti-Patterns to Avoid

- **mp.solutions.face_detection (legacy API):** Deprecated w 0.10.x, do usuniecia w przyszlych wersjach. Uzywaj Tasks API (`mp.tasks.vision.FaceDetector`).
- **LIVE_STREAM mode z callbackiem:** Nadmiarowa zlozonosc — callback w osobnym watku, rezultat przez lock. VIDEO mode synchroniczny jest prostszy i rownie szybki na RPi4.
- **face_size obliczony z surowych pikseli bez normalizacji:** Protokol wymaga `face_size = int(area_ratio * 255 / 100)` gdzie `area_ratio = bbox_area / frame_area * 100`.
- **ColourGains (0.0, 0.0):** Picamera2 interpretuje jako "wlacz AWB" — resetuje lock. Zawsze fallback na (1.0, 1.0).
- **asyncio:** Picamera2 i MediaPipe sa blokujace — asyncio nie daje korzysci, dodaje zlozonosc. Unikac.
- **timestamp_ms = int(time.time() * 1000):** MediaPipe VIDEO wymaga MONOTONICZNIE ROSNACEGO timestamp. Jezeli system czas cofnie sie (NTP sync), detect_for_video rzuci wyjatek. Uzywac `time.monotonic_ns() // 1_000_000`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Binary 8B frame builder | Reczny struct.pack w brain.py | `SerialInterface.send_frame()` | Juz zaimplementowany, przetestowany, DTR+low_latency wbudowane |
| AWB warmup | Nowy wzorzec | Skopiuj z `legacy/src/modes/test_tracker.py:Picamera2Stream.start()` | Przetestowany dwuetapowy pattern z fallback (1.0,1.0) i re-read |
| YUV420→BGR | Wlasna konwersja | `cv2.cvtColor(klatka, cv2.COLOR_YUV420p2BGR)` | Wzorzec z legacy — na Bookworm format moze byc NV12 (sprawdzic) |
| Thread-safe frame buffer | Reczny double-buffer | Prosty `threading.Lock()` + `self._klatka` | Identyczny wzorzec jak w `Picamera2Stream` z legacy |

**Key insight:** Caly legacy `src/modes/test_tracker.py` jest wzorcem do adaptacji. Glowne zmiany: zamiana DNN na MediaPipe, zamiana `MaszynaStanow` (sterowanie serwami) na `SerialInterface` (TX do Arduino), usuniecie `PanTiltSystem` z importow.

---

## Common Pitfalls

### Pitfall 1: MediaPipe nie instaluje sie na Python 3.13

**What goes wrong:** `pip install mediapipe` fail z "no matching distribution" lub ABI error. Dev machine ma Python 3.13.5 — RPi tez moze miec 3.13 jesli Trixie (Debian 13).

**Why it happens:** mediapipe 0.10.x wspiera Python 3.9-3.12 maksymalnie. Python 3.13 zmienilo pybind11 ABI.

**How to avoid:** Weryfikacja `python3 --version` jako krok 0 na RPi. Jezeli 3.13 — uzyj pyenv lub `python3.11` (Bookworm ma 3.11 obok 3.13). Venv: `python3.11 -m venv venv --system-site-packages`.

**Warning signs:** `import mediapipe` → Segmentation fault lub ImportError natychmiast po pip install.

### Pitfall 2: MediaPipe wymaga RGB, Picamera2 daje YUV420→BGR

**What goes wrong:** Przekazanie klatki BGR bezposrednio do `mp.Image(image_format=mp.ImageFormat.SRGB, data=klatka_bgr)` powoduje bledne kolory — MediaPipe przetwarza jako RGB, piksele sa w kolejnosci BGR. Detekcja dziala gorzej, zaufanie spada.

**Why it happens:** OpenCV konwencja = BGR. MediaPipe konwencja = RGB. `mp.ImageFormat.SRGB` wymaga RGB.

**How to avoid:**

```python
klatka_rgb = cv2.cvtColor(klatka_bgr, cv2.COLOR_BGR2RGB)
mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=klatka_rgb)
```

**Warning signs:** FPS nizszy niz oczekiwany, zaufanie detekcji nizsze niz 0.5, detekcje tylko w centrum kadru.

### Pitfall 3: MediaPipe VIDEO timestamp musi byc monotonicznie rosnacy

**What goes wrong:** `detect_for_video()` rzuca `RuntimeError: The input timestamp must be monotonically increasing` jezeli timestamp nie rosnie miedzy wywolaniami.

**Why it happens:** VIDEO mode uzywa trackingu miedzy klatkami — wymaga uporzadkowanego czasu.

**How to avoid:** Uzywac `time.monotonic_ns() // 1_000_000` (milisekundy monotonicznie) zamiast `int(time.time() * 1000)`. Alternatywnie: licznik inkrementowany reczenie (np. co 33ms per klatka).

**Warning signs:** RuntimeError przy pierwszej petli jesli NTP koryguje czas w dol.

### Pitfall 4: bounding_box w Tasks API jest pikselowy, nie normalizowany

**What goes wrong:** Obliczanie bledu error_x jako `origin_x / frame_width` zamiast `origin_x + width/2 - frame_width/2`. Wynik bledu blednie skalowany.

**Why it happens:** W Legacy Solutions API coords byly normalizowane [0,1]. W Tasks API `bounding_box` to `BoundingBox` z pikselowymi wspolrzednymi.

**How to avoid:**

```python
# Tasks API — wspolrzedne pikselowe (nie normalizowane)
bb = det.bounding_box
srodek_x = bb.origin_x + bb.width // 2
srodek_y = bb.origin_y + bb.height // 2
error_x = srodek_x - (frame_width // 2)   # w pikselach, zakres -160..+160 dla 320px
error_y = srodek_y - (frame_height // 2)
```

**Warning signs:** Serwa zawsze w skrajnych pozycjach lub brak reakcji na ruch twarzy.

### Pitfall 5: numpy >=2.0 lamie mediapipe import

**What goes wrong:** `import mediapipe` → `RuntimeError: numpy.core module not found` lub podobny blad po pip upgrade numpy.

**Why it happens:** mediapipe 0.10.x ma hard dep `numpy<2.0`. OpenCV 4.9+ lub inne pakiety moga podniesc numpy do 2.x automatycznie.

**How to avoid:** Pin w requirements-v2.txt: `numpy>=1.24,<2.0`. Weryfikacja po instalacji: `python -c "import numpy; print(numpy.__version__)"`.

**Warning signs:** mediapipe dziala przy instalacji, crashuje po pip install innego pakietu.

### Pitfall 6: Heartbeat gap >= 500ms odpala watchdog Arduino przy wolnym FPS

**What goes wrong:** Przy 12 FPS (83ms/klatka) + overhead detekcji MediaPipe, petla moze zajac >200ms. Jezeli heartbeat jest tylko w glownej petli (send co klatke), interwal TX moze przekroczyc 500ms Arduino watchdog timeout — Arduino przejdzie do SCAN autonomicznie nawet przy wykrytej twarzy.

**Why it happens:** Glowna petla jest jednowazkowa — splatane FPS detekcji z czestotliwoscia TX.

**How to avoid:** Osobny daemon thread heartbeat z `threading.Event` stop. Thread sprawdza co 50ms czy minely 200ms od ostatniego TX. Jezeli tak — wysyla SCAN heartbeat. Glowna petla aktualizuje `czas_ostatniej_tx` po kazdym send_frame.

**Warning signs:** Arduino logi "watchdog fired" mimo ze RPi dziala. Serwa wracaja do skanu przy aktywnym sledzeniu.

---

## Code Examples

### Error X/Y obliczanie i skalowanie do protokolu

```python
# Source: PROTOCOL_SPEC.md zakres -160..+160 dla rozdzielczosci 320px

def _oblicz_error(
    self,
    bbox: Tuple[int, int, int, int],
    shape: Tuple[int, int, int]
) -> Tuple[int, int, int]:
    """Oblicza error X/Y i face_size do wysylki w ramce 8B.

    Args:
        bbox: (x, y, w, h) w pikselach — Tasks API wspolrzedne pikselowe.
        shape: (H, W, C) klatki OpenCV.

    Returns:
        (error_x, error_y, face_size) — gotowe do send_frame().
        error_x/y: int16 -160..+160, face_size: uint8 0..255.
    """
    x, y, bw, bh = bbox
    h, w = shape[:2]

    # Srodek twarzy
    srodek_x = x + bw // 2
    srodek_y = y + bh // 2

    # Blad wzgledem centrum klatki (protokol: -160..+160 dla 320px)
    error_x = srodek_x - (w // 2)
    error_y = srodek_y - (h // 2)

    # Jezeli rozdzielczosc != 320 — skaluj do protokolu
    # (D-05: error_x zakres protokolu = polowa szerokosci 320px = 160)
    if w != 320:
        error_x = int(error_x * 160 / (w // 2))
        error_y = int(error_y * 160 / (h // 2))

    # Clamp do int16 zakresu protokolu
    error_x = max(-160, min(160, error_x))
    error_y = max(-160, min(160, error_y))

    # face_size jako procent kadru skalowany do 0-255
    area_ratio = (bw * bh) / (w * h)
    face_size = int(area_ratio * 255)
    face_size = max(0, min(255, face_size))

    return error_x, error_y, face_size
```

### YUV420→BGR — weryfikacja formatu (raz na start)

```python
# Source: legacy/src/modes/test_tracker.py:Picamera2Stream._petla_przechwytywania()
# UWAGA: Bookworm moze zwracac NV12 zamiast planar YUV420p — weryfikacja shape

klatka_yuv = self._picam2.capture_array("lores")
if not self._format_zweryfikowany:
    logger.info(f"Raw lores shape: {klatka_yuv.shape}, dtype: {klatka_yuv.dtype}")
    self._format_zweryfikowany = True

# Probuj NV12 (semi-planar) najpierw — dominujacy na Bookworm
try:
    klatka = cv2.cvtColor(klatka_yuv, cv2.COLOR_YUV2BGR_NV12)
except cv2.error:
    klatka = cv2.cvtColor(klatka_yuv, cv2.COLOR_YUV420p2BGR)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `mp.solutions.face_detection` (legacy) | `mp.tasks.vision.FaceDetector` (Tasks API) | mediapipe 0.10.0 (2023) | Inny model path (.task zamiast embedded), inny format bounding_box (pikselowy zamiast normalizowanego) |
| mediapipe wbudowany model | `.tflite` model file do pobrania | mediapipe 0.10.x | Model musi byc dostepny lokalnie — `models/blaze_face_short_range.tflite` |
| HAAR cascade streak filter (legacy) | MediaPipe BlazeFace | Phase 21 | Szybszy, dokladniejszy przy rotacji twarzy, brak streak filter potrzebnego |

**Deprecated/outdated:**

- `mp.solutions.face_detection.FaceDetection(...)` — legacy API, dziala ale deprecated w 0.10.x
- `cv2.CascadeClassifier` + streak filter — zastapione MediaPipe w v2.0
- PID na RPi (src/tracker.py) — PID przeniesiony na Arduino w v2.0

---

## Open Questions

1. **Czy pip install mediapipe dziala na konkretnej wersji RPi OS na docelowym RPi4?**
   - What we know: Bookworm + Python 3.11 + piwheels = prawdopodobnie tak wg community reports z 2024-2025. STATE.md notuje: "picamera2 nie importuje sie w Python 3.12 venv" z Phase 18 — wersja Python 3.11 moze byc dostepna przez pyenv.
   - What's unclear: Ktora dokladnie wersja OS jest na docelowym RPi4 (Bookworm vs Trixie). Python 3.11 vs 3.12 venv.
   - Recommendation: Krok 0 fazy — `python3 --version` na RPi przed pisaniem kodu. Jezeli 3.13 → pyenv install 3.11.

2. **NV12 vs YUV420p — ktory format zwraca Picamera2 lores na konkretnym OS?**
   - What we know: Bookworm tenduje do NV12 (semi-planar). Legacy test_tracker.py uzywa `COLOR_YUV420p2BGR` (planar). Maze byc bledne na Bookworm — powoduje niebieski tint.
   - What's unclear: Dokladny format na docelowej konfiguracji.
   - Recommendation: Pierwsza klatka → loguj `shape` YUV raw. Try NV12 first, fallback do YUV420p.

3. **Dokladny FPS MediaPipe FaceDetector na RPi4 przy 320x240?**
   - What we know: Benchmarki z SaraKIT: 12-30 FPS na RPi4 (zalezne od modelu i rozdzielczosci). blaze_face_short_range jest najszybszy.
   - What's unclear: Dokladny FPS przy 320x240 z Python overhead + Picamera2 + przetwarzanie.
   - Recommendation: Zaplanowac verifier test z `time.perf_counter()` mierzacy klatki przez 10 sekund.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | mediapipe install | UNKNOWN — dev ma 3.13 | dev: 3.13.5, RPi: UNKNOWN | pyenv install 3.11 na RPi |
| picamera2 | VIS-01 kamera | System apt (nie w venv) | system | --system-site-packages venv |
| mediapipe | VIS-01 detekcja | UNKNOWN na RPi | musi byc 0.10.x | PINTO0309 community wheel |
| numpy <2.0 | mediapipe dep | dev: zainstalowany | dev: unknown | pip install "numpy<2.0" |
| blaze_face_short_range.tflite | VIS-01 model | NIE — do pobrania | — | wget z storage.googleapis.com |
| /dev/ttyACM0 | VIS-05 serial TX | RPi-only (Arduino podlaczony) | — | mock mode w SerialInterface |
| cv2 (OpenCV) | HUD, cvtColor | Zainstalowany (legacy) | 4.8.x | — |
| pyserial | VIS-05 | Zainstalowany (Phase 19) | 3.5 | — |

**Missing dependencies with no fallback:**

- `blaze_face_short_range.tflite` — model musi byc pobrany przed uruchomieniem. `wget` jako Task Wave 0.
- Python 3.11 na RPi — jezeli brak, pyenv install 3.11 jako Task Wave 0.

**Missing dependencies with fallback:**

- `/dev/ttyACM0` — `SerialInterface` ma try/except; bez Arduino: serial TX failuje cicho (log error). Przydatne do testow kamerowych bez Arduino.

---

## Validation Architecture

Projekt nie ma `test_framework` configured (config.json: `"test_framework": "none"`). Weryfikacja empiryczna per CLAUDE.md.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Notes |
|--------|----------|-----------|-------------------|-------|
| VIS-01 | MediaPipe wykrywa twarz w kadrze 320x240 | smoke | `python3 run_pi_brain.py` + obserwacja logow | HUD bbox widoczny, log "twarze: N" |
| VIS-02 | Sticky tracking — brak migotania przy 2 twarzach | manual-only | Wstaw 2 twarze do kadru | Obserwacja stabilnosci bbox na HUD |
| VIS-03 | Error X/Y obliczony poprawnie | manual-only | Twarz w centrum → error ~0. Twarz z lewej → error_x < 0 | Log error_x/y na HUD |
| VIS-04 | AWB fix — brak niebieskiej/zielonej poswiaty | manual-only | Obserwacja wizualna klatki na HUD po 3s | Neutral kolory widoczne |
| VIS-05 | Serial TX ramek do Arduino | smoke | `python3 scripts/echo_test.py` + `python3 run_pi_brain.py` | Arduino ACK w logach |
| VIS-06 | Heartbeat co 200ms nawet bez twarzy | smoke | `python3 run_pi_brain.py` bez twarzy + obserwacja `dmesg` | Arduino NIE odpala watchdog w ciagu 10s |
| VIS-07 | Graceful shutdown na Ctrl+C | smoke | `python3 run_pi_brain.py` → Ctrl+C | "serial zamkniety", "kamera zatrzymana" w logu |

### Wave 0 Gaps

- [ ] `models/blaze_face_short_range.tflite` — model do pobrania: `wget -O models/blaze_face_short_range.tflite https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite`
- [ ] Python 3.11 venv z mediapipe — weryfikacja `python3 --version` + `python3 -c "import mediapipe; print(mediapipe.__version__)"` na RPi

---

## Project Constraints (from CLAUDE.md)

Dyrektywy projektu obowiazujace w tej fazie:

| Dyrektywa | Zastosowanie |
|-----------|--------------|
| Polskie nazwy metod i zmiennych w nowym kodzie | Wszystkie metody w `src/vision/camera.py`, `detector.py`, `brain.py`: `wykryj()`, `odczytaj()`, `zatrzymaj()`, `uruchom()` |
| Type hints z `typing` module na wszystkich metodach | `Optional[np.ndarray]`, `Tuple[int,int,int,int]`, `List[...]` na kazdej metodzie |
| try/except z logging.error() — nigdy re-raise | Bledy kamery, serial TX, MediaPipe — log i kontynuuj |
| 4-space indentation, bez automated formatter | Standard Python |
| Wzorzec daemon thread dla kamery | `threading.Thread(daemon=True)` w `KameraRPi` |
| Graceful hardware mock mode | SerialInterface moze failowac bez crashu; kamera moze failowac z retry |
| Jeden entry point w root: `run_pi_brain.py` | Wzorzec `run_test_tracker.py` |
| GSD workflow — nie edytowac plikow bezposrednio | Przez `/gsd:execute-phase` |
| Brak test framework | Weryfikacja empiryczna: logi + wizualna obserwacja HUD |
| Wszystkie komentarze w kodzie po polsku (INT-05) | Dotyczy nowego kodu Phase 21 |

---

## Sources

### Primary (HIGH confidence)

- `legacy/src/modes/test_tracker.py` — Picamera2Stream, HUD, graceful shutdown, AWB pattern — wzorzec do adaptacji
- `src/vision/serial_interface.py` — gotowa klasa SerialInterface — bezposrednio uzywalna
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja ramki 8B
- `.planning/phases/11-awb-fix/11-CONTEXT.md` — Decyzje AWB: dwuetapowy ColourGains lock
- `.planning/research/PITFALLS.md` (linii 1-99) — Pitfall 1 MediaPipe Python 3.13, DTR, latency
- `.planning/research/STACK.md` (linii 945-1064) — v2.0 Supplement: mediapipe stack, Tasks API wzorzec

### Secondary (MEDIUM confidence)

- `https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector/python` — Tasks API VIDEO/LIVE_STREAM mode, FaceDetectorOptions, detect_for_video()
- `https://github.com/raspberrypi/picamera2/issues/755` — picamera2 + mediapipe: RGB konwersja required, --system-site-packages venv
- WebSearch: mediapipe 0.10 na Bookworm Python 3.11 — "Python <=3.11 wspierane, numpy<2.0 hard dep" (verified across multiple sources)

### Tertiary (LOW confidence)

- WebSearch: PINTO0309/mediapipe-bin — community aarch64 wheel jako fallback (nie oficjalny)
- WebSearch: FPS benchmarki 12-30 FPS RPi4 — z SaraKIT project, nie oficjalne Google benchmarki

---

## Metadata

**Confidence breakdown:**

- Standard stack: MEDIUM — MediaPipe aarch64 install wymaga empirycznej weryfikacji na docelowym RPi; reszta (pyserial, picamera2, numpy pin) HIGH
- Architecture: HIGH — wzorce bezposrednio z legacy test_tracker.py + Tasks API official docs
- Pitfalls: HIGH (pkt 1-3, 5-6) / MEDIUM (pkt 4 bounding_box format — z oficjalnej doc)

**Research date:** 2026-03-31
**Valid until:** 2026-07-01 (mediapipe aktualizuje sie czesto — sprawdzic wersje przed instalacja)
