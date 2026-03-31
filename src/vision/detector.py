"""Detektor twarzy MediaPipe z sticky tracking dla ARIES-LITE v2.0.

Dostarcza WykrywaczTwarzy — wrapper MediaPipe FaceDetector Tasks API
w trybie VIDEO z synchronicznym detect_for_video() oraz sticky tracking
z 20% histereza (eliminuje migotanie przy 2+ twarzach w kadrze).
"""

import logging
import os
from typing import List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

logger = logging.getLogger(__name__)

# --- Stale modulowe ---
MODEL_PATH: str = "models/blaze_face_short_range.tflite"
MIN_CONFIDENCE: float = 0.5
STICKY_PROG: float = 0.20  # 20% histereza — wymagany wzrost area do przeskoku celu (D-06)


class WykrywaczTwarzy:
    """Wrapper MediaPipe FaceDetector — Tasks API, tryb VIDEO z sticky tracking.

    Wykrywa twarze w klatkach BGR 320x240 uzywajac modelu BlazeFace (short range).
    Sticky tracking wybiera najwieksza twarz z 20% histereza — brak migotania
    przy 2+ twarzach w kadrze. Wymaga pliku modelu w MODEL_PATH przed inicjalizacja.
    """

    def __init__(
        self, model_path: str = MODEL_PATH, min_confidence: float = MIN_CONFIDENCE
    ) -> None:
        """Inicjalizuje WykrywaczTwarzy — laduje model MediaPipe FaceDetector.

        Args:
            model_path: Sciezka do pliku modelu .tflite.
            min_confidence: Minimalny prog pewnosci detekcji (0.0-1.0).

        Raises:
            FileNotFoundError: Gdy plik modelu nie istnieje pod model_path.
        """
        # Walidacja istnienia pliku modelu — czytelny blad przy braku modelu
        if not os.path.isfile(model_path):
            raise FileNotFoundError(
                f"Model MediaPipe nie znaleziony: {model_path}. "
                f"Pobierz: wget https://storage.googleapis.com/mediapipe-models/"
                f"face_detector/blaze_face_short_range/float16/1/"
                f"blaze_face_short_range.tflite -P models/"
            )

        # Konfiguracja FaceDetector — tryb VIDEO dla synchronicznego detect_for_video()
        opcje = mp_vision.FaceDetectorOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=mp_vision.RunningMode.VIDEO,
            min_detection_confidence=min_confidence,
        )
        self._detektor = mp_vision.FaceDetector.create_from_options(opcje)

        # Stan sticky tracking
        self._sticky_bbox: Optional[Tuple[int, int, int, int]] = None

        logger.info(f"MediaPipe FaceDetector zaladowany: {model_path}")

    def wykryj(
        self, klatka_bgr: np.ndarray, timestamp_ms: int
    ) -> List[Tuple[int, int, int, int]]:
        """Wykrywa twarze w klatce BGR. Zwraca liste bbox (x, y, w, h) w pikselach.

        Konwertuje BGR→RGB (MediaPipe wymaga RGB), wywoluje detect_for_video()
        i mapuje wyniki na liste pikselowych wspolrzednych bounding box.
        Bounding box Tasks API jest w pikselach (nie normalizowany).

        Args:
            klatka_bgr: Klatka OpenCV w formacie BGR.
            timestamp_ms: Monotoniczny timestamp w milisekundach (musi rosnac miedzy klatkami).

        Returns:
            Lista krotek (x, y, w, h) w pikselach dla kazdej wykrytej twarzy.
            Pusta lista gdy brak detekcji lub wystapit blad.
        """
        try:
            # Konwersja BGR → RGB — MediaPipe wymaga RGB (Pitfall 2)
            klatka_rgb = cv2.cvtColor(klatka_bgr, cv2.COLOR_BGR2RGB)

            # Utworz obiekt mp.Image z danych RGB
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=klatka_rgb)

            # Synchroniczna detekcja — blokuje do uzyskania wyniku
            wynik = self._detektor.detect_for_video(mp_image, timestamp_ms)

            # Mapowanie wynikow na liste pikselowych bbox
            twarze: List[Tuple[int, int, int, int]] = []
            for det in wynik.detections:
                bb = det.bounding_box
                # origin_x/y, width, height — wspolrzedne pikselowe (Tasks API)
                twarze.append((bb.origin_x, bb.origin_y, bb.width, bb.height))

            return twarze

        except Exception as e:
            logger.error(f"Blad detekcji MediaPipe: {e}")
            return []

    def wybierz_twarz(
        self, twarze: List[Tuple[int, int, int, int]]
    ) -> Optional[Tuple[int, int, int, int]]:
        """Sticky tracking — wybiera najwieksza twarz z 20% histereza.

        Jezeli brak twarzy: resetuje sticky i zwraca None.
        Jezeli brak poprzedniego celu: wybiera natychmiast najwieksza twarz.
        Przeskakuje na nowy cel TYLKO gdy jest o STICKY_PROG% wiekszy od aktualnego.
        Jezeli sticky zniknal z kadru: trzyma ostatnia znana pozycje (hold przez 1 klatke).

        Args:
            twarze: Lista bbox (x, y, w, h) z metody wykryj().

        Returns:
            Wybrany bbox (x, y, w, h) lub None gdy brak twarzy.
        """
        # Brak twarzy — reset sticky i zwroc None
        if not twarze:
            self._sticky_bbox = None
            return None

        # Oblicz area kazdej twarzy (w * h)
        obszary = [w * h for (x, y, w, h) in twarze]
        idx_max = obszary.index(max(obszary))
        twarz_max = twarze[idx_max]

        # Brak poprzedniego celu — ustaw i zwroc natychmiast
        if self._sticky_bbox is None:
            self._sticky_bbox = twarz_max
            return twarz_max

        area_sticky = self._sticky_bbox[2] * self._sticky_bbox[3]
        area_max = obszary[idx_max]

        # Przeskocz na nowy cel tylko gdy wyraznie wiekszy (o STICKY_PROG%)
        if area_max > area_sticky * (1.0 + STICKY_PROG):
            logger.debug(
                f"Sticky switch: area {area_sticky} → {area_max} "
                f"(wzrost {(area_max / area_sticky - 1.0) * 100:.1f}%)"
            )
            self._sticky_bbox = twarz_max
            return twarz_max

        # Szukaj aktualnej pozycji sticky bbox wsrod wykrytych twarzy
        # Kryteria: najblizszy srodek do poprzedniego srodka sticky
        sx = self._sticky_bbox[0] + self._sticky_bbox[2] // 2
        sy = self._sticky_bbox[1] + self._sticky_bbox[3] // 2

        najblizszy_dist = float("inf")
        najblizszy_bbox: Optional[Tuple[int, int, int, int]] = None

        for twarz in twarze:
            tx = twarz[0] + twarz[2] // 2
            ty = twarz[1] + twarz[3] // 2
            dist = (tx - sx) ** 2 + (ty - sy) ** 2
            if dist < najblizszy_dist:
                najblizszy_dist = dist
                najblizszy_bbox = twarz

        # Jezeli znaleziono bliska twarz — aktualizuj wspolrzedne sticky
        if najblizszy_bbox is not None:
            self._sticky_bbox = najblizszy_bbox
            return najblizszy_bbox

        # Sticky zniknal z kadru — trzymaj ostatnia znana pozycje (hold)
        return self._sticky_bbox

    def zamknij(self) -> None:
        """Zamyka detektor i zwalnia zasoby TFLite."""
        self._detektor.close()
        logger.info("MediaPipe FaceDetector zamkniety")
