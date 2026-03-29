# Phase 11: AWB Fix - Research

**Researched:** 2026-03-29
**Domain:** Picamera2 ColourGains API — configure-time vs post-start AWB lock sequencing
**Confidence:** HIGH (code-derived, backed by upstream Picamera2 issue tracker)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Dwa etapy ustawiania ColourGains:
  - Etap 1 (configure-time): Fallback gains w `create_video_configuration(controls={"ColourGains": AWB_FALLBACK_GAINS})` — neutralne kolory od frame 1, przed startem ISP
  - Etap 2 (post-start): Po 2s warm-up, `capture_metadata()` + `set_controls()` z rzeczywistymi gains sensora — re-lock z auto-AWB converged values
- **D-02:** Istniejacy re-read z Phase 9 (D-06) pozostaje — weryfikacja czy gains sie ustawily po set_controls
- **D-03:** `AWB_FALLBACK_GAINS = (1.0, 1.0)` — neutralne, bez wzmocnienia. Minimalna ingerencja w kolory, eliminuje blue tint. Odkomentowac i uzyc w create_video_configuration()
- **D-04:** Fallback (0.0, 0.0) NIGDY nie uzywac — Picamera2 interpretuje jako "re-enable AWB"
- **D-05:** Gdy `capture_metadata()["ColourGains"]` zwraca `None`: uzyj fallback `(1.0, 1.0)`, zaloguj WARNING. Nie crashuj, nie retry
- **D-06:** Gdy `capture_metadata()["ColourGains"]` zwraca `(0.0, 0.0)`: traktuj jak None — uzyj fallback, zaloguj WARNING ("AWB still running, using fallback")
- **D-07:** Odkomentowac fallback guard w `start()` (linie 82-84) — przywrocic obsluge None z nowa wartoscia (1.0, 1.0)

### Claude's Discretion

- Czas warm-up (2s) — Claude moze dostosowac jesli research wskazuje inna wartosc
- Kolejnosc logow — Claude zdecyduje o formacie komunikatow

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AWB-01 | ColourGains sa ustawione na etapie create_video_configuration() — neutralne kolory od pierwszej klatki | Picamera2 `controls` dict in `create_video_configuration()` applies before ISP starts — guarantees frame-1 color. See PITFALLS.md Pitfall 3 and upstream issue #933. |
| AWB-02 | Obraz nie ma blue tint — skora wyglada naturalnie w normalnym oswietleniu wewnetrznym | `(1.0, 1.0)` fallback eliminates blue tint by applying neutral gains before any AWB algorithm runs. Post-start re-lock with settled auto values gives natural colors for actual lighting. |
</phase_requirements>

---

## Summary

Faza 11 to naprawa jednego konkretnego bugu: brak configure-time lock na ColourGains w Picamera2. Aktualny kod (`src/modes/test_tracker.py` linie 67-69) wywoluje `create_video_configuration()` BEZ parametru `controls` — oznacza to, ze ISP startuje z auto-AWB wlaczonym i pierwsze klatki maja blue tint zanim post-start `set_controls()` sie wykona (2-3 klatki opoznienia w driver queue). Rownoczesnie skomentowany fallback guard (linie 82-84) oznacza crash gdy `capture_metadata()["ColourGains"]` zwroci `None` lub `(0.0, 0.0)`.

Naprawa wymaga trzech zsynchronizowanych zmian w jednym pliku: (1) odkomentowanie i zmiana wartosci `AWB_FALLBACK_GAINS`, (2) dodanie `controls={"ColourGains": AWB_FALLBACK_GAINS}` do `create_video_configuration()`, (3) przywrocenie i rozszerzenie fallback guard w bloku post-start o obsuge `(0.0, 0.0)`.

Czas warm-up 2s jest prawidlowy i potwierdzony przez upstream (PITFALLS.md). Istniejacy re-read block (linie 89-101) z Phase 9 zostaje bez zmian.

**Primary recommendation:** Dodac `controls={"ColourGains": (1.0, 1.0)}` do `create_video_configuration()` — jedna linia kodu eliminuje blue tint od pierwszej klatki.

---

## Standard Stack

### Core

Brak nowych zaleznosci — faza modyfikuje isktniejacy kod bez dodawania bibliotek.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| picamera2 | system (apt) | Kamera Picamera2 — juz uzywana | Istniejaca zaleznosc; nie dodawac przez pip |

**Installation:** Zadna — wszystkie zaleznosci juz zainstalowane.

---

## Architecture Patterns

### Docelowa struktura Picamera2Stream.start()

Po naprawie kolejnosc wywolan powinna byc:

```
1. Picamera2()
2. create_video_configuration(lores=..., controls={"ColourGains": AWB_FALLBACK_GAINS})
   ↳ ColourGains = (1.0, 1.0) locked BEFORE configure()
3. configure(video_config)
4. start()
   ↳ ISP startuje z juz zalocowanymi ColourGains — frame 1 ma neutralne kolory
5. start capture thread
6. sleep(2.0)  -- warm-up: auto-AWB konwerguje
7. capture_metadata() → gains
8. if gains is None or gains == (0.0, 0.0):
       gains = AWB_FALLBACK_GAINS
       logger.warning(...)
9. set_controls({"ColourGains": (float(gains[0]), float(gains[1]))})
   ↳ re-lock z rzeczywistymi wartosciami sensora
10. logger.info(f"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})")
11. [istniejacy re-read block z Phase 9 — bez zmian]
```

### Pattern 1: Configure-time ColourGains lock

**What:** Przekazanie `controls` dict do `create_video_configuration()` aplikuje wartosc PRZED `configure()` i `start()`, zanim ISP w ogole sie uruchomi.

**When to use:** Zawsze gdy wymagane jest aby PIERWSZA klatka miala poprawne kolory — bez czekania na `set_controls()` po starcie.

**Example:**
```python
# Source: PITFALLS.md Pitfall 3 / upstream picamera2 issue #933
AWB_FALLBACK_GAINS = (1.0, 1.0)  # neutralne, nie (0.0, 0.0)

video_config = self._picam2.create_video_configuration(
    lores={"size": (self._width, self._height), "format": "YUV420"},
    controls={"ColourGains": AWB_FALLBACK_GAINS}
)
self._picam2.configure(video_config)
self._picam2.start()
```

### Pattern 2: Post-start re-lock z None/(0.0, 0.0) guard

**What:** Po warm-up odczytac rzeczywiste gains z sensora i re-lockowac. Obslugiwac dwa przypadki awarii: `None` (sensor nie zwrocil wartosci) i `(0.0, 0.0)` (AWB nadal dziala — nie skonczona konwergencja).

**When to use:** Etap 2 AWB lock — nadpisuje fallback z etapu 1 rzeczywistymi wartosciami dla konkretnego oswietlenia.

**Example:**
```python
# Source: PITFALLS.md Pitfall 3 + D-05, D-06 z CONTEXT.md
time.sleep(2.0)
metadata = self._picam2.capture_metadata()
gains = metadata.get("ColourGains")
if gains is None or gains == (0.0, 0.0):
    logger.warning("AWB still running lub ColourGains niedostepne, uzywam fallback (1.0, 1.0)")
    gains = AWB_FALLBACK_GAINS
self._picam2.set_controls({"ColourGains": (float(gains[0]), float(gains[1]))})
r, b = gains
logger.info(f"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})")
```

### Anti-Patterns to Avoid

- **`ColourGains = (0.0, 0.0)` w set_controls:** Picamera2 interpretuje jako "re-enable AWB" — nie blokuje kolorow, odwraca caly efekt naprawi. Zawsze filtruj przed ustawieniem.
- **`set_controls()` przed `start()`:** Wywolania set_controls przed startem kamery sa ignorowane przez Picamera2 (per RPi forums t=365052). Jedyna droga do configure-time lock to parametr `controls` w `create_video_configuration()`.
- **`AwbEnable: False` razem z `ColourGains`:** Powoduje sequencing conflict w niektorych wersjach Picamera2 na Bookworm (issue #825). Ustawienie samego `ColourGains` implicitly disables AWB.
- **Integer gains zamiast float:** `(2, 1)` zamiast `(2.0, 1.0)` — TypeError na niektorych wersjach Picamera2. Zawsze explicit float.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| AWB neutral-color lock | Custom color matrix correction | `controls={"ColourGains": (1.0, 1.0)}` w `create_video_configuration()` | Picamera2 API obsluguje to bezposrednio na poziomie ISP — zadne opencv postprocessing nie jest potrzebne |
| AWB convergence detection | Polling loop sprawdzajacy kolor klatki | `time.sleep(2.0)` + `capture_metadata()` | 2s to empirycznie sprawdzony czas konwergencji; polling bylyby nadmiarowym skomplikowaniem |

**Key insight:** Picamera2 ISP pipeline jest wlasciwym miejscem do konfiguracji kolorow — interwencja na poziomie pixel-correction w OpenCV bylaby zawodna i obciazalaby CPU RPi4.

---

## Common Pitfalls

### Pitfall 1: Brak configure-time lock — blue tint od frame 1

**What goes wrong:** `create_video_configuration()` bez `controls` startuje ISP z auto-AWB. `set_controls()` po `start()` wchodzi do efektu po 2-3 klatkach (kernel driver request queue). Wlasnie dlatego pierwsze klatki maja blue tint nawet gdy post-start lock dziala poprawnie.

**Why it happens:** Picamera2 przetwarza `set_controls()` asynchronicznie po stronie kernela. Wywolanie natychmiast po `start()` gwarantuje tylko ze request wejdzie do kolejki — nie ze wejdzie w zycie na nastepnej klatce. Configure-time `controls` sa aplikowane synchronicznie przed uruchomieniem ISP.

**How to avoid:** Zawsze przekazywac `controls={"ColourGains": AWB_FALLBACK_GAINS}` do `create_video_configuration()` — to jest Etap 1 strategii AWB.

**Warning signs:** Blue tint na HUD przez pierwsze 2-3 sekundy, potem poprawne kolory (wskazuje ze post-start lock dziala, ale configure-time brakuje).

### Pitfall 2: Crash gdy capture_metadata() zwraca None

**What goes wrong:** Aktualny kod (linia 85-86) wywoluje `r, b = gains` bez sprawdzenia czy `gains is None`. Gdy sensor nie zwroci wartosci (niektore kombinacje Picamera2/libcamera na Bookworm), kod crasha z `TypeError: cannot unpack non-iterable NoneType object`.

**Why it happens:** Fallback guard (linie 82-84) zostal wyskomentowany. Zostal dodany w v1.7 z wartoscia `(2.5, 1.9)` ale komentarz wskazuje ze nalezy zmienic wartosc na `(1.0, 1.0)`.

**How to avoid:** Odkomentowac guard i zmienic wartosc na `(1.0, 1.0)` per D-07. Jednoczesnie rozszerzyc o check `gains == (0.0, 0.0)` per D-06.

**Warning signs:** `TypeError: cannot unpack non-iterable NoneType object` przy starcie test_trackera — aplikacja crasha przed pokazaniem jakiejkolwiek klatki.

### Pitfall 3: (0.0, 0.0) nie jest neutralne — to sygnał "re-enable AWB"

**What goes wrong:** Przekazanie `ColourGains = (0.0, 0.0)` do `set_controls()` lub `create_video_configuration()` NIE ustawia zerowego wzmocnienia — Picamera2 interpretuje to jako polecenie wznowienia auto-AWB. Blue tint powroci.

**Why it happens:** Picamera2 API uzywa `(0.0, 0.0)` jako specjalnego sentinel value. Wartosc ta moze pojawic sie w `capture_metadata()["ColourGains"]` gdy AWB nie skonczylo konwergencji w ciagu 2s warm-up.

**How to avoid:** Zawsze sprawdzac `gains == (0.0, 0.0)` obok `gains is None` i traktowac jednakowo — jako signal do uzycia fallback.

### Pitfall 4: Zbyt agresywne lub zbyt pasywne fallback gains

**What goes wrong:** Fallback `(2.5, 1.9)` (stara wartosc) moze dawac cieplo-zolty tint zamiast neutralnego. Fallback `(1.0, 1.0)` jest neutralny ale ignoruje fizyczna czulosc sensora IMX219 — kolory moga byc lekko nieoptymalne.

**Why it happens:** Brak "uniwersalnego" poprawnego fallback. Wartosci gain zaleza od srodowiska oswietlenia.

**How to avoid:** `(1.0, 1.0)` jest prawidlowym wyborem per D-03 — minimalna ingerencja. Post-start re-lock z rzeczywistymi wartosciami sensora po 2s warm-up dostarczy optymalnych gains dla aktualnego oswietlenia (Etap 2).

---

## Code Examples

Verified patterns from code analysis and PITFALLS.md:

### Kompletny blok AWB w Picamera2Stream.start() po naprawie

```python
# Source: PITFALLS.md Pitfall 3 + CONTEXT.md D-01 through D-07
AWB_FALLBACK_GAINS = (1.0, 1.0)  # linia 35 — odkomentowac, zmien wartosc

def start(self) -> None:
    """Inicjalizuje kamere i uruchamia watek przechwytywania."""
    self._picam2 = Picamera2()
    # ETAP 1: configure-time lock — neutralne kolory od frame 1 (D-01, AWB-01)
    video_config = self._picam2.create_video_configuration(
        lores={"size": (self._width, self._height), "format": "YUV420"},
        controls={"ColourGains": AWB_FALLBACK_GAINS}
    )
    self._picam2.configure(video_config)
    self._picam2.start()
    logger.info(f"Picamera2 uruchomiona: {self._width}x{self._height} YUV420 (konwersja do BGR)")

    self._running = True
    self._thread = threading.Thread(target=self._petla_przechwytywania, daemon=True)
    self._thread.start()

    # ETAP 2: post-start re-lock z rzeczywistymi wartosciami sensora (D-01)
    logger.info("Czekam na stabilizację AWB (2s)...")
    time.sleep(2.0)
    metadata = self._picam2.capture_metadata()
    gains = metadata.get("ColourGains")
    # Guard: None lub (0.0, 0.0) = AWB nie skonczylo konwergencji (D-05, D-06, D-07)
    if gains is None or gains == (0.0, 0.0):
        logger.warning("AWB still running lub ColourGains niedostepne, uzywam fallback (1.0, 1.0)")
        gains = AWB_FALLBACK_GAINS
    self._picam2.set_controls({"ColourGains": (float(gains[0]), float(gains[1]))})
    r, b = gains
    logger.info(f"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})")

    # Weryfikacja (Phase 9 D-06 — bez zmian, linie 89-101)
    meta_po = self._picam2.capture_metadata()
    gains_po = meta_po.get("ColourGains")
    if gains_po is not None:
        r_po, b_po = gains_po
        logger.info(f"ColourGains potwierdzone z sensora: (R={r_po:.2f}, B={b_po:.2f})")
        if abs(r_po - r) > 0.1 or abs(b_po - b) > 0.1:
            logger.warning(
                f"AWB gains roznia sie od zadanych: zadane=(R={r:.2f}, B={b:.2f}), "
                f"rzeczywiste=(R={r_po:.2f}, B={b_po:.2f})"
            )
    else:
        logger.warning("ColourGains niedostepne w re-read metadata po set_controls")
```

### Zmiany wzgledem obecnego kodu (diff view)

```
LINIA 35:
  PRZED: #AWB_FALLBACK_GAINS = (1.0, 1.0)  # (Red, Blue) — neutralne, bez wzmocnienia
  PO:     AWB_FALLBACK_GAINS = (1.0, 1.0)  # (Red, Blue) — neutralne, bez wzmocnienia

LINIE 67-69 (create_video_configuration):
  PRZED: video_config = self._picam2.create_video_configuration(
             lores={"size": (self._width, self._height), "format": "YUV420"}
         )
  PO:    video_config = self._picam2.create_video_configuration(
             lores={"size": (self._width, self._height), "format": "YUV420"},
             controls={"ColourGains": AWB_FALLBACK_GAINS}
         )

LINIE 81-85 (fallback guard):
  PRZED: gains = metadata.get("ColourGains")
         #if gains is None:
         #    logger.warning("ColourGains niedostępne, używam fallback (2.5, 1.9)")
         #    gains = AWB_FALLBACK_GAINS
         self._picam2.set_controls({"ColourGains": gains})
  PO:    gains = metadata.get("ColourGains")
         if gains is None or gains == (0.0, 0.0):
             logger.warning("AWB still running lub ColourGains niedostepne, uzywam fallback (1.0, 1.0)")
             gains = AWB_FALLBACK_GAINS
         self._picam2.set_controls({"ColourGains": (float(gains[0]), float(gains[1]))})
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `set_controls()` tylko po `start()` | `controls` dict w `create_video_configuration()` jako primary lock | Picamera2 issue #933 (potwierdzone) | Eliminuje blue tint od pierwszej klatki — nie tylko po 2s |
| Fallback `(2.5, 1.9)` | Fallback `(1.0, 1.0)` | Phase 11 decision | Neutralne zamiast potencjalnie cieple-zolte |
| Guard tylko na `None` | Guard na `None` lub `(0.0, 0.0)` | Phase 11 decision | Eliminuje crash gdy AWB nie skonczone |

**Deprecated/outdated:**
- Fallback gains `(2.5, 1.9)`: stara wartosc z v1.7, zastapiona przez `(1.0, 1.0)` — mniejsza ingerencja

---

## Environment Availability

Step 2.6: SKIPPED — faza jest czysto code-only. Wszystkie zaleznosci (picamera2, OpenCV) sa juz zainstalowane i uzywane przez istniejacy kod. Zadnych nowych zewnetrznych zaleznosci.

---

## Validation Architecture

Zgodnie z `config.json`: `test_framework: "none"`. Brak unit testow — weryfikacja jest empiryczna.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | none (empirical verification only) |
| Config file | none |
| Quick run command | `python3 run_test_tracker.py` |
| Full suite command | `python3 run_test_tracker.py` (visual + log inspection) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Notes |
|--------|----------|-----------|-------------------|-------|
| AWB-01 | ColourGains w create_video_configuration() | manual | `python3 run_test_tracker.py` + log inspection | Weryfikacja: log zawiera `ColourGains zablokowane` z niezerowymi wartosciami |
| AWB-02 | Brak blue tint od pierwszej klatki | manual/visual | `python3 run_test_tracker.py` | Weryfikacja: wizualna — skora wyglada naturalnie natychmiast po starcie |

### Sampling Rate

- **Per task commit:** `python3 run_test_tracker.py` — sprawdz logi startowe
- **Phase gate:** Dwa kryteria musza byc TRUE jednoczesnie: (1) log `ColourGains zablokowane: (R=X.XX, B=X.XX)` z X.XX > 0.0, (2) brak blue tint od frame 1 (wizualnie)

### Wave 0 Gaps

None — istniejaca infrastruktura (run_test_tracker.py) pokrywa wszystkie wymagania fazy.

---

## Open Questions

1. **Warm-up time: 2s wystarczajace?**
   - What we know: 2s jest aktualnie uzywane i udokumentowane w PITFALLS.md jako "nie skracac ponizej 1s"
   - What's unclear: Czy w niskim oswietleniu lub przy starcie z zimnej kamery AWB moze potrzebowac dluzej
   - Recommendation: Pozostac przy 2s (zgodnie z Claude's Discretion) — jesli po naprawie kolory nadal nie sa idealne po post-start re-lock, rozwazyc 3s w nastepnym cyklu

2. **Float vs tuple type safety:**
   - What we know: PITFALLS.md Integration Gotchas dokumentuje ze integer gains powoduja TypeError na niektorych wersjach
   - What's unclear: Czy `capture_metadata()["ColourGains"]` zwraca tuple z floatami czy potencjalnie inne typy
   - Recommendation: Zawsze explicit cast `(float(gains[0]), float(gains[1]))` w set_controls — juz uwzglednionne w Code Examples

---

## Sources

### Primary (HIGH confidence)

- `src/modes/test_tracker.py` — bezposrednia analiza kodu: linie 35 (AWB_FALLBACK_GAINS), 67-69 (create_video_configuration), 82-87 (fallback guard + set_controls), 89-101 (re-read block)
- `.planning/research/PITFALLS.md` Pitfall 3 — AWB ColourGains API sequencing (code-derived + upstream issue references)
- `.planning/research/PITFALLS.md` Pitfall 6 — AWB fallback gains values
- `.planning/phases/11-awb-fix/11-CONTEXT.md` — locked decisions D-01 through D-07

### Secondary (MEDIUM confidence)

- GitHub raspberrypi/picamera2 issue #933 (via PITFALLS.md) — controls in create_video_configuration() apply at configure time
- GitHub raspberrypi/picamera2 discussions #592 (via PITFALLS.md) — (0.0, 0.0) = re-enable AWB confirmed by maintainer
- GitHub raspberrypi/picamera2 issue #825 (via PITFALLS.md) — AwbEnable + ColourGains sequencing conflict

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — brak nowych zaleznosci, analiza istniejacego kodu
- Architecture: HIGH — dwie zmiany w jednym pliku, wzorzec potwierdzony przez upstream Picamera2 issues
- Pitfalls: HIGH — wyprowadzone bezposrednio z analizy kodu i upstream bug reports

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stabilny zakres — Picamera2 API zmienia sie rzadko)

---

## Project Constraints (from CLAUDE.md)

Nastepujace dyrektywy CLAUDE.md sa relewantne dla tej fazy:

- **Polish comments/variable names:** Wszystkie nowe zmienne i komentarze w kodzie musza byc po polsku (np. `# neutralne, bez wzmocnienia`)
- **No unit tests:** Weryfikacja jest empiryczna — HTTP responses, visual confirmation, command output. Brak testow automatycznych.
- **Two entry points:** Faza modyfikuje tylko `src/modes/test_tracker.py` (uzywany przez `run_test_tracker.py`). NIE dotykac `src/vision.py` ani `main.py`.
- **Commit convention:** `fix(test-tracker): opis` lub `feat(awb): opis`
- **Picamera2 requires `--system-site-packages`:** Nie instalowac przez pip, uzyc systemowej wersji
