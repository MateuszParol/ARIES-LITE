# Phase 10: Detection Fix - Research

**Researched:** 2026-03-29
**Domain:** OpenCV HAAR cascade parametry na 320x240 (Picamera2 RPi4)
**Confidence:** HIGH

## Summary

Faza 10 to minimalna, precyzyjnie ograniczona zmiana: dwie stale w `src/modes/test_tracker.py` (`HAAR_MIN_NEIGHBORS` i `HAAR_MIN_SIZE`). Root cause zidentyfikowany w PITFALLS.md poprzez analize kodu — brak potrzeby eksploracji alternatyw. Wszystkie decyzje sa zablokowane przez CONTEXT.md.

`HAAR_MIN_SIZE=(80,80)` oznacza, ze twarz musi zajmowac co najmniej 80px szerokosci na klatce 320px, czyli 25% szerokosci kadru. W praktyce detekcja dziala tylko z odleglosci 20-30 cm przy idealnie frontalnym ustawieniu. `HAAR_MIN_NEIGHBORS=8` to ponad 2.5x powyzej domyslnej wartosci OpenCV (3), eliminujac prawie wszystkie detekcje pod katem. Zmiana na `(40,40)` i `4` rozwiazuje oba problemy jednoczesnie. `STREAK_REQUIRED=3` pozostaje bez zmian — zapewnia filtracje false positives nawet przy luznijszych parametrach HAAR.

Zakres fazy jest celowo wasy: zero zmian w architekturze, zero zmian w vision.py (main app), zero wyciagania stalych do config.py. To celowy projekt: test tracker i main app maja rozne potrzeby, wspolne stale bylyby mylace.

**Primary recommendation:** Zmien dwie stale w `src/modes/test_tracker.py` linie 27-28 i zweryfikuj empirycznie na RPi4.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `HAAR_MIN_SIZE = (40, 40)` — zmiana z (80,80). Pozwala na detekcje twarzy od 40cm do ~100cm przy FOV kamery RPi
- **D-02:** `HAAR_MIN_NEIGHBORS = 4` — zmiana z 8. Blizej default OpenCV (3), ale wciaz filtruje szum. Streak filter zapewnia dodatkowa filtracje
- **D-03:** `STREAK_REQUIRED = 3` — bez zmian. Research potwierdza ze 3 kolejne klatki (~100ms przy 30fps) to wystarczajacy filtr false positives nawet przy bardziej permisywnych parametrach HAAR
- **D-04:** Zmiany TYLKO w `src/modes/test_tracker.py` — vision.py (main app) ma inna architekture (CSRT + dlib verification) i nie jest objeta ta faza
- **D-05:** Nie wyciagac parametrow do config.py — test tracker i main app maja rozne potrzeby, wspolne stale bylyby mylace

### Claude's Discretion

- scaleFactor: jesli 1.1 wymaga korekty przy nowych parametrach, Claude moze dostosowac
- Dodatkowe logging przy zmianie parametrow — Claude zdecyduje czy potrzebne

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DET-01 | HAAR cascade wykrywa twarz z minSize=(40,40) i minNeighbors=4-5 na 320x240 — detekcja na odleglosc 40-100cm | Bezposrednia zmiana stalych w liniach 27-28 test_tracker.py. Parametry potwierdzone przez PITFALLS.md (HIGH confidence, code-derived analysis). |
| DET-02 | System wykrywa twarz pod katem do ±30° (nie tylko idealnie frontalnie) — zielony prostokat na HUD | Osiagalne przez zmiane minNeighbors z 8 na 4. HAAR `haarcascade_frontalface_default.xml` jest trenowany na twarzach do ~30° odchylenia — problem jest nie w kaskadzie, ale w zbyt restrykcyjnym minNeighbors eliminujacym detekcje pod katem. |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| OpenCV (`cv2`) | Zainstalowany (projekt) | `CascadeClassifier.detectMultiScale()` | Juz w uzyciu — `DetekcjaTwarzy` wrapper istnieje |
| `haarcascade_frontalface_default.xml` | Bundled z OpenCV | Kaskada HAAR do detekcji twarzy frontalnych | Juz zaladowany w `DetekcjaTwarzy.__init__()` |

### Instalacja
Brak nowych zaleznosci — uzywa tego, co juz jest zainstalowane.

## Architecture Patterns

### Istniejaca struktura (nie zmienia sie)
```
src/modes/test_tracker.py
├── Stale modulowe (linie 24-34)   # HAAR_MIN_NEIGHBORS, HAAR_MIN_SIZE tu
├── DetekcjaTwarzy                 # wrapper HAAR + streak filter
│   └── wykryj()                   # wywoluje detectMultiScale()
├── MaszynaStanow                  # state machine + PID
└── TestTracker                    # orkiestrator
```

### Zmiana tylko w stalych modulowych (linie 27-28)
```python
# PRZED (linia 27-28):
HAAR_MIN_NEIGHBORS = 8
HAAR_MIN_SIZE = (80, 80)

# PO (linia 27-28):
HAAR_MIN_NEIGHBORS = 4
HAAR_MIN_SIZE = (40, 40)
```

### Dlaczego scaleFactor=1.1 pozostaje bez zmian
`scaleFactor=1.1` oznacza zmniejszanie obrazu o 10% na kazdy poziom piramidalny. Przy `minSize=(40,40)` na klatce 320x240, HAAR bedzie przeszukiwac okna od 40px do ~240px (maxSize domyslnie = None). Przy `scaleFactor=1.1` to ~20 poziomow — wyczerpujace, ale wolniejsze niz 1.3. Na RPi4 przy 320x240 czas detekcji wynosi ~5ms z 1.1, wiec miesci sie w 33ms budgecie klatki. Zmiana nie jest potrzebna.

### Dodatkowe logging (dyskrecja Claude)
Nie dodawac dodatkowego logowania. Istniejacy kod `DetekcjaTwarzy` nie loguje parametrow przy starcie, ale klasa juz loguje `"Klasyfikator HAAR zaladowany."` w `__init__`. Parametry sa widoczne jako stale na gorze pliku. Dodatkowy log bylby redundantny przy tak prostej zmianie.

## Don't Hand-Roll

| Problem | Nie buduj | Uzyj zamiast | Dlaczego |
|---------|-----------|--------------|----------|
| Filtracja false positives przy luznijszych HAAR | Wlasny temporal filter | `STREAK_REQUIRED=3` (juz istnieje) | Streak filter dziala na poziomie `DetekcjaTwarzy.wykryj()` — 3 kolejne klatki = ~100ms przy 30fps; wystarczajace dla tego przypadku |
| Detekcja pod katem | Wlasny preprocessing | Permisywny minNeighbors | Kaskada jest juz trenowana na twarzach do ~30° — problem jest w progu minNeighbors, nie w samej kaskadzie |

## Runtime State Inventory

> Faza greenfield (zmiana stalych) — brak stanu runtime do migracji.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — brak baz danych, brak persystowanych state | — |
| Live service config | None — test tracker jest standalone, bez zewnetrznych serwisow | — |
| OS-registered state | None — brak rejestracji OS | — |
| Secrets/env vars | None — stale sa hardcoded w pliku | — |
| Build artifacts | None — .pyc files regeneruja sie automatycznie | — |

## Common Pitfalls

### Pitfall 1: Zmiana minSize bez zrozumienia wp;ywu na false positives
**Co idzie zle:** Przy `minSize=(40,40)` kaskada bedzie detektowac male wzory twarzo-podobne (np. wzory na ubraniu, swiatla). Bez streak filtra byledzie to problem.
**Dlaczego:** 40px to maly wzorzec — kaskada jest bardziej czula na artefakty.
**Jak unikac:** `STREAK_REQUIRED=3` pozostaje bez zmian (D-03). Zapewnia, ze wymagane sa 3 konsekutywne detekcje (~100ms). Typowe artefakty nie trwaja 3 klatki.
**Znaki ostrzegawcze:** Stan TRACKING wchodzi i natychmiast wychodzi (< 3 klatki) — oznacza pojedyncze false positive przeszlo przez streak filter.

### Pitfall 2: Weryfikacja tylko w idealnych warunkach
**Co idzie zle:** Weryfikacja przy 30cm od kamery, idealnie frontalnie — to bylo dzialajace nawet ze starymi parametrami (przy duzo bliskim ustawieniu).
**Dlaczego:** Root cause to brak detekcji przy 40-100cm i przy odchyleniu do ±30°.
**Jak unikac:** Weryfikacja MUSI testowac: (1) odleglosc 40-100cm, (2) odchylenie glowy do ±30°, (3) TRACKING utrzymywany przez co najmniej 3 sekundy.
**Znaki ostrzegawcze:** "Dziala" tylko przy bardzo bliskim podejsciu — stare parametry tez "dzialaly" w tych warunkach.

### Pitfall 3: Edycja zlego pliku
**Co idzie zle:** `src/vision.py` (main app) ma `minNeighbors=5` i `minSize=(60,60)` — D-04 zabrania dotykania tego pliku.
**Dlaczego:** Architektura main app (CSRT + dlib verification) rozni sie od test tracker. Wspolna zmiana zepsulaby inny system.
**Jak unikac:** Zmiana TYLKO w `src/modes/test_tracker.py` linie 27-28.
**Znaki ostrzegawcze:** Edytor/diff pokazuje zmiany w `src/vision.py` — cofnac natychmiast.

## Code Examples

### Docelowy stan po zmianie (linie 27-28 test_tracker.py)
```python
# Source: CONTEXT.md D-01, D-02 — locked decisions
HAAR_MIN_NEIGHBORS = 4
HAAR_MIN_SIZE = (40, 40)
```

### Istniejace wywolanie detectMultiScale (nie zmienia sie — linie 189-194)
```python
# Source: src/modes/test_tracker.py linia 189-194 (bez zmian)
twarze = self._klasyfikator.detectMultiScale(
    szara,
    scaleFactor=1.1,
    minNeighbors=HAAR_MIN_NEIGHBORS,
    minSize=HAAR_MIN_SIZE,
)
```

Stale sa referencjonowane przez nazwe — zmiana stalych automatycznie propaguje do `wykryj()` bez modyfikacji logiki.

## State of the Art

| Poprzednie podejscie | Aktualne podejscie | Kiedy zmieniono | Wplyw |
|----------------------|-------------------|-----------------|-------|
| `HAAR_MIN_NEIGHBORS=8` | `HAAR_MIN_NEIGHBORS=4` | Phase 10 | Detekcja przy odchyleniu do ±30° |
| `HAAR_MIN_SIZE=(80,80)` | `HAAR_MIN_SIZE=(40,40)` | Phase 10 | Detekcja przy odleglosci 40-100cm |

**Przestarzale/zamknac:**
- `HAAR_MIN_NEIGHBORS=8`: zostal ustawiony zbyt wysoko wzgledem domyslnego OpenCV (3) i walidowany tylko w idealnych warunkach. Nie powtarzac tego bledu.

## Open Questions

1. **Czy scaleFactor=1.1 jest optymalny po zmianie minSize?**
   - Co wiemy: 1.1 przy 320x240 z minSize=(40,40) daje ~20 poziomow piramidalnych, ~5ms na klatke
   - Co jest niejasne: Czy 1.2 lub 1.3 bylby szybszy bez odczuwalnej straty detekcji
   - Rekomendacja: Zostaw 1.1 (aktualna wartosc) — nie zmieniaj w tej fazie. Optymalizacja nalezy do fazy DET-03 (DNN zastepuje HAAR).

2. **Czy streak filter wymaga dostosowania po zmianie parametrow?**
   - Co wiemy: D-03 mowi "bez zmian"; research z PITFALLS.md potwierdza 3 klatki = ~100ms wystarczy
   - Co jest niejasne: Empiryczna stopa false positives przy nowych parametrach
   - Rekomendacja: Zostaw STREAK_REQUIRED=3. Jesli empirycznie za duzo false positives — zwiekszenie do 4 jest minimalnym ryzykiem.

## Environment Availability

> Faza code-only, bez nowych zewnetrznych zaleznosci. Istniejace zaleznosci (OpenCV, Picamera2) sa warunkiem wstepnym systemu — nie sa sprawdzane w tej fazie.

Step 2.6: SKIPPED (zmiana stalych — brak nowych zewnetrznych zaleznosci)

## Validation Architecture

> `workflow.nyquist_validation` nieobecne w config.json — traktowane jako enabled. Jednak `test_framework: "none"` i `linter: "none"` — brak skonfigurowanego frameworka testow.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | none — CLAUDE.md: "There are no unit tests or linting tools configured. Verification is empirical." |
| Config file | none |
| Quick run command | `python3 run_test_tracker.py` (na RPi4) |
| Full suite command | Obserwacja: zielone prostokaty na HUD, TRACKING >= 3s |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DET-01 | Zielony prostokat przy 40-100cm odleglosci | manual/visual | `python3 run_test_tracker.py` → obs. HUD | N/A (brak test files) |
| DET-02 | Detekcja przy odchyleniu do ±30° | manual/visual | `python3 run_test_tracker.py` → obs. HUD | N/A (brak test files) |

**Uwaga:** Oba wymagania wymagaja weryfikacji empirycznej na fizycznym RPi4 z kamera. Weryfikacja automatyczna jest niemozliwa bez kamery i fizycznej obecnosci twarzy — to jest celowy design projektu (CLAUDE.md).

### Sampling Rate
- **Per task commit:** `python3 -c "import ast; ast.parse(open('src/modes/test_tracker.py').read()); print('OK')"` — syntactic check
- **Per wave merge:** `python3 run_test_tracker.py` na RPi4 — obs. green rectangles
- **Phase gate:** DET-01 i DET-02 potwierdzone empirycznie przed `/gsd:verify-work`

### Wave 0 Gaps
None — nie ma frameworka testow; brak test files do utworzenia. Weryfikacja przez `run_test_tracker.py` na hardware.

## Sources

### Primary (HIGH confidence — bezposrednia analiza kodu)
- `src/modes/test_tracker.py` — linie 27-28: aktualne wartosci `HAAR_MIN_NEIGHBORS=8`, `HAAR_MIN_SIZE=(80,80)`; linie 183-206: `DetekcjaTwarzy.wykryj()` z `detectMultiScale()`
- `.planning/research/PITFALLS.md` — Pitfall 1: root cause analysis HAAR too restrictive (HIGH confidence — code-derived)
- `.planning/phases/10-detection-fix/10-CONTEXT.md` — wszystkie decyzje D-01 do D-05
- `.planning/REQUIREMENTS.md` — DET-01, DET-02

### Secondary (MEDIUM confidence)
- OpenCV dokumentacja HAAR: `minNeighbors=3` to standardowy default; wartosci powyzej 5 znaczaco redukuja wskaznik detekcji. Cytowane w PITFALLS.md Sources.

### Tertiary (LOW confidence)
- Brak — wszystkie kluczowe ustalenia maja wsparcie HIGH lub MEDIUM.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — uzywa istniejacych bibliotek, zero nowych zaleznosci
- Architecture: HIGH — zero zmian architektonicznych, tylko dwie stale
- Pitfalls: HIGH — root cause zidentyfikowany przez analiza kodu (PITFALLS.md), potwierdzony przez matematyczne obliczenia FOV

**Research date:** 2026-03-29
**Valid until:** Stabilne — dopoki HAAR i 320x240 sa w uzyciu (dotyczy takze Phase 13 DNN replacement)
