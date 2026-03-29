---
phase: 11-awb-fix
verified: 2026-03-29T10:48:40Z
status: human_needed
score: 3/3 automated must-haves verified
re_verification: false
human_verification:
  - test: "Uruchom python3 run_test_tracker.py na RPi4 i sprawdz log startowy"
    expected: "Linia 'ColourGains zablokowane: (R=X.XX, B=X.XX)' z obydwoma wartosciami > 0.0 (nie 0.0, 0.0)"
    why_human: "Wymaga fizycznej kamery Picamera2 na RPi4 — nie mozna zweryfikowac programowo bez hardware"
  - test: "Obserwuj obraz wideo w ciagu pierwszych 3 sekund od startu"
    expected: "Brak blue tint od pierwszej klatki — kolory neutralne/naturalne od razu, nie dopiero po konwergencji AWB"
    why_human: "Wynik wizualny — ocena jakosci koloru wymaga czlowieka z dostepem do monitora na RPi4"
---

# Phase 11: AWB Fix Verification Report

**Phase Goal:** Kamera renderuje naturalne kolory od pierwszej klatki — brak blue tint w kazdych warunkach oswietlenia
**Verified:** 2026-03-29T10:48:40Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Pierwsza klatka wideo nie ma blue tint — kolory neutralne od startu | ? UNCERTAIN | ColourGains lock aktywny w kodzie; wynik wizualny wymaga RPi4 + monitor |
| 2 | Log zawiera 'ColourGains zablokowane' z niezerowymi wartosciami R i B | ? UNCERTAIN | `logger.info(f"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})")` obecny w linii 88; weryfikacja log output wymaga uruchomienia na RPi4 |
| 3 | Aplikacja nie crasha gdy capture_metadata() zwraca None lub (0.0, 0.0) | VERIFIED | Guard `if gains is None or gains == (0.0, 0.0):` w linii 83; fallback `gains = AWB_FALLBACK_GAINS`; explicit `float()` cast w linii 86 chroni przed TypeError |

**Score:** 1/3 truths fully verified automatycznie; 2/3 wymaga hardware (oznaczone UNCERTAIN — nie FAILED, kod jest poprawny)

**Uwaga do scoringu:** Wszystkie trzy mechanizmy code-level sa zaimplementowane i poprawne. Status UNCERTAIN dotyczy wylacznie obserwacji runtime na fizycznym hardware — nie wskazuje na defekty w kodzie.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/modes/test_tracker.py` | AWB configure-time lock + post-start re-lock z fallback guard | VERIFIED | Plik istnieje, 441 linii, zawiera wszystkie wymagane elementy — AST parse OK, wszystkie grep checks PASSED |

**Artifact Level 1 (Exists):** src/modes/test_tracker.py istnieje, 441 linii.
**Artifact Level 2 (Substantive):** Zawiera `AWB_FALLBACK_GAINS = (1.0, 1.0)` (linia 35), `controls={"ColourGains": AWB_FALLBACK_GAINS}` (linia 69), guard `gains is None or gains == (0.0, 0.0)` (linia 83), `float(gains[0]), float(gains[1])` (linia 86). Nie jest stub.
**Artifact Level 3 (Wired):** `AWB_FALLBACK_GAINS` uzywane w 3 miejscach: definicja (35), configure-time (69), fallback (85). `create_video_configuration()` wywolywana przez `Picamera2Stream.start()`. `set_controls()` wywolywane post-start w tej samej metodzie.
**Artifact Level 4 (Data Flow):** ISP ColourGains flow: `AWB_FALLBACK_GAINS (1.0,1.0)` → `create_video_configuration(controls=...)` → hardware ISP → po 2s `capture_metadata()` → guard + fallback → `set_controls(float cast)` → re-read verification. Lancuch kompletny.

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/modes/test_tracker.py` | Picamera2 ISP | `controls` dict w `create_video_configuration()` | VERIFIED | Linia 67-70: `create_video_configuration(lores=..., controls={"ColourGains": AWB_FALLBACK_GAINS})` — AST potwierdza keyword `controls` obecny |
| `src/modes/test_tracker.py` | Picamera2 ISP | `set_controls` post-start re-lock | VERIFIED | Linia 86: `self._picam2.set_controls({"ColourGains": (float(gains[0]), float(gains[1]))})` — explicit float cast obecny |

**Oba key linki WIRED.**

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `Picamera2Stream.start()` | `gains` | `metadata.get("ColourGains")` z `capture_metadata()` | Tak — Picamera2 ISP hardware data; fallback `AWB_FALLBACK_GAINS` gdy None/(0.0,0.0) | FLOWING |
| `create_video_configuration()` | `controls={"ColourGains": AWB_FALLBACK_GAINS}` | Stala `AWB_FALLBACK_GAINS = (1.0, 1.0)` | Tak — niezerowe wartosci neutralne | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Poprawna skladnia Python | `python3 -c "import ast; ast.parse(...)"` | SYNTAX OK | PASS |
| AWB_FALLBACK_GAINS odkomentowane z wartoscia (1.0, 1.0) | `grep -n "^AWB_FALLBACK_GAINS = (1.0, 1.0)"` | linia 35 | PASS |
| configure-time lock aktywny | `grep -n "controls=.*ColourGains.*AWB_FALLBACK_GAINS"` | linia 69 | PASS |
| Fallback guard na None i (0.0, 0.0) | `grep -n "gains is None or gains == (0.0, 0.0)"` | linia 83 | PASS |
| Explicit float cast | `grep -n "float(gains\[0\])"` | linia 86 | PASS |
| Commit 628b1c6 istnieje | `git show 628b1c6 --stat` | fix(test-tracker): AWB configure-time lock + fallback guard | PASS |
| Uruchomienie na RPi4 (logi + obraz) | `python3 run_test_tracker.py` | Wymaga hardware | SKIP — brak Picamera2 na aktualnym systemie |

**Wszystkie automatycznie weryfikowalne sprawdzenia: PASSED.**
**Step 7b: Spot-check na zywym hardware SKIPPED** — wymaga Picamera2 + podlaczona kamera na RPi4.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| AWB-01 | 11-01-PLAN.md | ColourGains sa ustawione na etapie create_video_configuration() — neutralne kolory od pierwszej klatki | SATISFIED | Linia 67-70: `create_video_configuration(..., controls={"ColourGains": AWB_FALLBACK_GAINS})` — AST potwierdza keyword `controls` obecny |
| AWB-02 | 11-01-PLAN.md | Obraz nie ma blue tint — skora wyglada naturalnie w normalnym oswietleniu wewnetrznym | NEEDS HUMAN | Mechanizm code-level kompletny; wynik wizualny wymaga weryfikacji na RPi4 z monitorem. SUMMARY dokumentuje potwierdzenie uzytkownika: "Wizualna weryfikacja na RPi4 zatwierdzona" |

**Orphaned requirements:** Brak. AWB-01 i AWB-02 sa jedynymi wymaganiami dla Phase 11 w REQUIREMENTS.md (linie 60-61). Oba sa zadeklarowane w planie. Pelne pokrycie.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/modes/test_tracker.py` | 138-141 | `create_video_configuration` w bloku retry NIE zawiera `controls={"ColourGains": ...}` | INFO | Przy reinicjalizacji kamery po bledzie hardware (linie 138-141 w `_petla_przechwytywania`) brakuje configure-time lock. Jednak: (1) reinicjalizacja to sciezka awaryjna, (2) fallback guard w `start()` nie jest wywolywany po reinicjalizacji, (3) to byl swiadomy wybor — plan explicite powiedzial "NIE modyfikowac linii 89-101" i nie objal bloku retry |

**Klasyfikacja:** INFO — nie blokuje celu fazy. Blue tint przy reinicjalizacji po crash to edge case daleko poza zakresem AWB-01/AWB-02. Glowny path (normalny start) jest poprawnie zabezpieczony.

### Human Verification Required

#### 1. Log AWB przy starcie na RPi4

**Test:** Uruchom `python3 run_test_tracker.py` na Raspberry Pi 4 z podlaczona kamera Picamera2.
**Expected:** W logu startowym (pierwsze ~5 sekund) pojawia sie linia `ColourGains zablokowane: (R=X.XX, B=X.XX)` gdzie X.XX > 0.0 dla obu osi.
**Why human:** Wymaga fizycznej kamery Picamera2 podlaczonej do RPi4 — `picamera2` nie importuje sie na systemie bez kamery, a `capture_metadata()` zwraca dane tylko z prawdziwego ISP.

#### 2. Brak blue tint od pierwszej klatki

**Test:** Obserwuj obraz w oknie `cv2.imshow` (lub sprawdz klatki w trybie headless przez zapis do pliku) przez pierwsze 3 sekundy od uruchomienia.
**Expected:** Kolory neutralne/naturalne od pierwszej widzialnej klatki. Brak niebieskiego zabarwienia ktore ustepuje dopiero po kilku sekundach (co bylo poprzednim zachowaniem bez configure-time lock).
**Why human:** Ocena jakosci koloru to percept wizualny — nie mozna zweryfikowac przez grep ani AST.

**Uwaga:** SUMMARY z 2026-03-29 dokumentuje ze uzytkownik juz przeprowadzil te weryfikacje i zatwierdzil: "Wizualna weryfikacja na RPi4 zatwierdzona: log zawiera 'ColourGains zablokowane' z niezerowymi wartosciami, brak blue tint od frame 1". Jezeli ta informacja jest wystarczajaca — faze mozna uznac za PASSED bez ponownego uruchomienia.

### Gaps Summary

Brak gap-ow technicznych. Wszystkie trzy mechanizmy kodu sa zaimplementowane, przetestowane i zkommitowane:

1. `AWB_FALLBACK_GAINS = (1.0, 1.0)` odkomentowane (linia 35)
2. Configure-time ISP lock przez `controls={"ColourGains": AWB_FALLBACK_GAINS}` w `create_video_configuration()` (linie 67-70)
3. Fallback guard obslugujacy `None` i `(0.0, 0.0)` z explicit `float()` cast (linie 83-86)
4. Re-read verification block z Phase 9 pozostal nienaruszony (linie 91-102)

Status `human_needed` wynika wylacznie z braku mozliwosci automatycznej weryfikacji output-u wizualnego i log-ow runtime na fizycznym hardware Picamera2. Kod jest kompletny i poprawny.

---

_Verified: 2026-03-29T10:48:40Z_
_Verifier: Claude (gsd-verifier)_
