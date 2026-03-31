# Phase 23: Integracja + Kalibracja — Research

**Researched:** 2026-03-31
**Domain:** Distributed tracker integration, servo calibration, Arduino C++ OOP refactor, Polish naming refactor
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Skrypt kalibracyjny Python na RPi (`scripts/kalibracja_serw.py`): wysyła sekwencję testową — error_x=+50 (symulacja twarzy po prawej) i użytkownik obserwuje czy serwo jedzie w prawo. Analogicznie error_y=+30 dla tilt. Deterministyczny, powtarzalny.

**D-02:** Wynik kalibracji utrwalony jako `#define PAN_INVERT` i `#define TILT_INVERT` w firmware (obecny mechanizm z Phase 20). Zmiana wymaga rekompilacji — akceptowalne, bo kalibracja jednorazowa.

**D-03:** RPi: zachowaj obecne nazwy klas — MozgRPi (= VisionManager), SerialInterface, WykrywaczTwarzy, KameraRPi. Nazwy polskie spójne z konwencją nowego kodu. INT-04 opisuje odpowiedzialności, nie wymusza angielskich nazw.

**D-04:** Arduino: refaktoryzacja .ino na klasy C++ w tym samym pliku. Wyodrębnij: ServoPID (pid_tick, gainy, anti-windup), MaszynaStanow (przejścia, dispatch), HMI (LCD, buzzer, przycisk). Globalne zmienne zastąpione polami klas.

**D-07:** Pełny refactor — wszystkie komentarze, zmienne, nazwy funkcji i komunikaty w kodzie po polsku. Zarówno nowy kod jak i istniejący. Dotyczy obu stron: RPi (`src/vision/*.py`) i Arduino (`aries_controller.ino`).

**D-08:** Wyjątek: nazwy techniczne/biblioteczne zostają po angielsku — PID, UART, GPIO, EEPROM, constrain(), millis(), Serial, INVERT. Polskie tylko nazwy domenowe (tryb, błąd, kąt, skan, śledź, ramka, klatka).

### Claude's Discretion

**D-05:** Metoda pomiaru latencji end-to-end — Researcher zbada: logi timestamps (RPi time.monotonic() vs Arduino millis()), round-trip skrypt, lub inna metoda. Kryterium: mierzalny dowód per INT-01.

**D-06:** Scenariusz testowy E2E — Researcher oceni możliwości automatyzacji na hardware. Musi pokryć: INT-01 (tracking działa), INT-02 (negative feedback poprawny), INT-03 (tilt w SCAN i TRACK).

Wewnętrzna struktura klas C++ Arduino (pola, metody, kolejność).
Kolejność refaktoru: najpierw integracja czy najpierw OOP.
Zakres refaktoru nazewnictwa: które konkretne zmienne/funkcje zmieniać.

### Deferred Ideas (OUT OF SCOPE)

Brak — dyskusja pozostała w zakresie fazy.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INT-01 | End-to-end tracking — twarz wykryta na RPi → błąd wysłany → Arduino PID koryguje serwa → kamera śledzi twarz | Łańcuch już istnieje w kodzie; kalibracja `PAN_INVERT` + weryfikacja latencji przez logi timestamps |
| INT-02 | Poprawna logika kierunków (negative feedback) — twarz po prawej = ruch serwa w prawo | Skrypt kalibracyjny wysyła deterministyczny błąd +50; `PAN_INVERT` #define odwraca kierunek |
| INT-03 | Oś pionowa (tilt) działa poprawnie w obu trybach (SCAN i TRACK) | `TILT_INVERT (-1)` już w firmware; weryfikacja SCAN przez obserwację sinusoidy + TRACK przez skrypt kalibracyjny z error_y |
| INT-04 | Kod modularny OOP: klasy VisionManager, SerialInterface, ServoPID | RPi: klasy już są OOP (MozgRPi, SerialInterface, WykrywaczTwarzy, KameraRPi); Arduino: refaktor na ServoPID, MaszynaStanow, HMI w tym samym .ino |
| INT-05 | Wszystkie komentarze w kodzie w języku polskim | Audyt istniejących angielskich nazw; systematyczny refaktor zmiennych, funkcji, komentarzy |

</phase_requirements>

---

## Summary

Faza 23 jest fazą integracji — cały łańcuch `MediaPipe → SerialInterface → Arduino PID → serwa` jest już zaimplementowany w poprzednich fazach. Główna praca to: (1) kalibracja kierunków serw skryptem testowym, (2) refaktoryzacja Arduino firmware na klasy C++, (3) polonizacja istniejącego kodu na obu stronach.

System end-to-end jest funkcjonalny. Kod RPi (`src/vision/*.py`) jest już w pełni OOP z polskimi nazwami klas. Arduino firmware jest proceduralnym C z polskimi komentarzami — wymaga wyodrębnienia klas ServoPID, MaszynaStanow, HMI. Skrypt kalibracyjny jest nowym plikiem na wzór `scripts/echo_test.py`.

**Primary recommendation:** Kolejność pracy: najpierw kalibracja (weryfikuje że system w ogóle działa E2E), potem OOP refaktor Arduino, potem polonizacja. Nie mix jednocześnie — każdy krok osobny commit z empiryczną weryfikacją.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyserial | 3.5 | Serial TX na RPi | Już w użyciu; `SerialInterface.send_frame()` gotowy |
| QuickPID | 3.1.9 | PID dual-axis na Arduino | Już skonfigurowany z anti-windup, 100 Hz |
| Servo (Arduino) | bundled | Kontrola serw MG-90S | Już w użyciu z `safe_startup()` |
| LiquidCrystal | bundled | LCD 1602 HMI | Już w użyciu z `lcd_tick()` |
| mediapipe | 0.10.18 | Detekcja twarzy | Już w użyciu w `WykrywaczTwarzy` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| arduino-cli | 1.4.1 | Kompilacja i upload firmware | Po każdej zmianie .ino |
| time.monotonic_ns | stdlib | Timestamps latencji na RPi | Pomiar czasu TX w petli_glownej |

**Installation:** Wszystkie zależności już zainstalowane. Nowy kod nie wymaga nowych pakietów.

---

## Architecture Patterns

### Istniejąca struktura kodu (bez zmian)

```
src/vision/
├── brain.py          # MozgRPi — petla glowna, error calc, TX, heartbeat
├── camera.py         # KameraRPi — Picamera2, AWB fix, daemon thread
├── detector.py       # WykrywaczTwarzy — MediaPipe FaceDetector, sticky tracking
├── serial_interface.py  # SerialInterface — send_frame(), open(), close()
└── __init__.py

src/arduino/aries_controller/
└── aries_controller.ino  # Firmware — do refaktoru OOP

scripts/
├── echo_test.py      # Wzorzec skryptu testowego serial
└── kalibracja_serw.py  # NOWY — skrypt kalibracyjny (D-01)

run_pi_brain.py       # Entry point
```

### Pattern 1: Skrypt kalibracyjny (D-01)

**What:** Skrypt deterministic serial test — wysyła znane błędy bez konieczności uruchamiania kamery.
**When to use:** Jednorazowo przy kalibracji kierunków serw; można powtarzać przy zmianie montażu.
**Wzorzec z echo_test.py:**

```python
# Source: scripts/echo_test.py
iface = SerialInterface(port=PORT, timeout=2.0)
iface.open()
time.sleep(2.0)           # Leonardo boot delay
iface._ser.reset_input_buffer()
iface.send_frame(mode=MODE_TRACK, error_x=50, error_y=0, face_size=128)
```

**Skrypt kalibracyjny (scripts/kalibracja_serw.py) — struktura:**
```python
# Krok 1: PAN — wysyła error_x=+50 (twarz po prawej) przez ~2s
# Oczekiwany wynik: serwo pan przesuwa sie w PRAWO → PAN_INVERT=+1 poprawny
# Jesli serwo idzie w lewo → PAN_INVERT=-1

# Krok 2: PAN odwrotny — error_x=-50
# Krok 3: TILT — error_y=+30 (twarz ponizej centrum)
# Oczekiwany wynik: serwo tilt kompensuje w DOL → TILT_INVERT=-1 (juz zweryfikowany v1.7)
# Krok 4: TILT odwrotny — error_y=-30

# Po kazdym kroku: pytanie uzytkownika PASS/FAIL (input())
```

**KLUCZOWY FAKT:** Arduino watchdog odpala się po 500ms bez ramek. Skrypt musi wysyłać ciągłe ramki przez cały czas testu, nie tylko jedną. Pętla `while t < CZAS_TESTU: send_frame(...)` z `time.sleep(0.05)` — 20 Hz.

### Pattern 2: Arduino OOP refactor (D-04)

**What:** Wyodrębnij globalne zmienne i funkcje na klasy C++ w tym samym pliku .ino.
**When to use:** Refaktor bez zmiany zachowania — czysto strukturalny.

**Docelowa struktura klas w aries_controller.ino:**

```cpp
// Source: D-04 + analiza istniejącego firmware
class ServoPID {
  // Pola: pidPan, pidTilt, serwo_pan, serwo_tilt
  //       kat_pan, kat_tilt, ostatni_blad_x, ostatni_blad_y
  //       czas_ostatniego_pid, czas_startowy_skanu
public:
  void inicjalizuj();           // init_pid() + safe_startup() + attach
  void pid_tick();              // petla PID 100 Hz
  void skan_tick(unsigned long teraz);  // Lissajous
  void ustaw_serwa();           // write() z clamping
  void pid_reset();             // Reset() obu PID
};

class MaszynaStanow {
  // Pola: stan_systemu (StanSystemu), czas_ostatniej_ramki
  //       bufor ramki, stan_parsera, ramka_idx
public:
  void przetwarzaj_bajt(uint8_t bajt);  // parser
  void dispatch_ramke();                 // ekstrak + przejdz_do
  void przejdz_do(StanSystemu nowy);     // tranzycja
  void watchdog_tick();                   // millis() watchdog
  StanSystemu stan() const;
};

class HMI {
  // Pola: lcd, czas_ostatniego_lcd
  //       przycisk_ostatni_stan, przycisk_czas_zmiany
public:
  void inicjalizuj();           // begin(), bootscreen
  void lcd_tick();              // odswiezanie 5 Hz
  void przycisk_tick();         // debounce + abort
  void buzzer_beep();           // tone() 1kHz 100ms
};

// Globalne instancje (Arduino nie wspiera konstruktorow z parametrami w inicjalizacji)
ServoPID serwa;
MaszynaStanow maszyna;
HMI hmi;
```

**Zależności między klasami w .ino:**
- `MaszynaStanow::dispatch_ramke()` musi wywolywac `serwa.pid_reset()` i `hmi.buzzer_beep()` — cross-class call.
- Opcja A: Przekaż referencje w konstruktorze: `MaszynaStanow(ServoPID& s, HMI& h)` — czyste OOP.
- Opcja B (REKOMENDOWANE): Globalne instancje, `dispatch_ramke()` wolne bezpośrednio `serwa.pid_reset()` — prostsze dla .ino hobby project, bez cyklicznych headerów.

**KLUCZOWY FAKT:** Arduino IDE nie wspiera C++ headerów między klasami w tym samym .ino pliku bez forward declarations. Globalne instancje ze wzajemnymi wywołaniami wymagają deklaracji forward lub właściwej kolejności klas.

**Kolejność deklaracji w .ino:**
1. `#include`, `#define`, `enum`
2. Deklaracja `class HMI` (nie zależy od innych)
3. Deklaracja `class ServoPID` (nie zależy od HMI)
4. Deklaracja `class MaszynaStanow` (zależy od ServoPID i HMI)
5. Globalne instancje: `ServoPID serwa; HMI hmi; MaszynaStanow maszyna(serwa, hmi);`
6. `setup()`, `loop()`

### Pattern 3: Pomiar latencji E2E (D-05)

**Rekomendacja po analizie kodu:** Logi timestamps na stronie RPi.

**Uzasadnienie:**
- Arduino `Serial.print()` kosztuje ~1ms na bajt przy 115200 baud — logowanie timestamps z Arduino spowolniłoby pętlę PID 100 Hz. UNIKAĆ.
- RPi `time.monotonic_ns()` jest już używany w `_petla_glowna()` jako `timestamp_ms`.
- Wystarczy dodać log z timestamp TX w `send_frame()` lub w petli MozgRPi.
- Kryterium INT-01: "<100ms" — latencja USB CDC jest typowo 2-8ms na Linux z `set_low_latency_mode`. Warunkiem są: FPS kamery + czas detekcji MediaPipe + latencja USB.

**Implementacja pomiaru:**
```python
# W MozgRPi._petla_glowna() po send_frame()
czas_tx_ms = time.monotonic_ns() // 1_000_000
logger.info(f"[LATENCJA] TX TRACK: ts={czas_tx_ms}ms err_x={error_x} err_y={error_y}")
```

Pomiar end-to-end z serwa jest niemożliwy bez sprzętowego oscyloskopu. Alternatywa: zmierzyć przez log czasy `detekcja → send_frame()` — to część latencji. Ruch serwa odbywa się w 10ms interwale PID na Arduino.

**Mierzalny dowód dla INT-01:**
- Log pokazuje czas od wykrycia twarzy do send_frame: <= ~30ms (kamera 30 FPS + MediaPipe ~15ms na RPi4)
- USB CDC latencja: 2-8ms
- PID interwał: 10ms (deterministyczny)
- Suma estymowana: ~50-60ms < 100ms ✓

### Pattern 4: Scenariusz testowy E2E (D-06)

**Rekomendacja: Hybryda — skrypt syntetyczny + checklist ręczny z żywą twarzą.**

**Powód:** Na hardware embedded nie można w pełni automatyzować obserwacji ruchu fizycznych serw. Arduino nie odsyła stanu serw przez serial (protokół jednostronny per PROTOCOL_SPEC.md).

**Scenariusz:**

```
Test 1 — INT-01 (E2E latencja):
  Akcja: python3 run_pi_brain.py z podłączonym Arduino
  Obserwacja: logi timestamps, serwą się ruszają
  PASS: serwa reagują w kadrze <=3s od startu + logi pokazu TX

Test 2 — INT-02 (negative feedback PAN):
  Akcja: scripts/kalibracja_serw.py (error_x=+50)
  Obserwacja: serwo pan → PRAWO
  PASS: ruch w kierunku przewidzianym przez PAN_INVERT

Test 3 — INT-03a (TILT w SCAN):
  Akcja: Odpal run_pi_brain.py, poczekaj na SCAN (brak twarzy)
  Obserwacja: serwo tilt oscyluje górę/dół
  PASS: widoczny ruch pionowy w obu kierunkach

Test 4 — INT-03b (TILT w TRACK):
  Akcja: scripts/kalibracja_serw.py (error_y=+30)
  Obserwacja: serwo tilt kompensuje
  PASS: ruch tilt w oczekiwanym kierunku

Test 5 — Żywa twarz (sumaryczny E2E):
  Akcja: Stań przed kamerą po prawej stronie kadru
  Obserwacja: kamera podąża za twarzą
  PASS: konwergencja PID — twarz w centrum <=3s
```

---

## Don't Hand-Roll

| Problem | Nie buduj | Użyj zamiast | Dlaczego |
|---------|-----------|--------------|----------|
| Kalibracja PID gains | Custom auto-tuner | Ręczna kalibracja Kp=2.0 Ki=0.1 Kd=0.5 z Phase 20 | Gains zweryfikowane empirycznie, nie zmieniać w tej fazie |
| Pomiar latencji hardware | Osobny protokół ACK | time.monotonic_ns() w logach RPi | ACK to SER-06 w v2.1 — poza zakresem |
| Forward declarations Arduino | Osobne .h pliki | Właściwa kolejność klas w jednym .ino | Projekt hobby, arduino-cli kompiluje pojedynczy .ino |
| DTR reset protection | Custom USB reset handling | `ser.dtr = False` przed `open()` — już w SerialInterface | Caterina bootloader fix już zaimplementowany |

---

## Audyt istniejących nazw do zmiany (INT-05)

### Arduino firmware (`aries_controller.ino`) — nazwy do spolonizowania

Zasada: ang. domenowe → polskie; lib/techniczne → zostawiamy (per D-08).

| Obecna nazwa | Proponowana polska | Typ | Uwaga |
|---|---|---|---|
| `pan_wej`, `pan_wyj`, `pan_sp` | `pan_wejscie`, `pan_wyjscie`, `pan_setpoint` | float pola PID | setpoint zostaje — techniczne |
| `tilt_wej`, `tilt_wyj`, `tilt_sp` | `tilt_wejscie`, `tilt_wyjscie`, `tilt_setpoint` | float pola PID | |
| `kat_pan`, `kat_tilt` | zostawiamy — już polskie | — | kat = polskie ✓ |
| `ostatni_blad_x`, `ostatni_blad_y` | zostawiamy — już polskie | — | blad = polskie ✓ |
| `stan_parsera` | zostawiamy — już polskie | — | ✓ |
| `stan_systemu` | zostawiamy — już polskie | — | ✓ |
| `ramka_buf`, `ramka_idx` | zostawiamy — już polskie | — | ✓ |
| `czas_ostatniej_ramki` | zostawiamy — już polskie | — | ✓ |
| `czas_ostatniego_pid` | zostawiamy — już polskie | — | ✓ |
| `czas_startowy_skanu` | zostawiamy — już polskie | — | ✓ |
| `IDLE`, `SCAN`, `TRACK` (enum) | `BEZCZYNNOSC`, `SKANOWANIE`, `SLEDZENIE` | enum wartości | Tekst na LCD już po polsku (`SLEDZ`, `SKAN`, `IDLE`) — spójność |
| `safe_startup()` | `bezpieczny_start()` | funkcja | |
| `init_pid()` | `inicjalizuj_pid()` | funkcja | |
| `pid_tick()` | `pid_krok()` | funkcja | |
| `skan_tick()` | `skan_krok()` | funkcja | |
| `lcd_tick()` | `lcd_krok()` | funkcja | |
| `przycisk_tick()` | `przycisk_krok()` | funkcja | |
| `ustaw_serwa()` | zostawiamy — już polskie | — | ✓ |
| `przetwarzaj_bajt()` | zostawiamy — już polskie | — | ✓ |
| `dispatch_ramke()` | `przetworz_ramke()` | funkcja | dispatch = ang. |
| `przejdz_do()` | zostawiamy — już polskie | — | ✓ |
| `WAIT_START`, `READ_PAYLOAD` (enum) | `CZEKAJ_START`, `CZYTAJ_PAYLOAD` | enum wartości | |
| `HALF_FRAME_W` | `POLOWA_RAMKI` | #define | |
| Komentarze ang. | Przetłumacz | komentarze | Np. "timer" opisy |

**UWAGA:** Zmiana enum `IDLE/SCAN/TRACK` → `BEZCZYNNOSC/SKANOWANIE/SLEDZENIE` wymaga aktualizacji:
- `przejdz_do()` — case statements
- `dispatch_ramke()` — cast z trybu
- `lcd_tick()` — switch/case na tryb_str
- `setup()` — `stan_systemu = BEZCZYNNOSC`
- Watchdog w `loop()`

### RPi Python (`src/vision/*.py`) — audyt

**brain.py:**
- `MODE_IDLE`, `MODE_SCAN`, `MODE_TRACK` — stałe modulowe → `TRYB_BEZCZYNNOSC`, `TRYB_SKANOWANIE`, `TRYB_SLEDZENIE` (lub zostawiamy — są spójne z protokołem i używane w SerialInterface)
- `HEARTBEAT_INTERVAL`, `HEARTBEAT_POLL` — zostawiamy jako stałe techniczne
- Zmienne lokalne w `_petla_glowna()`: `tryb = "TRACK"/"SCAN"` → `tryb = "SLEDZENIE"/"SKANOWANIE"` (widoczne w HUD)
- Komentarze angielskie — przetłumaczyć

**serial_interface.py:**
- `START_MARKER`, `FRAME_SIZE`, `BAUDRATE` — zostawiamy (techniczne)
- `payload` → `dane` lub `zawartosc` w `_buduj_ramke()`
- Komentarze angielskie — przetłumaczyć

**detector.py, camera.py:**
- Kod już jest prawie w pełni po polsku
- Sprawdzić: `MODEL_PATH`, `MIN_CONFIDENCE`, `STICKY_PROG` — zostawiamy (techniczne)
- Komentarze angielskie — przetłumaczyć

**WAŻNE:** Zmiana `MODE_SCAN` / `MODE_TRACK` w `brain.py` — to wartości int (0/1/2), nie stringi. Zmiana nazwy stałej jest bezpieczna. Ale `send_frame(mode=MODE_TRACK)` musi nadal wysyłać `mode=2`. Zamiana stałych jest czysto kosmetyczna.

---

## Common Pitfalls

### Pitfall 1: Watchdog resetuje stan podczas kalibracji
**Co się psuje:** Skrypt kalibracyjny wysyła jedną ramkę i czeka — Arduino wraca do SCAN po 500ms.
**Dlaczego:** Watchdog millis() odpala się po 500ms bez ramki, przechodzi do SCAN resetując PID.
**Jak uniknąć:** Skrypt kalibracyjny musi wysyłać ramki w pętli (co ~50ms) przez cały czas obserwacji. Nie tylko jedna ramka.
**Wzorzec:**
```python
koniec = time.monotonic() + CZAS_TESTU_S
while time.monotonic() < koniec:
    iface.send_frame(mode=MODE_TRACK, error_x=blad_x, error_y=0, face_size=128)
    time.sleep(0.05)  # 20 Hz
```

### Pitfall 2: Zmiana enum StanSystemu psuje cast w dispatch_ramke()
**Co się psuje:** Zmiana `IDLE=0, SCAN=1, TRACK=2` na `BEZCZYNNOSC=0, SKANOWANIE=1, SLEDZENIE=2` — cast `(StanSystemu)tryb` nadal działa jeśli wartości liczbowe są niezmienione.
**Dlaczego:** Arduino C++ enum implicit cast z uint8 działa na wartości numeryczne, nie nazwy.
**Jak uniknąć:** Zachować `= 0, = 1, = 2` explicite przy definicji enum. Sprawdzić każde miejsce użycia.

### Pitfall 3: Forward declaration w Arduino OOP
**Co się psuje:** `MaszynaStanow` wywołuje `serwa.pid_reset()` — ale `ServoPID` może być zadeklarowany po `MaszynaStanow` w pliku.
**Dlaczego:** Arduino IDE/arduino-cli kompiluje plik .ino jako C++ jednostka translacji — kolejność deklaracji klas ma znaczenie.
**Jak uniknąć:** Deklaruj klasy od najmniej zależnych do najbardziej zależnych: `HMI` → `ServoPID` → `MaszynaStanow`. LUB użyj forward declaration na początku pliku.

### Pitfall 4: QuickPID pola to wskaźniki — przeniesienie do klasy wymaga uwagi
**Co się psuje:** `QuickPID pidPan(&pan_wej, &pan_wyj, &pan_sp, ...)` — QuickPID trzyma wskaźniki do zmiennych. Gdy pola są w klasie i klasa jest kopiowana/przenoszona, wskaźniki mogą zostać unieważnione.
**Dlaczego:** Arduino nie ma move semantics, ale obiekt globalny nie będzie kopiowany.
**Jak uniknąć:** Użyj globalnych instancji (`ServoPID serwa;`) — nie kopiuj ani nie przekazuj przez wartość. QuickPID musi być zainicjalizowany w `inicjalizuj()` metodzie z `SetOutputLimits` etc., nie w konstruktorze (unika problemów z kolejnością inicjalizacji globalnych).

### Pitfall 5: Leonardo boot delay przy otwieraniu portu w skrypcie
**Co się psuje:** Skrypt otwiera port i od razu wysyła ramki — Arduino jeszcze się inicjalizuje (bootscreen 2s + safe_startup 1s).
**Dlaczego:** `setup()` zajmuje ~3s (2s LCD bootscreen + 1s safe_startup ramp).
**Jak uniknąć:** `time.sleep(4.0)` po `iface.open()` zanim wyślemy pierwszą ramkę kalibracyjną. Wzorzec z echo_test.py używa 2s — dla kalibracji potrzeba 4s.

### Pitfall 6: DTR reset przy otwieraniu portu
**Co się psuje:** Jeśli `ser.dtr` nie jest `False` przed `open()`, Leonardo resetuje się przy podłączeniu. Wszystkie globale się reinicjalizują.
**Dlaczego:** Caterina bootloader reaguje na zmianę DTR.
**Jak uniknąć:** `SerialInterface.open()` już ustawia `dtr=False` — nie pomijać tej metody.

### Pitfall 7: Polonizacja przerywa działający system
**Co się psuje:** Zmiana nazw stałych/funkcji bez aktualizacji wszystkich użyć powoduje błędy kompilacji Arduino lub NameError w Python.
**Jak uniknąć:** Refaktor nazewnictwa w osobnym commicie, po potwierdzeniu że E2E działa. Traktuj jako czysto kosmetyczny krok — nie mix z logiką.

---

## Code Examples

Verified patterns from existing codebase:

### Skrypt kalibracyjny — petla wysylania

```python
# Source: scripts/echo_test.py + wzorzec D-01
import time
from src.vision.serial_interface import SerialInterface

PORT = "/dev/ttyACM0"
CZAS_TESTU_S = 3.0
OPOZNIENIE_TX = 0.05  # 20 Hz
MODE_TRACK = 2

iface = SerialInterface(port=PORT, timeout=2.0)
iface.open()
time.sleep(4.0)  # Leonardo boot delay (2s LCD + 1s safe_startup + 1s margines)
iface._ser.reset_input_buffer()

print("TEST PAN: error_x=+50 — obserwuj serwo PAN")
print("Oczekiwany ruch: PRAWO (positive error = face right of center)")
koniec = time.monotonic() + CZAS_TESTU_S
while time.monotonic() < koniec:
    iface.send_frame(mode=MODE_TRACK, error_x=50, error_y=0, face_size=128)
    time.sleep(OPOZNIENIE_TX)

wynik = input("Serwo pan poruszylo sie w PRAWO? [t/n]: ")
```

### Arduino OOP — ServoPID szkielet

```cpp
// Source: D-04 + analiza aries_controller.ino
class ServoPID {
public:
  float kat_pan;
  float kat_tilt;
  int16_t ostatni_blad_x;
  int16_t ostatni_blad_y;

private:
  Servo _serwo_pan;
  Servo _serwo_tilt;
  float _pan_wejscie, _pan_wyjscie, _pan_setpoint;
  float _tilt_wejscie, _tilt_wyjscie, _tilt_setpoint;
  QuickPID _pid_pan;
  QuickPID _pid_tilt;
  unsigned long _czas_ostatniego_pid;
  unsigned long _czas_startowy_skanu;

public:
  ServoPID() :
    kat_pan(0.0f), kat_tilt(0.0f),
    ostatni_blad_x(0), ostatni_blad_y(0),
    _pan_wejscie(0), _pan_wyjscie(0), _pan_setpoint(0),
    _tilt_wejscie(0), _tilt_wyjscie(0), _tilt_setpoint(0),
    _pid_pan(&_pan_wejscie, &_pan_wyjscie, &_pan_setpoint, KP, KI, KD, QuickPID::Action::direct),
    _pid_tilt(&_tilt_wejscie, &_tilt_wyjscie, &_tilt_setpoint, KP, KI, KD, QuickPID::Action::direct),
    _czas_ostatniego_pid(0), _czas_startowy_skanu(0) {}

  void inicjalizuj() {
    _serwo_pan.attach(PAN_PIN);
    _serwo_tilt.attach(TILT_PIN);
    bezpieczny_start();
    inicjalizuj_pid_params();
  }

  void pid_krok() { /* dawna pid_tick() */ }
  void skan_krok(unsigned long teraz) { /* dawna skan_tick() */ }
  void ustaw_serwa() { /* bez zmian */ }
  void pid_reset() { _pid_pan.Reset(); _pid_tilt.Reset(); }
};
```

### Pomiar latencji w MozgRPi

```python
# Source: src/vision/brain.py _petla_glowna() — do dodania
czas_przed_tx = time.monotonic_ns() // 1_000_000
self._serial.send_frame(mode=MODE_TRACK, error_x=error_x, error_y=error_y, face_size=face_size)
czas_po_tx = time.monotonic_ns() // 1_000_000
logger.info(f"[LAT] send_frame: {czas_po_tx - czas_przed_tx}ms | err_x={error_x} err_y={error_y}")
```

---

## Validation Architecture

Konfiguracja `workflow.nyquist_validation` nie ustawiona w `.planning/config.json` (brak klucza) — traktuję jako enabled. JEDNAK `test_framework: none` i `require_verification: true` w config — weryfikacja empiryczna, nie automatyczne testy.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | brak (per CLAUDE.md: "There are no unit tests or linting tools configured") |
| Config file | none |
| Quick run command | `python3 scripts/kalibracja_serw.py` |
| Full suite command | Checklist ręczny (patrz scenariusz D-06) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INT-01 | E2E tracking działa, latencja <100ms | empirical + log | `python3 run_pi_brain.py` — obs. ruch serw + logi timestamps | ✅ run_pi_brain.py |
| INT-02 | Negative feedback PAN — twarz po prawej = serwo w prawo | empirical-script | `python3 scripts/kalibracja_serw.py` | ❌ Wave 0 |
| INT-03 | Tilt działa w SCAN (oscyluje) i TRACK (śledzi) | empirical-script | `python3 scripts/kalibracja_serw.py` (tilt step) | ❌ Wave 0 |
| INT-04 | Klasy OOP bez cyklicznych importów | compilation | `arduino-cli compile src/arduino/aries_controller/` | ✅ (po refaktorze) |
| INT-05 | Polonizacja kodu | code review | grep po angielskich nazwach domenowych | ✅ manualne |

### Wave 0 Gaps
- [ ] `scripts/kalibracja_serw.py` — pokrywa INT-02, INT-03 (nowy plik)

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 | run_pi_brain.py, skrypt kalibracyjny | ✓ | 3.13.5 (dev) / 3.12 (RPi venv) | — |
| mediapipe | WykrywaczTwarzy | ✓ | 0.10.18 | — |
| pyserial | SerialInterface | ✓ | 3.5 | — |
| opencv | KameraRPi, HUD | ✓ | 4.11.0 | — |
| arduino-cli | kompilacja firmware | ✓ | 1.4.1 | — |
| /dev/ttyACM0 | SerialInterface, skrypt kalibracyjny | ✗ (dev machine) | — | Nie dotyczy na RPi |
| Picamera2 | KameraRPi | ✗ (dev machine) | — | Tylko na RPi |
| Arduino Leonardo + serwa | kalibracja, E2E | ✗ (dev machine) | — | Wymagane na RPi |
| models/blaze_face_short_range.tflite | WykrywaczTwarzy | ✓ | — | — |

**Missing dependencies with no fallback:**
- Arduino Leonardo + serwa fizyczne — wymagane do kalibracji i weryfikacji INT-01..INT-03. Muszą być podłączone na RPi.
- `/dev/ttyACM0` — wymagane na RPi z podłączonym Arduino.

**Missing dependencies with fallback:**
- Na maszynie deweloperskiej (Windows/non-RPi): skrypt kalibracyjny + run_pi_brain.py wymaga RPi. Kompilacja Arduino i refaktor kodu mogą być wykonane bez RPi.

---

## State of the Art

| Stara podejście | Aktualne podejście | Kiedy zmieniono | Impact |
|---|---|---|---|
| Proceduralny C w .ino | Klasy C++ w .ino (D-04) | Phase 23 | Czytelność, enkapsulacja |
| Mieszane ang./pol. nazwy | Pełna polonizacja (D-07/D-08) | Phase 23 | Spójność z konwencją |
| Brak skryptu kalibracyjnego | `scripts/kalibracja_serw.py` | Phase 23 | Powtarzalna kalibracja |

---

## Open Questions

1. **Wartości PAN_INVERT po nowym montażu Arduino**
   - Co wiemy: STATE.md: "pan+=prawo — wymaga re-weryfikacji na nowym montażu Arduino" (v1.7 decyzja sprzed v2.0 redesign)
   - Brak pewności: PAN_INVERT w firmware jest `+1` — może wymagać zmiany na `-1`
   - Rekomendacja: Skrypt kalibracyjny odpowie na to pytanie empirycznie. Planer powinien uwzględnić możliwy commit zmiany #define po kalibracji.

2. **Kolejność refaktoru: integracja vs OOP vs polonizacja**
   - Co wiemy: Te zmiany są niezależne logicznie
   - Rekomendacja: Plan 23-01: Kalibracja E2E (weryfikacja INT-01..INT-03). Plan 23-02: OOP Arduino + polonizacja (INT-04 + INT-05). Nie mix — łatwiej debugować.

3. **Czy zmiana enum IDLE→BEZCZYNNOSC jest wymagana przez INT-05?**
   - Co wiemy: INT-05 mówi "nazwy zmiennych i komunikaty w kodzie" — enum wartości są nazwami w kodzie
   - Rekomendacja: Tak, zmienić. Ale to osobny commit po weryfikacji działającego firmware.

---

## Project Constraints (from CLAUDE.md)

- Cały kod: Polish-language comments, variable names, method names (wyjątek: nazwy techniczne per D-08)
- Python: 4-space indent, type hints z `typing` module, `Optional`/`Tuple`/`List`
- Error handling: try/except z `logging.error()`, nigdy nie re-raise, zawsze loguj i kontynuuj
- Logging: `logger = logging.getLogger(__name__)`, poziomy: INFO dla tranzycji stanu, WARNING dla fallback/clamp, ERROR dla błędów hardware
- Arduino: nie używać hardware WDT (`wdt_enable()`) — Caterina bootloader bug
- Git commits: `type(scope): description` — jeden task = jeden commit
- Brak test framework — weryfikacja empiryczna (output komend, obserwacja fizyczna)
- Brak formatera/lintera — ręczne utrzymanie stylu

---

## Sources

### Primary (HIGH confidence)
- `/home/parolisko/ARIES-LITE/src/arduino/aries_controller/aries_controller.ino` — cały firmware, wszystkie funkcje i struktury
- `/home/parolisko/ARIES-LITE/src/vision/brain.py` — MozgRPi 353 linie
- `/home/parolisko/ARIES-LITE/src/vision/serial_interface.py` — SerialInterface 137 linii
- `/home/parolisko/ARIES-LITE/src/vision/detector.py` — WykrywaczTwarzy 179 linii
- `/home/parolisko/ARIES-LITE/src/vision/camera.py` — KameraRPi 206 linii
- `/home/parolisko/ARIES-LITE/.planning/protocol/PROTOCOL_SPEC.md` — LOCKED specyfikacja 8B
- `/home/parolisko/ARIES-LITE/.planning/phases/23-integracja-kalibracja/23-CONTEXT.md` — decyzje D-01..D-08
- `/home/parolisko/ARIES-LITE/scripts/echo_test.py` — wzorzec skryptu serial

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — decyzja "PAN_INVERT wymaga re-weryfikacji na nowym montażu"
- `.planning/REQUIREMENTS.md` — definicje INT-01..INT-05
- `.planning/ROADMAP.md` — Phase 23 success criteria

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — wszystkie biblioteki już zainstalowane i używane
- Architecture: HIGH — cały łańcuch E2E już istnieje w kodzie, analiza oparta na odczycie plików
- Pitfalls: HIGH — oparte na analizie istniejącego kodu + udokumentowanych decyzjach poprzednich faz
- Skrypt kalibracyjny: HIGH — wzorzec z echo_test.py dokładnie pasuje
- Arduino OOP: MEDIUM — QuickPID pointer behavior w klasie wymaga ostrożności

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stabilne tech stack)
