import cv2
import threading
import logging
from . import config

logger = logging.getLogger(__name__)

class VideoStream:
    """
    Asynchroniczny menadżer strumienia wideo z kamery uzywający tła (daemon thread).
    Powala to na drastyczne zwiekszenie FPS w OpenCV na RPi (zdejmuje oczekiwanie na I/O z glownego watku).
    """

    def __init__(self, src=config.CAMERA_INDEX):
        self.stream = cv2.VideoCapture(src)
        
        # Opcjonalnie V4L2 backend daje nizsze opoznienie, 
        # cv2.CAP_V4L2 można podać w src: cv2.VideoCapture(src, cv2.CAP_V4L2) - zalezy od os
        
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        self.stream.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
        
        (self.grabbed, self.frame) = self.stream.read()
        self._frame_lock = threading.Lock()
        self.stopped = False
        
        if not self.grabbed:
            logger.error(f"Nie mozna uruchomic kamery z indexem: {src}")

    def start(self):
        """Zaczyna watek odczytu w tle."""
        logger.info("Uruchamianie watku kamery...")
        threading.Thread(target=self.update, args=(), daemon=True).start()
        return self

    def update(self):
        """Petla stale uaktualniajaca klatke plynaca z drivera kamery"""
        while True:
            if self.stopped:
                return
            with self._frame_lock:
                (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        """Pobiera najswiezsza frame"""
        with self._frame_lock:
            return self.frame

    def stop(self):
        """Zwalnia kamere"""
        logger.info("Zamykanie strumienia kamery.")
        self.stopped = True
        self.stream.release()
