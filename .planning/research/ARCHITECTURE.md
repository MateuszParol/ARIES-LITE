# Architecture Research

**Domain:** Embedded real-time vision + servo control (RPi4 / Picamera2 / PID) — v1.9 Stabilizacja Ruchu i Obrazu
**Researched:** 2026-03-29
**Confidence:** HIGH (kod odczytany bezpośrednio, bugi przetracowane do konkretnych linii)

---

## Standard Architecture

### System Overview (stan aktualny — ścieżka test trackera)

```
run_test_tracker.py
    │
    └─ TestTracker.uruchom()
           │
           ├─ Picamera2Stream.odczytaj()                ← kamera YUV420 320x240
           │       └─ _petla_przechwytywania()          ← daemon thread
           │              capture_array("lores")
           │              → cvtColor(YUV420p2BGR)       ← BUG-3: powinno 2RGB → zielony tint
           │
           ├─ DetekcjaTwarzy.wykryj()                   ← DNN co DNN_SKIP_EVERY=5 klatek + streak=3
           │
           └─ MaszynaStanow.tick()
                   │
                   ├─ SCANNING → _skanuj()
                   │       set_angles(pan=sin(t), tilt=0.0)   ← BUG-1: tilt zawsze 0 podczas skanowania
                   │       DNN blokuje co 5 klatek ~150ms      ← BUG-2: nieregularny interwał → szarpanie
                   │
                   ├─ SCANNING→TRACKING: _przejdz_do(TRACKING)
                   │       brak PID reset()                    ← BUG-4: nagromadzony integral powoduje ucieczkę
                   │
                   ├─ TRACKING → _sledz()
                   │       PID(blad_pan/tilt) → korekta → set_angles()
                   │       [poprawna logika, ale przez BUG-4 initial output może być duży]
                   │
                   └─ PanTiltSystem.set_angles(pan, tilt)
                           pan_servo.angle = pan_clamped    ← GPIO 12, pigpiod H-PWM
                           tilt_servo.angle = tilt_clamped  ← GPIO 13, pigpiod H-PWM
```

### Component Responsibilities

| Komponent | Plik | Odpowiedzialność | Dotknięty przez fix |
|-----------|------|------------------|---------------------|
| `Picamera2Stream` | `test_tracker.py:55–170` | Capture YUV420→BGR, AWB lock, retry | BUG-3: zmiana stałej cvtColor |
| `DetekcjaTwarzy` | `test_tracker.py:173–239` | DNN inference co 5 klatek, streak filter | Pośrednio BUG-2 (DNN blokuje pętlę) |
| `MaszynaStanow` | `test_tracker.py:242–345` | State machine + dual-axis PID + skanowanie | BUG-1, BUG-2, BUG-4 |
| `PanTiltSystem` | `hardware.py:15–109` | Servo abstraction, soft limits, smooth_move_to | Bez zmian |
| `TestTracker` | `test_tracker.py:348–468` | Orchestrator: camera + detect + tick + HUD | Bez zmian |

---

## Recommended Project Structure (niezmieniona)

Wszystkie 4 fixy mieszczą się w jednym pliku — `src/modes/test_tracker.py`.
Żaden fix nie wymaga zmian w `hardware.py`, `config.py` ani `run_test_tracker.py`.

```
ARIES-LITE/
├── src/
│   ├── config.py               # stałe — bez zmian
│   ├── hardware.py             # PanTiltSystem — bez zmian
│   └── modes/
│       └── test_tracker.py     # JEDYNY plik modyfikowany (wszystkie 4 fixy)
├── models/                     # DNN weights — bez zmian
├── run_test_tracker.py         # entry point — bez zmian
└── requirements.txt            # bez zmian
```

---

## Architectural Patterns

### Pattern 1: Izolacja zmian w jednym pliku

**Co:** Wszystkie 4 fixy dotyczą `src/modes/test_tracker.py`. Brak zmian w stabilnych modułach
(`hardware.py`, `config.py`, `run_test_tracker.py`).

**Dlaczego:** Minimalizuje ryzyko regresji. `hardware.py` i `config.py` są sprawdzone empirycznie
na RPi4. Każda zmiana tam wymaga ponownej weryfikacji sprzętowej.

**Trade-off:** Gęsty plik modułu. Akceptowalne dla projektu tej skali (solo developer, embedded).

---

### Pattern 2: YUV420 konwersja — BUG-3 (green tint)

**Co:** `cv2.COLOR_YUV420p2BGR` zamienia kanały R i B w konwersji YUV→BGR.
Wynik ma kanały B i R zamienione — obraz wygląda jak dominacja kanału G (zielony tint)
bo czerwień i niebieskość trafiają na złe pozycje.

**Mechanism:** Picamera2 dostarcza YUV420 z libcamera. Konwencja nazewnictwa libcamera
i OpenCV są wzajemnie odwrócone. Oficjalny przykład Picamera2 (`examples/yuv_to_rgb.py`)
używa `cv2.COLOR_YUV420p2RGB` aby uzyskać poprawny BGR dla OpenCV.

**Potwierdzenie:** GitHub issue #848 raspberrypi/picamera2 — maintainer dodał ostrzeżenie
do dokumentacji o tym zachowaniu. Oficjalny plik przykładowy potwierdza `COLOR_YUV420p2RGB`.

**Lokalizacja buga:** `test_tracker.py:118` w `_petla_przechwytywania()`:
```python
# PRZED (błąd):
klatka = cv2.cvtColor(klatka_yuv, cv2.COLOR_YUV420p2BGR)
# PO (fix):
klatka = cv2.cvtColor(klatka_yuv, cv2.COLOR_YUV420p2RGB)
```

**Note:** Istniejący mechanizm AWB lock (sleep 2s → capture_metadata → set_controls) jest
architekturalnie poprawny. Zielony tint pochodzi z błędnej konwersji YUV, nie z AWB.
`G stały, niezależny od sceny` — to klasyczny objaw R↔B swap, nie problem gain.
Kanał G w libcamera ColourGains jest zawsze 1.0 (tylko R i B są regulowane przez ColourGains).

**Confidence:** HIGH — potwierdzone oficjalnym przykładem i issue trackerem Picamera2.

---

### Pattern 3: Tilt w skanowaniu — BUG-1

**Co:** `_skanuj()` hardkoduje `tilt=0.0` zawsze (`test_tracker.py:302`).
Serwo tilt stoi w miejscu podczas skanowania. Twarze na różnych wysokościach nie są wykrywane.

**Root cause:** Implementacja skanowania jest 1D (tylko oś pan).

**Fix:** Dodać sinusoidę tilt z inną częstotliwością (Lissajous pattern pokrywa 2D przestrzeń):

Nowe stałe modułowe (dodać do sekcji L25–36):
```python
SCAN_AMPLITUDE_TILT = 15.0    # mniejszy zakres niz pan — limit TILT_LIMIT_MAX=30
SCAN_FREQUENCY_TILT = 0.07    # wolniejszy od pan — unika powtorzenia trasy
```

Zmodyfikowana metoda (L299–303):
```python
def _skanuj(self) -> None:
    """Skanowanie Lissajous: pan = A_pan * sin(2π*f_pan*t), tilt = A_tilt * sin(2π*f_tilt*t)."""
    t = time.time()
    pan = SCAN_AMPLITUDE * math.sin(2.0 * math.pi * SCAN_FREQUENCY * t + self._scan_phase_offset)
    tilt = SCAN_AMPLITUDE_TILT * math.sin(2.0 * math.pi * SCAN_FREQUENCY_TILT * t)
    self.hardware.set_angles(pan, tilt)
```

**Note tilt w TRACKING:** W trybie TRACKING tilt działa poprawnie — `_sledz()` oblicza
`nowy_tilt = hardware.tilt_angle + korekta_tilt` i wysyła do `set_angles()`. Serwo tilt
nie reaguje w TRACKING tylko gdy: (a) twarz jest idealnie wycentrowana wertykalnie (blad_tilt=0)
— co jest poprawnym zachowaniem, lub (b) BUG-4 powoduje ucieczke zanim tilt zdaży reagować.

**Confidence:** HIGH — analiza kodu.

---

### Pattern 4: Smooth scanning — BUG-2 (szarpanie)

**Co:** DNN inference blokuje pętlę co `DNN_SKIP_EVERY=5` klatek (~50–150ms na RPi4).
W tym czasie `set_angles()` nie jest wywoływane. Po powrocie z inference, pętla wysyła
wartość `sin(time.time())` — serwo skacze do nowej pozycji bez interpolacji.

**Mechanism:** Pętla główna nie ma stałego timingu. DNN blokuje: 5 szybkich klatek
(brak inference, ~2ms każda) + 1 wolna klatka (DNN ~50–150ms). Serwo odbiera:
5 regularnych sygnałów → długa przerwa → jeden duży skok → 5 regularnych → itd.

**Fix options:**

*Opcja A — minimalna (zmiana DNN_SKIP_EVERY):*
Zwiększyć `DNN_SKIP_EVERY` z 5 do 10. Mniej stallów DNN = rzadsze, ale nie mniejsze skoki.
Zmiana jednej stałej. Weryfikacja: czy skoki są subiektywnie mniejsze.

*Opcja B — właściwa (servo control thread):*
Oddzielić wątek servo od pętli detekcji:
- Pętla główna: oblicza `target_pan`, `target_tilt` (bez `set_angles()`)
- Servo thread: co 50ms interpoluje aktualną pozycję w kierunku target, woła `set_angles()`
- Komunikacja: `threading.Lock` + dwa float volatile (target_pan, target_tilt)

*Opcja C — prosta interpolacja w pętli:*
Nie wysyłać `set_angles()` bezpośrednio z `_skanuj()`. Zamiast tego: każdy tick porównuje
aktualny kąt z docelowym i wykonuje krok max `SERVO_STEP=1.0°`. Przy 10 FPS pipeline
i kroku 1°, skok może wynosić max 1° na tick zamiast 10°+.

**Recommendation:** Etap 1: zmień `DNN_SKIP_EVERY=10` (minimalne ryzyko, szybka weryfikacja).
Jeśli skoki nadal widoczne — wdrożyć Opcja B (servo thread).

**Files changed:** `test_tracker.py` — stała `DNN_SKIP_EVERY` L29 lub nowy wątek.

---

### Pattern 5: PID reset przy TRACKING entry — BUG-4

**Co:** `_przejdz_do()` (L336–345) resetuje PID tylko przy wejściu w `STATE_SCANNING`.
Przy SCANNING→TRACKING, integral accumulator PID zachowuje wartość z poprzedniej sesji.

**Mechanism:**
- Poprzednia sesja TRACKING trwa 5s z twarzą 50px poza centrum (blad_tilt=50)
- Integral ≈ `50 * (5s / 0.033s_sample_time)` = 7575 "pixel-ticks"
- `simple-pid` output_limits klampuje OUTPUT ale nie integral (windup nadal rośnie)
- Po powrocie do SCANNING → twarz znika → TARGET_LOST → SCANNING → nowa twarz → TRACKING
- Przy pierwszym `_sledz()` tick: `I * integral = 0.001 * 7575 = 7.57°` → klampa do 10°
- Serwo natychmiast skacze do limitu zanim twarz zdąży być stabilnie wycentrowana

**Fix:** Dodać `reset()` przy wejściu w TRACKING:
```python
def _przejdz_do(self, nowy_stan: str) -> None:
    logger.info(f"Zmiana stanu: {self.stan} → {nowy_stan}")
    self.stan = nowy_stan
    self._czas_ostatniego_celu = time.time()
    if nowy_stan == config.STATE_SCANNING:
        self.pid_pan.reset()
        self.pid_tilt.reset()
        raw = self.hardware.pan_angle / SCAN_AMPLITUDE
        self._scan_phase_offset = math.asin(max(-1.0, min(1.0, raw)))
    elif nowy_stan == config.STATE_TRACKING:     # NOWE
        self.pid_pan.reset()                     # NOWE
        self.pid_tilt.reset()                    # NOWE
```

**Dlaczego `reset()` jest bezpieczne:** `simple-pid reset()` zeruje integral i last_error.
Przy pierwszym `_sledz()` po reset, PID startuje od 0 — output = P * blad + 0 + D * blad.
To jest poprawne zachowanie przy wejściu w nowe śledzenie. Bez reset() system startuje
z "pamięcią" poprzedniej sesji — błędne.

**Confidence:** HIGH — `simple-pid` dokumentuje `reset()` jako oczyszczenie stanu wewnętrznego.
Zasada sterowania: zawsze resetuj PID przy wejściu do nowego trybu sterowania.

---

## Data Flow

### Przepływ po zastosowaniu wszystkich fixów

```
Picamera2 (YUV420)
    ↓
cvtColor(YUV420p2RGB)           ← [FIX-3: poprawna konwersja, brak zielonego tintu]
    ↓
DetekcjaTwarzy.wykryj()         ← DNN co DNN_SKIP_EVERY klatek (zwiększone do 10)
    ↓
MaszynaStanow.tick(bbox, w, h)
    │
    ├─ SCANNING → _skanuj()
    │       pan = A_pan * sin(2π * f_pan * t + offset)
    │       tilt = A_tilt * sin(2π * f_tilt * t)      ← [FIX-1: tilt skanuje sinusoidą]
    │       set_angles(pan, tilt)
    │       [DNN_SKIP_EVERY=10 → rzadsze stalle]       ← [FIX-2: mniej szarpania]
    │
    ├─ SCANNING→TRACKING: _przejdz_do(TRACKING)
    │       pid_pan.reset()                             ← [FIX-4: czysty start PID]
    │       pid_tilt.reset()
    │
    └─ TRACKING → _sledz()
            blad_pan  = face_cx - frame_cx
            blad_tilt = face_cy - frame_cy
            korekta_pan  = -pid_pan(blad_pan)
            korekta_tilt = -pid_tilt(blad_tilt)
            set_angles(pan + Δpan, tilt + Δtilt)        ← tilt reaguje poprawnie
            ↓
    PanTiltSystem.set_angles(pan_clamped, tilt_clamped)
    pan_servo.angle = pan_clamped   ← GPIO 12, pigpiod
    tilt_servo.angle = tilt_clamped ← GPIO 13, pigpiod
```

---

## Integration Points — macierz zmian

| Fix | Plik | Linia | Metoda | Typ zmiany | Ryzyko |
|-----|------|-------|--------|------------|--------|
| BUG-1: tilt scanning | `test_tracker.py` | L25–36, L299–303 | moduł top + `_skanuj` | MODIFY — +stałe, +sin tilt | NISKIE |
| BUG-2: smooth scan | `test_tracker.py` | L29 | stała `DNN_SKIP_EVERY` | MODIFY — wartość 5→10 | NISKIE |
| BUG-3: green tint | `test_tracker.py` | L118 | `_petla_przechwytywania` | MODIFY — stała cvtColor | MINIMALNE |
| BUG-4: PID escape | `test_tracker.py` | L336–345 | `_przejdz_do` | MODIFY — +2 linie reset | NISKIE |

**Pliki NIE zmieniane:**
- `src/hardware.py` — `PanTiltSystem` jest poprawny, logi WARNING na clamp już istnieją
- `src/config.py` — stałe PID i limity serw są OK; nowe stałe scan tilt trafią do `test_tracker.py`
- `run_test_tracker.py` — entry point jest poprawny

---

## Build Order

Kolejność implementacji respektuje zależności weryfikacyjne i ryzyko:

```
Etap 1: BUG-3 — AWB/YUV fix (test_tracker.py L118)
    Niezależny od reszty. Jednolinijkowa zmiana.
    Weryfikacja: kolory normalne od pierwszej klatki, brak zielonego tintu
    Ryzyko: bliskie zeru — jedna stała w jednej linii

Etap 2: BUG-4 — PID reset na TRACKING entry (test_tracker.py L336-345)
    Niezależny od fix 1 i 3. Dwie linie kodu.
    Weryfikacja: wejście w TRACKING bez natychmiastowego skoku serwa
    Ryzyko: niskie — reset() jest udokumentowanym mechanizmem simple-pid

Etap 3: BUG-1 — tilt w skanowaniu (test_tracker.py L25-36 + L299-303)
    Zależy od: potwierdzenia działania sprzętu tilt z Etap 2 (TRACKING tilt działa → serwo OK)
    Weryfikacja: HUD pokazuje Tilt:+X.X (≠ 0.0) podczas SCANNING
    Nowe stałe: SCAN_AMPLITUDE_TILT=15.0, SCAN_FREQUENCY_TILT=0.07

Etap 4: BUG-2 — smooth scan (test_tracker.py L29)
    Zależy od: Etap 3 (nie ma sensu wygładzać zanim tilt działa w skanowaniu)
    Weryfikacja: subiektywna gładkość ruchu na RPi4, brak widocznych skoków
    Pierwsza próba: DNN_SKIP_EVERY 5→10
    Jeśli niewystarczające: wdrożyć servo interpolation thread (Opcja B)
```

---

## Anti-Patterns

### Anti-Pattern 1: Naprawa YUV przez zmianę AWB gains

**Co robią:** Próbują korygować zielony tint przez zmianę `AWB_FALLBACK_GAINS` z (1.0,1.0)
na inne wartości (np. (0.8, 1.2)).

**Dlaczego złe:** Problem nie leży w gains. R i B są zamienione przez błędną konwersję YUV.
Żadna kombinacja ColourGains (R, B) nie koryguje zamiany kanałów — kanał G pozostaje
dominujący bo R wylądował na miejscu B i vice versa.

**Zamiast tego:** Zmień `COLOR_YUV420p2BGR` na `COLOR_YUV420p2RGB` w `_petla_przechwytywania`.

---

### Anti-Pattern 2: Reset PID tylko przy wejściu w STATE_SCANNING

**Co robią:** `_przejdz_do()` resetuje PID tylko `if nowy_stan == STATE_SCANNING`.

**Dlaczego złe:** Integral accumulates during TRACKING session. Re-entry into TRACKING
with leftover integral causes immediate max-output spike ("escape").

**Zamiast tego:** Reset PID przy KAŻDYM wejściu w stan gdzie kontroler startuje od nowa —
zarówno SCANNING jak i TRACKING.

---

### Anti-Pattern 3: Skanowanie 1D (tylko pan)

**Co robią:** `set_angles(pan=sin(t), tilt=0.0)` — tilt zawsze zerowy.

**Dlaczego złe:** Twarze na różnych wysokościach są pomijane. System "szuka" tylko
w poziomej linii, nie w 2D przestrzeni.

**Zamiast tego:** Lissajous pattern: pan i tilt z różnymi częstotliwościami sinusoidalnymi.
`SCAN_AMPLITUDE_TILT=15.0` (bezpieczny margines od `TILT_LIMIT_MAX=30`),
`SCAN_FREQUENCY_TILT=0.07` (wolniejszy od pan=0.1 → nieperiodyczne pokrycie).

---

### Anti-Pattern 4: Modyfikacja hardware.py dla fixów PID/scan

**Co robią:** Zmieniają soft limits, dodają offset lub filtrowanie w `set_angles()`.

**Dlaczego złe:** `PanTiltSystem` to warstwa hardware — chroni fizyczny kabel kamery (ribbon).
Logika sterowania należy do `MaszynaStanow`, nie do `PanTiltSystem`.
Logi WARNING na clamp w `set_angles()` już istnieją i są wystarczające do diagnostyki.

**Zamiast tego:** Diagnoza przez logi PID w `_sledz()`. Naprawa w `_przejdz_do()` (reset)
lub `_skanuj()` (tilt sinusoida).

---

## Architecture Invariants (nie naruszać)

1. `MaszynaStanow` nie importuje `DetekcjaTwarzy` — granica celowo utrzymana.
2. `smooth_move_to()` pozostaje jedyną ścieżką safe startup do serw.
3. `_przejdz_do()` pozostaje jedyną metodą zmiany stanu — brak inline `self.stan =` poza nią.
4. `set_angles()` w `PanTiltSystem` pozostaje jedyną metodą wysyłania sygnału do serw.
5. AWB lock (sleep 2s → capture_metadata → set_controls) pozostaje w `Picamera2Stream.start()`.

---

## Sources

- Kod: `src/modes/test_tracker.py` — odczytany bezpośrednio (HIGH confidence)
- Kod: `src/hardware.py` — odczytany bezpośrednio (HIGH confidence)
- Kod: `src/config.py` — odczytany bezpośrednio (HIGH confidence)
- Kontekst: `.planning/PROJECT.md` sekcja "Current Milestone v1.9" — HIGH confidence
- [Picamera2 yuv_to_rgb.py example](https://github.com/raspberrypi/picamera2/blob/main/examples/yuv_to_rgb.py) — oficjalny przykład, `COLOR_YUV420p2RGB` (HIGH confidence)
- [Picamera2 issue #848 — RGB Colorspaces and opencv](https://github.com/raspberrypi/picamera2/issues/848) — dokumentuje R↔B swap problem (HIGH confidence)
- [Picamera2 issue #322 — ColourCorrectionMatrix with AWB disabled](https://github.com/raspberrypi/picamera2/issues/322) — Green channel zawsze 1.0 w libcamera (MEDIUM confidence)
- [simple-pid integral windup and reset](https://en.wikipedia.org/wiki/Integral_windup) — zasada sterowania (HIGH confidence — ogólna wiedza)

---

*Architecture research for: ARIES-LITE v1.9 — Stabilizacja Ruchu i Obrazu*
*Researched: 2026-03-29*
