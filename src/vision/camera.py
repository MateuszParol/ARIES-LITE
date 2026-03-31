"""Modul kamery Picamera2 z AWB fix dla ARIES-LITE v2.0.

Dostarcza KameraRPi — daemon thread przechwytujacy klatki YUV420
z sensora IMX219, konwertujacy do BGR i blokujacy ColourGains
po stabilizacji AWB (dwuetapowy fix eliminujacy niebieska poswiate).
"""

import logging
import sys
import threading
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# --- Stale modulowe ---
LORES_WIDTH: int = 320
LORES_HEIGHT: int = 240
AWB_WARMUP_DELAY: float = 2.0          # sekundy oczekiwania na stabilizacje AWB
AWB_FALLBACK_GAINS: tuple = (2.2, 1.8)  # (Red, Blue) — empiryczne dla IMX219 w swietle dziennym
CAMERA_MAX_RETRIES: int = 3
CAMERA_RETRY_DELAY: float = 1.0        # sekundy miedzy probami ponownej inicjalizacji

# Proba importu Picamera2 (wymaga systemu RPi z --system-site-packages)
try:
    from picamera2 import Picamera2
except ImportError:
    logger.error(
        "Nie mozna zaimportowac picamera2. "
        "Zainstaluj: sudo apt install python3-picamera2 "
        "i uruchom venv z --system-site-packages"
    )
    sys.exit(1)


class KameraRPi:
    """Wrapper kamery Picamera2 z watkowym przechwytywaniem klatek i AWB fix.

    Daemon thread przechwytuje klatki YUV420 z Picamera2 lores stream,
    konwertuje do BGR (NV12 probe first, fallback YUV420p) i udostepnia
    przez odczytaj() z lockiem. Dwuetapowy AWB fix eliminuje niebieska
    poswiate sensora IMX219: ColourGains ustawiane w konfiguracji (klatka 0)
    i ponownie po 2s warmup z rzeczywistymi gains z metadata sensora.
    """

    def __init__(
        self, szerokosc: int = LORES_WIDTH, wysokosc: int = LORES_HEIGHT
    ) -> None:
        """Inicjalizuje KameraRPi bez uruchamiania kamery.

        Args:
            szerokosc: Szerokosc klatki lores w pikselach (domyslnie 320).
            wysokosc: Wysokosc klatki lores w pikselach (domyslnie 240).
        """
        self._szerokosc = szerokosc
        self._wysokosc = wysokosc
        self._picam2: Optional[Picamera2] = None
        self._klatka: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running: bool = False
        self._watek: Optional[threading.Thread] = None
        self._format_zweryfikowany: bool = False

    def start(self) -> None:
        """Inicjalizuje kamere, wykonuje dwuetapowy AWB fix i uruchamia daemon thread.

        Etap 1: ColourGains w create_video_configuration() — neutralne od klatki 0.
        Etap 2: Po AWB_WARMUP_DELAY — capture_metadata() + set_controls() z rzeczywistymi gains.
        Fallback na AWB_FALLBACK_GAINS gdy metadata zwroci None lub (0.0, 0.0).
        Po AWB: uruchom daemon thread _petla_przechwytywania.
        """
        self._picam2 = Picamera2()

        # Etap 1: ColourGains w konfiguracji — eliminuje niebieska poswiate od klatki 0
        konfiguracja = self._picam2.create_video_configuration(
            lores={"size": (self._szerokosc, self._wysokosc), "format": "YUV420"},
            controls={"ColourGains": AWB_FALLBACK_GAINS}
        )
        self._picam2.configure(konfiguracja)
        self._picam2.start()
        logger.info(
            f"Picamera2 uruchomiona: {self._szerokosc}x{self._wysokosc} YUV420 "
            f"(wstepne ColourGains: R={AWB_FALLBACK_GAINS[0]:.2f}, B={AWB_FALLBACK_GAINS[1]:.2f})"
        )

        # Etap 2: Warmup AWB — czekaj na stabilizacje i odczytaj rzeczywiste gains
        logger.info(f"Czekam na stabilizacje AWB ({AWB_WARMUP_DELAY}s)...")
        time.sleep(AWB_WARMUP_DELAY)

        metadata = self._picam2.capture_metadata()
        gains = metadata.get("ColourGains") if metadata else None

        if gains is None or gains == (0.0, 0.0):
            logger.warning(
                f"ColourGains niedostepne w metadata — uzywam fallback "
                f"(R={AWB_FALLBACK_GAINS[0]:.2f}, B={AWB_FALLBACK_GAINS[1]:.2f})"
            )
            gains = AWB_FALLBACK_GAINS

        # Zablokuj ColourGains na odczytanych wartosciach
        self._picam2.set_controls({"ColourGains": (float(gains[0]), float(gains[1]))})
        r, b = gains
        logger.info(f"ColourGains zablokowane: (R={r:.2f}, B={b:.2f})")

        # Uruchom daemon thread przechwytywania
        self._running = True
        self._watek = threading.Thread(
            target=self._petla_przechwytywania, daemon=True, name="kamera-rpi"
        )
        self._watek.start()

    def _petla_przechwytywania(self) -> None:
        """Daemon thread: przechwytuje klatki YUV420 i konwertuje do BGR.

        Probuje najpierw COLOR_YUV2BGR_NV12 (Bookworm moze zwracac NV12),
        przy bledzie fallback na COLOR_YUV420p2BGR. Przy bledach kamery
        probuje ponownej inicjalizacji do CAMERA_MAX_RETRIES razy.
        """
        _retry_count: int = 0

        while self._running:
            try:
                klatka_yuv = self._picam2.capture_array("lores")
                _retry_count = 0  # reset po udanym przechwyceniu

                # Konwersja YUV420 → BGR: probe NV12 first (Bookworm), fallback YUV420p
                try:
                    klatka = cv2.cvtColor(klatka_yuv, cv2.COLOR_YUV2BGR_NV12)
                except cv2.error:
                    klatka = cv2.cvtColor(klatka_yuv, cv2.COLOR_YUV420p2BGR)

                # Weryfikacja formatu — loguj shape raz przy pierwszej klatce
                if not self._format_zweryfikowany:
                    logger.info(
                        f"Format klatki zweryfikowany: shape={klatka.shape}, dtype={klatka.dtype}"
                    )
                    self._format_zweryfikowany = True

                # Zapisz klatke pod lockiem
                with self._lock:
                    self._klatka = klatka

            except Exception as e:
                _retry_count += 1
                logger.error(f"Blad kamery ({_retry_count}/{CAMERA_MAX_RETRIES}): {e}")

                if _retry_count >= CAMERA_MAX_RETRIES:
                    logger.error("Kamera niedostepna — zatrzymanie petli przechwytywania")
                    self._running = False
                    break

                # Proba ponownej inicjalizacji kamery
                try:
                    self._picam2.stop()
                    self._picam2.close()
                except Exception:
                    pass

                time.sleep(CAMERA_RETRY_DELAY)

                try:
                    self._picam2 = Picamera2()
                    konfiguracja = self._picam2.create_video_configuration(
                        lores={"size": (self._szerokosc, self._wysokosc), "format": "YUV420"},
                        controls={"ColourGains": AWB_FALLBACK_GAINS}
                    )
                    self._picam2.configure(konfiguracja)
                    self._picam2.start()
                    logger.info("Kamera ponownie uruchomiona po bledzie")
                except Exception as blad_reinit:
                    logger.error(f"Ponowna inicjalizacja nieudana: {blad_reinit}")
                continue

            time.sleep(0.001)  # minimalne usspienie — oddaj czas procesora

    def odczytaj(self) -> Optional[np.ndarray]:
        """Zwraca aktualna klatke BGR (thread-safe, kopia).

        Returns:
            Klatka BGR jako np.ndarray lub None jezeli kamera jeszcze nie dostarczyla klatki.
        """
        with self._lock:
            return self._klatka.copy() if self._klatka is not None else None

    def zatrzymaj(self) -> None:
        """Zatrzymuje daemon thread i zamyka kamera (dwuetapowe: stop() + close()).

        Czeka na zakonczenie watku z timeout=2.0s.
        """
        self._running = False

        if self._watek is not None:
            self._watek.join(timeout=2.0)

        if self._picam2 is not None:
            try:
                self._picam2.stop()
                self._picam2.close()
            except Exception as e:
                logger.warning(f"Blad przy zamykaniu kamery: {e}")
            self._picam2 = None

        logger.info("Kamera zatrzymana")
