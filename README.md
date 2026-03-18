# 🤖 ARIES-LITE: Autonomous Real-time Intelligent Eye System

**ARIES-LITE** to zaawansowana platforma badawcza dedykowana autonomicznemu śledzeniu obiektów w czasie rzeczywistym. System integruje technologie **Internetu Rzeczy (IoT)**, **Uczenia Maszynowego (Machine Learning)** oraz klasyczną **Teorię Sterowania (Regulacja PID)**. 

Projekt umożliwia pełną bezprzewodową kontrolę nad dwuosiowym manipulatorem kamerowym za pomocą responsywnego interfejsu webowego.

---

## 🇵🇱 Wersja Polska

### 📖 Opis Projektu
ARIES-LITE został zaprojektowany, aby rozwiązać problem płynnego śledzenia dynamicznych celów przy ograniczonych zasobach obliczeniowych platformy Raspberry Pi 4. Sercem systemu jest autorska implementacja pętli sprzężenia zwrotnego, która analizuje 128-wymiarowe wektory cech twarzy (face encodings) i przekłada błąd pozycjonowania na precyzyjny ruch serwomechanizmów.



### 🌟 Kluczowe Funkcjonalności
* **Deep Learning Face Recognition:** System nie tylko wykrywa obecność twarzy, ale identyfikuje konkretną osobę na podstawie zdjęcia wzorcowego, odróżniając ją od osób postronnych.
* **Zaawansowany Regulator PID:** Eliminacja drgań mechanicznych i efektu oscylacji dzięki precyzyjnemu dostrojeniu członów $K_p$, $K_i$ oraz $K_d$.
* **Mobile-First Command Center:** Interfejs graficzny działający w przeglądarce smartfona (Flask), oferujący strumieniowanie obrazu MJPEG oraz zarządzanie bazą celów.
* **Inteligentne Skanowanie (Heuristic Sweep):** W przypadku utraty celu, system po 2 sekundach inicjuje algorytm poszukiwania oparty na dynamicznym skanowaniu sferycznym.
* **Safe Startup Procedure:** Inkrementalne pozycjonowanie serwomechanizmów przy starcie systemu, chroniące układ przed skokami napięcia (brownout).

### 🛠️ Architektura Sprzętowa

| Komponent | Specyfikacja | Rola |
| :--- | :--- | :--- |
| **RPi 4B** | 4GB RAM, Quad-core Cortex-A72 | Jednostka obliczeniowa i host serwera |
| **Kamera v2** | 8MP Sony IMX219 | Akwizycja obrazu wysokiej gęstości |
| **MG-90S** | Metalowe przekładnie, 1.8kg/cm | Precyzyjne pozycjonowanie osi X/Y |
| **Zasilanie** | Separowane (5V 3A / 6V 2A) | Stabilność prądowa układu sterowania |

### 💻 Instalacja i Konfiguracja

1.  **Klonowanie repozytorium:**
    ```bash
    git clone [https://github.com/MateuszParol/ARIES-LITE.git](https://github.com/MateuszParol/ARIES-LITE.git)
    cd ARIES-LITE
    ```
2.  **Przygotowanie środowiska:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
3.  **Uruchomienie:**
    ```bash
    python3 main.py
    ```

### ⚠️ Rozwiązywanie Problemów (Troubleshooting)

* **Problem: Obraz klatkuje lub ma duże opóźnienie (Input Lag).**
    * *Rozwiązanie:* Przetwarzanie twarzy jest obciążające. Zmniejsz rozdzielczość analizy w `config.py` do 320x240 lub 160x120. Upewnij się, że RPi ma aktywne chłodzenie.
* **Problem: Serwa drżą (Jittering).**
    * *Rozwiązanie:* Sprawdź połączenie masy (GND). Minus z koszyka baterii musi być połączony z pinem GND Raspberry Pi. Zwiększ wartość tłumienia w parametrze $K_d$.
* **Problem: Nagłe restarty systemu podczas ruchu.**
    * *Rozwiązanie:* Silniki MG-90S generują piki prądowe. Użyj kondensatora elektrolitycznego (np. 470uF) przy szynie zasilania serw lub sprawdź wydajność baterii AA.
* **Problem: Błąd "Camera not detected".**
    * *Rozwiązanie:* Na systemie Raspberry Pi OS (Bookworm) wymagane jest użycie stosu `libcamera`. Sprawdź komendą `libcamera-hello`, czy system widzi sensor.

---

## 🇺🇸 English Version

### 📖 Project Overview
ARIES-LITE is an engineering platform designed to tackle the challenge of smooth target tracking under the hardware constraints of the Raspberry Pi 4. The core of the system is a custom feedback loop that analyzes 128-dimensional face descriptors and translates positional errors into micro-degree servo adjustments.



### 🌟 High-End Features
* **Neural Face Recognition:** Uses Dlib-based encodings to distinguish the primary target from unauthorized individuals with high precision.
* **Dual-Axis PID Control:** Eliminates mechanical jitter and overshooting by fine-tuning $K_p$, $K_i$, and $K_d$ constants.
* **Mobile Command Center:** A lightweight Flask-based web interface for MJPEG live streaming and target management via smartphone.
* **Heuristic Scanning:** When the target is lost, the system initiates an automated spherical scan pattern to re-acquire the subject.
* **Safe Startup Logic:** Prevents sudden current draw by incrementally moving servos to the center position upon initialization.

### 🛠️ Hardware Stack

| Component | Specification | Role |
| :--- | :--- | :--- |
| **RPi 4B** | 4GB RAM, Quad-core Cortex-A72 | Compute Engine & Web Host |
| **Camera v2** | 8MP Sony IMX219 | High-fidelity image acquisition |
| **MG-90S** | Metal Geared, 1.8kg/cm torque | X/Y Axis Actuation |
| **Power Supply** | Isolated (5V 3A / 6V 2A) | Voltage stability for servos |



### 💻 Setup & Deployment

1.  **Clone the Repo:**
    ```bash
    git clone [https://github.com/MateuszParol/ARIES-LITE.git](https://github.com/MateuszParol/ARIES-LITE.git)
    cd ARIES-LITE
    ```
2.  **Dependencies:** Ensure `dlib` is compiled correctly for ARM architecture.
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run:** `python3 main.py`

### ⚠️ Troubleshooting

* **Issue: Excessive Lag/Low FPS.**
    * *Fix:* Downscale processing resolution in `config.py`. Face recognition is CPU-intensive; consider using HOG instead of CNN models for detection.
* **Issue: Servo Instability.**
    * *Fix:* Verify common ground (GND) connection between RPi and external power. Adjust the $K_d$ parameter to dampen oscillations.
* **Issue: Sudden System Reboots.**
    * *Fix:* Check for brownouts. Power servos through an external source, never directly from the RPi 5V pin.
* **Issue: Camera "Not Found" on Debian Bookworm.**
    * *Fix:* Transition to the `libcamera` stack and ensure the interface is enabled via `raspi-config`.

---

## 👨‍💻 Authorship & Affiliation

**Lead Engineer:** Mateusz Parol  
**Company:** [DeveloBite](https://github.com/DeveloBite)  
**Research Institution:** Koszalin University of Technology (Politechnika Koszalińska)  

*This research is conducted at the Faculty of Electronics and Computer Science, focusing on the optimization of real-time control systems and edge-computing vision algorithms.*