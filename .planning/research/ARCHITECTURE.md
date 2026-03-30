# Architecture Research

**Domain:** Distributed embedded vision + real-time servo control (RPi4 Mozg + Arduino Leonardo Uklad Wykonawczy)
**Researched:** 2026-03-30
**Confidence:** HIGH (validated against official docs, reference implementations, and existing codebase)

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│              MOZG — Raspberry Pi 4 (Python)                     │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │ Picamera2    │   │  MediaPipe   │   │  Serial Sender   │    │
│  │ Stream thread│──▶│  Face Detect │──▶│  (pyserial)      │    │
│  │ (daemon)     │   │  + Error calc│   │  115200 baud     │    │
│  └──────────────┘   └──────────────┘   └────────┬─────────┘    │
│                                                  │ USB /dev/ttyACM0
└──────────────────────────────────────────────────┼──────────────┘
                                                   │ USB Serial
┌──────────────────────────────────────────────────┼──────────────┐
│              UKLAD WYKONAWCZY — Arduino Leonardo │              │
│                                                  ▼              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │ Serial Parser│──▶│  PID Pan+Tilt│──▶│  Servo Library   │    │
│  │ (ISR + buffer│   │  (100+ Hz)   │   │  MG-90S D9/D10   │    │
│  └──────────────┘   └──────────────┘   └──────────────────┘    │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │  Watchdog    │   │  LCD 1602    │   │  Buzzer + Button │    │
│  │  (serial TO) │   │  RS/E/D4–D7  │   │  D8 / D7        │    │
│  └──────────────┘   └──────────────┘   └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Node | Responsibility | Communicates With |
|-----------|------|----------------|-------------------|
| `Picamera2Stream` | RPi4 | YUV420→BGR capture, AWB fix, daemon thread | `pi_brain.py` (frames) |
| `MediaPipe FaceDetector` | RPi4 | Face bounding box detection, largest-face selection | `pi_brain.py` (bbox) |
| `ErrorCalculator` | RPi4 | Normalize error to [-1.0, +1.0] relative to frame centre | Serial sender |
| `SerialSender` | RPi4 | Frame encoding, checksum, pyserial write at ~30 Hz | Arduino parser |
| `SerialParser` | Arduino | ISR-driven byte accumulation, frame validation, checksum | PID controller |
| `PIDController` | Arduino | Dual-axis PID at 100+ Hz (setpoint = 0), angle computation | Servo library |
| `ServoDriver` | Arduino | Arduino `Servo.write()` to MG-90S on D9 (pan), D10 (tilt) | Physical hardware |
| `WatchdogTimer` | Arduino | millis()-based serial timeout, returns to SCAN on silence | State machine |
| `LCD1602` | Arduino | 4-bit mode status display (mode, angles, FPS) | State machine |
| `BuzzerButton` | Arduino | Buzzer feedback on state change; D7 button = abort track | State machine |

---

## Recommended Project Structure

```
ARIES-LITE/
├── src/
│   ├── arduino/
│   │   └── aries_controller/
│   │       └── aries_controller.ino    # caly firmware Arduino
│   ├── vision/
│   │   └── pi_brain.py                 # MediaPipe + serial sender (nowy glowny skrypt)
│   ├── config.py                       # stale — bez zmian (PID gains, limity)
│   └── hardware.py                     # zachowany w legacy/ lub usuniety (servo teraz na Arduino)
├── legacy/                             # v1.x monolityczny kod jako referencja
│   ├── main.py
│   ├── run_test_tracker.py
│   └── src/
├── web/                                # opcjonalnie — Flask UI moze zostac dla podgladu
├── models/                             # DNN weights — mozliwe usuniecie (MediaPipe = bundled)
├── requirements.txt                    # nowe: mediapipe, pyserial; usuniete: gpiozero, pigpio, dlib
└── .planning/
```

### Structure Rationale

- **`src/arduino/`**: Firmware zywi wlasny katalog. Oddzielenie .ino od Python zapobiega
  importowaniu jako modul Python. Arduino IDE / arduino-cli szuka `aries_controller/aries_controller.ino`.
- **`src/vision/pi_brain.py`**: Nowy entry point RPi — zastepuje `run_test_tracker.py`.
  Nie dziedziczy po starym kodzie (rozny stack kamerowy i brak PID po stronie Pi).
- **`legacy/`**: Poprzednie milestony zachowane. Umozliwia rollback bez git bisect.
  Zgodne z decyzja projektowa "Stary monolit zachowany w `legacy/`".

---

## Architectural Patterns

### Pattern 1: Brain-Muscle Split (RPi = wizja, Arduino = sterowanie)

**Co:** RPi4 zajmuje sie wylacznie detekcja i obliczaniem bledu. Arduino zajmuje sie
wylacznie PID i serwami. Zaden wezel nie robi obu rzeczy jednoczesnie.

**Dlaczego:** RPi4 Python ma GIL i nieregularne latencje GC. PID w Pythonie na RPi4
osiaga ~30 Hz z jitterem. Arduino bez OS osiaga >100 Hz z deterministycznym timingiem.
Podział eliminuje single point of failure — Arduino dziala autonomicznie gdy Pi zawiesza sie.

**Trade-off:** Komunikacja przez USB Serial dodaje latencje ~1-5ms na ramke. Akceptowalne
dla sledzenia twarzy (cykl PID = 10ms przy 100 Hz).

**Confidence:** HIGH — wzorzec stosowany w robotyce (ROS: compute node + controller node).
Potwierdzone przez projekt SaraKIT (MediaPipe RPi + BLDC controller).

---

### Pattern 2: Asymetryczny protokol szeregowy (Pi pisze, Arduino odpowiada)

**Co:** RPi4 wysyla klatki danych do Arduino (dominujacy nadawca). Arduino opcjonalnie
odsyla ACK lub status. Komunikacja nie jest RPC — brak blokujacego oczekiwania na odpowiedz.

**Dlaczego:** Petla wizji na Pi jest niezalezna od czestotliwosci PID na Arduino.
Pi wysyla z ~30 Hz (klatka kamery). Arduino petla PID biegnie z 100+ Hz bez czekania
na kolejna wiadomosc. Blokujacy request/response niszczyloby deterministyczny timing PID.

**Trade-off:** Pi nie ma potwierdzenia ze ramka dotarla. Przy utracie ramki Arduino
kontynuuje PID z ostatnim bledem (hold-last) co jest bezpieczniejsze niz zatrzymanie.

---

### Pattern 3: Fixed-length binary frame z checksum

**Co:** Kazda wiadomosc Pi→Arduino ma stala dlugosc (8 bajtow). Bez dlugosci w naglowku.
Arduino wie dokładnie ile bajtow czytac po bajcie startowym.

**Format ramki (Pi → Arduino):**
```
Bajt 0:  0xAA           — start marker (stały)
Bajt 1:  tryb           — 0x00=SCAN, 0x01=TRACK, 0x02=IDLE
Bajt 2:  blad_x_high    — error_x jako int16 big-endian, high byte
Bajt 3:  blad_x_low     — error_x jako int16 big-endian, low byte
Bajt 4:  blad_y_high    — error_y jako int16 big-endian, high byte
Bajt 5:  blad_y_low     — error_y jako int16 big-endian, low byte
Bajt 6:  rozmiar_twarzy — face bbox width jako uint8 (0–255 po normalizacji)
Bajt 7:  checksum       — XOR bajtow 1–6 (weryfikacja integralnosci)
```

**Dlaczego XOR nie CRC:** Dla 6 bajtow danych XOR wykrywa wszystkie bledy
jednobitowe i wiekszosc wielobitowych. CRC-8 byloby silniejsze (2% klas bledow
wiecej) ale wymaga tablic lookup lub wielomianow — niepotrzebna komplikacja
dla 115200 baud USB (BTL hardware error rate bardzo niski).

**Dlaczego int16 dla bledu:** MediaPipe zwraca bbox origin_x, origin_y, width, height
jako piksele (0–320 dla 320x240). Blad = face_cx - frame_cx moze byc -160 do +160.
int16 daje zakres -32768..+32767 — duzy margines bez rzutowania float.

**Dlaczego NIE ASCII/tekst:** "S 45 -23\n" jest czytelne dla czlowieka ale wymaga
parsowania strconv na Arduino (atoi) i zajmuje 10+ bajtow vs 8 fixed. Przy 115200 baud
i 30 Hz: ASCII = ~300 bajtow/s vs binary = 240 bajtow/s. Nie to jest bottleneck —
wazniejsza jest prostosc parsowania po stronie Arduino bez alokacji.

**Confidence:** MEDIUM-HIGH — pattern z Eli Bendersky (framing article) + todbot blog.
Konkretny format zaprojektowany dla tego projektu, wymaga walidacji na sprzecie.

---

### Pattern 4: Arduino watchdog via millis() (nie AVR WDT)

**Co:** Arduino sprawdza `millis() - ostatnia_ramka_ms > WATCHDOG_MS` w petli.
Jesli Pi nie wyslalo ramki przez WATCHDOG_MS (sugestia: 2000ms), Arduino przechodzi
do trybu SCAN z preset kata pan/tilt = 0,0.

**Dlaczego NIE `wdt_reset()` (AVR hardware WDT):** AVR WDT na Leonardo resetuje caly
mikrokontroler (pelny reboot, ~1-2s dead time). Dla utraty komunikacji z Pi chcemy
**autonomiczny SCAN** — serwa dalej sie ruszaja, LCD pokazuje "WATCHDOG", a gdy Pi
wroci, system plynnie wznawia TRACK. Hardware WDT byłby zbyt drastyczny.

**Implementacja Arduino:**
```cpp
const unsigned long WATCHDOG_MS = 2000;
unsigned long ostatnia_ramka_ms = 0;

void loop() {
    if (Serial.available() >= 8) {
        parse_frame();
        ostatnia_ramka_ms = millis();
    }
    if (millis() - ostatnia_ramka_ms > WATCHDOG_MS) {
        tryb = TRYB_SCAN;  // autonomiczny powrot do skanowania
    }
    pid_tick();  // zawsze wykonywany, niezaleznie od Serial
}
```

**Confidence:** HIGH — wzorzec aplikacyjny watchdog z Interrupt/Memfault best practices.
Uwaga: AVR WDT ma bug na Arduino Leonardo przy bootloaderze — niektore wersje nie resettuja
WDT poprawnie. Aplikacyjny millis() watchdog omija ten problem calkowicie.

---

### Pattern 5: MediaPipe face_detector API (Tasks API)

**Co:** `mediapipe.tasks.python.vision.FaceDetector` — nie stary `mediapipe.solutions`.
Tasks API jest oficjalnym nastepca (Google, 2023). Zwraca `FaceDetectorResult` z listą
`Detection`, kazdy z `BoundingBox(origin_x, origin_y, width, height)` w pikselach.

**Kluczowe API:**
```python
import mediapipe as mp
from mediapipe.tasks.python import vision as mp_vision

options = mp_vision.FaceDetectorOptions(
    base_options=mp.tasks.BaseOptions(model_asset_path="blaze_face_short_range.tflite"),
    running_mode=mp_vision.RunningMode.VIDEO,  # lub IMAGE, LIVE_STREAM
)
detector = mp_vision.FaceDetector.create_from_options(options)

# W petli:
mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_bgr)
result = detector.detect_for_video(mp_image, timestamp_ms)
# result.detections[0].bounding_box.origin_x, .origin_y, .width, .height
```

**Wybor "sticky largest face":** Sposrod `result.detections`, wybierz detekcje o
najwiekszym `bounding_box.width * bounding_box.height`. Eliminuje to skok do nowej
twarzy gdy pojawi sie osoba trzecia w tle — zachowanie opisane w PROJECT.md.

**Wydajnosc na RPi4:** ~10 FPS dla face landmark detection (468 punktow). Face detector
(tylko bbox, bez landmarkow) bedzie szybszy — szacowane 15-25 FPS. Wystarczy do obliczania
bledu przy 30 Hz kamery (Pi wysyla co druga/trzecia klatke do Arduino gdy detekcja wolna).

**Confidence:** MEDIUM — oficjalne API z Google AI Developers (zweryfikowane). FPS na RPi4
to szacunek z wynikow face_landmarker (~10 FPS) interpolowany dla prostszego face_detector.
Wymaga empirycznej weryfikacji na RPi4.

---

### Pattern 6: Kalibracja orientacji serw jako konfigurowalna stala

**Co:** Kierunek korekty serwa (pan/tilt) zalezy od montazu fizycznego. W v1.7
empirycznie potwierdzono: `korekta_tilt = -pid_tilt`. W v2.0 na Arduino, znak korekty
musi byc konfigurowalny bez reflashowania firmware.

**Implementacja:** Stale `PAN_DIR` i `TILT_DIR` w EEPROM lub jako `#define` na gorze `.ino`:
```cpp
#define PAN_DIR  (+1)   // +1 lub -1, empirycznie
#define TILT_DIR (-1)   // -1 potwierdzony w v1.7
```

**Dlaczego nie w runtime:** Kierunek serwa nie zmienia sie w trakcie dzialania. Stala
czasu kompilacji jest zerowym kosztem runtime i jasno dokumentuje empiryczna decyzje.

---

## Data Flow

### Pelny przepływ (v2.0 distributed)

```
Picamera2 YUV420 (320x240)
    ↓ cvtColor(YUV420p2RGB)              — daemon thread
    ↓
MediaPipe FaceDetector.detect_for_video()
    ↓
Wybor najwyzszej twarzy (max bbox area)
    ↓
Obliczenie bledu:
    error_x = face_cx - frame_cx         — piksele, int16
    error_y = face_cy - frame_cy         — piksele, int16
    tryb = TRACK (twarz znaleziona) lub SCAN (brak twarzy)
    ↓
Enkodowanie ramki 8-bajtowej (binary + XOR checksum)
    ↓
pyserial.write(frame)  →  USB /dev/ttyACM0  →  Arduino Serial
    ↓
[Arduino]
SerialParser: czeka na 0xAA, czyta 7 bajtow, weryfikuje XOR
    ↓
PID(error_x) → delta_pan    |   (100 Hz loop, millis() timing)
PID(error_y) → delta_tilt   |
    ↓
pan_angle  = clamp(pan_angle  + PAN_DIR  * delta_pan,  -60, +60)
tilt_angle = clamp(tilt_angle + TILT_DIR * delta_tilt, -30, +30)
    ↓
servo_pan.write(pan_angle + 90)     — Arduino Servo: 0-180 stopni
servo_tilt.write(tilt_angle + 90)
    ↓
LCD update (tryb, pan, tilt) + buzzer na zmiane trybu
```

### Watek RPi4

Minimalistyczny model — 2 watki (nie 4 jak w v1.x):

```
Thread 1 (main): pi_brain.py petla glowna
    Picamera2 capture → MediaPipe detect → error calc → serial write
    ~15-25 iteracji/s (ograniczone przez MediaPipe na RPi4)

Thread 2 (daemon): Picamera2Stream._petla_przechwytywania
    Async frame capture, shared buffer (threading.Lock)
    30 FPS capture rate (niezalezne od czestotliwosci detekcji)
```

**Dlaczego nie potrzeba osobnego watku serial sender:** Pi pisze do serial w main
thread po kazdej detekcji. Przy 15-25 detekcji/s i 8-bajtowych paczkach,
`serial.write(8 bytes)` trwa <0.1ms przy 115200 baud — nie blokuje.

### Petla Arduino

```
setup():
    Serial.begin(115200)
    servo_pan.attach(9); servo_tilt.attach(10)
    smooth_move_to(0, 0)        — bezpieczny startup (nie wolno skakac)
    lcd.begin(16, 2)
    lcd.print("ARIES v2.0")

loop() [bez delay(), deterministyczne]:
    // --- Serial receive (non-blocking) ---
    if (Serial.available() >= 8):
        parse_frame()           — czyta, weryfikuje XOR, aktualizuje state
        ostatnia_ramka_ms = millis()

    // --- Watchdog ---
    if (millis() - ostatnia_ramka_ms > WATCHDOG_MS):
        tryb = TRYB_SCAN

    // --- PID tick (100 Hz) ---
    unsigned long now = millis()
    if (now - ostatni_pid_ms >= PID_INTERVAL_MS):  // 10ms = 100 Hz
        ostatni_pid_ms = now
        if (tryb == TRYB_TRACK):
            pid_update()
            servo_pan.write(pan_angle + 90)
            servo_tilt.write(tilt_angle + 90)
        else:
            scan_step()         — sinusoidalny scan po stronie Arduino

    // --- HMI ---
    lcd_update()                — throttled, co ~200ms
    handle_button()             — D7 INPUT_PULLUP, debounce
```

---

## Scaling Considerations

| Concern | Aktualna konfiguracja | Potencjalne problemy |
|---------|----------------------|----------------------|
| Serial latency | 115200 baud, 8B = ~0.7ms/ramke | Pomijalne dla 15-30 Hz wizji |
| Arduino PID jitter | millis() ±1ms (nie hardware timer) | Akceptowalne dla MG-90S; dla ultra-smooth: Timer1 ISR |
| MediaPipe FPS | ~15-25 FPS (szacunek) | Jesli <10 FPS: zmniejsz resolucje do 240x180 lub skip frames |
| USB buffer overrun | pyserial + USB CDC bufory | Pi wysyla 8B/frame, Arduino czyta seryjnie — brak ryzyka overrun |

---

## Anti-Patterns

### Anti-Pattern 1: PID po stronie RPi4 (Python)

**Co robią:** Zostawiają PID w pi_brain.py i wysylają gotowe katy do Arduino.
**Dlaczego złe:** Python GIL + gc.collect() powoduja jitter 10-50ms. PID wymaga
regularnego timingu (dT powinno byc stalym). Przy 30 Hz w Pythonie i jitterze 30ms
(10% cyklu), derivative term d(error)/dT moze dac falszywe spike'i.
Arduino wykonuje PID z dT = 10ms ±1ms (millis precision) — 3x lepsza regulacja.
**Zamiast tego:** Pi oblicza tylko blad pikseli i wysyla go do Arduino. Arduino liczy PID.

---

### Anti-Pattern 2: ASCII/text protokol serial

**Co robią:** Wysylają "TRACK 45 -23\n" jako tekst.
**Dlaczego złe:** atoi/sscanf na Arduino sa wolne i ryzykowne na bledach parsowania.
Brak wbudowanego checksuma — jeden przeklamany bajt daje bledny kat. Zmienna dlugosc
utrudnia resynchronizacje po bledzie.
**Zamiast tego:** Fixed-length binary frame z start markerem i XOR checksum (Pattern 3).

---

### Anti-Pattern 3: Blokujacy ACK (request-response)

**Co robią:** Pi wysyla ramke, czeka na Arduino "OK\n" przed wysylaniem kolejnej.
**Dlaczego złe:** Round-trip time USB Serial = ~2-5ms. Przy 30 Hz (33ms/klatke)
2-5ms to 6-15% cyklu stracone na czekanie. Jesli Arduino jest zajete PID lub LCD,
ACK moze byc opozniony — Pi blokuje sie, kamera laguje.
**Zamiast tego:** Pi wysyla non-stop (fire-and-forget). Arduino przetwarza ostatnia
dobra ramke. Brak ACK = brak blokowania = niezalezne Hz po obu stronach.

---

### Anti-Pattern 4: Servo.write() w loop() bez timer throttling

**Co robią:** Wywoluja servo.write() w kazdej iteracji loop() bez sprawdzenia czasu.
**Dlaczego złe:** Arduino loop() bez delay() biega ~50-100 kHz. Wywoływanie
servo.write() 50000x/s nie przyspieza serwa — MG-90S akceptuje sygnaly PWM 50 Hz.
Nadmierne wywolania generuja goraco procesora bez efektu i moga zaklocac timing PWM.
**Zamiast tego:** Timer PID throttlowany do 100 Hz (co 10ms) przez millis() check.

---

### Anti-Pattern 5: Brak smooth_move_to() przy starcie Arduino

**Co robią:** Inicjalizuja serwa z `servo.write(90)` bezposrednio.
**Dlaczego złe:** Jesli serwa sa w pozycji ±45° przed uruchomieniem, natychmiastowy
skok do 90° (centrum) powoduje high current draw → mozliwy brownout zasilania 6V.
Znany problem z v1.x (dokumentowany w CLAUDE.md: "smooth_move_to() must be used at startup").
**Zamiast tego:** setup() czyta aktualny kat (lub zaklada 0°) i interpoluje do centrum
w krokach co 20ms przez petla `for` z `delay(20)`.

---

## Build Order Implications

Kolejnosc budowania respektuje zaleznosci hardwarowe i ryzyko:

```
Etap 1: Serial protocol + parser (Arduino) + sender (Python)
    Niezalezny od MediaPipe i PID. Mozna testowac z hardkodowanymi wartosciami.
    Weryfikacja: echo test — Pi wysyla ramke, Arduino odsyla raw bytes przez Serial Monitor.
    Ryzyko: niskie (czysty software, bez hardware poza USB).

Etap 2: PID na Arduino z hardkodowanym bledem
    Zalezny od Etap 1 (protokol musi dzialac).
    Testuj PID z error_x=50, error_y=-30 wstrzykniętym z Pythona lub hardkodowanym.
    Weryfikacja: serwa poruszaja sie plynnie, konwerguja do 0°.
    Ryzyko: srednie (sprzet — uwazaj na brownout przy naglych skokach).

Etap 3: MediaPipe na RPi4 + obliczanie bledu
    Niezalezny od Arduino PID (mozna testowac z samym drukowaniem bledu).
    Weryfikacja: detect() zwraca bbox; error_x/y zmienia sie przy ruchu twarzy.
    Ryzyko: niskie (software-only, brak sprzetu po stronie Pi).

Etap 4: Integracja end-to-end (Pi MediaPipe → serial → Arduino PID → serwa)
    Zalezny od Etap 1, 2, 3.
    Weryfikacja: twarz w centrum = serwa nieruchome; twarz na lewo = pan dazy w lewo.
    Ryzyko: srednie (orientacja serw wymaga empirycznej kalibracji PAN_DIR/TILT_DIR).

Etap 5: HMI — LCD, buzzer, przycisk D7
    Niezalezny od logiki PID po integracji Etap 4.
    Weryfikacja: LCD pokazuje "TRACK 12 -5", buzzer przy zmianie trybu.
    Ryzyko: niskie.

Etap 6: Watchdog + testy stabilnosci
    Zalezny od Etap 4 (musi byc pelen system).
    Weryfikacja: wylacz Pi → Arduino przechodzi do SCAN po WATCHDOG_MS.
    Ryzyko: niskie (juz zaplanowane w architekturze).
```

---

## Integration Points

### External Hardware

| Interface | Polaczenie | Uwagi |
|-----------|-----------|-------|
| USB Serial | /dev/ttyACM0, 115200 baud | Arduino Leonardo = USB CDC natywny, bez adaptera |
| IMX219 Camera | CSI ribbon cable | Picamera2 + libcamera, ten sam backend co v1.x |
| MG-90S PAN | Arduino D9 (PWM) | Arduino Servo library, 50 Hz PWM |
| MG-90S TILT | Arduino D10 (PWM) | Arduino Servo library, 50 Hz PWM |
| LCD 1602 | RS=12, E=11, D4=5, D5=4, D6=3, D7=2 | 4-bit mode, LiquidCrystal library |
| Buzzer | Arduino D8 | tone() / digitalWrite |
| Button | Arduino D7 (INPUT_PULLUP) | Active LOW, wymaga debounce |
| Servo power | Zewnetrzne 6V | Oddzielone od 5V RPi — zapobiega brownout |

### Internal Boundaries

| Granica | Komunikacja | Uwagi |
|---------|------------|-------|
| Pi main thread ↔ Picamera2 daemon | `threading.Lock` + shared numpy frame | Identycznie jak v1.x |
| Pi main ↔ Arduino | USB Serial, binary 8B frames, 1-way dominant | Fire-and-forget |
| Arduino Serial ISR ↔ PID loop | Volatile shared state (error_x, error_y, tryb) | Atomic na AVR dla uint8/int16 |
| Arduino PID ↔ Servo | Servo library internal | Servo.write() thread-safe w single-threaded Arduino |

---

## Sources

- [MediaPipe Face Detector Python API](https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector/python) — bounding box format, Tasks API (HIGH confidence)
- [MediaPipe for Raspberry Pi](https://www.cnx-software.com/2023/08/21/mediapipe-for-raspberry-pi-released-no-code-low-code-on-device-machine-learning-solutions/) — oficjalne wsparcie RPi, 2023 (HIGH confidence)
- [Arduino Serial Protocol Design Patterns — todbot blog](https://todbot.com/blog/2009/07/30/arduino-serial-protocol-design-patterns/) — fixed-length vs delimiter framing (HIGH confidence)
- [Framing in Serial Communications — Eli Bendersky](https://eli.thegreenplace.net/2009/08/12/framing-in-serial-communications/) — start marker + checksum pattern (HIGH confidence)
- [Firmware Watchdog Best Practices — Interrupt/Memfault](https://interrupt.memfault.com/blog/firmware-watchdog-best-practices) — aplikacyjny watchdog vs hardware WDT (HIGH confidence)
- [ArduinoPanTilt — Elucidation](https://github.com/Elucidation/ArduinoPanTilt) — referencyjna implementacja RPi+Arduino serial servo control (MEDIUM confidence)
- [SaraKIT Face Tracking MediaPipe RPi](https://github.com/SaraEye/SaraKIT-Face-Tracking-MediaPipe-Raspberry-Pi-64bit) — MediaPipe pan-tilt na RPi (MEDIUM confidence)
- [PySerial API](https://pyserial.readthedocs.io/en/latest/pyserial_api.html) — non-blocking read + threading patterns (HIGH confidence)
- CLAUDE.md + PROJECT.md — decyzje architektoniczne v2.0 (HIGH confidence — source of truth)

---

*Architecture research for: ARIES-LITE v2.0 — Architektura Rozproszona (RPi4 + Arduino Leonardo)*
*Researched: 2026-03-30*
