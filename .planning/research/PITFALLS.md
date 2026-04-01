# Pitfalls Research — v2.1 Migracja Leonardo → Uno R4 WiFi + DataLogger Shield

**Domain:** Arduino firmware migration (ATmega32U4 → Renesas RA4M1) + DataLogger Shield (RTC DS1307 + SD card) integration do systemu PID 100 Hz real-time.
**Researched:** 2026-04-01
**Confidence:** HIGH (Arduino forum issue analysis, official docs, release notes) / MEDIUM (QuickPID 32-bit specific — limited direct evidence)

**Scope:** v2.1 milestone — port istniejacego firmware (QuickPID, Servo, LiquidCrystal, protokol 8B, watchdog millis()) z Leonardo (ATmega32U4) na Uno R4 WiFi (Renesas RA4M1) oraz dodanie DataLogger Shield (SD SPI + RTC I2C). Każda pułapka mapuje się na konkretne ryzyko migracji lub integracji.

---

## Critical Pitfalls

### Pitfall 1: Servo Library — wersja przed 1.2.2 powoduje jitter/ticking na R4

**What goes wrong:**
Standardowa biblioteka `Servo` w wersjach przed 1.2.2 generuje na Uno R4 WiFi serwomechanizm "ticking" — impuls PWM zmienia się skokowo co ~100 µs zamiast płynnie. Efekt: serwa MG-90S drgają, PID traci stabilność. Ten sam kod na Uno R3/Leonardo działa bez zarzutu.

**Why it happens:**
Renesas RA4M1 używa 32-bitowych timerów GPT (General Purpose Timer) z innym API niż AVR. Implementacja Servo w wersjach < 1.2.2 nie obsługuje architektury `renesas_uno` (błąd przy kompilacji: "library Servo claims to run on renesas architecture but not renesas_uno"). Fix był mergowany PR #116 przez KurtE we wrześniu 2023, ale oficjalny release Servo v1.2.2 pojawił się dopiero w lipcu 2024.

**How to avoid:**
1. Zainstaluj Servo >= 1.2.2 przed pierwszą kompilacją: Arduino Library Manager → Servo → sprawdź wersję.
2. Po kompilacji sprawdź ostrzeżenia — jeśli pojawia się "incompatible with your current board which runs on renesas_uno architecture", biblioteka jest za stara.
3. Jeśli Library Manager nie podaje 1.2.2+, zainstaluj ręcznie z GitHub: `arduino/Arduino/tree/master/libraries/Servo`.
4. Testuj serwomechanizm bez PID najpierw: przykład `Sweep` — ruch powinien być płynny bez kroków.

**Warning signs:**
- Serwa drgają lub "tikają" przy stałym zadanym kącie
- Kompilator wypisuje ostrzeżenie o niezgodności architektury dla biblioteki Servo
- Kąt serwa zmienia się w skokami widocznych na oscyloskopie lub w logach Serial

**Phase to address:**
Faza 1 (Port pinów + weryfikacja Servo) — przed jakimkolwiek kodem PID sprawdź Servo na pętli Sweep. Brak płynnego ruchu = zła wersja biblioteki.

---

### Pitfall 2: DataLogger Shield — I2C wyłącza się po pełnym osadzeniu shielda (złe styki nagłówków)

**What goes wrong:**
Po pełnym osadzeniu DataLogger Shield na Uno R4 WiFi komunikacja I2C z RTC DS1307 przestaje działać. Wire.begin() inicjalizuje się bez błędu, ale `rtc.begin()` z RTClib zwraca false lub czas jest niepoprawny (rok 2000, godzina 00:00:00). Przy delikatnym uniesieniu shielda lub podłączeniu przez kable jumper I2C wraca do działania.

**Why it happens:**
Stacking headers DataLogger Shield (wersja Rev C) mają szpilki niestandardowego wymiaru (0.015" × 0.025" zamiast standardowych 0.025" × 0.025"). Mechaniczny nacisk przy pełnym osadzeniu powoduje niewystarczający kontakt elektryczny na pinach SCL/SDA. Dodatkowo shield Rev C ma pull-upy 2.2 kΩ podciągnięte do IOREF (~5.4 V), co jest poprawne dla R4 (5V I2C), ale fizyczne złe styki niwelują tę zaletę.

**How to avoid:**
1. Przed testowaniem I2C: pocynuj szpilki nagłówków na pinach A4 (SDA) i A5 (SCL) shielda — dodatkowa cyna wypełnia luz.
2. Przetestuj I2C z shieldem połączonym przez kable jumper (bez mechanicznego osadzenia) — jeśli I2C działa przy kablach a nie działa przy shieldzie, problem jest fizyczny.
3. Skanuj magistralę I2C skanerem (`Wire.beginTransmission(0x68)`) przed pisaniem jakiegokolwiek kodu RTClib.
4. Sprawdź adres DS1307: powinien odpowiadać na 0x68.

**Warning signs:**
- `rtc.begin()` zwraca false
- Czas pokazuje "2000-01-01 00:00:00" (DS1307 nie skomunikowany)
- I2C scanner nie wykrywa urządzenia pod 0x68
- Problem znika gdy shield jest delikatnie uniesiony

**Phase to address:**
Faza 2 (Integracja DataLogger Shield — RTC) — weryfikacja I2C skanerem jest obowiązkowa PRZED pisaniem kodu logowania. Fizyczne pocynowanie nagłówków to działanie jednokrotne.

---

### Pitfall 3: SD.begin() zawiesza pętlę gdy karta SD jest nieobecna lub źle sformatowana

**What goes wrong:**
Jeśli `SD.begin(10)` zostanie wywołane w `setup()` bez karty SD lub z kartą sformatowaną jako NTFS/exFAT, `SD.begin()` może zawisnąć na kilka sekund lub zwrócić false bez komunikatu. W najgorszym przypadku wywołanie `SD.open()` po nieudanym `SD.begin()` zawiesza Arduino na czas nieoznaczony — PID nigdy nie startuje.

**Why it happens:**
Biblioteka SD.h inicjalizuje SPI i szuka karty odpowiadającej na protokół SPI Mode 0. Brak odpowiedzi karty powoduje timeout wewnątrz SPI, który na RA4M1 (bez watchdoga sprzętowego aktywnego w setup()) może zablokować wykonanie. Dodatkowy problem: SD na R4 wymaga SPI <= 5 MHz — standardowe `SD.begin(10)` próbuje wyższej prędkości i może nie wykrywać karty.

**How to avoid:**
1. Zawsze sprawdzaj wynik `SD.begin()`:
   ```cpp
   if (!SD.begin(10)) {
     Serial.println(F("SD fail — kontynuacja bez logowania"));
     sd_dostepne = false;
   }
   ```
2. Użyj `SD.begin(10, SPI_QUARTER_SPEED)` jeśli karta nie jest wykrywana przy domyślnej prędkości.
3. Formatuj karty SD jako FAT32 (nie exFAT, nie NTFS) — Arduino SD.h obsługuje tylko FAT16/FAT32.
4. Cały kod logowania owijaj warunkiem `if (sd_dostepne)` — system musi działać bez karty.
5. Nigdy nie blokuj `setup()` na inicjalizacji SD — PID musi startować niezależnie od dostępności kary.

**Warning signs:**
- `setup()` trwa dłużej niż 2 sekundy (widoczne przez brak pierwszego wydruku Serial po > 2s)
- Arduino zawieszone po starcie — nie odpowiada na komendy Serial
- `SD.begin()` zwraca false ale kod kontynuuje i `SD.open()` zawiesza się

**Phase to address:**
Faza 3 (SD logging) — `sd_dostepne` flag jest wymagana od pierwszego commita z kodem SD. Testy: uruchomienie bez karty SD nie może blokować PID.

---

### Pitfall 4: SD.print() / dataFile.close() blokuje pętlę PID na 5–50 ms

**What goes wrong:**
Wywołanie `dataFile.println(...)` lub `dataFile.close()` wewnątrz pętli 100 Hz powoduje sporadyczne opóźnienia 5–50 ms na operację SPI zapisu do karty SD. Przy pętli 10 ms (100 Hz) pojedynczy zapis może opóźnić iterację PID 5–50x. Efekt: serwomechanizm jerks (szarpie) w momencie logowania, zwłaszcza przy rotacji pliku dziennego.

**Why it happens:**
SD.h używa blokującego SPI. FAT32 wymaga aktualizacji tablicy plików (FAT) co N sektorów — ta operacja trwa znacznie dłużej niż pojedynczy zapis. `dataFile.close()` zawsze flush'uje i aktualizuje FAT, co powoduje najdłuższy stall. Na R4 SPI jest ograniczone do 5 MHz (wolniejsze niż R3), co pogarsza sytuację.

**How to avoid:**
1. NIGDY nie wywołuj `dataFile.close()` wewnątrz pętli PID — zamykaj plik tylko przy zmianie nazwy (rotacja dzienna) lub przy shutdown.
2. Loguj do bufora w RAM, zapisuj bufor do SD tylko co N iteracji (np. co 10 ramek TRACK — już w specyfikacji projektu).
3. Użyj `dataFile.flush()` zamiast `close()` dla trwałości danych bez kosztownej aktualizacji FAT.
4. Mierz czas pojedynczego `println()` przed integracją z pętlą:
   ```cpp
   unsigned long t0 = micros();
   dataFile.println(bufor);
   Serial.println(micros() - t0); // sprawdź czy < 1000 µs
   ```
5. Jeśli opóźnienie > 1 ms, przenieś logowanie do osobnego stanu (loguj tylko w IDLE lub przy zmianie stanu, nie co-tick w TRACKING).

**Warning signs:**
- PID output jest stabilny bez shielda, jerks z shieldem
- Serwomechanizm szarpie w regularnych interwałach (zbiegą z częstością logowania)
- Serial.print(micros()) pokazuje iteracje pętli > 10 000 µs (zamiast ~10 000 µs regularnie)

**Phase to address:**
Faza 3 (SD logging) — benchmark latencji zapisu SD PRZED wstawieniem do pętli PID. Wynik > 1 ms = logowanie poza pętlą.

---

### Pitfall 5: Serial na R4 WiFi — ESP32 USB bridge wprowadza opóźnienia przy pierwszym połączeniu

**What goes wrong:**
Na Leonardo `Serial` to natywne USB CDC na ATmega32U4 — port pojawia się natychmiast po starcie, bez dodatkowego chipa. Na Uno R4 WiFi `Serial` przechodzi przez ESP32-S3 jako USB bridge. Efekt: przy starcie Arduino, `Serial.available()` może zwracać 0 przez 100–500 ms, zanim ESP32 ustanowi połączenie USB. Kod czekający na `Serial.available() > 0` w `setup()` może blokować inicjalizację.

**Why it happens:**
ESP32-S3 pełni rolę USB-to-Serial bridge'a z osobnym firmware (uno-r4-wifi-usb-bridge). Inicjalizacja ESP32 po powrocie zasilania trwa dłużej niż natywne USB CDC. Dodatkowo: ESP32 odpowiada za "1200 bps touch" do wejścia w tryb bootloadera — to inny mechanizm niż DTR/reset na Leonardo.

**How to avoid:**
1. Nie blokuj `setup()` na `while (!Serial)` — użyj timeoutu:
   ```cpp
   unsigned long t_start = millis();
   while (!Serial && millis() - t_start < 500) {}
   // kontynuuj niezależnie
   ```
2. Strona RPi: `serial.open()` z `pyserial` NIE wymaga `write_timeout=0` i `dsrdtr=False` jak na Leonardo — na R4 DTR nie resetuje układu. Sprawdź czy istniejący kod pi_brain.py nie ma workaroundów specyficznych dla Leonardo (np. `dtr=False`).
3. Usuń kod Caterina-specific: `if (UDCON & _BV(LSM)) { USBCON |= _BV(DETACH); _delay_ms(10); }` — to jest kod bootloadera Leonardo, niekompilowalny i bezcelowy na R4.
4. Przetestuj komunikację: wyślij pakiet testowy z RPi 1s po otwarciu portu i sprawdź czy Arduino odpowiada.

**Warning signs:**
- Arduino "nie odpowiada" przez pierwsze 0.5s po USB connect
- Pi_brain.py zgłasza `serial.SerialException` przy pierwszym pakiecie po restarcie Arduino
- Kod zawierający `UDCON`, `USBCON`, `_BV(DETACH)` — to AVR-specific, nie skompiluje się na R4

**Phase to address:**
Faza 1 (Port pinów + Serial) — sprawdź pi_brain.py pod kątem Leonardo-specific workaroundów PRZED pierwszym testem komunikacji z R4.

---

### Pitfall 6: dtostrf() nie istnieje na ARM/Renesas — kod AVR-specific nie kompiluje się

**What goes wrong:**
Jeśli istniejący firmware używa `dtostrf(wartosc, szerokosc, precyzja, bufor)` do konwersji float na string (np. do logowania CSV), kod nie skompiluje się na Uno R4 WiFi. Komunikat błędu: `'dtostrf' was not declared in this scope`. Ta funkcja jest częścią AVR libc — nie istnieje w newlib-nano używanym przez RA4M1.

**Why it happens:**
`dtostrf()` pochodzi z `<avr/dtostrf.h>` — headerze specyficznym dla AVR libc. Toolchain ARM Cortex-M4 (arm-none-eabi-gcc z newlib-nano) tej funkcji nie dostarcza. Programiści przyzwyczajeni do Arduino Uno/Mega/Leonardo zakładają że `dtostrf()` jest standardową funkcją Arduino.

**How to avoid:**
Zastąp `dtostrf()` przez `sprintf()` z formatem `%f` — na ARM/RA4M1 `sprintf` obsługuje `%f` natively:
```cpp
// AVR (stary kod):
char bufor[16];
dtostrf(wartosc_float, 6, 2, bufor);

// ARM/R4 (nowy kod):
char bufor[16];
sprintf(bufor, "%6.2f", wartosc_float);
// lub krócej:
snprintf(bufor, sizeof(bufor), "%.2f", wartosc_float);
```
Alternatywnie użyj `String(wartosc_float, 2)` dla prostych przypadków (ale String heap = ostrożnie w pętli 100 Hz).

**Warning signs:**
- Błąd kompilacji: `'dtostrf' was not declared in this scope`
- Błąd kompilacji: `#include <avr/dtostrf.h>` — plik nie istnieje w ARM toolchain

**Phase to address:**
Faza 1 (Port firmware — kompilacja bazowa) — kompilacja pod `Arduino Uno R4 WiFi` ujawni wszystkie AVR-specific wywołania. Napraw błędy kompilacji zanim uruchomisz cokolwiek na sprzęcie.

---

## Technical Debt Patterns

Skróty które wyglądają rozsądnie ale tworzą długoterminowe problemy.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `dataFile.close()` w każdej iteracji pętli PID | Brak utraty danych przy resecie | Blokuje pętlę 5–50 ms każdy zapis, PID jerks | Nigdy w pętli PID — użyj flush() |
| `SD.begin()` bez sprawdzenia wyniku | Krótszy kod | System zawieszony gdy brak karty SD | Nigdy — `sd_dostepne` flag jest wymagana |
| `while (!Serial) {}` bez timeoutu | Pewność że Serial gotowy | Blokuje setup() na zawsze gdy USB nie podłączone | Nigdy bez timeoutu |
| Pomijanie wersji Servo przy instalacji | Szybki start | Servo jitter niewykrywalny bez oscyloskopu | Nigdy — zweryfikuj >= 1.2.2 |
| `String` do budowania linii CSV | Czytelny kod | Heap fragmentation w pętli 100 Hz, lagi GC | Tylko w setup(), nigdy w pętli PID |
| `dtostrf()` pozostawione bez zmiany | Działało na AVR | Błąd kompilacji na R4 (blokuje cały build) | Nigdy — zamień na sprintf() |

---

## Integration Gotchas

Typowe błędy przy łączeniu komponentów DataLogger Shield z istniejącym firmware.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SD + I2C równocześnie | Zakładanie że SPI i I2C są niezależne — mogą blokować się nawzajem na R4 | Testuj SD i I2C osobno najpierw, potem razem; sprawdź czy `Wire.begin()` przed `SD.begin()` nie powoduje konfliktu |
| SD Card pin CS | Użycie domyślnego SS bez inicjalizacji | Jawnie podaj CS pin: `SD.begin(10)` — D10 to standardowy CS dla DataLogger Shield V1.0 |
| RTC DS1307 adres | Zakładanie 0x68 bez weryfikacji | Uruchom I2C scanner przed RTClib; 0x68 to prawidłowy adres DS1307 |
| LCD + SPI jednocześnie | LCD na A0/A1 nie ma konfliktu z SPI, ale D2-D5 LCD mogą kolidować z projektami innych shieldów | Mapa pinów v2.1 jest zaplanowana bez konfliktów — nie zmieniaj jej |
| Servo D6/D9 + SPI D10-D13 | Zakładanie konfliktu timerów (nie ma) | Servo D6 i D9 używają innych timerów GPT niż SPI — brak konfliktu na R4 przy prawidłowej wersji Servo |
| RTClib + Wire | `Wire.begin()` musi być wywołane przed `rtc.begin()` | Kolejność: `Wire.begin()`, `SD.begin()`, `rtc.begin()` w setup() |

---

## Performance Traps

Wzorce działające prawidłowo ale psujące pętlę 100 Hz.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `dataFile.close()` w pętli PID | PID jitter co N ms, jerky servo | Zamknij plik tylko przy rotacji dziennej lub shutdown | Przy każdym zamknięciu pliku |
| `String` heap allocation w pętli | Rzadkie zawieszenia / spowolnienia po kilku minutach | char[] bufor statyczny, sprintf() | Po ~1000 alokacji (heap fragmentation) |
| `SD.open()` bez flagi O_CREAT | Plik nie jest tworzony, `println()` do nullptr | `SD.open(nazwa, FILE_WRITE)` automatycznie tworzy plik | Przy pierwszym uruchomieniu z nową kartą |
| SPI.setDataMode() w starym kodzie | Błąd kompilacji na R4 (brak tej metody w SPI API R4) | Użyj `SPI.beginTransaction(SPISettings(...))` | R4 SPI API jest nowsze niż R3 |
| millis() watchdog porównanie ze znakiem | Watchdog działa błędnie po 49 dniach rollover | `if ((unsigned long)(millis() - last_rx) > TIMEOUT)` — unsigned arithmetic | Po ~49 dniach uptime |

---

## Security Mistakes

Nie dotyczy systemu embedded bez sieciowego API. Uwagi bezpieczeństwa:

| Mistake | Risk | Prevention |
|---------|------|------------|
| Brak walidacji pola `mode` w pakiecie 8B | Nieprawidłowa wartość mode może wywołać nieistniejący stan maszyny stanów | Sprawdź `mode` przed przejściem stanu: `if (mode < 0 || mode > MAX_MODE) ignoruj_pakiet()` |
| Brak weryfikacji sumy kontrolnej XOR | Uszkodzony pakiet może wywołać nagły ruch serwa | XOR checksum z pakietu 8B jest weryfikowane — nie usuwaj tej weryfikacji podczas portu |

---

## "Looks Done But Isn't" Checklist

Rzeczy wyglądające na gotowe ale brakujące kluczowych elementów.

- [ ] **Servo płynny ruch:** Często brakuje sprawdzenia wersji biblioteki — zweryfikuj `Sweep` działa bez jitter PRZED testem PID
- [ ] **RTC inicjalizacja:** Często brakuje `rtc.adjust()` przy pierwszym uruchomieniu — sprawdź czy czas jest poprawny po odłączeniu zasilania na 30 sekund
- [ ] **SD logging:** Często brakuje `sd_dostepne` guard — sprawdź że uruchomienie BEZ karty SD nie zawiesza Arduino
- [ ] **Serial komunikacja:** Często brakuje usunięcia Leonardo-specific workaroundów z pi_brain.py — sprawdź `dtr=False` lub `dsrdtr=False` w pyserial init
- [ ] **Rotacja pliku dziennego:** Często brakuje flagi czy plik jest już otwarty — sprawdź że `SD.open()` nie jest wywoływane dwukrotnie dla tego samego pliku
- [ ] **dtostrf → sprintf:** Często brakuje zamiany wszystkich wywołań — wyszukaj `dtostrf` w całym firmware, żaden nie powinien pozostać
- [ ] **Watchdog unsigned arithmetic:** Sprawdź że `millis() - last_rx_time` używa rzutowania `(unsigned long)` lub że oba operandy są `unsigned long`

---

## Recovery Strategies

Gdy pułapki wystąpią mimo prewencji — jak przywrócić działanie.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Servo jitter (zła wersja biblioteki) | LOW | Arduino Library Manager → Servo → zainstaluj 1.2.2+ → rekompilacja |
| I2C nie działa z shieldem | LOW | Pocynuj szpilki A4/A5 nagłówków; test przez kable jumper |
| SD.begin() zawiesza setup() | LOW | Odłącz kartę SD, dodaj guard `if (!SD.begin(10)) { sd_dostepne = false; }`, wgraj firmware, podłącz kartę |
| SD write blokuje PID | MEDIUM | Refactor: wynieś logowanie poza bezpośrednią pętlę PID, użyj licznika ramek |
| dtostrf błąd kompilacji | LOW | Zastąp każde `dtostrf(v,w,p,buf)` przez `snprintf(buf, sizeof(buf), "%w.pf", v)` |
| Serial nie odpowiada (ESP32 bridge init) | LOW | Dodaj 500 ms timeout w `while (!Serial)`, sprawdź i usuń DTR workaroundy z pi_brain.py |

---

## Pitfall-to-Phase Mapping

Jak fazy roadmapu powinny adresować te pułapki.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Servo library < 1.2.2 (jitter) | Faza 1: Port firmware — weryfikacja Servo | Test Sweep 0°→90°→0° na serwie, brak drgań przez 30s |
| I2C shield styki (brak kontaktu) | Faza 2: Integracja DataLogger — RTC | I2C scanner wykrywa 0x68, `rtc.now().year() == 2026` |
| SD.begin() blokuje setup() | Faza 3: SD logging — inicjalizacja | Uruchomienie bez karty SD → Arduino nie zawieszone, Serial wypisuje "SD fail" |
| SD write latencja w pętli PID | Faza 3: SD logging — benchmark | micros() przed/po println() < 1000 µs; serwomechanizm płynny podczas logowania |
| Serial ESP32 bridge opóźnienie | Faza 1: Port firmware — Serial | Pi_brain.py wysyła pakiet po 1s od connect; Arduino odpowiada poprawnie |
| dtostrf AVR-specific | Faza 1: Port firmware — kompilacja bazowa | `Sketch → Verify/Compile` pod Arduino Uno R4 WiFi — zero błędów |
| SD + I2C konflikt SPI | Faza 3: SD logging — integracja kompletna | SD loguje CSV + RTC zwraca poprawny czas jednocześnie przez 60s |
| millis() watchdog unsigned | Faza 1: Port firmware — watchdog | Code review: `(unsigned long)(millis() - last_rx)` w każdym porównaniu timeout |

---

## Sources

- [Trouble with Servos on R4 WiFi — Arduino Forum](https://forum.arduino.cc/t/trouble-with-servos-on-r4-wifi/1151749) — potwierdzony jitter, fix w Servo 1.2.2 (lipiec 2024)
- [Data logger shield UNO R4 I2C conflict — Arduino Forum](https://forum.arduino.cc/t/data-logger-shield-uno-r4-i2c-conflict/1330380) — fizyczny problem styczkow nagłówków
- [data logger shield and UNO R4 I2C conflict — Adafruit Forums](https://forums.adafruit.com/viewtopic.php?t=215319) — pull-up 2.2kΩ do IOREF, Rev C shield
- [Arduino UNO R4 SPI with SD Card — Arduino Forum](https://forum.arduino.cc/t/arduino-uno-r4-spi-with-sd-card/1328547) — dataFile.close() wymagane, SPI MODE konflikty
- [UNO R4 Wifi with SD-Card — Arduino Forum](https://forum.arduino.cc/t/uno-r4-wifi-with-sd-card/1369843) — SPI_QUARTER_SPEED jako obejście
- [Using SPI with Arduino UNO R4 Wifi — Arduino Forum](https://forum.arduino.cc/t/using-spi-with-arduino-uno-r4-wifi/1326603) — SPI <= 5 MHz limit na R4
- [R4 WiFi shows up as TinyUSB CDC — Arduino Forum](https://forum.arduino.cc/t/r4-wifi-shows-up-as-tinyusb-cdc-in-win7-device-manager/1300166) — ESP32 USB bridge architektura
- [Upload fails when 1200bps touch causes port change — ArduinoCore-renesas GitHub](https://github.com/arduino/ArduinoCore-renesas/issues/73) — DTR / bootloader różnice vs Leonardo
- [Arduino uno-r4-library-compatibility — GitHub](https://github.com/arduino/uno-r4-library-compatibility) — oficjalna lista kompatybilności bibliotek
- [dtostrf() alternative for ARM — Arduino Forum](https://forum.arduino.cc/t/dtostrf-alternative-for-concatenating-a-float-and-a-string/101621) — sprintf() jako zamiennik na ARM
- [conversion from float on Nano 33 IoT — Arduino Forum](https://forum.arduino.cc/t/conversion-from-float-to-formatted-character-array-on-arduino-nano-33-iot/703520) — potwierdzenie sprintf %f na ARM

---
*Pitfalls research for: Arduino firmware migration Leonardo → Uno R4 WiFi + DataLogger Shield (real-time PID 100 Hz)*
*Researched: 2026-04-01*
