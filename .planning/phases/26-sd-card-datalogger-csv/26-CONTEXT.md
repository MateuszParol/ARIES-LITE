# Phase 26: SD Card + DataLogger CSV - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Zapis telemetrii na kartę SD w formacie CSV z RTC timestamps (epoch sekundy), rotacja dobowa plików LYYMMDD.CSV (FAT 8.3), ring buffer 50 wpisów w RAM, graceful degradation bez karty SD, benchmark latencji zapisu. Klasa DataLogger w OOP (spójna z ZegarRTC, HMI, ServoPID, MaszynaStanow).

Faza NIE obejmuje: integracji DataLogger z MaszynaStanow (Phase 27), logowania zmian stanów (Phase 27), zmian w protokole binarnym 8B, zmian w PID/servo/wizji.

</domain>

<decisions>
## Implementation Decisions

### Format i kolumny CSV
- **D-01:** Timestamp jako Unix epoch sekundy (uint32 z DateTime.unixtime()) — kompaktowy, łatwy do parsowania w Python/Excel
- **D-02:** Kolumny: timestamp,stan,pan,tilt,error_x,error_y,face_size,latency_ms — zgodne z roadmap
- **D-03:** Precyzja integer — pan/tilt jako int (stopnie), error jako int (piksele), face_size int, latency_ms int. snprintf z %d, bez float formatting
- **D-04:** Separator: przecinek (standard CSV). Excel wymaga importu, ale Python/pandas natywnie kompatybilny
- **D-05:** Nagłówek kolumn w pierwszej linii KAŻDEGO nowego pliku — plik self-contained

### Strategia zapisu i buforowanie
- **D-06:** Logowanie co 10 klatek RPi (~3 wpisy/sek przy 30Hz input). Licznik klatek w MaszynaStanow przekazywany do DataLogger
- **D-07:** Ring buffer 50 wpisów w RAM (~4KB, char bufor[50][80]). Flush cały bufor jednym file.print(). Chroni pętlę PID 100Hz — zapis IO tylko co ~17 sek. Zgodne z LOG-03
- **D-08:** Logowanie telemetrii TYLKO w stanie SLEDZENIE — error_x/y i face_size mają sens tylko z wykrytą twarzą. SKANOWANIE/BEZCZYNNOSC bez wpisów telemetrii. (Zmiany stanów logowane w Phase 27)

### Degradation bez karty SD
- **D-09:** Sprawdzenie SD.begin(10) TYLKO w setup() — jednorazowe. Jeśli fail: sd_dostepne=false na całą sesję, brak retry w loop(). Zgodne z roadmap SC#3
- **D-10:** Brak blokady startu — system działa normalnie bez SD (PID, tracking, HMI bez zmian)

### Nazewnictwo plików i rotacja
- **D-11:** Format LYYMMDD.CSV (FAT 8.3) — L260402.CSV dla 2026-04-02. Sortowalne alfabetycznie, prefiks L=Log

### Claude's Discretion
- Zachowanie HMI przy SD fail — poziom alarmu LCD/buzzer (spójność z RTC fail z Phase 25 D-08)
- Zachowanie przy braku RTC — millis() fallback vs. wyłączenie logowania (czy millis() timestamps są użyteczne?)
- Mechanizm wykrywania zmiany dnia (co flush vs. co wpis vs. inne)
- Rozmiar bufora linii (80 bajtów szacunek — zweryfikować z rzeczywistą długością wiersza)
- Szczegóły benchmarku latencji (LOG-05) — ile iteracji, format wyniku

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Firmware Arduino (baza do modyfikacji)
- `src/arduino/aries_controller/aries_controller.ino` — Firmware v2.1 z ZegarRTC (Phase 25). Baza do dodania DataLogger. Klasy OOP: HMI, ServoPID, MaszynaStanow, ZegarRTC.

### Research v2.1
- `.planning/research/ARCHITECTURE.md` — Kluczowe sekcje: "SD Logging + RTC + Pin Migration Integration", "Integration Points: SPI Bus", "Timing Impact Analysis: 100Hz PID Loop", "Data Flow (rozszerzony o DataLogger)"
- `.planning/research/STACK.md` — SD.h standardowa, RTClib 2.1.4, ArduinoCore-renesas >=1.4.1
- `.planning/research/PITFALLS.md` — Kolejność Wire→RTC→SD, timing SD write vs PID

### Kontekst poprzednich faz
- `.planning/phases/25-rtc-ds1307-izolowana-integracja/25-CONTEXT.md` — D-13: interfejs ZegarRTC gotowy dla DataLogger (odczytaj_czas(), czy_dostepny())
- `.planning/phases/24-migracja-pinow-i-kompilacja-bazowa/24-CONTEXT.md` — D-04: piny SPI D10-D13 zarezerwowane pod SD

### Specyfikacje
- `.planning/REQUIREMENTS.md` — LOG-01 (CSV zapis), LOG-02 (rotacja dobowa), LOG-03 (ring buffer), LOG-04 (graceful degradation), LOG-05 (benchmark latencji)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ZegarRTC` klasa (Phase 25): `odczytaj_czas() -> DateTime`, `czy_dostepny() -> bool` — DataLogger użyje do timestamps i nazwy pliku
- `HMI` klasa: `lcd_bootscreen()` — modyfikacja aby wyświetlić status SD. `buzzer_beep()` — alarm SD fail
- OOP pattern: globalna instancja z referencjami — `DataLogger logger(zegar);`
- `millis()` throttle pattern (PID 10ms, LCD 200ms) — DataLogger będzie miał własny throttle (co 10 klatek)

### Established Patterns
- Klasy OOP z metodami `inicjalizuj() -> bool`, polskie nazewnictwo
- Konstruktor z listą inicjalizacyjną i referencjami
- `constrain()` dla clamp, `snprintf()` dla formatowania stringów
- Globalny enum StanSystemu — DataLogger odczyta stan z MaszynaStanow

### Integration Points
- `setup()`: dodanie `SD.begin(10)` + `logger.inicjalizuj()` PO Wire.begin() + ZegarRTC.inicjalizuj()
- `loop()`: dodanie `logger.krok(stan, pan, tilt, err_x, err_y, face_size, latency)` PO HMI tick
- Nowy `#include <SD.h>` + `#define SD_CS_PIN 10`
- Nowa globalna instancja: `DataLogger logger(zegar);`
- Kolejność globalna: serwa → hmi → maszyna → logger (logger ostatni)
- Flash: `arduino-cli compile/upload --fqbn arduino:renesas_uno:unor4wifi --port /dev/ttyACM0`

</code_context>

<specifics>
## Specific Ideas

- Ring buffer char[50][80] — ~4KB RAM z 32KB dostępnego na Uno R4 WiFi (12% zużycia)
- Flush co 50 wpisów = co ~17 sek. Worst case utrata 17 sek danych przy power-loss — akceptowalne dla telemetrii
- ARCHITECTURE.md potwierdza: DataLogger write ~0.35ms nie blokuje PID 100Hz (10ms interval)
- SD.h standardowa biblioteka Arduino — nie wymaga instalacji przez arduino-cli
- Benchmark LOG-05: micros() wokół file.print() — wynik w komentarzu lub Serial log

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 26-sd-card-datalogger-csv*
*Context gathered: 2026-04-02*
