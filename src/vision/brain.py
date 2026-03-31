"""Glowny modul sterowania MozgRPi dla ARIES-LITE v2.0.

Dostarcza MozgRPi — synchroniczna petla sterowania: kamera -> detekcja
-> obliczenie bledu X/Y -> wyslanie ramki binarnej 8B do Arduino.
Osobny daemon thread WatekHeartbeat zapewnia heartbeat co 200ms
niezaleznie od FPS detekcji (per protokol D-07).
"""

import logging
import threading
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np

from .camera import KameraRPi
from .detector import WykrywaczTwarzy
from .serial_interface import SerialInterface

logger = logging.getLogger(__name__)

# --- Stale modulowe ---
HEARTBEAT_INTERVAL: float = 0.200   # 200ms — max odstep miedzy TX (per D-07)
HEARTBEAT_POLL: float = 0.050       # 50ms poll w watku heartbeat
MODE_IDLE: int = 0                   # Tryb spoczynkowy
MODE_SCAN: int = 1                   # Tryb skanowania (Arduino skanuje autonomicznie)
MODE_TRACK: int = 2                  # Tryb sledzenia twarzy


class WatekHeartbeat(threading.Thread):
    """Daemon thread wysylajacy heartbeat co HEARTBEAT_INTERVAL sekund.

    Monitoruje czas ostatniej TX i wysyla ramke SCAN gdy minelo
    HEARTBEAT_INTERVAL bez wysylki z petli glownej. Zapobiega uruchomieniu
    watchdog Arduino (per D-07: Arduino watchdog odpala sie przy braku ramki >500ms).
    """

    def __init__(
        self, serial_iface: SerialInterface, czas_ostatniej_tx_ref: List[float]
    ) -> None:
        """Inicjalizuje WatekHeartbeat.

        Args:
            serial_iface: Interfejs szeregowy do wysylania ramek heartbeat.
            czas_ostatniej_tx_ref: Mutowalny ref (lista [float]) do czasu ostatniej TX.
                                   Wspodzielony z MozgRPi — aktualizowany przez obie strony.
        """
        super().__init__(daemon=True, name="heartbeat")
        self._serial = serial_iface
        self._czas_ref = czas_ostatniej_tx_ref  # lista [float] — mutowalny ref
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """Sygnalizuje watkowi zatrzymanie."""
        self._stop_event.set()

    def run(self) -> None:
        """Petla heartbeat: sprawdza czas TX i wysyla ramke SCAN gdy potrzeba."""
        while not self._stop_event.is_set():
            try:
                # Sprawdz czy minelo HEARTBEAT_INTERVAL od ostatniej TX
                if time.time() - self._czas_ref[0] >= HEARTBEAT_INTERVAL:
                    self._serial.send_frame(
                        mode=MODE_SCAN, error_x=0, error_y=0, face_size=0
                    )
                    self._czas_ref[0] = time.time()
            except Exception as e:
                logger.error(f"Heartbeat TX blad: {e}")
                # Nie przerywaj petli — kontynuuj heartbeat mimo bledow TX

            self._stop_event.wait(HEARTBEAT_POLL)


class MozgRPi:
    """Glowna klasa sterowania RPi — integruje wizje, detekcje i TX do Arduino.

    Synchroniczna petla: kamera.odczytaj() -> detektor.wykryj() ->
    detektor.wybierz_twarz() -> _oblicz_error() -> serial.send_frame().
    Osobny daemon thread WatekHeartbeat zapewnia TX co max 200ms
    niezaleznie od FPS detekcji (brak twarzy nie wstrzymuje komunikacji).
    """

    def __init__(self, port: str = "/dev/ttyACM0") -> None:
        """Inicjalizuje MozgRPi bez uruchamiania kamery ani portu.

        Args:
            port: Sciezka do portu szeregowego Arduino (domyslnie /dev/ttyACM0).
        """
        self._kamera = KameraRPi()
        self._detektor = WykrywaczTwarzy()
        self._serial = SerialInterface(port=port)
        self._running: bool = False
        self._headless: bool = False
        self._czas_ostatniej_tx: List[float] = [0.0]  # mutowalny ref dla heartbeat
        self._heartbeat: Optional[WatekHeartbeat] = None
        self._zatrzymano: bool = False  # guard przeciw podwojnemu wywolaniu zatrzymaj()

        # Licznik klatek SCAN — do ograniczenia czestotliwosci logowania latencji
        self._licznik_scan_log: int = 0

        # Zmienne HUD — FPS tracking
        self._czas_klatki_prev: float = 0.0

    def uruchom(self) -> None:
        """Otwiera zasoby, uruchamia watki i wywoluje petla glowna.

        Sekwencja inicjalizacji:
        1. Otworz port szeregowy (jesli fail: loguj warning, kontynuuj bez serial)
        2. Uruchom kamere (start() — inicjalizacja Picamera2 + AWB fix)
        3. Uruchom daemon thread heartbeat
        4. Uruchom petla glowna (blokujaca)
        5. Po powrocie z petli: wywolaj zatrzymaj() dla cleanup
        """
        # Otworz port szeregowy — nie-krytyczny blad (mozna pracowac bez TX)
        try:
            self._serial.open()
        except Exception as e:
            logger.warning(
                f"Nie mozna otworzyc portu szeregowego: {e}. "
                "Kontynuuje bez TX do Arduino."
            )

        # Uruchom kamere — blokuje przez ~2s (AWB warmup)
        self._kamera.start()

        # Uruchom daemon thread heartbeat
        self._heartbeat = WatekHeartbeat(
            serial_iface=self._serial,
            czas_ostatniej_tx_ref=self._czas_ostatniej_tx,
        )
        self._heartbeat.start()

        # Uruchom petla glowna (blokujaca — konczy sie gdy self._running = False)
        self._running = True
        self._petla_glowna()

        # Po powrocie z petli: cleanup (moze byc juz wywolany przez signal handler)
        self.zatrzymaj()

    def _petla_glowna(self) -> None:
        """Synchroniczna petla sterowania: kamera -> detekcja -> TX.

        Timestamp monotonic_ns // 1_000_000 zapewnia monotonicznie rosnacy
        timestamp w milisekundach (Pitfall 3 z Research: nie uzywac time.time()
        dla detect_for_video — moze cofnac sie przy ntp sync).
        """
        while self._running:
            try:
                # Monotoniczny timestamp w ms — wymagany przez MediaPipe VIDEO mode
                timestamp_ms: int = time.monotonic_ns() // 1_000_000

                # Odczytaj klatke z kamery
                klatka = self._kamera.odczytaj()
                if klatka is None:
                    time.sleep(0.01)
                    continue

                # Detekcja twarzy — zwraca liste bbox (x, y, w, h)
                twarze = self._detektor.wykryj(klatka, timestamp_ms)

                # Sticky selection — wybierz najlepsza twarz z histereza 20%
                bbox = self._detektor.wybierz_twarz(twarze)

                # Oblicz blad i wyslij ramke do Arduino
                if bbox is not None:
                    error_x, error_y, face_size = self._oblicz_error(bbox, klatka.shape)
                    tryb = "TRACK"
                    try:
                        czas_przed_tx = time.monotonic_ns() // 1_000_000
                        self._serial.send_frame(
                            mode=MODE_TRACK,
                            error_x=error_x,
                            error_y=error_y,
                            face_size=face_size,
                        )
                        czas_po_tx = time.monotonic_ns() // 1_000_000
                        logger.info(
                            f"[LAT] TX TRACK: {czas_po_tx - czas_przed_tx}ms "
                            f"err_x={error_x} err_y={error_y} ts={czas_po_tx}"
                        )
                        self._czas_ostatniej_tx[0] = time.time()
                    except Exception as e:
                        logger.error(f"TX (TRACK) blad: {e}")
                else:
                    # Brak twarzy — per D-07: wyslij SCAN, Arduino skanuje autonomicznie
                    error_x, error_y, face_size = 0, 0, 0
                    tryb = "SCAN"
                    try:
                        self._serial.send_frame(
                            mode=MODE_SCAN,
                            error_x=0,
                            error_y=0,
                            face_size=0,
                        )
                        self._czas_ostatniej_tx[0] = time.time()
                        self._licznik_scan_log += 1
                        if self._licznik_scan_log % 50 == 0:
                            czas_po_tx = time.monotonic_ns() // 1_000_000
                            logger.info(f"[LAT] TX SCAN: heartbeat ok ts={czas_po_tx}")
                    except Exception as e:
                        logger.error(f"TX (SCAN) blad: {e}")

                # HUD — rysuj na klatce i wyswietl (z headless fallback)
                self._rysuj_hud(klatka, bbox, error_x, error_y, tryb)

            except Exception as e:
                logger.error(f"Blad w petli glownej: {e}")
                # Kontynuuj — petla nie moze sie zatrzymac przez jednostkowy blad

    def _oblicz_error(
        self,
        bbox: Tuple[int, int, int, int],
        shape: Tuple[int, ...],
    ) -> Tuple[int, int, int]:
        """Oblicza blad X/Y wzgledem centrum klatki oraz rozmiar twarzy.

        Blad X/Y normalizowany do zakresu -160..+160 (polowa 320px).
        Skalowanie dla rozdzielczosci innych niz 320px.
        face_size = (area twarzy / area klatki) * 255.

        Args:
            bbox: Bounding box twarzy (x, y, szerokosc, wysokosc) w pikselach.
            shape: Shape klatki NumPy (h, w, c) lub (h, w).

        Returns:
            Trojka (error_x, error_y, face_size) — error sklamowany do zakresow.
        """
        x, y, bw, bh = bbox
        h, w = shape[:2]

        # Srodek bounding boxa
        srodek_x: int = x + bw // 2
        srodek_y: int = y + bh // 2

        # Blad wzgledem centrum klatki
        error_x: int = srodek_x - (w // 2)
        error_y: int = srodek_y - (h // 2)

        # Skalowanie do zakresu -160..+160 / -120..+120 dla niestandardowych rozdzielczosci
        if w != 320:
            error_x = int(error_x * 160 / (w // 2))
            error_y = int(error_y * 120 / (h // 2))

        # Clamp bledu do protokolarnych zakresow
        error_x = max(-160, min(160, error_x))
        error_y = max(-120, min(120, error_y))

        # Rozmiar twarzy jako procent klatki * 255 (uint8)
        area_ratio: float = (bw * bh) / (w * h)
        face_size: int = max(0, min(255, int(area_ratio * 255)))

        return error_x, error_y, face_size

    def _rysuj_hud(
        self,
        klatka: np.ndarray,
        bbox: Optional[Tuple[int, int, int, int]],
        error_x: int,
        error_y: int,
        tryb: str,
    ) -> None:
        """Rysuje HUD na klatce i wyswietla przez cv2.imshow (z headless fallback).

        Elementy HUD:
        - Prostokat bounding box twarzy (jezeli wykryta)
        - Crosshair w centrum klatki
        - Tekst: tryb (TRACK/SCAN), blad X/Y, FPS

        Per D-03: headless fallback — jezeli cv2.imshow wyrzuci cv2.error
        (brak wyswietlacza), ustaw _headless=True i skip imshow w kolejnych kl.

        Args:
            klatka: Klatka BGR do rysowania (modyfikowana in-place).
            bbox: Bounding box twarzy lub None.
            error_x: Blad X do wyswietlenia.
            error_y: Blad Y do wyswietlenia.
            tryb: Aktualny tryb ("TRACK" lub "SCAN").
        """
        h, w = klatka.shape[:2]
        cx, cy = w // 2, h // 2

        # Prostokat bounding box twarzy
        if bbox is not None:
            x, y, bw, bh = bbox
            cv2.rectangle(klatka, (x, y), (x + bw, y + bh), (0, 255, 0), 2)

        # Crosshair w centrum klatki
        cv2.line(klatka, (cx - 15, cy), (cx + 15, cy), (0, 255, 255), 1)
        cv2.line(klatka, (cx, cy - 15), (cx, cy + 15), (0, 255, 255), 1)

        # Oblicz FPS na podstawie czasu miedzy klatkami
        teraz = time.perf_counter()
        fps = 0.0
        if self._czas_klatki_prev > 0.0:
            delta = teraz - self._czas_klatki_prev
            fps = 1.0 / delta if delta > 0.0 else 0.0
        self._czas_klatki_prev = teraz

        # Tekst HUD — tryb, blad X/Y, FPS
        cv2.putText(
            klatka, f"Tryb: {tryb}", (10, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1
        )
        cv2.putText(
            klatka, f"eX:{error_x:+4d} eY:{error_y:+4d}", (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1
        )
        cv2.putText(
            klatka, f"FPS: {fps:.1f}", (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1
        )

        # Wyswietl klatke (headless fallback gdy brak wyswietlacza)
        if not self._headless:
            try:
                cv2.imshow("ARIES-LITE pi_brain", klatka)
                cv2.waitKey(1)
            except cv2.error:
                self._headless = True
                logger.info("Headless mode — brak wyswietlacza, cv2.imshow wyaczony")

    def zatrzymaj(self) -> None:
        """Zatrzymuje system — thread-safe, guard przeciw podwojnemu wywolaniu.

        UWAGA: ta metoda moze byc wywolana z INNEGO WATKU niz petla glowna
        (signal handler w run_pi_brain.py wywoluje mozg.zatrzymaj() z kontekstu
        signal handlera, podczas gdy _petla_glowna() biegnie w watku glownym).
        Dlatego self._running = False jest jedyna operacja zatrzymujaca petli —
        flaga bool jest thread-safe w CPython (GIL). Reszta cleanup uruchamia
        sie po powrocie z _petla_glowna() (w uruchom()), LUB tutaj jezeli petla
        juz nie dziala. Guard _zatrzymano zapobiega podwojnemu cleanup gdy
        signal handler i uruchom() wywola zatrzymaj() jednoczesnie.
        """
        # Guard przeciw podwojnemu wywolaniu (signal handler + uruchom())
        if self._zatrzymano:
            return
        self._zatrzymano = True

        # Zatrzymaj petla glowna (thread-safe pod GIL)
        self._running = False

        try:
            # Zatrzymaj daemon thread heartbeat
            if self._heartbeat is not None:
                self._heartbeat.stop()
                self._heartbeat.join(timeout=1.0)
                self._heartbeat = None

            # Zamknij detektor MediaPipe i zwolnij zasoby TFLite
            self._detektor.zamknij()

            # Zamknij port szeregowy
            self._serial.close()

            # Zatrzymaj kamere (join daemon thread + Picamera2 stop/close)
            self._kamera.zatrzymaj()

            # Zamknij wszystkie okna OpenCV
            cv2.destroyAllWindows()

            logger.info("MozgRPi zatrzymany")

        except Exception as e:
            logger.error(f"Blad podczas zatrzymywania MozgRPi: {e}")
            # Kontynuuj zamykanie — nie przerywaj cleanup przy bledzie
