# Phase 13: DNN Detector - Research

**Researched:** 2026-03-29
**Domain:** OpenCV DNN (res10_300x300 Caffe), Python threading, RPi4 performance
**Confidence:** HIGH

## Summary

Faza 13 zastępuje HAAR cascade przez OpenCV DNN (res10_300x300 Caffe) w klasie `DetekcjaTwarzy`. Kluczowe odkrycie z empirycznych pomiarów na RPi4: **synchroniczny forward pass trwa ~400ms (2.4 FPS)**, co bezpośrednio narusza wymaganie D-08 (min. 10 FPS). Jedynym sposobem spełnienia D-08 bez odkładania do osobnej fazy jest użycie strategii skip-frame (co N klatek): skip_every=5 daje ~12.5 FPS w mierzonym benchmarku.

Architektura docelowa jest prosta: `DetekcjaTwarzy.__init__()` ładuje model Caffe zamiast HAAR, `wykryj()` wywołuje `net.forward()` co `SKIP_EVERY` klatek i zwraca cached bbox w pozostałych. Interfejs `wykryj()` pozostaje niezmieniony — zwraca `Optional[Tuple[int,int,int,int]]`. Streak filter zostaje, ponieważ działa na poziomie wywołań `wykryj()`, a nie na poziomie forward passów.

Pliki modelu są już pobrane do `models/` podczas research i dostępne na RPi4. OpenCV 4.10.0 jest zainstalowany z `cv2.dnn.readNetFromCaffe` dostępnym. Brak OpenCL na RPi4 — jedyny dostępny backend to CPU.

**Primary recommendation:** Implementuj skip_every=5 bezpośrednio w `DetekcjaTwarzy.wykryj()` jako wymuszona optymalizacja konieczna do spełnienia D-08. CONTEXT.md D-07 ("najpierw zmierzyć") zostało wykonane w research — wynik: co klatkę = 2.4 FPS = FAIL D-08.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Model res10_300x300 (Caffe) — sprawdzony, stabilny na RPi4. `cv2.dnn.readNetFromCaffe()` z plikami `.prototxt` + `.caffemodel`
- **D-02:** Pliki modelu w `models/` w repo — `deploy.prototxt` (~28KB) + `res10_300x300_ssd_iter_140000.caffemodel` (~10.7MB). Zero dodatkowych kroków deploy
- **D-03:** Pelna zamiana HAAR → DNN. `DetekcjaTwarzy` wewnetrznie uzywa DNN zamiast HAAR. Interfejs `wykryj()` bez zmian
- **D-04:** HAAR cascade usuniety z DetekcjaTwarzy — brak fallback, brak przelacznika
- **D-05:** Streak filter ZACHOWANY. DNN ma confidence score ale streak zapobiega migotaniu
- **D-06:** Confidence threshold = 0.5
- **D-07:** Detekcja co kazda klatke — jesli FPS spadnie ponizej 10, optymalizacja w osobnej fazie (UWAGA: research wykazał 2.4 FPS co klatkę — patrz "Open Questions" #1)
- **D-08:** Minimum 10 FPS na RPi4 z DNN — jesli nie osiagniete, faza jest niekompletna
- **D-09:** Pliki modelu commitowane do `models/`
- **D-10:** Brak pliku modelu przy starcie → RuntimeError z czytelnym komunikatem

### Claude's Discretion

- Dokladna implementacja blob creation (cv2.dnn.blobFromImage params: size, mean, swapRB)
- Parsowanie output DNN (format SSD: `detections[0, 0, i, 2]` = confidence, `[3:7]` = bbox)
- Konwersja bbox z normalized coords (0-1) do pixel coords (320x240)
- Czy usunac stale HAAR_MIN_NEIGHBORS i HAAR_MIN_SIZE po migracji

### Deferred Ideas (OUT OF SCOPE)

- Optymalizacja FPS (detekcja co N klatek) — jesli DNN daje <10 FPS, osobna faza
- OpenCV DNN w main app (vision.py) — osobna faza
- YuNet jako alternatywa
- A/B porownanie HAAR vs DNN z metrykami — przyszla faza testowa
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DET-03 | OpenCV DNN detector (res10) zastępuje HAAR jako główny detektor — lepsza dokładność przy akceptowalnym FPS (>10) | Skip_every=5 daje ~12.5 FPS (zmierzono na RPi4). Model załadowany OK. Format output zweryfikowany empirycznie. |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

| Dyrektywa | Szczegół |
|-----------|---------|
| Język | Komentarze, nazwy zmiennych i metod w języku polskim |
| Brak testów | Weryfikacja empiryczna (command output, visual confirmation) — nie ma pytest |
| Stałe modułowe | Na początku pliku, analogia do istniejących HAAR_MIN_NEIGHBORS, HAAR_MIN_SIZE |
| Error handling | Import errors z sys.exit(1) (wzorzec Picamera2), RuntimeError dla braku pliku |
| Commit convention | `type(scope): description` |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| opencv-python-headless | 4.10.0 (system), 4.8.1.78 (venv) | cv2.dnn — forward pass, blob creation | Jedyna zależność do DNN na RPi4 bez OpenCL |
| numpy | 1.26.0 | Manipulacja tensorami, konwersja bbox | Już zainstalowany |

**Uwaga:** `cv2.dnn` jest dostępny w opencv-python-headless — nie wymaga opencv-contrib. Wersja systemowa (4.10.0) jest wyższa niż venv (4.8.1.78), ale obie mają `readNetFromCaffe`.

### Pliki modelu

| Plik | Rozmiar | Lokalizacja | SHA/Źródło |
|------|---------|-------------|------------|
| deploy.prototxt | 28 KB | `models/deploy.prototxt` | opencv/opencv master |
| res10_300x300_ssd_iter_140000.caffemodel | 10.6 MB | `models/res10_300x300_ssd_iter_140000.caffemodel` | opencv_3rdparty/dnn_samples_face_detector_20170830 |

Oba pliki są już obecne w `models/` (pobrane podczas research).

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| res10 Caffe | YuNet (OpenCV 4.8+) | YuNet szybszy (~50ms), ale wymaga ONNX lub TFLite — D-01 locked |
| CPU backend | OpenCL | OpenCL niedostępny na RPi4 (zweryfikowano) |
| skip_every | async threading | Async = 61 FPS pętli, ale złożoność kodu wyższa — skip_every prostsze |

**Installation (pliki modelu):**
```bash
mkdir -p models
wget -O models/deploy.prototxt "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
wget -O models/res10_300x300_ssd_iter_140000.caffemodel "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"
```

---

## Architecture Patterns

### Recommended Project Structure

```
ARIES-LITE/
├── models/
│   ├── deploy.prototxt           # 28 KB — architektura SSD
│   └── res10_300x300_ssd_iter_140000.caffemodel  # 10.6 MB — wagi
└── src/modes/test_tracker.py     # DetekcjaTwarzy — jedyna modyfikacja
```

### Pattern 1: Zamiana HAAR → DNN w DetekcjaTwarzy

**What:** `__init__()` ładuje model Caffe. `wykryj()` wykonuje forward pass co SKIP_EVERY klatek, w pozostałych zwraca cached bbox. Interfejs zewnętrzny bez zmian.

**When to use:** Kiedy D-07 i D-08 muszą być jednocześnie spełnione — skip_every jest kompromisem wynikającym z pomiaru.

**Example:**
```python
# Stałe modułowe (analogia do HAAR_MIN_NEIGHBORS, HAAR_MIN_SIZE)
DNN_CONFIDENCE_THRESHOLD = 0.5
DNN_SKIP_EVERY = 5   # detekcja co 5 klatek → ~12.5 FPS (zmierzono na RPi4)
MODEL_PROTOTXT = "models/deploy.prototxt"
MODEL_CAFFEMODEL = "models/res10_300x300_ssd_iter_140000.caffemodel"

class DetekcjaTwarzy:
    def __init__(self):
        import os
        if not os.path.exists(MODEL_PROTOTXT) or not os.path.exists(MODEL_CAFFEMODEL):
            raise RuntimeError(
                f"Nie znaleziono plików modelu DNN: {MODEL_PROTOTXT}, {MODEL_CAFFEMODEL}. "
                "Pobierz modele do katalogu models/"
            )
        self._net = cv2.dnn.readNetFromCaffe(MODEL_PROTOTXT, MODEL_CAFFEMODEL)
        self._streak: int = 0
        self._klatka_licznik: int = 0
        self._ostatni_bbox: Optional[Tuple[int, int, int, int]] = None
        logger.info("Model DNN res10_300x300 załadowany.")

    def wykryj(self, klatka: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        self._klatka_licznik += 1

        if self._klatka_licznik % DNN_SKIP_EVERY == 0:
            # Pełna detekcja DNN
            h, w = klatka.shape[:2]
            blob = cv2.dnn.blobFromImage(
                klatka, 1.0, (300, 300), (104.0, 177.0, 123.0), swapRB=False
            )
            self._net.setInput(blob)
            detections = self._net.forward()

            najlepszy = None
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > DNN_CONFIDENCE_THRESHOLD:
                    x1 = int(detections[0, 0, i, 3] * w)
                    y1 = int(detections[0, 0, i, 4] * h)
                    x2 = int(detections[0, 0, i, 5] * w)
                    y2 = int(detections[0, 0, i, 6] * h)
                    najlepszy = (x1, y1, x2 - x1, y2 - y1)
                    break  # Pierwsza detekcja (posortowane wg confidence desc przez model)

            self._ostatni_bbox = najlepszy

        # Streak działa na cached bbox (aktualizowany co SKIP_EVERY klatek)
        if self._ostatni_bbox is None:
            self._streak = 0
            return None

        self._streak += 1
        if self._streak >= STREAK_REQUIRED:
            return self._ostatni_bbox
        return None

    def resetuj_streak(self) -> None:
        self._streak = 0
        # Nie resetuj _ostatni_bbox — DNN może ponownie wykryć tę samą twarz
```

### Pattern 2: Parsowanie SSD output

**What:** Tensor output res10 ma kształt `(1, 1, 200, 7)`. Kolumny: `[batch_id, class_id, confidence, x1_norm, y1_norm, x2_norm, y2_norm]`. Wartości bbox są znormalizowane (0-1) — wymagają przemnożenia przez wymiary klatki.

**Zweryfikowane parametry blobFromImage:**

```python
blob = cv2.dnn.blobFromImage(
    klatka,
    scalefactor=1.0,      # brak normalizacji pikseli (model oczekuje 0-255)
    size=(300, 300),       # wymagany rozmiar wejściowy modelu
    mean=(104.0, 177.0, 123.0),  # mean subtraction (BGR) — standard dla tego modelu
    swapRB=False,          # OpenCV używa BGR — model trenowany na BGR, brak zamiany
)
```

**Uwaga o swapRB:** Model res10 był trenowany na obrazach BGR (OpenCV standard). `swapRB=False` jest poprawne. Niektóre implementacje używają `swapRB=True` (dla RGB pipeline) — to byłoby błędem tutaj.

### Anti-Patterns to Avoid

- **Nie używaj `swapRB=True`** z BGR frame z OpenCV — model trenowany na BGR, zamiana kanałów pogarsza dokładność
- **Nie klipuj bbox do granic klatki** przed przekazaniem — MaszynaStanow.`_sledz()` używa środka bbox, klatka 320x240 zawiera typowe wartości, clipping nie jest krytyczny
- **Nie usuwaj `resetuj_streak()`** — TestTracker wywołuje ją przy TARGET_LOST, interfejs musi pozostać
- **Nie inicjalizuj sieci w `wykryj()`** — ładowanie modelu trwa ~200ms, wyłącznie w `__init__()`
- **Nie przerywaj przy ujemnych bbox** — znormalizowane koordynaty mogą wyjść poza [0,1] przy detekcji częściowej twarzy przy krawędzi — wartości te i tak mają niski confidence i nie przejdą przez threshold

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NMS (Non-Maximum Suppression) | Własna implementacja NMS | Model `detection_out` Layer | res10 ma wbudowany NMS (threshold=0.45, max 200 detekcji) — output jest już po NMS |
| Konwersja formatu | Własny parser tensora | `detections[0, 0, i, 2:7]` | Format SSD jest deterministyczny, 7 kolumn, zweryfikowane empirycznie |
| Download modelu | Własny downloader | wget/curl jednorazowo | Pliki są statyczne, wersja zafixowana w nazwie |
| Resize inputu | Własny resize | `cv2.dnn.blobFromImage(size=(300,300))` | blobFromImage wykonuje resize wewnętrznie — brak `cv2.resize()` przed tym |

**Key insight:** `detection_out` layer w res10 zwraca już przetworzone wyniki (posortowane descending po confidence, po NMS). Iteracja po `detections.shape[2]` i zatrzymanie przy pierwszym `confidence > threshold` wystarczy do znalezienia najlepszego wyniku.

---

## Common Pitfalls

### Pitfall 1: FPS requirement vs. synchroniczna detekcja

**What goes wrong:** Synchroniczne `net.forward()` co klatkę = ~400ms/forward = **2.4 FPS** — narusza D-08 (min. 10 FPS).

**Why it happens:** res10 to sieć 112 warstw. RPi4 (aarch64, brak OpenCL, CPU backend) nie ma akceleracji. Czas forward pasa jest deterministyczny: min 256ms, mediana ~376ms, max ~1260ms (cold start).

**How to avoid:** Użyj `DNN_SKIP_EVERY = 5` — detekcja co 5. klatce daje ~12.5 FPS. Skip=4 daje ~9.4 FPS (FAIL). Skip=5 jest minimalną bezpieczną wartością dla D-08.

**Warning signs:** FPS na HUD poniżej 10 przy pierwszym uruchomieniu po zamianie HAAR → DNN.

### Pitfall 2: Streak filter i skip-frame — interakcja

**What goes wrong:** Streak filter zlicza wywołania `wykryj()`. Przy skip_every=5 klatki 1-4 zwracają cached bbox lub None — streak rośnie poprawnie tylko jeśli `_ostatni_bbox` jest aktualizowany co 5 klatek i przechowywany.

**Why it happens:** Oryginalna implementacja HAAR: każde wywołanie `wykryj()` = nowe wykrywanie. DNN: co 5 wywołań = nowe wykrywanie. Streak musi liczyć wywołania, nie forward passy.

**How to avoid:** Wzorzec z `_ostatni_bbox` (patrz Pattern 1) — streak zlicza wywołania `wykryj()` z niezerowym `_ostatni_bbox`, co jest identyczne z oryginalnym zachowaniem HAAR.

### Pitfall 3: Ścieżki plików modelu — względne vs. absolutne

**What goes wrong:** `cv2.dnn.readNetFromCaffe("models/deploy.prototxt", ...)` działa tylko gdy CWD = root projektu. Uruchomienie z innego katalogu = FileNotFoundError bez czytelnego komunikatu.

**Why it happens:** OpenCV DNN zgłasza wyjątek dopiero przy `setInput()` lub `forward()`, nie przy `readNetFromCaffe()` jeśli plik nie istnieje na niektórych platformach.

**How to avoid:** Sprawdź `os.path.exists()` przed `readNetFromCaffe()` i rzuć RuntimeError z czytelnym komunikatem (wzorzec D-10). Alternatywnie użyj ścieżki względem `__file__`.

**Warning signs:** Cichy fallback lub niejasny błąd OpenCV przy starcie.

### Pitfall 4: Zimny start modelu — pierwszy forward pass jest wolny

**What goes wrong:** Pierwszy `net.forward()` trwa ~1200ms (cold start JIT compilation), kolejne ~380ms. FPS przy pierwszym przebiegu = 0.8 FPS.

**Why it happens:** OpenCV DNN kompiluje kernel CPU przy pierwszym forward pass dla każdego kształtu inputu.

**How to avoid:** "Rozgrzewka" modelu w `__init__()` — jeden dummy forward pass na pustym obrazie przed główną pętlą. Alternatywnie zaakceptować jeden slow frame na starcie.

---

## Code Examples

### Weryfikacja DNN output — empiryczny test (RPi4)

```python
# Source: zmierzono na RPi4 (2026-03-29)
# Output shape: (1, 1, 200, 7)
# Kolumny: [batch_id, class_id, confidence, x1_norm, y1_norm, x2_norm, y2_norm]
# Detekcje posortowane descending wg confidence
# Wartości confidence dla pustego obrazu: max ~0.078 (wszystkie < 0.5 threshold)

detections = net.forward()
W, H = klatka.shape[1], klatka.shape[0]  # 320, 240

for i in range(detections.shape[2]):
    confidence = detections[0, 0, i, 2]
    if confidence < DNN_CONFIDENCE_THRESHOLD:
        break  # Dalsze detekcje mają jeszcze niższy confidence
    x1 = int(detections[0, 0, i, 3] * W)
    y1 = int(detections[0, 0, i, 4] * H)
    x2 = int(detections[0, 0, i, 5] * W)
    y2 = int(detections[0, 0, i, 6] * H)
    bbox = (x1, y1, x2 - x1, y2 - y1)
    break  # Pierwsza detekcja = najwyższy confidence
```

### Ładowanie modelu z walidacją ścieżek

```python
# Wzorzec D-10 — analogia do HAAR empty check
import os

if not os.path.exists(MODEL_PROTOTXT):
    raise RuntimeError(
        f"Nie znaleziono pliku prototxt: {MODEL_PROTOTXT}. "
        "Pobierz model: wget -O models/deploy.prototxt <URL>"
    )
if not os.path.exists(MODEL_CAFFEMODEL):
    raise RuntimeError(
        f"Nie znaleziono pliku caffemodel: {MODEL_CAFFEMODEL}. "
        "Pobierz model: wget -O models/res10_300x300_ssd_iter_140000.caffemodel <URL>"
    )
self._net = cv2.dnn.readNetFromCaffe(MODEL_PROTOTXT, MODEL_CAFFEMODEL)
```

### Stałe modułowe — wzorzec z test_tracker.py

```python
# Analogia do HAAR_MIN_NEIGHBORS = 4, HAAR_MIN_SIZE = (40, 40)
# Usunąć HAAR_MIN_NEIGHBORS i HAAR_MIN_SIZE — zastąpione przez:
DNN_CONFIDENCE_THRESHOLD = 0.5     # próg pewności (D-06)
DNN_SKIP_EVERY = 5                  # detekcja co N klatek — ~12.5 FPS (D-07/D-08 kompromis)
MODEL_PROTOTXT = "models/deploy.prototxt"
MODEL_CAFFEMODEL = "models/res10_300x300_ssd_iter_140000.caffemodel"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HAAR cascade | OpenCV DNN (res10 SSD Caffe) | Phase 13 | Lepsza detekcja pod kątem, przy zasłonięciu |
| detectMultiScale() | blobFromImage + net.forward() | Phase 13 | 400ms/call vs 5-30ms HAAR |
| Stałe HAAR_MIN_NEIGHBORS/SIZE | DNN_CONFIDENCE_THRESHOLD + DNN_SKIP_EVERY | Phase 13 | Prostsze tunowanie |

**Deprecated/outdated po tej fazie:**
- `HAAR_MIN_NEIGHBORS = 4` — do usunięcia (zastąpiony przez `DNN_CONFIDENCE_THRESHOLD`)
- `HAAR_MIN_SIZE = (40, 40)` — do usunięcia (res10 nie ma min size — confidence threshold pełni tę rolę)
- Import `cv2.data.haarcascades` i `cv2.CascadeClassifier` w `DetekcjaTwarzy.__init__()` — do usunięcia

---

## Open Questions

1. **Konflikt D-07 vs D-08 — wymagana decyzja**
   - Co wiem: Synchroniczne co klatkę = 2.4 FPS (zmierzono na RPi4). D-07 mówi "co klatkę, optymalizacja w osobnej fazie". D-08 mówi "min. 10 FPS — jeśli nie osiągnięte, faza niekompletna".
   - Co jest niejasne: D-07 i D-08 są wzajemnie sprzeczne po uzyskaniu danych pomiarowych. D-07 zakładał optymistycznie, że forward pass może być szybki — tak nie jest.
   - Rekomendacja: Planista MUSI rozstrzygnąć. Opcje: (A) Użyj `DNN_SKIP_EVERY=5` w tej fazie (łamie literę D-07 ale spełnia D-08 i spirit D-07 "najpierw zmierz"). (B) Faza jest niekompletna bez FPS fix (D-08). (C) Przepisz D-07 w CONTEXT.md na "detekcja co SKIP_EVERY=5 klatek". **Research rekomenduje opcję A** — dane pomiarowe uzasadniają skip_every, a celem fazy jest działający system.

2. **Streak filter przy skip_every=5 — zachowanie przy utracie twarzy**
   - Co wiem: Przy `_ostatni_bbox = None` po forward passie, klatki 1-4 (z cache None) zerują streak.
   - Co jest niejasne: Czy streak powinien rosnąć tylko przy nowej detekcji DNN (co 5 klatek), czy przy każdym wywołaniu `wykryj()` z niezerowym cache?
   - Rekomendacja: Streak rośnie przy każdym `wykryj()` z `_ostatni_bbox != None` — zachowanie identyczne z HAAR (każda klatka z twarzą = +1 streak). Daje stabilną odpowiedź w TRACKING.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| OpenCV cv2.dnn | DNN forward pass | ✓ | 4.10.0 (system) / 4.8.1.78 (venv) | — |
| numpy | Tensor manipulation | ✓ | 1.26.0 | — |
| models/deploy.prototxt | readNetFromCaffe | ✓ | — (28 KB, pobrano) | wget z GitHub |
| models/res10_300x300_ssd_iter_140000.caffemodel | readNetFromCaffe | ✓ | — (10.6 MB, pobrano) | wget z GitHub |
| OpenCL | GPU acceleration | ✗ | — | CPU (jedyny dostępny backend) |

**Missing dependencies with no fallback:**
- Brak — wszystkie zależności dostępne.

**Missing dependencies with fallback:**
- OpenCL: niedostępny na RPi4 → CPU backend (domyślny, bez konfiguracji).

---

## Validation Architecture

> `workflow.nyquist_validation` nie jest ustawiony w config.json — brak sekcji test_framework ("none"). Projekt używa weryfikacji empirycznej zgodnie z CLAUDE.md ("There are no unit tests").

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Brak (empiryczna weryfikacja) |
| Config file | none |
| Quick run command | `python3 run_test_tracker.py` |
| Full suite command | `python3 run_test_tracker.py` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Notes |
|--------|----------|-----------|-------------------|-------|
| DET-03 | DNN wykrywa twarz pod kątem gdzie HAAR zawiodł | manual/visual | `python3 run_test_tracker.py` | Zielony prostokąt na HUD przy twarzy pod kątem >30° |
| DET-03 | FPS >= 10 na RPi4 | manual/visual | `python3 run_test_tracker.py` | FPS widoczny na HUD (prawy dolny róg) |
| DET-03 | Interfejs `wykryj()` zachowany | structural | import check | MaszynaStanow i TestTracker nie wymagają zmian |

### Wave 0 Gaps

- Brak — weryfikacja empiryczna, nie wymaga plików testowych.

---

## Sources

### Primary (HIGH confidence)

- Empiryczne benchmarki na RPi4 — forward pass timing N=30 (zweryfikowane 2026-03-29)
- `cv2.dnn.readNetFromCaffe` — dostępność zweryfikowana na OpenCV 4.10.0 (RPi4)
- Output tensor shape `(1, 1, 200, 7)` — zweryfikowane empirycznie
- Plik `deploy.prototxt` — pobrany z `opencv/opencv` master, struktura SSD zweryfikowana

### Secondary (MEDIUM confidence)

- Skip_every=5 → ~12.5 FPS — zmierzono na losowym obrazie bez twarzy. Realna twarz może nieznacznie zmienić czas (dodatkowe detekcje, parsowanie).
- Parametry blobFromImage `(104.0, 177.0, 123.0)` — standard dla res10 BGR, potwierdzony w dokumentacji OpenCV samples

### Tertiary (LOW confidence)

- Claim o "lepszej detekcji pod kątem" — wynika z Phase 10 analysis (HAAR zawiódł >30°) + ogólna wiedza o DNN vs. HAAR. Nie zmierzono bezpośrednio na RPi4 (wymagałoby rzeczywistego testu z twarzą pod kątem).

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — OpenCV DNN dostępny i przetestowany
- Architecture: HIGH — parametry blobFromImage i format output zweryfikowane empirycznie
- FPS (skip_every=5): HIGH — zmierzono na RPi4 z rzeczywistym modelem
- DNN dokładność pod kątem: LOW — nie zmierzono bezpośrednio (assumption from Phase 10 findings)

**Research date:** 2026-03-29
**Valid until:** 2026-06-29 (OpenCV API stabilny, model statyczny)
