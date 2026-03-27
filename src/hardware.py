import time
import logging
from . import config

try:
    from gpiozero import AngularServo
    from gpiozero.pins.pigpio import PiGPIOFactory
    PIGPIO_AVAILABLE = True
except ImportError:
    PIGPIO_AVAILABLE = False
    logging.warning("gpiozero / pigpio not found. Running in mock hardware mode.")

logger = logging.getLogger(__name__)

class PanTiltSystem:
    def __init__(self, pan_pin: int = 12, tilt_pin: int = 13):
        """
        Klasa reprezentująca cały system zmotoryzowany Pan/Tilt.
        Tworzy instancje serw uzywajac narzedzia pypgio celem uzyskania stabilnego PID-a/H-PWM.
        """
        self.pan_angle = 0.0
        self.tilt_angle = 0.0
        self.pan_servo = None
        self.tilt_servo = None
        self._mock_mode = not PIGPIO_AVAILABLE
        
        if not self._mock_mode:
            try:
                # Wymuszenie fabryki pigpio umozliwia sprzetowy PWM dający idealną gładkość
                factory = PiGPIOFactory()
                self.pan_servo = AngularServo(pan_pin, min_angle=-90, max_angle=90, pin_factory=factory)
                self.tilt_servo = AngularServo(tilt_pin, min_angle=-90, max_angle=90, pin_factory=factory)
                logger.info("Hardware servos with PiGPIO initialized successfully.")
            except Exception as e:
                logger.error(f"Nie mozna uruchomic pigpio. Sprawdz czy dziala demon (sudo pigpiod): {e}")
                self._mock_mode = True
        
        if self._mock_mode:
            logger.info("Uruchamiono obsluge serw w srodowisku okrojonym MOCK (bez pigpio/win32).")

    def set_angles(self, pan: float, tilt: float) -> None:
        """
        Ustawia bezposredni kat na osi X i Y, uwzgledniajac zabezpieczenia (Soft Limits) dla obu osi.
        
        :param pan: Docelowy kąt X (horyzontalnie)
        :param tilt: Docelowy kąt Y (wertykalnie)
        """
        # Obetnij wartości do zadeklarowanych bezpiecznych stref dla kamery RPi
        pan_clamped = max(config.PAN_LIMIT_MIN, min(config.PAN_LIMIT_MAX, pan))
        tilt_clamped = max(config.TILT_LIMIT_MIN, min(config.TILT_LIMIT_MAX, tilt))

        if pan_clamped != pan:
            logger.warning(f"Clamp pan: {pan:.1f} → {pan_clamped:.1f} (limit)")
        if tilt_clamped != tilt:
            logger.warning(f"Clamp tilt: {tilt:.1f} → {tilt_clamped:.1f} (limit)")

        self.pan_angle = pan_clamped
        self.tilt_angle = tilt_clamped
        
        if not self._mock_mode and self.pan_servo and self.tilt_servo:
            self.pan_servo.angle = self.pan_angle
            self.tilt_servo.angle = self.tilt_angle

    def smooth_move_to(self, target_pan: float, target_tilt: float, step: float = config.SERVO_STEP, delay: float = 0.05) -> None:
        """
        Inkrementalnie dociera do odpowiednich wartosci by uniknac szarpniec.
        Opcja glownie sluzaca funkcji "Safe Start". Ta funkcja powstrzyma system w pętli `while` aż do osiągnięcia celu.
        
        :param target_pan: Kąt docelowy Pan
        :param target_tilt: Kąt docelowy Tilt
        """
        logger.info(f"Rozpoczynam inkrementalny (Smooth) ruch z [Pan: {self.pan_angle}, Tilt: {self.tilt_angle}] do [Pan: {target_pan}, Tilt: {target_tilt}]")
        
        while abs(self.pan_angle - target_pan) > step or abs(self.tilt_angle - target_tilt) > step:
            new_pan = self.pan_angle
            new_tilt = self.tilt_angle
            
            # Ruch w strone PANA
            if self.pan_angle < target_pan:
                new_pan = min(self.pan_angle + step, target_pan)
            elif self.pan_angle > target_pan:
                new_pan = max(self.pan_angle - step, target_pan)
                
            # Ruch w strone TILT
            if self.tilt_angle < target_tilt:
                new_tilt = min(self.tilt_angle + step, target_tilt)
            elif self.tilt_angle > target_tilt:
                new_tilt = max(self.tilt_angle - step, target_tilt)
                
            self.set_angles(new_pan, new_tilt)
            time.sleep(delay)
            
        # Wyrownaj ulamki pozostalosci na ostatnim kroku
        self.set_angles(target_pan, target_tilt)

    def attach_servos(self):
        """Podłącza sygnał PWM do pinów zaprogramowanych (powrót po detach)"""
        pass # Optionalne jesli API to umozliwia w prosty sposob

    def detach_servos(self):
        """Odłącza zasilanie/PWM programowe (przydatne przy IDLE/Cleanup) dla schłodzenia"""
        if not self._mock_mode and self.pan_servo and self.tilt_servo:
             self.pan_servo.detach()
             self.tilt_servo.detach()
