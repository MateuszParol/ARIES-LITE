"""
Test Tracker v1.6 — Autonomiczny moduł testowy pętli sterowania.

Dowodzi działania: Picamera2 + HAAR detekcja + PID tracking + skanowanie sinusoidalne.
Standalone — nie wymaga Flaska ani dlib.
"""

import math
import sys
import time
import logging
import threading
from typing import Optional, Tuple

import cv2
import numpy as np
from simple_pid import PID

from src import config
from src.hardware import PanTiltSystem

logger = logging.getLogger(__name__)

# --- Stałe modułowe ---
LORES_WIDTH = 320
LORES_HEIGHT = 240
HAAR_MIN_NEIGHBORS = 8
HAAR_MIN_SIZE = (50, 50)
STREAK_REQUIRED = 3
SCAN_AMPLITUDE = 45.0       # stopnie
SCAN_FREQUENCY = 0.1        # Hz (pełny cykl = 10s)
PID_OUTPUT_LIMIT = 10.0
CAMERA_MAX_RETRIES = 3
CAMERA_RETRY_DELAY = 1.0  # sekundy miedzy probami ponownej inicjalizacji

# Stan TARGET_LOST (przejściowy, wizualny)
STATE_TARGET_LOST = "TARGET_LOST"

# Próba importu Picamera2
try:
    from picamera2 import Picamera2
except ImportError:
    logger.error(
        "Nie mozna zaimportowac picamera2. "
        "Zainstaluj: sudo apt install python3-picamera2 "
        "i uruchom venv z --system-site-packages"
    )
    sys.exit(1)


class Picamera2Stream:
    """Wrapper kamery Picamera2 z wątkowym przechwytywaniem klatek."""

    def __init__(self, width: int = LORES_WIDTH, height: int = LORES_HEIGHT):
        self._width = width
        self._height = height
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._picam2 = None

    def start(self) -> None:
        """Inicjalizuje kamere i uruchamia watek przechwytywania."""
        self._picam2 = Picamera2()
        video_config = self._picam2.create_video_configuration(
            lores={"size": (self._width, self._height), "format": "BGR888"}
        )
        self._picam2.configure(video_config)
        self._picam2.start()
        logger.info(f"Picamera2 uruchomiona: {self._width}x{self._height} BGR888")

        self._running = True
        self._thread = threading.Thread(target=self._petla_przechwytywania, daemon=True)
        self._thread.start()

    def _petla_przechwytywania(self) -> None:
        """Watek daemon: przechwytuje klatki w petli z ponowna inicjalizacja przy bledzie."""
        _retry_count = 0
        _format_zweryfikowany = False

        while self._running:
            try:
                klatka = self._picam2.capture_array("lores")
                _retry_count = 0  # reset po udanym przechwyceniu

                # Weryfikacja formatu na pierwszej klatce
                if not _format_zweryfikowany:
                    logger.info(f"Format klatki: shape={klatka.shape}, dtype={klatka.dtype}")
                    if klatka.ndim == 3 and klatka.shape[2] == 4:
                        logger.warning("4-kanalowy format wykryty — przycinam do BGR")
                        klatka = klatka[:, :, :3]
                    _format_zweryfikowany = True

            except Exception as e:
                _retry_count += 1
                logger.error(f"Blad kamery ({_retry_count}/{CAMERA_MAX_RETRIES}): {e}")
                if _retry_count >= CAMERA_MAX_RETRIES:
                    logger.error("Kamera niedostepna — zatrzymanie systemu")
                    self._running = False
                    break
                # Proba ponownej inicjalizacji
                try:
                    self._picam2.stop()
                    self._picam2.close()
                except Exception:
                    pass
                time.sleep(CAMERA_RETRY_DELAY)
                try:
                    self._picam2 = Picamera2()
                    video_config = self._picam2.create_video_configuration(
                        lores={"size": (self._width, self._height), "format": "BGR888"}
                    )
                    self._picam2.configure(video_config)
                    self._picam2.start()
                    logger.info("Kamera ponownie uruchomiona po bledzie")
                except Exception as reinit_err:
                    logger.error(f"Ponowna inicjalizacja nieudana: {reinit_err}")
                continue

            with self._lock:
                self._frame = klatka
            time.sleep(0.01)

    def odczytaj(self) -> Optional[np.ndarray]:
        """Zwraca ostatnią klatkę (thread-safe)."""
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def stop(self) -> None:
        """Zatrzymanie kamery — dwuetapowe: stop() + close()."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self._picam2 is not None:
            try:
                self._picam2.stop()
            finally:
                self._picam2.close()
            logger.info("Picamera2 zatrzymana i zamknięta.")


class DetekcjaTwarzy:
    """Detekcja twarzy HAAR z filtrem streak (fałszywe pozytywy)."""

    def __init__(self):
        haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._klasyfikator = cv2.CascadeClassifier(haar_path)
        if self._klasyfikator.empty():
            raise RuntimeError(f"Nie udało się załadować kaskady HAAR: {haar_path}")
        self._streak: int = 0
        logger.info("Klasyfikator HAAR załadowany.")

    def wykryj(self, klatka: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Wykrywa twarz w klatce. Zwraca bbox (x, y, w, h) największej twarzy
        tylko gdy streak >= STREAK_REQUIRED. None jeśli brak stabilnej detekcji.
        """
        szara = cv2.cvtColor(klatka, cv2.COLOR_BGR2GRAY)
        twarze = self._klasyfikator.detectMultiScale(
            szara,
            scaleFactor=1.1,
            minNeighbors=HAAR_MIN_NEIGHBORS,
            minSize=HAAR_MIN_SIZE,
        )

        if len(twarze) == 0:
            self._streak = 0
            return None

        # Wybierz największą twarz wg pola powierzchni
        najw = max(twarze, key=lambda r: r[2] * r[3])
        self._streak += 1

        if self._streak >= STREAK_REQUIRED:
            return tuple(najw)
        return None

    def resetuj_streak(self) -> None:
        """Resetuje licznik streak (przy zmianie stanu)."""
        self._streak = 0


class MaszynaStanow:
    """Maszyna stanów + PID: SCANNING → TRACKING → TARGET_LOST → SCANNING."""

    def __init__(self):
        self.hardware = PanTiltSystem()
        self.stan = config.STATE_SCANNING

        # Dwa kontrolery PID (z config)
        self.pid_pan = PID(config.PID_PAN_P, config.PID_PAN_I, config.PID_PAN_D, setpoint=0)
        self.pid_pan.output_limits = (-PID_OUTPUT_LIMIT, PID_OUTPUT_LIMIT)

        self.pid_tilt = PID(config.PID_TILT_P, config.PID_TILT_I, config.PID_TILT_D, setpoint=0)
        self.pid_tilt.output_limits = (-PID_OUTPUT_LIMIT, PID_OUTPUT_LIMIT)

        self._czas_ostatniego_celu = time.time()

    def inicjalizuj(self) -> None:
        """Safe Start — płynny ruch do pozycji neutralnej (HW-01)."""
        logger.info("Safe Start: płynny ruch serw do (0, 0)")
        self.hardware.smooth_move_to(0, 0)
        self.stan = config.STATE_SCANNING
        logger.info("Safe Start zakończony. Stan: SCANNING")

    def tick(self, bbox: Optional[Tuple[int, int, int, int]], w: int, h: int) -> str:
        """
        Główna logika per-klatka. Zwraca aktualny stan (str).

        :param bbox: Wykryta twarz (x, y, bw, bh) lub None
        :param w: Szerokość klatki
        :param h: Wysokość klatki
        """
        if self.stan == config.STATE_SCANNING:
            if bbox is not None:
                self._przejdz_do(config.STATE_TRACKING)
                self._sledz(bbox, w, h)
            else:
                self._skanuj()

        elif self.stan == config.STATE_TRACKING:
            if bbox is not None:
                self._czas_ostatniego_celu = time.time()
                self._sledz(bbox, w, h)
            else:
                # Brak twarzy — sprawdź timeout
                if time.time() - self._czas_ostatniego_celu >= config.TIME_TO_LOST_SEC:
                    self.stan = STATE_TARGET_LOST
                    logger.info("Target Lost — przejście do SCANNING")
                    self._przejdz_do(config.STATE_SCANNING)
                # else: trzymaj pozycję (hold)

        elif self.stan == STATE_TARGET_LOST:
            # Natychmiastowe przejście do SCANNING (obsłużone powyżej)
            self._przejdz_do(config.STATE_SCANNING)

        return self.stan

    def _skanuj(self) -> None:
        """Skanowanie sinusoidalne: pan = A * sin(2π * f * t), tilt = 0."""
        t = time.time()
        pan = SCAN_AMPLITUDE * math.sin(2.0 * math.pi * SCAN_FREQUENCY * t)
        self.hardware.set_angles(pan, 0.0)

    def _sledz(self, bbox: Tuple[int, int, int, int], w: int, h: int) -> None:
        """Śledzenie PID — oblicza błąd i koryguje kąty serw."""
        x, y, bw, bh = bbox
        srodek_x = x + bw // 2
        srodek_y = y + bh // 2

        ramka_cx = w // 2
        ramka_cy = h // 2

        blad_pan = srodek_x - ramka_cx
        blad_tilt = srodek_y - ramka_cy

        # Pan negowany (jak w tracker.py:77)
        korekta_pan = -self.pid_pan(blad_pan)
        korekta_tilt = self.pid_tilt(blad_tilt)

        nowy_pan = self.hardware.pan_angle + korekta_pan
        nowy_tilt = self.hardware.tilt_angle + korekta_tilt

        self.hardware.set_angles(nowy_pan, nowy_tilt)

    def _przejdz_do(self, nowy_stan: str) -> None:
        """Zmiana stanu z resetem PID przy wejściu w SCANNING."""
        logger.info(f"Zmiana stanu: {self.stan} → {nowy_stan}")
        self.stan = nowy_stan
        self._czas_ostatniego_celu = time.time()
        if nowy_stan == config.STATE_SCANNING:
            self.pid_pan.reset()
            self.pid_tilt.reset()


class TestTracker:
    """Orkiestrator — łączy kamerę, detekcję i maszynę stanów."""

    def __init__(self):
        self.kamera = Picamera2Stream()
        self.detekcja = DetekcjaTwarzy()
        self.maszyna = MaszynaStanow()
        self._running = False
        self._headless = False

    def uruchom(self) -> None:
        """Główna pętla: start kamery → safe start → capture → detect → tick → HUD → display."""
        self.kamera.start()
        self.maszyna.inicjalizuj()
        self._running = True

        logger.info("TestTracker uruchomiony. Naciśnij 'q' lub Ctrl+C aby zakończyć.")

        while self._running:
            klatka = self.kamera.odczytaj()
            if klatka is None:
                time.sleep(0.01)
                continue

            h, w = klatka.shape[:2]

            # Detekcja twarzy
            bbox = self.detekcja.wykryj(klatka)

            # Tick maszyny stanów
            stan = self.maszyna.tick(bbox, w, h)

            # Rysuj HUD
            self._rysuj_hud(klatka, bbox, stan)

            # Wyswietlanie z upscale 2x i fallback headless
            if not self._headless:
                wyswietlana = cv2.resize(klatka, (640, 480), interpolation=cv2.INTER_NEAREST)
                try:
                    cv2.imshow("ARIES-LITE Test Tracker", wyswietlana)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        logger.info("Klawisz 'q' — zatrzymanie.")
                        break
                except cv2.error:
                    logger.info("Brak wyswietlacza (cv2.error) — przelaczam na tryb headless")
                    self._headless = True
                    cv2.destroyAllWindows()
            else:
                # Tryb headless — loguj stan co zmiane
                pass  # Logi stanow sa juz w MaszynaStanow._przejdz_do()

        self.zatrzymaj()

    def _rysuj_hud(self, klatka: np.ndarray, bbox: Optional[Tuple[int, int, int, int]], stan: str) -> None:
        """Nakładka HUD: prostokąt na twarzy, etykieta stanu, celownik."""
        h, w = klatka.shape[:2]

        # Celownik (środek kadru)
        cx, cy = w // 2, h // 2
        rozmiar = 15
        cv2.line(klatka, (cx - rozmiar, cy), (cx + rozmiar, cy), (0, 255, 255), 1)
        cv2.line(klatka, (cx, cy - rozmiar), (cx, cy + rozmiar), (0, 255, 255), 1)

        # Prostokąt na twarzy
        if bbox is not None:
            x, y, bw, bh = bbox
            cv2.rectangle(klatka, (x, y), (x + bw, y + bh), (0, 255, 0), 2)

        # Etykieta stanu
        kolor_stanu = {
            config.STATE_SCANNING: (0, 165, 255),   # pomarańczowy
            config.STATE_TRACKING: (0, 255, 0),      # zielony
            STATE_TARGET_LOST: (0, 0, 255),           # czerwony
        }.get(stan, (255, 255, 255))

        cv2.putText(klatka, f"STAN: {stan}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, kolor_stanu, 2)

        # Info o kątach serw
        pan = self.maszyna.hardware.pan_angle
        tilt = self.maszyna.hardware.tilt_angle
        cv2.putText(klatka, f"Pan:{pan:+.1f} Tilt:{tilt:+.1f}", (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    def zatrzymaj(self) -> None:
        """Cleanup: zatrzymanie petli, powrot serw do neutralnej, zwolnienie kamery."""
        self._running = False
        self.kamera.stop()
        logger.info("Powrot do pozycji neutralnej...")
        self.maszyna.hardware.smooth_move_to(0, 0)
        self.maszyna.hardware.detach_servos()
        cv2.destroyAllWindows()
        logger.info("TestTracker zatrzymany — zasoby zwolnione.")
