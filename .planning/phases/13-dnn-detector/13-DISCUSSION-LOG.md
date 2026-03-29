# Phase 13: DNN Detector - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 13-dnn-detector
**Areas discussed:** Wybor modelu DNN, Strategia migracji, Progi detekcji i FPS, Dostarczenie modelu

---

## Wybor modelu DNN

| Option | Description | Selected |
|--------|-------------|----------|
| res10_300x300 (Caffe) | Sprawdzony model OpenCV DNN (~23MB). Dziala z cv2.dnn.readNetFromCaffe(). Dobrze udokumentowany, stabilny na RPi. Wymaga resize do 300x300. | ✓ |
| YuNet (ONNX) | Nowszy, lekki (~350KB). Obslugiwany przez cv2.FaceDetectorYN od OpenCV 4.5.4+. Szybszy, ale mniej przetestowany na RPi4/aarch64. | |
| Ty zdecyduj | Claude wybierze na podstawie researchu i kompatybilnosci z RPi4. | |

**User's choice:** res10_300x300 (Caffe) (Recommended)
**Notes:** None

---

## Strategia migracji

| Option | Description | Selected |
|--------|-------------|----------|
| Pelna zamiana | DNN zastepuje HAAR calkowicie. Klasa DetekcjaTwarzy uzywa DNN wewnetrznie, interfejs wykryj() bez zmian. HAAR usuniety. Prostsze, mniej kodu. | ✓ |
| DNN + HAAR fallback | DNN jako primary, HAAR jako backup jesli plik modelu brak lub DNN zawiedzie. Bezpieczniejsze ale bardziej zlozone. | |
| Konfigurowalny przelacznik | Flaga CLI --detector haar/dnn wybiera backend. Mozliwosc porownania A/B. Wiecej kodu ale elastycznosc. | |

**User's choice:** Pelna zamiana (Recommended)
**Notes:** None

## Streak filter z DNN

| Option | Description | Selected |
|--------|-------------|----------|
| Zachowaj streak | DNN ma confidence score ale streak filter zapobiega migotaniu. Sprawdzony mechanizm z HAAR, bezpieczna decyzja. | ✓ |
| Usun streak, uzyj confidence | DNN zwraca confidence — wystarczy prog np. 0.7. Streak jest redundantny jesli DNN jest stabilny. | |
| Ty zdecyduj | Claude zdecyduje na podstawie testow DNN. | |

**User's choice:** Zachowaj streak (Recommended)
**Notes:** None

---

## Progi detekcji i FPS

### Confidence threshold

| Option | Description | Selected |
|--------|-------------|----------|
| 0.5 | Permisywny prog — DNN wykryje wiecej twarzy, streak filter odfiltruje migotanie. Analogia do HAAR z minNeighbors=4. | ✓ |
| 0.7 (konserwatywny) | Tylko pewne detekcje. Mniej false positives ale moze nie wykryc twarzy pod katem. | |
| Ty zdecyduj | Claude dobierze po researchu. | |

**User's choice:** 0.5 (Recommended)

### Czestotliwosc detekcji

| Option | Description | Selected |
|--------|-------------|----------|
| Kazda klatka | Najprostsze. Jesli res10 dalby <10 FPS, optymalizacja w osobnej fazie. Najpierw zmierzyc, potem optymalizowac. | ✓ |
| Co 2-3 klatki | DNN co N klatek, miedzy nimi uzyj ostatniego bbox. Wyzszy FPS ale lag w sledzeniu. | |
| Ty zdecyduj | Claude zdecyduje na podstawie benchmarkow. | |

**User's choice:** Kazda klatka (Recommended)
**Notes:** None

---

## Dostarczenie modelu

| Option | Description | Selected |
|--------|-------------|----------|
| W repo (models/) | Plik .caffemodel + .prototxt w katalogu models/. Proste, zero dodatkowych krokow deploy. 23MB to akceptowalne dla RPi projektu. | ✓ |
| Download przy starcie | Skrypt sciaga model z URL jesli brak lokalnie. Mniejsze repo ale wymaga internetu przy pierwszym uruchomieniu. | |
| Ty zdecyduj | Claude wybierze najlepsze podejscie. | |

**User's choice:** W repo (models/) (Recommended)
**Notes:** None

---

## Claude's Discretion

- Dokladna implementacja blob creation (blobFromImage params)
- Parsowanie output DNN (SSD format)
- Konwersja bbox z normalized coords do pixel coords
- Czy usunac stale HAAR_MIN_NEIGHBORS i HAAR_MIN_SIZE po migracji

## Deferred Ideas

- Optymalizacja FPS (detekcja co N klatek) — jesli DNN daje <10 FPS
- OpenCV DNN w main app (vision.py) — osobna faza
- YuNet jako alternatywa — jesli res10 za wolny
- A/B porownanie HAAR vs DNN z metrykami
