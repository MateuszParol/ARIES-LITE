"""Detektor twarzy OpenCV DNN (res10_300x300 SSD) z sticky tracking dla ARIES-LITE v2.1.

Dostarcza WykrywaczTwarzy — wrapper OpenCV DNN Caffe SSD
z synchronicznym forward() oraz sticky tracking
z 20% histereza (eliminuje migotanie przy 2+ twarzach w kadrze).

Zastepuje MediaPipe FaceDetector — eliminuje zaleznosc od mediapipe
ktora nie wspiera Python 3.13 na aarch64.
"""

import logging
import os
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# --- Stale modulowe ---
PROTOTXT_PATH: str = "models/deploy.prototxt"
CAFFEMODEL_PATH: str = "models/res10_300x300_ssd_iter_140000.caffemodel"
MIN_CONFIDENCE: float = 0.5
STICKY_PROG: float = 0.20  # 20% histereza — wymagany wzrost area do przeskoku celu (D-06)


class WykrywaczTwarzy:
    """Wrapper OpenCV DNN res10_300x300 SSD — detekcja twarzy z sticky tracking.

    Wykrywa twarze w klatkach BGR 320x240 uzywajac modelu Caffe SSD.
    Sticky tracking wybiera najwieksza twarz z 20% histereza — brak migotania
    przy 2+ twarzach w kadrze. Wymaga plikow modelu w PROTOTXT_PATH i CAFFEMODEL_PATH.
    """

    def __init__(
        self,
        prototxt_path: str = PROTOTXT_PATH,
        caffemodel_path: str = CAFFEMODEL_PATH,
        min_confidence: float = MIN_CONFIDENCE,
    ) -> None:
        """Inicjalizuje WykrywaczTwarzy — laduje model OpenCV DNN Caffe SSD.

        Args:
            prototxt_path: Sciezka do pliku deploy.prototxt.
            caffemodel_path: Sciezka do pliku caffemodel.
            min_confidence: Minimalny prog pewnosci detekcji (0.0-1.0).

        Raises:
            FileNotFoundError: Gdy pliki modelu nie istnieja.
        """
        for path in (prototxt_path, caffemodel_path):
            if not os.path.isfile(path):
                raise FileNotFoundError(f"Model DNN nie znaleziony: {path}")

        self._net = cv2.dnn.readNetFromCaffe(prototxt_path, caffemodel_path)
        self._min_confidence = min_confidence

        # Stan sledzenia przyklejonego (sticky tracking)
        self._sticky_bbox: Optional[Tuple[int, int, int, int]] = None

        logger.info(f"OpenCV DNN SSD zaladowany: {caffemodel_path}")

    def wykryj(
        self, klatka_bgr: np.ndarray, timestamp_ms: int = 0
    ) -> List[Tuple[int, int, int, int]]:
        """Wykrywa twarze w klatce BGR. Zwraca liste bbox (x, y, w, h) w pikselach.

        Tworzy blob 300x300 z klatki, przepuszcza przez siec DNN
        i filtruje wyniki powyzej min_confidence.

        Args:
            klatka_bgr: Klatka OpenCV w formacie BGR.
            timestamp_ms: Nieuzywany — zachowany dla kompatybilnosci interfejsu z MozgRPi.

        Returns:
            Lista krotek (x, y, w, h) w pikselach dla kazdej wykrytej twarzy.
            Pusta lista gdy brak detekcji lub wystapit blad.
        """
        try:
            h, w = klatka_bgr.shape[:2]

            # Blob 300x300 z normalizacja srednia (104, 177, 123) — standard res10 SSD
            blob = cv2.dnn.blobFromImage(
                klatka_bgr, 1.0, (300, 300), (104.0, 177.0, 123.0)
            )
            self._net.setInput(blob)
            detections = self._net.forward()

            twarze: List[Tuple[int, int, int, int]] = []
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence < self._min_confidence:
                    continue

                # Wspolrzedne znormalizowane 0..1 -> piksele
                x1 = max(0, int(detections[0, 0, i, 3] * w))
                y1 = max(0, int(detections[0, 0, i, 4] * h))
                x2 = min(w, int(detections[0, 0, i, 5] * w))
                y2 = min(h, int(detections[0, 0, i, 6] * h))

                bw = x2 - x1
                bh = y2 - y1
                if bw > 0 and bh > 0:
                    twarze.append((x1, y1, bw, bh))

            return twarze

        except Exception as e:
            logger.error(f"Blad detekcji DNN: {e}")
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
                f"Przelaczenie sticky: obszar {area_sticky} → {area_max} "
                f"(wzrost {(area_max / area_sticky - 1.0) * 100:.1f}%)"
            )
            self._sticky_bbox = twarz_max
            return twarz_max

        # Szukaj aktualnej pozycji celu sticky wsrod wykrytych twarzy
        # Kryterium: najblizszy srodek do poprzedniego srodka celu
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

        # Jezeli znaleziono bliska twarz — aktualizuj wspolrzedne celu sticky
        if najblizszy_bbox is not None:
            self._sticky_bbox = najblizszy_bbox
            return najblizszy_bbox

        # Cel sticky zniknal z kadru — trzymaj ostatnia znana pozycje (hold)
        return self._sticky_bbox

    def zamknij(self) -> None:
        """Zamyka detektor (no-op dla OpenCV DNN — brak zasobow do zwolnienia)."""
        logger.info("OpenCV DNN detektor zamkniety")
