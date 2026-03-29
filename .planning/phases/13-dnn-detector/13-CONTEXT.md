# Phase 13: DNN Detector - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Zamiana HAAR cascade na OpenCV DNN (res10_300x300 Caffe) jako glowny detektor twarzy w test_tracker.py. Interfejs `wykryj()` zachowany — `MaszynaStanow` i `TestTracker` nie wymagaja zmian. Cel: lepsza dokladnosc (katy, czesciowe zasloniecie) przy akceptowalnym FPS (>10 na RPi4).

</domain>

<decisions>
## Implementation Decisions

### Wybor modelu DNN
- **D-01:** Model res10_300x300 (Caffe) — sprawdzony, stabilny na RPi4, dobrze udokumentowany. Wymaga cv2.dnn.readNetFromCaffe() z plikami .prototxt + .caffemodel
- **D-02:** Pliki modelu w katalogu `models/` w repo — deploy.prototxt (~28KB) + res10_300x300_ssd_iter_140000.caffemodel (~10.7MB). Zero dodatkowych krokow deploy

### Strategia migracji
- **D-03:** Pelna zamiana HAAR → DNN. Klasa `DetekcjaTwarzy` wewnetrznie uzywa DNN zamiast HAAR. Interfejs `wykryj()` bez zmian — zwraca ten sam format bbox (x, y, w, h) lub None
- **D-04:** HAAR cascade usuniety z DetekcjaTwarzy — brak fallback, brak przelacznika. Prostsza implementacja
- **D-05:** Streak filter ZACHOWANY. DNN ma confidence score ale streak zapobiega migotaniu detekcji. Sprawdzony mechanizm — nie usuwac

### Progi detekcji i FPS
- **D-06:** Confidence threshold = 0.5 — permisywny prog, streak filter odfiltruje niestabilne detekcje. Analogia do HAAR z minNeighbors=4
- **D-07:** Detekcja co kazda klatke — najprostsze podejscie. Jesli FPS spadnie ponizej 10, optymalizacja (co N klatek) w osobnej fazie. Najpierw zmierzyc, potem optymalizowac
- **D-08:** Minimum 10 FPS na RPi4 z DNN — jesli nie osiagniete, faza jest niekompletna

### Dostarczenie modelu
- **D-09:** Pliki modelu commitowane do `models/` w repozytorium. 23MB to akceptowalne dla projektu RPi4
- **D-10:** Jesli plik modelu brakuje przy starcie — RuntimeError z czytelnym komunikatem (analogia do obecnego HAAR empty check)

### Claude's Discretion
- Dokladna implementacja blob creation (cv2.dnn.blobFromImage params: size, mean, swapRB)
- Parsowanie output DNN (format SSD: detections[0, 0, i, 2] = confidence, [3:7] = bbox)
- Konwersja bbox z normalized coords (0-1) do pixel coords (320x240)
- Czy usunac stale HAAR_MIN_NEIGHBORS i HAAR_MIN_SIZE po migracji

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Detekcja
- `src/modes/test_tracker.py` — `DetekcjaTwarzy` klasa (linia 170+), `wykryj()` metoda (linia 184+), stale HAAR (linie 27-29), `STREAK_REQUIRED` (linia 29)
- `src/modes/test_tracker.py` — `MaszynaStanow._sledz()` (linia 277-305) — uzywa `self.detekcja.wykryj(klatka)`, NIE zmieniac
- `src/modes/test_tracker.py` — `TestTracker.petla()` (linia 350+) — wywoluje `self.detekcja.wykryj()`, NIE zmieniac

### Entry point
- `run_test_tracker.py` — moze potrzebowac aktualizacji importow jesli zmienia sie struktura

### Kontekst (nie modyfikowac)
- `src/vision.py` — main app HybridVision, osobna architektura — NIE dotykac w tej fazie
- `src/tracker.py` — main app TrackerMachine — NIE dotykac w tej fazie

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DetekcjaTwarzy` klasa — wrapper z streak filterem, wystarczy zamienic wnetrze `wykryj()` i `__init__()`
- `_rysuj_hud()` — rysuje bbox z detekcji, format (x,y,w,h) musi byc zachowany
- Streak filter (`_streak`, `STREAK_REQUIRED`, `resetuj_streak()`) — zachowany bez zmian

### Established Patterns
- Stale modulowe na poczatku pliku (LORES_WIDTH, LORES_HEIGHT, HAAR_*) — DNN stale analogicznie
- Import error handling z sys.exit(1) (Picamera2) — analogicznie dla braku pliku modelu
- `detectMultiScale()` zwraca array of (x,y,w,h) — DNN output wymaga konwersji do tego formatu

### Integration Points
- `DetekcjaTwarzy.__init__()` — zamiana ladowania HAAR na ladowanie DNN
- `DetekcjaTwarzy.wykryj()` — zamiana detectMultiScale na DNN forward pass + parsowanie
- Nowy katalog `models/` z plikami res10
- Stale HAAR_MIN_NEIGHBORS i HAAR_MIN_SIZE — do zastapienia przez DNN_CONFIDENCE_THRESHOLD

</code_context>

<specifics>
## Specific Ideas

- res10 wymaga resize inputu do 300x300 przez blobFromImage — obecna klatka to 320x240
- Output res10 to SSD format: tensor [1, 1, N, 7] gdzie kolumny = [batch_id, class_id, confidence, x1, y1, x2, y2] (normalized 0-1)
- Konwersja z (x1,y1,x2,y2) normalized → (x,y,w,h) pixels: x=x1*W, y=y1*H, w=(x2-x1)*W, h=(y2-y1)*H
- Phase 10 potwierdzila ze HAAR nie wykrywa pod katem >30° — DNN powinien to naprawic

</specifics>

<deferred>
## Deferred Ideas

- Optymalizacja FPS (detekcja co N klatek) — jesli DNN daje <10 FPS, osobna faza
- OpenCV DNN w main app (vision.py) — osobna faza, inna architektura
- YuNet jako alternatywa — jesli res10 okazalby sie za wolny
- A/B porownanie HAAR vs DNN z metrykami — przyszla faza testowa

</deferred>

---

*Phase: 13-dnn-detector*
*Context gathered: 2026-03-29*
