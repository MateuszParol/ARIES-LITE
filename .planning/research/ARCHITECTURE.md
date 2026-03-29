# Architecture Research

**Domain:** Embedded real-time face tracking (RPi4) — v1.8 Critical Hardware Fix
**Researched:** 2026-03-29
**Confidence:** HIGH (bezpośredni audit kodu v1.7 + kontekst hardware z PROJECT.md/STATE.md)

## Standard Architecture

### System Overview — istniejąca architektura (v1.7, stan wejściowy dla v1.8)

```
┌─────────────────────────────────────────────────────────────────┐
│                    run_test_tracker.py                           │
│                    TestTracker.uruchom()                         │
├─────────────────────────────────────────────────────────────────┤
│  WARSTWA WEJŚCIA                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Picamera2Stream (wątek daemon)                          │    │
│  │  YUV420 lores (320x240) → BGR konwersja                  │    │
│  │  AWB: sleep(2) → capture_metadata() → set_controls()    │    │
│  │  [PROBLEM v1.8: brak AwbEnable:False, logi niewystarczające] │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │ odczytaj() → Optional[np.ndarray] │
├─────────────────────────────┼───────────────────────────────────┤
│  WARSTWA DETEKCJI                                                │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │  DetekcjaTwarzy.wykryj()                                 │    │
│  │  HAAR cascade + streak filter (N=3)                      │    │
│  │  minNeighbors=8, minSize=(80,80)                         │    │
│  │  [PROBLEM v1.8: brak zielonych prostokątów na hardware,  │    │
│  │   wymaga idealnej pozycji frontalnej]                    │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │ Optional[Tuple[x, y, w, h]]       │
├─────────────────────────────┼───────────────────────────────────┤
│  WARSTWA STEROWANIA                                              │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │  MaszynaStanow.tick(bbox, w, h)                          │    │
│  │  SCANNING → TRACKING → TARGET_LOST → SCANNING            │    │
│  │  _sledz(): PID dual-axis → korekta → set_angles()        │    │
│  │  [PROBLEM v1.8: TILT zamrożony na 0.0 w HUD,            │    │
│  │   PAN ucieka do limitu — brak logów diagnostycznych]    │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │ set_angles(pan, tilt)              │
├─────────────────────────────┼───────────────────────────────────┤
│  WARSTWA HARDWARE                                                │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │  PanTiltSystem.set_angles()                              │    │
│  │  soft limits → WARNING log → pan/tilt_angle → H-PWM     │    │
│  │  GPIO12 (pan), GPIO13 (tilt), pigpiod                    │    │
│  │  [STATUS: poprawny, logi clampa już działają]            │    │
│  └──────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  WARSTWA HUD                                                     │
│  _rysuj_hud() → cv2.imshow 640x480 (lub headless fallback)      │
└─────────────────────────────────────────────────────────────────┘
```

### Przepływ danych per-klatka (główna pętla uruchom())

```
klatka = kamera.odczytaj()               # None → sleep(0.01), skip
    ↓
bbox = detekcja.wykryj(klatka)           # HAAR + streak → Optional bbox
    ↓
stan = maszyna.tick(bbox, w, h)          # State machine + PID → set_angles()
    ↓
resetuj_streak() przy TARGET_LOST entry  # (stan==TARGET_LOST && poprzedni==TRACKING)
    ↓
_rysuj_hud(klatka, bbox, stan)           # cv2 overlay: bbox rect, stan, kąty, FPS
    ↓
cv2.imshow(resize 2x → 640x480)          # lub headless fallback
```

### Component Responsibilities

| Komponent | Odpowiedzialność | Plik | Status v1.8 |
|-----------|-----------------|------|-------------|
| `Picamera2Stream` | Przechwytywanie YUV420→BGR w tle, retry, AWB lock | `test_tracker.py` | MODYFIKOWANY |
| `DetekcjaTwarzy` | HAAR + streak filter, wybór największej twarzy | `test_tracker.py` | ZASTĘPOWANY |
| `MaszynaStanow` | Przejścia stanów, PID dual-axis, sinusoidal scan | `test_tracker.py` | MODYFIKOWANY (_sledz) |
| `PanTiltSystem` | Soft limits, zapis kątów, H-PWM pigpiod | `hardware.py` | BEZ ZMIAN |
| `TestTracker` | Orkiestrator: łączy warstwy, HUD, graceful shutdown | `test_tracker.py` | MINIMALNE ZMIANY |

## Recommended Project Structure

Struktura plików pozostaje niezmieniona. Wszystkie zmiany v1.8 mieszczą się w jednym pliku:

```
src/
├── modes/
│   └── test_tracker.py     # JEDYNY plik modyfikowany w v1.8:
│                           #  - Picamera2Stream.start(): AWB diagnostics + AwbEnable:False
│                           #  - DetekcjaTwarzy → DetekcjaTwarzyDNN (nowa klasa, ten sam interfejs)
│                           #  - MaszynaStanow._sledz(): logi diagnostyczne PID (P1-P4)
├── hardware.py             # BEZ ZMIAN
├── config.py               # EWENTUALNE ROZSZERZENIE o próg pewności DNN
└── ...
```

Uzasadnienie: Jeden plik = minimalne ryzyko regresji w stabilnych warstwach (hardware, flask).
Nie tworzymy pakietu `detectors/` — nowa klasa detektora to ~40 linii kodu wewnątrz
tego samego pliku.

## Architectural Patterns

### Pattern 1: Zamiana detektora — interfejs bez zmiany orkiestratora

**Co:** Kontrakt `wykryj(klatka) → Optional[Tuple[int,int,int,int]]` pozostaje niezmieniony.
`TestTracker.uruchom()` nie wie nic o technologii detekcji. Podmiana to wyłącznie zmiana
jednej linii w `TestTracker.__init__` oraz nowa klasa z tym samym interfejsem publicznym.

**Kiedy:** Zawsze przy zamianie HAAR na DNN/MediaPipe w v1.8.

**Trade-offs:** Pros — zero zmian w orkiestratorze, maszynie stanów i HUD.
Cons — jeśli nowy detektor zwraca coords relatywne (0.0–1.0), trzeba je skonwertować
do pikseli wewnątrz nowej klasy zanim wróci `Tuple[int,int,int,int]`.

**Punkt integracji:**
```python
# TestTracker.__init__() — linia 299–301 — jedyna zmiana w orkiestratorze:
# PRZED:
self.detekcja = DetekcjaTwarzy()
# PO:
self.detekcja = DetekcjaTwarzyDNN()   # ten sam interfejs wykryj() i resetuj_streak()

# uruchom() linia 332 — NIE zmienia się:
bbox = self.detekcja.wykryj(klatka)
```

**Rekomendowany detektor: OpenCV DNN z modelem YuNet (`face_detection_yunet_2023mar.onnx`)**
- Model ~380 KB, wbudowany w `cv2.FaceDetectorYN` od OpenCV 4.5.4
- Działa na CPU RPi4 ~20-30ms/klatka (15-20 FPS pipeline)
- Nie wymaga dodatkowych instalacji poza `opencv-python`
- Zwraca bbox + confidence — prosty filtr progu

**Alternatywa: MediaPipe BlazeFace**
- Szybszy (~15ms) ale wymaga `pip install mediapipe` (~100MB) — ciężkie na RPi4
- Wyższe opóźnienie przy imporcie, bardziej skomplikowany setup
- Rekomendacja: użyć YuNet najpierw; MediaPipe jako fallback jeśli YuNet niedokładny

### Pattern 2: Dodanie logów PID bez zmiany logiki sterowania

**Co:** `MaszynaStanow._sledz()` to jedyne miejsce produkcji wyjścia PID i wywołania
`set_angles()`. Cała diagnostyka PID ląduje tu — bez modyfikacji innych metod.

**Kiedy:** Debugowanie zamrożonego tilta (HUD `Tilt:+0.0`) i runaway pana.

**Trade-offs:** Pros — precyzyjne pomiary w 4 punktach (błąd → wyjście PID → korekta →
po clampie) bez szumu z innych ścieżek. Cons — przy 20 FPS logi zalewają stderr;
throttle co 10-30 klatek lub użycie `logger.debug` (aktywny tylko przy `--log-level DEBUG`).

**Punkty pomiarowe w _sledz():**
```python
def _sledz(self, bbox, w, h):
    x, y, bw, bh = bbox
    srodek_x = x + bw // 2
    srodek_y = y + bh // 2
    ramka_cx = w // 2
    ramka_cy = h // 2

    blad_pan  = srodek_x - ramka_cx  # P1: błąd w pikselach
    blad_tilt = srodek_y - ramka_cy

    korekta_pan  = -self.pid_pan(blad_pan)    # P2: wyjście PID w stopniach
    korekta_tilt = -self.pid_tilt(blad_tilt)

    nowy_pan  = self.hardware.pan_angle + korekta_pan   # P3: żądany kąt przed clampem
    nowy_tilt = self.hardware.tilt_angle + korekta_tilt

    # DODAĆ — diagnostyka (throttle: co 10 klatek lub logger.debug):
    logger.debug(
        f"PID sledz: "
        f"err=({blad_pan:+.1f}px,{blad_tilt:+.1f}px) "
        f"korekta=({korekta_pan:+.3f}deg,{korekta_tilt:+.3f}deg) "
        f"cur=({self.hardware.pan_angle:+.1f},{self.hardware.tilt_angle:+.1f}) "
        f"req=({nowy_pan:+.1f},{nowy_tilt:+.1f})"
    )

    self.hardware.set_angles(nowy_pan, nowy_tilt)
    # P4: hardware.pan_angle / tilt_angle po set_angles() = wartości po clampie
    # Logi WARNING clampa już istnieją w PanTiltSystem.set_angles() — nie duplikować
```

**Diagnoza na podstawie logów:**

| Objaw | P1 (błąd) | P2 (korekta) | P4 (po clampie) | Wniosek |
|-------|-----------|--------------|-----------------|---------|
| Tilt=0 w HUD, twarz nie wycentrowana | `blad_tilt != 0` | `korekta_tilt != 0` | `tilt_angle = 0` | clamp w set_angles lub serwo nie reaguje |
| Tilt=0 w HUD, brak detekcji | `blad_tilt = 0` | `korekta_tilt = 0` | `tilt_angle = 0` | bbox=None, detekcja nie działa |
| PAN ucieka od razu | `blad_pan mały` | `korekta_pan duża` | WARNING: clamp | wzmocnienie PID za duże lub błędny sign |
| PAN ucieka od razu | `blad_pan rośnie` | `korekta_pan rośnie` | — | pozytywne sprzężenie — błędny sign korekty |

### Pattern 3: AWB diagnostics — weryfikacja mechanizmu lock

**Co:** Mechanizm AWB lock (sleep 2s → capture_metadata → set_controls) jest poprawny
architekturalnie. Problem v1.8: brak potwierdzenia że lock faktycznie zadziałał + brak
`AwbEnable: False` powoduje że AWB może nadpisać gains po locku.

**Kiedy:** Blue tint od startu lub chwilowy tint po dłuższej pracy.

**Trade-offs:** Pros — zero ryzyka, tylko logi + jeden parametr. Cons — nie naprawia
złych gains automatycznie (ale logi umożliwiają ręczne dostrojenie fallback).

**Punkt integracji — Picamera2Stream.start() linie 78-87:**
```python
# Po istniejącym sleep(2.0) i capture_metadata():
logger.info(f"AWB metadata kompletna: {metadata}")   # pełny dump — ujawnia AwbEnable, ColourGains, etc.

gains = metadata.get("ColourGains")
if gains is None:
    logger.warning("ColourGains niedostępne, używam fallback (2.5, 1.9)")
    gains = AWB_FALLBACK_GAINS

# ZMIANA: dodać AwbEnable: False — wyłącza dalsze modyfikacje przez algorytm AWB
self._picam2.set_controls({
    "AwbEnable": False,    # KLUCZOWE — bez tego AWB może nadpisać ColourGains po locku
    "ColourGains": gains
})
r, b = gains
logger.info(f"ColourGains zablokowane (AWB disabled): R={r:.2f}, B={b:.2f}")
```

**Drugi punkt integracji — reinit w _petla_przechwytywania linie 122-127:**
Ta sama zmiana musi być w `create_video_configuration` w ścieżce reinit, żeby AWB
był wyłączony po reinicjalizacji kamery przy błędzie.

## Data Flow

### Przepływ detekcji — nowy detektor YuNet (OpenCV DNN)

```
klatka BGR (320x240)
    ↓
DetekcjaTwarzyDNN.wykryj(klatka)
    ├─ cv2.FaceDetectorYN.detect(klatka)
    │   → (retval, faces) gdzie faces: ndarray shape (N, 15)
    │     [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, score]
    ├─ filtr: faces[i, 14] >= DNN_CONFIDENCE_THRESHOLD (np. 0.5)
    ├─ wybór największej twarzy wg faces[i, 2] * faces[i, 3]
    ├─ streak filter (identyczny mechanizm jak HAAR — reużyty)
    └─ return (int(x), int(y), int(w), int(h))  ← ten sam typ co HAAR
```

### Przepływ PID z diagnostyką (v1.8)

```
bbox (x, y, bw, bh)  ← z nowego detektora
    ↓
[LOG P1] blad_pan  = srodek_x - ramka_cx    (piksele, ±160 max dla 320px)
[LOG P1] blad_tilt = srodek_y - ramka_cy    (piksele, ±120 max dla 240px)
    ↓
pid_pan(blad_pan)   → output (stopnie, ograniczone do ±10 przez output_limits)
pid_tilt(blad_tilt) → output
    ↓
[LOG P2] korekta_pan  = -output_pan
[LOG P2] korekta_tilt = -output_tilt
    ↓
[LOG P3] nowy_pan  = hardware.pan_angle  + korekta_pan
[LOG P3] nowy_tilt = hardware.tilt_angle + korekta_tilt
    ↓
hardware.set_angles(nowy_pan, nowy_tilt)
    ↓
[LOG P4 — już istnieje] WARNING jeśli clamp zastosowany
soft_clamp: pan ∈ [-60, +60], tilt ∈ [-30, +30]
    ↓
pan_servo.angle / tilt_servo.angle  (H-PWM GPIO12/GPIO13)
```

### Krytyczne punkty pomiarowe

| Punkt | Co mierzyć | Gdzie w kodzie | Co ujawnia |
|-------|-----------|----------------|------------|
| P1 | `blad_pan`, `blad_tilt` w pikselach | `_sledz()` przed PID | czy detekcja daje prawidłowe bbox |
| P2 | `korekta_pan`, `korekta_tilt` w stopniach | `_sledz()` po PID | czy PID produkuje niezerowe wyjście dla obu osi |
| P3 | `nowy_pan`, `nowy_tilt` przed clampem | `_sledz()` przed set_angles | czy wartości mieszczą się w limitach |
| P4 | `hardware.pan/tilt_angle` po clampie | `set_angles()` (już logowane) | potwierdzenie zapisu do servo |
| P5 | `ColourGains` (R, B) z metadata | `Picamera2Stream.start()` | diagnostyka blue tint |
| P6 | `AwbEnable` status po locku | `Picamera2Stream.start()` | czy AWB faktycznie wyłączone |

## Scaling Considerations

Projekt single-device embedded — skalowanie nie dotyczy. Ograniczenia wydajnościowe v1.8:

| Komponent | Obecny koszt (RPi4) | Po zamianie DNN | Akceptowalność |
|-----------|---------------------|-----------------|----------------|
| HAAR detectMultiScale | ~8-12ms/klatka | — | — |
| YuNet FaceDetectorYN | — | ~20-35ms/klatka | TAK (15-20 FPS) |
| MediaPipe BlazeFace | — | ~12-20ms/klatka | TAK (~20 FPS) |
| PID tick (_sledz) | <1ms | bez zmiany | TAK |
| AWB warm-up (jednorazowy) | 2s startup | bez zmiany | TAK |
| Logi PID (dodane) | ~0.1ms/klatka | bez zmiany | TAK |

Minimalny akceptowalny FPS dla śledzenia PID: 10 FPS. YuNet przy 320x240 mieści się.

## Anti-Patterns

### Anti-Pattern 1: Naprawa PID przez modyfikację hardware.py

**Co robią:** Zmieniają soft limits, dodają filtrowanie wyjścia albo offset w `set_angles()`.

**Dlaczego złe:** `set_angles()` to warstwa hardware — chroni fizyczny kabel kamery.
Dodanie logiki korekcji PID ukrywa problem zamiast go naprawić. Logging clampa (WARNING)
już istnieje i jest wystarczający do diagnozy.

**Zamiast tego:** Diagnoza przez logi P1-P4 w `_sledz()`. Naprawa w `_sledz()` lub
`config.py` (PID_TILT_P, PID_TILT_I, PID_TILT_D).

### Anti-Pattern 2: Nowy detektor ze zmienionym typem zwracanym

**Co robią:** Nowa klasa detektora zwraca listę bboxów, słownik, `detection_result` obiekty
lub landmarks — wymuszając zmiany w `TestTracker.uruchom()` i `MaszynaStanow.tick()`.

**Dlaczego złe:** Zmiany w orkiestratorze = ryzyko regresji w logice stanów i HUD.
Dwa miejsca do debugowania zamiast jednego.

**Zamiast tego:** Nowy detektor MUSI implementować ten sam interfejs:
`wykryj(klatka: np.ndarray) -> Optional[Tuple[int,int,int,int]]`
`resetuj_streak() -> None`
Konwersja coords relatywnych → piksele wewnątrz nowej klasy, przed return.

### Anti-Pattern 3: Zamiana Picamera2 na cv2.VideoCapture "dla uproszczenia"

**Co robią:** Przechodzą na VideoCapture bo prostsze.

**Dlaczego złe:** Picamera2 to natywny backend libcamera na Bookworm 64-bit — daje
niższe opóźnienie i pełną kontrolę ColourGains (VideoCapture tego nie ma). Blue tint
to błąd konfiguracji AWB lock (`AwbEnable: False` brakuje), nie wada Picamera2.

**Zamiast tego:** Dodać `"AwbEnable": False` do `set_controls()` i zalogować pełne metadata.

### Anti-Pattern 4: Logi PID na poziomie INFO co klatkę

**Co robią:** `logger.info(f"PID: ...")` w `_sledz()` bez ograniczenia częstotliwości.

**Dlaczego złe:** 20 FPS = 1200 linii/min, 72 000 linii/godz. Przepełnienie logu,
spowolnienie I/O na RPi4 (SD card), utrudnia czytanie innych logów.

**Zamiast tego:** `logger.debug()` (aktywny tylko przy `--log-level DEBUG`) lub wewnętrzny
counter `self._log_counter` z modulo 30 (log co ~1.5s przy 20 FPS).

## Integration Points

### Nowe vs. zmodyfikowane komponenty v1.8

| Komponent | Status | Zakres zmiany | Ryzyko regresji |
|-----------|--------|---------------|-----------------|
| `Picamera2Stream.start()` | ZMODYFIKOWANY | +`AwbEnable:False` do set_controls(), +pełny metadata log | NISKIE |
| `Picamera2Stream._petla_przechwytywania` reinit | ZMODYFIKOWANY | Ta sama zmiana AWB w ścieżce reinit | NISKIE |
| `DetekcjaTwarzy` | ZASTĄPIONY przez `DetekcjaTwarzyDNN` | Nowa klasa, identyczny interfejs publiczny | NISKIE (stara klasa zostaje jako fallback) |
| `MaszynaStanow._sledz()` | ZMODYFIKOWANY | +logi P1-P4 jako `logger.debug` | ZERO (tylko logi) |
| `MaszynaStanow._skanuj()` | BEZ ZMIAN | — | — |
| `MaszynaStanow._przejdz_do()` | BEZ ZMIAN | — | — |
| `TestTracker.__init__()` | ZMODYFIKOWANY | Podmiana `self.detekcja = DetekcjaTwarzyDNN()` | NISKIE |
| `TestTracker.uruchom()` | BEZ ZMIAN | — | — |
| `PanTiltSystem` (`hardware.py`) | BEZ ZMIAN | — | — |
| `config.py` | EWENTUALNE ROZSZERZENIE | +`DNN_CONFIDENCE_THRESHOLD = 0.5` | ZERO |

### Kolejność implementacji — zależności

```
Krok 1: AWB diagnostics (Picamera2Stream.start + reinit)
    - Niezależne od wszystkiego
    - Zerowe ryzyko: tylko logi + jeden parametr AwbEnable
    - Ujawnia czy AWB jest źródłem blue tint NA HARDWARE
    ↓
Krok 2: PID debug logging (MaszynaStanow._sledz)
    - Niezależne od detektora
    - Zerowe ryzyko: tylko logger.debug bez zmiany logiki
    - Uruchomić na RPi4 z HAAR, zbierać logi, potwierdzić co jest zamrożone
    ↓
Krok 3: Analiza logów z kroków 1-2 na hardware
    - Logi P1-P4 ujawnią: czy tilt=0 bo korekta=0 (błąd sign?) czy clamp (wychodzi poza limit?)
    - Logi P5/P6 ujawnią: czy AWB lock zadziałał, jakie gains
    - Na podstawie logów decydujemy czy potrzebna naprawa sign/gain/config
    ↓
Krok 4: Ewentualna naprawa PID (config.py lub _sledz sign)
    - Tylko jeśli logi z kroku 2-3 to potwierdzą
    - Zmiana w _sledz() lub config.py PID_TILT_*
    ↓
Krok 5: Zamiana detektora DetekcjaTwarzy → DetekcjaTwarzyDNN (YuNet)
    - Ostatnia, bo wymaga testowania na RPi4 z kamerą
    - Niezależna od AWB i PID fix
    - Weryfikacja: zielone prostokąty pojawiają się bez idealnej pozycji frontalnej
```

### Internal Boundaries (niezmienione w v1.8)

| Granica | Komunikacja | Niezmienność |
|---------|-------------|--------------|
| `Picamera2Stream` → `TestTracker` | `odczytaj() → Optional[np.ndarray]` | ZACHOWANA |
| `DetekcjaTwarzy/DNN` → `TestTracker` | `wykryj() → Optional[Tuple]` | ZACHOWANA (nowa klasa, ten sam typ) |
| `MaszynaStanow` → `PanTiltSystem` | `set_angles(pan, tilt)` | ZACHOWANA |
| `MaszynaStanow` ←→ `DetekcjaTwarzy` | `resetuj_streak()` przez `TestTracker` | ZACHOWANA |

### Architecture Invariants (nie wolno łamać w v1.8)

1. `MaszynaStanow` nie importuje `DetekcjaTwarzy/DNN` — granica celowo utrzymana.
2. `smooth_move_to()` pozostaje jedyną ścieżką startową do serw — bez bezpośredniego
   `set_angles()` przed zakończeniem safe startup.
3. `_przejdz_do()` pozostaje jedyną metodą zmiany stanu — brak inline `self.stan =` poza nią.
4. Interfejs `wykryj()` zwraca `Optional[Tuple[int,int,int,int]]` — bez względu na detektor.

## Sources

- Bezpośredni audit kodu: `src/modes/test_tracker.py` v1.7 (wszystkie metody) — HIGH confidence
- Bezpośredni audit kodu: `src/hardware.py` (PanTiltSystem) — HIGH confidence
- Bezpośredni audit kodu: `src/config.py` (wszystkie stałe) — HIGH confidence
- Kontekst hardware: `.planning/PROJECT.md` sekcja "Current Milestone v1.8" — HIGH confidence
- Kontekst hardware: `.planning/STATE.md` sekcja "Accumulated Context" — HIGH confidence
- OpenCV YuNet: `cv2.FaceDetectorYN` dostępny od OpenCV 4.5.4, model `face_detection_yunet_2023mar.onnx`
  (https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) — MEDIUM confidence
- Picamera2 ColourGains + AwbEnable: libcamera controls API, wcześniej zweryfikowane na target hardware
  w poprzednim milestone (SOURCE: istniejący ARCHITECTURE.md v1.7) — HIGH confidence

---
*Architecture research for: ARIES-LITE v1.8 Critical Hardware Fix*
*Researched: 2026-03-29*
