---
phase: 10-detection-fix
verified: 2026-03-29T10:13:07Z
status: human_needed
score: 3/4 must-haves verified
human_verification:
  - test: "Uruchom python3 run_test_tracker.py na RPi4 i stan 40-100cm od kamery"
    expected: "Zielony prostokat pojawia sie na HUD w ciagu 3 sekund od momentu ustawienia sie przed kamera"
    why_human: "Detekcja HAAR w realnych warunkach nie da sie zweryfikowac bez fizycznej kamery i twarzy — wymaga RPi4 + Picamera2 + fizycznej obecnosci"
  - test: "Odchyl glowe ~30° w lewo lub prawo przy aktywnym sledzeniu"
    expected: "Zielony prostokat pozostaje widoczny — TRACKING utrzymywany bez przerwania stanu"
    why_human: "Kata odchylenia glowy nie da sie zasymulowac statycznym kodem — wymaga fizycznej weryfikacji"
  - test: "Po wejsciu w TRACKING — obserwuj stan przez minimum 3 sekundy"
    expected: "Stan TRACKING utrzymywany bez migotania przez >= 3s (streak filter + PID)"
    why_human: "Stabilnosc czasowa stanu maszyny wymaga obserwacji live — nie da sie statycznie zweryfikowac"
---

# Phase 10: Detection Fix — Raport Weryfikacji

**Cel fazy:** HAAR cascade wykrywa twarze w realnych warunkach — zielone prostokaty widoczne na HUD przy normalnym uzytkowaniu
**Data weryfikacji:** 2026-03-29T10:13:07Z
**Status:** human_needed
**Re-weryfikacja:** Nie — weryfikacja inicjalna

## Osiagniecie Celu

### Prawdy Obserwowalne

| # | Prawda | Status | Dowod |
|---|--------|--------|-------|
| 1 | HAAR cascade wykrywa twarz przy odleglosci 40-100cm od kamery | ? HUMAN NEEDED | Parametry HAAR poprawne (minSize=40, minNeighbors=4), empiryczna weryfikacja odleglosci wymaga RPi4 |
| 2 | Detekcja dziala przy odchyleniu glowy do ±30° od frontalnej pozycji | ? HUMAN NEEDED | minNeighbors=4 (blizej default OpenCV 3) umozliwia detekcje pod katem, potwierdzenie wymaga fizycznej weryfikacji |
| 3 | Stan TRACKING utrzymywany przez co najmniej 3 sekundy bez przerwy | ? HUMAN NEEDED | STREAK_REQUIRED=3 bez zmian + stabilne parametry HAAR — weryfikacja czasowa wymaga obserwacji live |
| 4 | Zielony prostokat widoczny na HUD przy normalnym uzytkowaniu | ✓ VERIFIED | _rysuj_hud() linia 400: cv2.rectangle(..., (0, 255, 0), 2) — wywolywane z bbox gdy detekcja aktywna |

**Wynik:** 1/4 prawd zweryfikowanych programatycznie, 3/4 wymaga weryfikacji przez czlowieka

### Artefakty Wymagane

| Artefakt | Dostarcza | Status | Szczegoly |
|----------|-----------|--------|-----------|
| `src/modes/test_tracker.py` | Parametry HAAR dostrojone do warunkow realnych | ✓ VERIFIED | Istnieje, substantywny, okablowany |
| `src/modes/test_tracker.py` | Zredukowany minimalny rozmiar twarzy dla 40-100cm | ✓ VERIFIED | HAAR_MIN_SIZE = (40, 40) na linii 28 |

### Weryfikacja Artefaktow — Trzy Poziomy

#### src/modes/test_tracker.py

**Poziom 1 (Istnienie):** ✓ Plik istnieje

**Poziom 2 (Substancjalnosc):**
- `HAAR_MIN_NEIGHBORS = 4` — linia 27 (zmienione z 8) ✓
- `HAAR_MIN_SIZE = (40, 40)` — linia 28 (zmienione z 80x80) ✓
- `STREAK_REQUIRED = 3` — linia 29 (niezmienione) ✓
- Stare wartosci `HAAR_MIN_NEIGHBORS = 8` i `HAAR_MIN_SIZE = (80, 80)` usuniete ✓
- Syntax check Python AST: OK ✓

**Poziom 3 (Okablowanie):**
- `HAAR_MIN_NEIGHBORS` referencjonowana przez nazwe w `DetekcjaTwarzy.wykryj()` linia 192: `minNeighbors=HAAR_MIN_NEIGHBORS` ✓
- `HAAR_MIN_SIZE` referencjonowana przez nazwe w `DetekcjaTwarzy.wykryj()` linia 193: `minSize=HAAR_MIN_SIZE` ✓
- `_rysuj_hud()` wywolywana z bbox gdy detekcja aktywna (linia 367: `self._rysuj_hud(klatka, bbox, stan)`) ✓
- `cv2.rectangle(..., (0, 255, 0), 2)` rysuje zielony prostokat gdy bbox != None (linia 400) ✓

**Status: ✓ VERIFIED**

### Weryfikacja Kluczowych Polaczen (Key Links)

| Z | Do | Przez | Status | Szczegoly |
|---|----|----|--------|---------|
| `test_tracker.py` linie 27-28 (stale) | `DetekcjaTwarzy.wykryj()` `detectMultiScale()` | stale referencjonowane przez nazwe | ✓ WIRED | Linia 192: `minNeighbors=HAAR_MIN_NEIGHBORS`, linia 193: `minSize=HAAR_MIN_SIZE` |

### Sledzenie Przeplywu Danych (Poziom 4)

Nie dotyczy — zmiana parametrow stalych, nie komponentu renderujacego dane dynamiczne. Renderowanie HUD juz istnialo, zmieniono jedynie wejsciowe progi detekcji HAAR.

### Testy Behawioralne (Spot-Checks)

| Zachowanie | Komenda | Wynik | Status |
|------------|---------|-------|--------|
| Syntax Python OK | `python3 -c "import ast; ast.parse(...)"` | Syntax OK | ✓ PASS |
| Stala HAAR_MIN_NEIGHBORS=4 obecna | `grep "HAAR_MIN_NEIGHBORS = 4" src/modes/test_tracker.py` | linia 27 | ✓ PASS |
| Stala HAAR_MIN_SIZE=(40,40) obecna | `grep "HAAR_MIN_SIZE = (40, 40)" src/modes/test_tracker.py` | linia 28 | ✓ PASS |
| Stara wartosc HAAR_MIN_NEIGHBORS=8 usunieta | `grep "HAAR_MIN_NEIGHBORS = 8" src/modes/test_tracker.py` | brak wynikow | ✓ PASS |
| Stara wartosc HAAR_MIN_SIZE=(80,80) usunieta | `grep "HAAR_MIN_SIZE = (80, 80)" src/modes/test_tracker.py` | brak wynikow | ✓ PASS |
| STREAK_REQUIRED=3 niezmienione | `grep "STREAK_REQUIRED = 3" src/modes/test_tracker.py` | linia 29 | ✓ PASS |
| Stale referencjonowane w detectMultiScale | `grep "minNeighbors=HAAR_MIN_NEIGHBORS"` | linia 192 | ✓ PASS |
| Detekcja live na RPi4 | wymaga uruchomienia na sprz | nie testowalne | ? SKIP (wymaga Picamera2 + RPi4) |

### Pokrycie Wymagan

| Wymaganie | Plan zrodlowy | Opis | Status | Dowod |
|-----------|---------------|------|--------|-------|
| DET-01 | 10-01-PLAN.md | HAAR cascade wykrywa twarz z minSize=(40,40) i minNeighbors=4-5 na 320x240 — detekcja na odleglosc 40-100cm | ✓ SATISFIED (kod) / ? HUMAN (empirycznie) | `HAAR_MIN_SIZE = (40, 40)` linia 28, `HAAR_MIN_NEIGHBORS = 4` linia 27; REQUIREMENTS.md oznaczone [x] |
| DET-02 | 10-01-PLAN.md | System wykrywa twarz pod katem do ±30° (nie tylko idealnie frontalnie) — zielony prostokat na HUD | ✓ SATISFIED (kod) / ? HUMAN (empirycznie) | `minNeighbors=4` blizej default OpenCV (3) umozliwia detekcje pod katem; REQUIREMENTS.md oznaczone [x] |

Oba wymagania oznaczone jako `[x]` (ukonczone) i `Complete` w tabeli statusow REQUIREMENTS.md.

**Wymagania osieroconeSORPHANED:** Brak — wszystkie wymagania fazy 10 (DET-01, DET-02) zawarte w planie 10-01-PLAN.md.

### Znalezione Antywzorce

| Plik | Linia | Wzorzec | Waznosc | Wplyw |
|------|-------|---------|---------|-------|
| `src/modes/test_tracker.py` | 82-84 | Wykomentowany fallback AWB_FALLBACK_GAINS — gains moze byc None, co spowoduje TypeError: cannot unpack non-iterable NoneType na linii 86 | ⚠️ Ostrzezenie | Nie blokuje celu fazy (wykrywanie twarzy), ale moze powodowac crash przy starcie gdy sensor nie zwroci ColourGains |

**Uwaga do antywzorca AWB:** Zmiana ta nie jest czescia zakresu fazy 10 (plan zabrania zmian poza liniami 27-28), ale zostala wlaczona do commita `a5fa317`. Usuniety fallback moze powodowac `TypeError: cannot unpack non-iterable NoneType` na linii 86 (`r, b = gains`) gdy `gains is None`. To potencjalny regresja stabilnosci niezalezna od celu DET-01/DET-02.

### Weryfikacja Wymagana Przez Czlowieka

#### 1. Detekcja twarzy przy odleglosci 40-100cm (DET-01)

**Test:** `sudo pigpiod && python3 run_test_tracker.py` — stan 40-100cm od kamery
**Oczekiwane:** Zielony prostokat pojawia sie na HUD po maksymalnie 3 klatkach (STREAK_REQUIRED=3 przy ~30fps = ~100ms opoznienie)
**Dlaczego czlowiek:** Detekcja HAAR zalezy od rzeczywistych warunkow oswietlenia, kontrastu i proporcji twarzy — nie da sie zasymulowac bez fizycznej kamery

#### 2. Detekcja pod katem ±30° (DET-02)

**Test:** Przy aktywnym TRACKING — odchyl glowe ~30° w lewo lub prawo
**Oczekiwane:** Zielony prostokat pozostaje na HUD, TRACKING utrzymany
**Dlaczego czlowiek:** Kat glowy nie da sie zastapic syntetycznym testem — wymaga fizycznej twarzy pod katem

#### 3. Stabilnosc stanu TRACKING >= 3 sekundy

**Test:** Wejdz w stan TRACKING i obserwuj przez minimum 3 sekundy
**Oczekiwane:** Stan TRACKING bez przerywania — brak migotania do SCANNING i z powrotem
**Dlaczego czlowiek:** Stabilnosc czasowa maszyny stanow wymaga obserwacji live z rzeczywistym strumieniem kamer

#### 4. Weryfikacja braku false positives

**Test:** Skieruj kamere na pusty pokoj (bez twarzy widocznych)
**Oczekiwane:** System pozostaje w stanie SCANNING, NIE wchodzi w TRACKING
**Dlaczego czlowiek:** Podatnosc na false positives zalezy od konkretnego otoczenia i oswietlenia na RPi4

#### 5. Weryfikacja zachowania AWB przy starcie (regression check)

**Test:** Uruchom run_test_tracker.py i sprawdz logi przy inicjalizacji kamery
**Oczekiwane:** Brak `TypeError: cannot unpack non-iterable NoneType` przy linii `r, b = gains` — sensor zwraca ColourGains
**Dlaczego czlowiek:** Zachowanie sensora Picamera2 przy zwracaniu ColourGains jest sprzezowe i nie da sie zagwarantowac bez RPi4

## Podsumowanie Luk

Brak krytycznych luk blokujacych cel fazy w kodzie — zmiany HAAR sa kompletne, substancjalne i prawidlowo okablowane.

**Jedyne zastrzezenie:** Commit `a5fa317` zawiera zmiane poza zakresem planu (wykomentowany fallback AWB_FALLBACK_GAINS), co moze powodowac crash startowy gdy sensor nie zwroci ColourGains. Nie blokuje to DET-01/DET-02 bezposrednio, ale moze uniemozliwic dojscie do etapu detekcji. Zalecane sprawdzenie podczas weryfikacji empirycznej.

**Wszystkie testy programatyczne przeszly.** Cel fazy jest nieosiagalny do potwierdzenia bez fizycznej weryfikacji na RPi4.

---

_Zweryfikowane: 2026-03-29T10:13:07Z_
_Weryfikator: Claude (gsd-verifier)_
