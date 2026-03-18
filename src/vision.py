import cv2
import face_recognition
import numpy as np
import logging
import os
import threading
from typing import Tuple, Optional, Any

logger = logging.getLogger(__name__)

class HybridVision:
    """
    Podejscie hybrydowe do sledzenia:
    1. Szybki detektor kaskadowy HAAR (szuka kazdej twarzy) ~30FPS na RPi
    2. Tracker CSRT (lub KCF) slepą plamkę śledzi bez uzycia AI dla plynnego PID'a.
    3. Asynchronicznie odpytywane `face_recognition` z HOG pobrane raz na "N" klatek, 
       by zweryfikowac, czy to "Ten konkretny Target".
    """
    
    def __init__(self):
        # Zaladowanie klasyfikatora HAAR
        haar_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(haar_path)
        
        self.target_encoding = None
        self.tracker = None
        self.is_tracking = False
        self.target_verified = False  # Jesli true, to sledzony BBOX jest naszym celem
        
        self._async_lock = threading.Lock()
        self._verifying_task_active = False

    def load_target_image(self, image_path: str) -> bool:
        """Laduje zdjecie by wyciagnac z niego DNA twarzy (encoding). Zwraca True jesli sie udalo."""
        if not os.path.exists(image_path):
            logger.warning(f"Brak pliku referencyjnego: {image_path}")
            return False
            
        try:
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                with self._async_lock:
                    self.target_encoding = encodings[0]
                    self.target_verified = False # Reset status po nowym uploadzie
                logger.info(f"Nowy wzorzec ({image_path}) wczytany poprawnie.")
                return True
            else:
                logger.error("Nie wykryto twarzy na zdjeciu wzorcowym!")
                return False
        except Exception as e:
            logger.error(f"Blad przy ladowaniu wzorca: {e}")
            return False

    def init_tracker(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]):
        """Odpala szybki tracker do wiodacego boxa."""
        self.tracker = cv2.TrackerCSRT_create()  # lub cv2.TrackerKCF_create() dla slabszych pi
        self.tracker.init(frame, bbox)
        self.is_tracking = True
        self.target_verified = False # Na razie nie wiemy czy jest swoj czy wrog
        
    def stop_tracker(self):
        self.is_tracking = False
        self.tracker = None
        self.target_verified = False

    def process_frame(self, frame: np.ndarray) -> Tuple[Optional[Tuple[int, int, int, int]], bool]:
        """
        Główna logika hybrydowa przetwarzajaca 1 klatke.
        Zwraca listę z: (BBOX(x,y,w,h), czy_to_target)
        """
        # 1. Jesli Mamy Tracker wlaczony, aktualizujemy go najpierw
        if self.is_tracking and self.tracker is not None:
            success, bbox = self.tracker.update(frame)
            if success:
                bbox = tuple(map(int, bbox))
                # W asynchronicznym procesie wywolywana jest metoda Verify_Target.
                # Do czasu ukonczenia zwracamy box + wynik dotychczasowy
                return bbox, self.target_verified
            else:
                self.stop_tracker() # Gubi cel
                
        # 2. Jesli tracker nic nie widzi -> szukamy jakiejkolwiek twarzy szybkim HAAR.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        
        if len(faces) > 0:
            # Wez pierwsza/najwieksza i odpal tracker
            (x, y, w, h) = faces[0]
            bbox = (x, y, w, h)
            self.init_tracker(frame, bbox)
            
            # Jak tylko zlokalizujemy kandydata, asynchronicznie prosimy o Heavy dlib verify.
            self.trigger_async_verification(frame.copy(), bbox)
            return bbox, False
            
        return None, False

    def trigger_async_verification(self, frame_copy: np.ndarray, bbox: Tuple[int, int, int, int]):
        """Odpala kosztowny algorytm wyciagania wektorow bez zamrazania HUD-a i sterowania PID"""
        def heavy_task():
            with self._async_lock:
                if self.target_encoding is None:
                    self._verifying_task_active = False
                    return
                # face_recognition oczekuje w RGB i y1, x2, y2, x1 (top, right, bottom, left)
                x, y, w, h = bbox
                rgb_frame = cv2.cvtColor(frame_copy, cv2.COLOR_BGR2RGB)
                box_dlib = [(y, x + w, y + h, x)]
                
                try:
                    encodings = face_recognition.face_encodings(rgb_frame, box_dlib)
                    if encodings:
                        # Porównaj dystans, standardowo tolerancja 0.6
                        match = face_recognition.compare_faces([self.target_encoding], encodings[0], tolerance=0.55)[0]
                        self.target_verified = match
                    else:
                        self.target_verified = False
                except Exception as e:
                    logger.error(f"Verify thread exception: {e}")
                finally:
                    self._verifying_task_active = False

        if not self._verifying_task_active:
            self._verifying_task_active = True
            t = threading.Thread(target=heavy_task)
            t.daemon = True
            t.start()
