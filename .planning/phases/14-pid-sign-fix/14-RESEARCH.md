# Phase 14: PID Sign Fix - Research

**Researched:** 2026-04-04
**Domain:** PID negative feedback — kalibracja kierunku serw na Arduino Uno R4 WiFi
**Confidence:** HIGH

## Summary

Faza 14 to kalibracja empiryczna wartosci `PAN_INVERT` i `TILT_INVERT` w firmware Arduino (`aries_controller.ino` linie 37-38). Cel: zagwarantowanie, ze PID dziala jako negative feedback (serwa poruszaja sie W KIERUNKU twarzy, nie od niej). Lancuch znaku jest w pelni zrozumialy z kodu: RPi oblicza `error_x/y` jako odchylenie srodka twarzy od centrum kadru (pikselowo), przesyla przez 8B binarny protokol, Arduino normalizuje do `-1..+1` i podaje jako wejscie QuickPID (`Action::direct`), a wynik mnozy przez `PAN_INVERT/TILT_INVERT` przed dodaniem do kata serwa.

Skrypt `scripts/kalibracja_serw.py` istnieje i jest aktualny (kod zgodny z v2.0 R4 WiFi — bez DTR workaround). Wymaga drobnej aktualizacji: comment w nagłówku odwoluje sie do "Arduino Leonardo / Phase 22", co jest przestarzale. Logika kalibracji jest prawidlowa i dziala z aktualnym SerialInterface.

Kluczowe odkrycie (D-08, D-09): `QuickPID(Action::direct)` oznacza, ze wyjscie PID jest **dodatnie gdy wejscie > setpoint**. Setpoint = 0, wejscie = `error / POLOWA_RAMKI`. Dla twarzy po prawej: `error_x = +50` → wejscie PAN = +0.3125 → `_pan_wyjscie > 0`. Jesli `PAN_INVERT = +1`, to `kat_pan += +wartosc` → kamera jedzie w prawo. To jest poprawne negative feedback dla pan. Aktualna konfiguracja (`PAN_INVERT=+1, TILT_INVERT=-1`) musi byc empirycznie potwierdzona na R4 WiFi — montaz mechaniczny moze roznic sie od v1.7.

**Primary recommendation:** Uruchom skrypt kalibracyjny na podlaczonym R4 WiFi, zaobserwuj kierunek ruchu dla 4 krokow, zaktualizuj `PAN_INVERT`/`TILT_INVERT` jesli FAIL, rekompiluj i wgrywaj firmware przez `arduino-cli`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Uzyj istniejacego skryptu `scripts/kalibracja_serw.py` do empirycznej weryfikacji kierunku serw. Claude zweryfikuje stan skryptu (istnienie, aktualnosc) i zaktualizuje jesli trzeba.
- **D-02:** Kolejnosc kalibracji: najpierw pan (bardziej widoczny lewo-prawo), potem tilt.
- **D-03:** Fizyczny montaz identyczny jak w v1.7/v2.0 — pan+=prawo, tilt+=dol. Nie wymaga zmiany orientacji.
- **D-05:** Wynik kalibracji utrwalony jako `#define PAN_INVERT` i `#define TILT_INVERT` w firmware .ino — zmiana wymaga rekompilacji. Akceptowalne bo kalibracja jednorazowa.
- **D-06:** Weryfikacja przez skrypt kalibracyjny + obserwacja wizualna: error_x=+50 → serwo jedzie w prawo, error_y=+30 → serwo pochyla w dol.

### Claude's Discretion
- D-04: Szczegoly skryptu: amplituda testowa, czas obserwacji, zabezpieczenia (smooth_move, male katy), auto vs manual feedback.
- D-07: Czas obserwacji do potwierdzenia negative feedback (kontekst: Success Criteria mowi o konwergencji PID w 1-3s).
- D-08: Researcher zweryfikuje pelny lancuch znaku: _oblicz_error() w brain.py → serial TX → parser Arduino → PID → INVERT → servo. Ustali konwencje obu osi.
- D-09: Gdzie naprawic kierunek (tylko Arduino INVERT vs zmiana po stronie RPi). Researcher przeanalizuje najczystsze rozwiazanie.
- Amplituda i bezpieczenstwo testow kalibracyjnych.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| QuickPID | 3.1.9 (zainstalowany) | PID dual-axis na Arduino | Anti-windup, dOnMeas derivative; Action::direct steruje kierunkiem wyjscia |
| arduino-cli | 1.4.1 (zainstalowany) | Kompilacja i wgrywanie firmware | Dostepne w srodowisku, uzywane w poprzednich fazach |
| arduino:renesas_uno | 1.5.3 (zainstalowany) | Core dla Uno R4 WiFi | Wymagane dla Renesas RA4M1 |
| SerialInterface (src) | v2.0 | Wysylanie ramek 8B z RPi | Gotowa klasa, uzywana przez skrypt kalibracyjny |

### Nie wymagane nowych zaleznos ci
Faza nie dodaje nowych bibliotek — tylko zmiana `#define` i ewentualnie kosmetyczna aktualizacja skryptu.

**Weryfikacja arduino-cli:**
```bash
arduino-cli version        # 1.4.1 — dostepne
arduino-cli core list      # arduino:renesas_uno 1.5.3 — zainstalowane
```

---

## Architecture Patterns

### Lancuch znaku — pelna analiza (D-08)

```
RPi: brain.py _oblicz_error()
  error_x = srodek_x_twarzy - (w // 2)     # + gdy twarz po prawej
  error_y = srodek_y_twarzy - (h // 2)     # + gdy twarz ponizej centrum
  Zakres: error_x = -160..+160, error_y = -120..+120

         ↓ serial 8B LE int16 (PROTOCOL_SPEC.md LOCKED)

Arduino: ServoPID.pid_krok()
  _pan_wejscie  = (float)ostatni_blad_x / POLOWA_RAMKI   # -1..+1
  _tilt_wejscie = (float)ostatni_blad_y / POLOWA_RAMKI   # -1..+1
  Setpoint = 0.0f (cel: wyzerowanie bledu)

  QuickPID(Action::direct): output > 0 gdy input > setpoint
    → gdy twarz po prawej: error_x=+50 → input=+0.3125 → _pan_wyjscie > 0

  kat_pan  += PAN_INVERT  * _pan_wyjscie    # linia 270
  kat_tilt += TILT_INVERT * _tilt_wyjscie   # linia 271
```

**Warunek negative feedback (serwa ida W KIERUNKU twarzy):**

| Sytuacja | error | PID output | INVERT | Zmiana kata | Efekt |
|----------|-------|-----------|--------|-------------|-------|
| Twarz po prawej | error_x=+50 | _pan_wyjscie > 0 | PAN_INVERT=+1 | kat_pan += +wartosc | Kamera w prawo ✓ |
| Twarz po lewej | error_x=-50 | _pan_wyjscie < 0 | PAN_INVERT=+1 | kat_pan += -wartosc | Kamera w lewo ✓ |
| Twarz ponizej | error_y=+30 | _tilt_wyjscie > 0 | TILT_INVERT=-1 | kat_tilt += -wartosc | Kamera w gore ✗ |

**Krytyczne odkrycie dla tilt:** TILT_INVERT=-1 przy error_y=+30 (twarz ponizej) daje `kat_tilt -= wartosc` — kamera porusza sie do GORY. Ale Success Criteria mowi: "twarz ponizej srodka kadru — serwo tilt pochyla kamere w dol (w strone twarzy)".

Interpretacja: jezeli "ponizej centrum" w sensie pikselowym to `error_y > 0` (y pikselowy rosnie w dol), to kamera powinna opuscic sie w dol. Oznacza to ze `kat_tilt` powinien wzrosc (lub zmalec — zalezenie od orientacji montazu serwa tilt).

**To wymaga empirycznej weryfikacji** — mechanika montazu tilt decyduje, czy `kat_tilt += +wartosc` to ruch kamery w dol czy w gore. D-03 zakłada `tilt+=dol`, co sugeruje: `kat_tilt` wieksze = kamera nizej. Jezeli tak, to TILT_INVERT powinien byc `+1`, nie `-1`.

Wnioski: **obecny TILT_INVERT=-1 moze byc bledny** wzgledem nowego montazu R4 WiFi. Kalibracja empiryczna jest obowiazkowa.

### Gdzie naprawic (D-09) — rekomendacja

**Rekomendacja: Arduino INVERT, nie brain.py.**

Uzasadnienie:
- `#define PAN_INVERT/TILT_INVERT` jest semantycznie czystym miejscem: opisuje kierunek mechaniczny serwa, nie logike wizji
- brain.py `_oblicz_error()` jest poprawny matematycznie (standard vision coordinate: y rosnie w dol)
- Protokol binarny jest LOCKED — nie dotykamy serial_interface.py
- Zmiana znaku w brain.py ukrylaby fizyczna charakterystyke montazu

### Procedura kalibracji (D-04)

Skrypt `scripts/kalibracja_serw.py` wymaga aktualizacji komentarza nagłówkowego (odwołuje sie do "Leonardo / Phase 22"). Logika jest prawidlowa dla R4 WiFi.

**Parametry skryptu (aktualne):**
- `CZAS_TESTU_S = 3.0` — 3 sekundy wysylania per krok — wystarczajace
- `OPOZNIENIE_TX = 0.05` — 20 Hz — utrzymuje watchdog (500ms timeout) aktywny
- `error_x=+50, error_y=+30` dla krokow 1 i 3 — male katy, bezpieczne dla MG-90S
- Boot delay 4.0s — nalezy dostosowac do R4 WiFi (R4 nie ma Leonardo DTR reset issue; ESP32-S3 bridge wymaga czasu na CDC enumeration)

**Zabezpieczenia obecne w skrypcie:**
- 20 Hz TX zapobiega watchdog timeout Arduino
- `reset_input_buffer()` przed testem — unikniecie desynchronizacji
- `iface.close()` w `finally` — cleanup nawet przy przerwaniu

### Anti-Patterns to Avoid

- **Nie negowac error_x/y w brain.py** — to zmienialby konwencje protokolu i ukrywal mechanike
- **Nie zmieniaj setpoint QuickPID** — setpoint=0 jest poprawny (cel: wyzerowanie bledu pozycji)
- **Nie dotykaj gainy PID** (KP/KI/KD) w tej fazie — to faza kalibracji kierunku, nie strojenia regulatora
- **Nie pomiaj boot delay** przed kalibracją — R4 WiFi potrzebuje ~4s na USB CDC enumeration i inicjalizacje HMI

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Wysylanie ramek testowych | Rawny struct.pack w skrypcie | `SerialInterface.send_frame()` | Juz istnieje, przetestowany, XOR checksum included |
| Kompilacja firmware | Reczny avr-gcc/arm-gcc | `arduino-cli compile + upload` | Zainstalowany 1.4.1, core renesas_uno dostepny |
| Weryfikacja kierunku | Algorytmiczna analiza | Fizyczna obserwacja + skrypt | Mechanika montazu nie da sie wyznaczyc z kodu |

---

## Common Pitfalls

### Pitfall 1: Boot delay za krótki na R4 WiFi
**What goes wrong:** Skrypt otwiera port i od razu wysyla ramki, ale Arduino nie skonczylo inicjalizacji (LCD bootscreen 500ms + soft start rampa 1000ms + CDC enumeration ~500ms).
**Why it happens:** Stary OPOZNIENIE_BOOT=4.0s byl skrojony pod Leonardo (2s LCD + 1s safe_startup + 1s margines). R4 WiFi ma inny timing boot sequence.
**How to avoid:** Uzyj OPOZNIENIE_BOOT >= 5.0s dla R4 WiFi lub czekaj az Arduino wysle pierwszy sygnalny bajt.
**Warning signs:** Krok 1 nie powoduje ruchu serwa, LCD nie pokazuje "SLEDZ" mimo wysylania ramek.

### Pitfall 2: Watchdog timeout miedzy krokami
**What goes wrong:** 1-sekundowa przerwa `time.sleep(1.0)` miedzy krokami kalibracji powoduje, ze Arduino wraca do SKANOWANIE (watchdog 500ms). Nastepny krok startuje od niespodziewanej pozycji.
**Why it happens:** Watchdog timeout = 500ms, przerwa = 1000ms.
**How to avoid:** Skrypt juz uwzglednia to (komentarz "Arduino wroci do SCAN" — to jest oczekiwane zachowanie). Kazdy krok zaczyna wysylanie ramek, Arduino przechodzi do SLEDZENIE po odebraniu TRYB=2.
**Warning signs:** Serwa sa w srodkowej pozycji na poczatku kazdego kroku — to jest poprawne.

### Pitfall 3: QuickPID Action::direct vs reverse
**What goes wrong:** Pomylka kierunku akcji PID prowadzi do positive feedback bez wzgledu na INVERT.
**Why it happens:** QuickPID::Action::direct: output > 0 gdy input > setpoint. QuickPID::Action::reverse: output < 0 gdy input > setpoint. Aktualny kod uzywa direct — to jest poprawne przy `kat += INVERT * output`.
**How to avoid:** Nie zmieniaj Action — kalibracja odbywa sie przez INVERT, nie przez zmiane Action.

### Pitfall 4: Orientacja osi Y ekranu vs swiat fizyczny
**What goes wrong:** Mylic "twarz ponizej centrum" w sensie pikselowym (error_y > 0, bo y pikselowy rosnie w dol) z "kamera powinna isc w dol".
**Why it happens:** W ukladzie pikselowym: gora ekranu = y=0, dol ekranu = y=240. Twarz ponizej centrum → error_y > 0. Kamera musi sie pochylic w DOL zeby wycentrowac — kat tilt powinien wzrosc (jezeli montaz: wiekszy kat = nizsza kamera).
**How to avoid:** Krok 3 skryptu weryfikuje to empirycznie. Nie zakladaj znaku — obserwuj i mierz.

### Pitfall 5: Porownywanie INVERT z v1.7/legacy
**What goes wrong:** Zakladanie ze TILT_INVERT=-1 z v1.7 jest prawidlowe dla R4 WiFi.
**Why it happens:** Montaz mechaniczny serwa tilt mogl byc odwrocony przy migracji na nowy breadboard R4.
**How to avoid:** Zawsze uruchamiaj kalibracje od zera na nowym montazu sprzetowym.

---

## Code Examples

### Aktualny lancuch PID w firmware (zrodlo: aries_controller.ino linii 263-271)
```cpp
// Source: src/arduino/aries_controller/aries_controller.ino linia 263-271
if (stan == SLEDZENIE) {
    _pan_wejscie  = (float)ostatni_blad_x / POLOWA_RAMKI;   // normalizacja -1..+1
    _tilt_wejscie = (float)ostatni_blad_y / POLOWA_RAMKI;

    _pid_pan.Compute();
    _pid_tilt.Compute();

    // PAN_INVERT=+1, TILT_INVERT=-1 (linie 37-38 — do empirycznej weryfikacji)
    kat_pan  = constrain(kat_pan  + PAN_INVERT  * _pan_wyjscie,  PAN_MIN,  PAN_MAX);
    kat_tilt = constrain(kat_tilt + TILT_INVERT * _tilt_wyjscie, TILT_MIN, TILT_MAX);
    ustaw_serwa();
}
```

### Zmiana INVERT w firmware (miejsce edycji: linia 37-38)
```cpp
// Source: src/arduino/aries_controller/aries_controller.ino linia 36-38
// --- Kierunek serw — empiryczna kalibracja (D-04, D-12) ---
#define PAN_INVERT      (1)    // +1 lub -1 — zmien gdy PAN jedzie OD twarzy
#define TILT_INVERT     (-1)   // +1 lub -1 — zmien gdy TILT jedzie OD twarzy
```

### Kompilacja i wgrywanie po zmianie INVERT
```bash
# Source: arduino-cli docs, Phase 24 precedent
arduino-cli compile \
  --fqbn arduino:renesas_uno:unor4wifi \
  src/arduino/aries_controller/aries_controller.ino

arduino-cli upload \
  --fqbn arduino:renesas_uno:unor4wifi \
  --port /dev/ttyACM0 \
  src/arduino/aries_controller/aries_controller.ino
```

### Uruchomienie kalibracji
```bash
# Source: scripts/kalibracja_serw.py
source venv/bin/activate
python3 scripts/kalibracja_serw.py
```

### Obliczenie bledu w brain.py (zrodlo: src/vision/brain.py linia 229-253)
```python
# Source: src/vision/brain.py _oblicz_error()
# error_x > 0 gdy twarz po PRAWEJ stronie kadru
error_x = srodek_x - (w // 2)   # + gdy twarz po prawej
# error_y > 0 gdy twarz PONIZEJ centrum kadru (y pikselowy rosnie w dol)
error_y = srodek_y - (h // 2)   # + gdy twarz nizej niz centrum
```

---

## Stan skryptu kalibracyjnego — ocena (D-01)

**Plik istnieje:** `scripts/kalibracja_serw.py` — potwierdzono.

**Co jest aktualne:**
- Uzywa `SerialInterface` — poprawny dla R4 WiFi (brak DTR workaround)
- Logika 4 krokow (PAN prawo, lewo, TILT dol, gora) — prawidlowa
- TX 20 Hz, 3s per krok — odpowiednie parametry
- error_x=+50, error_y=+30 — bezpieczne male katy
- `reset_input_buffer()` + `finally: iface.close()` — poprawna obsluga zasobow

**Co wymaga aktualizacji:**
1. Komentarz naglowka: `"Arduino Leonardo z firmware Phase 22"` → powinno byc `"Arduino Uno R4 WiFi z firmware v2.1"` (LINE 15)
2. Komentarz naglowka: `"DTR=False zapobiega resetowi Leonardo per D-19"` jest w `main()` (LINE 77) — nieaktualny, ale nie wpływa na dzialanie; mozna zaktualizowac
3. `OPOZNIENIE_BOOT = 4.0` — rozwazyc zwiekszenie do 5.0s dla R4 WiFi safety margin

**Rekomendacja:** Zaktualizuj 2 komentarze (linie 15 i 77) i ewentualnie OPOZNIENIE_BOOT. Logika nie wymaga zmian.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| arduino-cli | Kompilacja i wgrywanie firmware | ✓ | 1.4.1 | Brak — krytyczne |
| arduino:renesas_uno core | Kompilacja dla R4 WiFi | ✓ | 1.5.3 | Brak — krytyczne |
| Python 3 | Skrypt kalibracyjny | ✓ | 3.13.5 | — |
| pyserial | SerialInterface w skrypcie | sprawdz pip | — | `pip install pyserial` |
| Uno R4 WiFi na /dev/ttyACM0 | Kalibracja + wgrywanie | ✗ (brak polaczenia w dev) | — | Kalibracja musi byc na RPi z podlaczonym R4 |
| Zasilacz 6V dla serw | Ruch serw podczas kalibracji | — | — | Kalibracja bez zasilacza = serwa sie nie ruszaja (D-04 fazy 28: odlozone z tego powodu) |

**Missing dependencies z fallback:**
- Arduino R4 WiFi i zasilacz 6V: wymagane fizycznie na RPi podczas wykonania fazy. Planer musi umieszcic weryfikacje sprzetowa jako prereq.

**Missing dependencies bez fallback:**
- arduino-cli i core renesas_uno sa zainstalowane — brak ryzyka.

---

## Validation Architecture

> `workflow.nyquist_validation` nieobecny w config.json → sekcja wymagana.
> Jednak `test_framework: "none"` i CLAUDE.md: "Weryfikacja jest empiryczna". Testy automatyczne nie sa stosowane w projekcie.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Brak — `test_framework: "none"` w config.json |
| Config file | Brak |
| Quick run command | Weryfikacja empiryczna: `python3 scripts/kalibracja_serw.py` |
| Full suite command | Obserwacja wizualna: twarz → serwo sledzi, brak ucieczki do limitow |

### Phase Requirements → Test Map

Faza nie ma zmapowanych REQ-IDs. Weryfikacja przez Success Criteria:

| Kryterium | Zachowanie | Typ testu | Komenda | |
|-----------|-----------|-----------|---------|--|
| SC-1 | Twarz po prawej → pan obraca w prawo | manual obserwacja | `python3 scripts/kalibracja_serw.py` krok 1 | Manual only |
| SC-2 | Twarz ponizej → tilt w dol | manual obserwacja | Krok 3 skryptu | Manual only |
| SC-3 | Serwa nie docieraja do limitow w 2s | manual obserwacja | Uruchom pelny system + kamera | Manual only |
| SC-4 | Twarz wycentrowana w 1-3s | manual obserwacja | Pelny system na RPi | Manual only |

### Sampling Rate
- **Per task commit:** `arduino-cli compile` — brak bledow kompilacji
- **Per wave merge:** `python3 scripts/kalibracja_serw.py` na RPi z podlaczonym R4 WiFi
- **Phase gate:** SC-1 i SC-2 PASS w skrypcie kalibracyjnym; SC-3 i SC-4 przez obserwacje pelnego systemu

### Wave 0 Gaps
Brak — nie ma infrastruktury testow do tworzenia. Weryfikacja empiryczna.

---

## Open Questions

1. **Aktualny stan TILT_INVERT na R4 WiFi**
   - What we know: `TILT_INVERT=-1` z v1.7. Analiza lancucha znaku sugeruje, ze moze byc niepoprawny (patrz Pitfall 4 i analiza w sekcji Architecture).
   - What's unclear: Orientacja mechaniczna serwa tilt na aktualnym breadboardzie R4 (nie mamy pewnosci czy wiekszy kat = kamera nizej czy wyzej).
   - Recommendation: Krok 3 skryptu kalibracyjnego (TILT dol) rozstrzyga to empirycznie.

2. **Czas boot delay dla R4 WiFi**
   - What we know: `OPOZNIENIE_BOOT=4.0s` byl tunowany dla Leonardo. R4 WiFi ma inny boot timing.
   - What's unclear: Czy 4s jest wystarczajace dla aktualnego firmware (LCD bootscreen + Soft Start rampa + DataLogger init + RTC init).
   - Recommendation: Zwieksz do 5.0s lub dodaj retry loop z timeout.

---

## Sources

### Primary (HIGH confidence)
- `src/arduino/aries_controller/aries_controller.ino` — bezposrednia analiza kodu: PAN_INVERT (linia 37), TILT_INVERT (linia 38), pid_krok() (linie 256-277), QuickPID Action::direct (linia 241-242)
- `src/vision/brain.py` — bezposrednia analiza _oblicz_error() (linie 211-253): konwencja znaku error_x/y
- `src/vision/serial_interface.py` — _buduj_ramke(): struct.pack('<BhhB') little-endian int16
- `scripts/kalibracja_serw.py` — aktualnosc i stan skryptu
- `.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja ramki 8B

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — Accumulated Context: decyzja o TILT_INVERT=-1 z v1.7, montaz standardowy pan+=prawo/tilt+=dol
- QuickPID README (github.com/Dlloydev/QuickPID) — Action::direct semantics: output increases when input > setpoint (z doswiadczenia w projekcie i dokumentacji biblioteki)

---

## Metadata

**Confidence breakdown:**
- Lancuch znaku (error → INVERT → kat): HIGH — bezposrednia analiza kodu
- Stan skryptu kalibracyjnego: HIGH — plik odczytany, logika zweryfikowana
- Aktualnosc INVERT dla R4 WiFi: LOW — wymaga empirycznej kalibracji, nie da sie wywnioskować z kodu
- Dostepnosc arduino-cli/core: HIGH — zweryfikowane `arduino-cli version` i `core list`
- Parametry boot delay dla R4: MEDIUM — na podstawie precedensu Phase 25 (ESP32-S3 bridge)

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stabilna domena — QuickPID API nie zmienia sie czesto)

## Project Constraints (from CLAUDE.md)

- Jezyk komentarzy i nazw zmiennych: **polski** (nowszy kod) lub angielski (starszy core)
- Brak testow automatycznych — weryfikacja empiryczna (HTTP, visual, command output)
- Brak formattera i lintera — nie wymaga konfiguracji
- Nowe stale w `src/config.py` lub w naglowku .ino jako `#define`
- Zapis wyniku kalibracji jako `#define PAN_INVERT/TILT_INVERT` w .ino (D-05)
- Kompilacja przez `arduino-cli compile + upload`
- Entry point dla systemu: `python3 main.py` (full) lub `python3 run_test_tracker.py` (test)
- Skrypt kalibracyjny: `python3 scripts/kalibracja_serw.py`
- GSD workflow: nie modyfikuj plikow poza GSD flow (execute-phase)
