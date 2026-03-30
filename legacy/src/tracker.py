import time
import logging
from simple_pid import PID
from typing import Tuple, Optional
from . import config
from .hardware import PanTiltSystem

logger = logging.getLogger(__name__)

class TrackerMachine:
    """
    Maszyna Stanow dla Systemu Sledzenia.
    Zajmuje sie oblczeniami PID i koordynowaniem stanow kamery.
    """
    
    def __init__(self):
        self.hardware = PanTiltSystem()
        self.state = config.STATE_SAFE_START
        self.is_running = True
        
        # PID Controller (Cel to srodek ekranu czyli 0 roznicy)
        self.pid_pan = PID(config.PID_PAN_P, config.PID_PAN_I, config.PID_PAN_D, setpoint=0)
        # Ograniczenie maksymalnej szybkosci korekcji (stopnie na klatke) aby uniknac skoku przy nowym boxie
        self.pid_pan.output_limits = (-10, 10) 

        self.pid_tilt = PID(config.PID_TILT_P, config.PID_TILT_I, config.PID_TILT_D, setpoint=0)
        self.pid_tilt.output_limits = (-10, 10)
        
        self.last_target_time = time.time()
        self.scan_step_pan = config.SERVO_STEP
        self.scan_step_tilt = config.SERVO_STEP / 2.0  # Tilt wolniej
        
        # Ustaw początkowe kąty jako logiczne 0 bez wysterowania jeszcze serwa
        self.target_pan = 0.0
        self.target_tilt = 0.0

    def start_pipeline(self):
        """Uruchamia safe-start i przechodzi w stan SCANNING"""
        logger.info("Faza Safe-Start: Wyrownywanie polozenia")
        self.hardware.smooth_move_to(0, 0, delay=0.03)
        self.target_pan = 0.0
        self.target_tilt = 0.0
        self.state = config.STATE_SCANNING
        self.last_target_time = time.time()

    def do_scan(self):
        """Plynne machanie glowa Lewo-Prawo po osi X az do konca limitow, potem zmiana Y"""
        self.target_pan += self.scan_step_pan
        
        if self.target_pan >= config.PAN_LIMIT_MAX or self.target_pan <= config.PAN_LIMIT_MIN:
            self.scan_step_pan *= -1 # Wroc z powrotem na osi x
            self.target_tilt += self.scan_step_tilt # ruszyc leciutko glowa w osi Y na koncu machniecia
            
            if self.target_tilt >= config.TILT_LIMIT_MAX or self.target_tilt <= config.TILT_LIMIT_MIN:
                self.scan_step_tilt *= -1
                
        self.hardware.set_angles(self.target_pan, self.target_tilt)

    def do_tracking(self, bbox: Tuple[int, int, int, int], frame_w: int, frame_h: int):
        """
        Logika dwuosiowego algorytmu (PID)
        Otrzymuje boxa, odnajduje srodek i przelicza blad. 
        """
        x, y, w, h = bbox
        obj_cx = x + w // 2
        obj_cy = y + h // 2
        
        # Center of frame
        frame_cx = frame_w // 2
        frame_cy = frame_h // 2
        
        # Wyliczenie roznicy
        error_pan = obj_cx - frame_cx
        error_tilt = obj_cy - frame_cy
        
        # Przelicz przez PID (- bo odwracamy wektor bledu na kierunek skretu by go zniwelowac)
        pan_correction = -self.pid_pan(error_pan)
        tilt_correction = self.pid_tilt(error_tilt)
        
        self.target_pan = self.hardware.pan_angle + pan_correction
        self.target_tilt = self.hardware.tilt_angle + tilt_correction
        
        self.hardware.set_angles(self.target_pan, self.target_tilt)

    def logic_tick(self, bbox: Optional[Tuple[int, int, int, int]], w: int, h: int, is_target: bool):
        """
        Metoda tickowana co klatkę. Maszyna stanów.
        """
        if self.state == config.STATE_SAFE_START:
            return  # Czekamy az proces z maina zainicjuje smooth start synchronicznie

        if self.state == config.STATE_IDLE:
            return
            
        if bbox is not None:
            # Zostal wykryty jakikolwiek obiekt twarzopodobny box.
            # Przed przejściem do Targetu powinnismy miec flage is_target
            if is_target:
                self.state = config.STATE_TRACKING
                self.last_target_time = time.time()
                self.do_tracking(bbox, w, h)
            else:
                # Nie chcemy ciagle skanowac na oslep jesli znalezlismy czlowieka (byc moze to nasz target, daj mu zweryfikowac).
                # Jesli tracker trzyma boxa a to nie target, mozemy zdecydowac - skanowac dalej, lub stanac w miejscu.
                # W tym podejsciu stanmy "wzrokiem" na obcym przez chwile by pozwolic algorytmowi dlib spokojnie przemielic rgb.
                self.last_target_time = time.time() 
        else:
            # Nikogo nie ma
            if time.time() - self.last_target_time > config.TIME_TO_LOST_SEC:
                if self.state != config.STATE_SCANNING:
                    logger.info("Target Lost. Przechodzenie w tryb Skanowania.")
                self.state = config.STATE_SCANNING
                self.do_scan()
