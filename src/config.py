"""Plik konfiguracyjny - Główne stałe systemu."""

# --- PID Controller Settings ---
# Należy dostroić te wartości do zachowania konkretnych serwomechanizmów i rozdzielczości klatki
# Wartości bazowe dla systemu na serwach MG-90S:
PID_PAN_P = 0.05
PID_PAN_I = 0.001
PID_PAN_D = 0.005

PID_TILT_P = 0.05
PID_TILT_I = 0.001
PID_TILT_D = 0.005

# --- Limity Skanowania i Ruchu Serw (Kąty) ---
# MG-90S normalnie wspiera od -90 do 90. 
# Zawężono zakres dla bezpieczeństwa taśmy od kamery
PAN_LIMIT_MIN = -60
PAN_LIMIT_MAX = 60

TILT_LIMIT_MIN = -30
TILT_LIMIT_MAX = 30

# Krok (skok w stopniach) używany podczas skanowania i safe-startu (dla płynności działania pętli opóźnionej)
SERVO_STEP = 1.0

# --- Kamera ---
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# --- Ścieżki i Pliki ---
TEMP_FACES_DIR = "tmp_faces"
DEFAULT_TARGET_IMAGE = "target.jpg"

# --- Zmienne Czasowe Skanowania ---
TIME_TO_LOST_SEC = 2.0  # Jak długo czekamy (w klatkach bez celu) by przejść na Skanowanie

# --- Definicje Stanu Systemu ---
STATE_SAFE_START = "SAFE_START"
STATE_SCANNING = "SCANNING"
STATE_TRACKING = "TRACKING"
STATE_IDLE = "IDLE"
