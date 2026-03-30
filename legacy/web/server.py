import time
import cv2
import threading
import signal
from typing import Generator
from flask import Flask, render_template, Response, request, jsonify
from werkzeug.utils import secure_filename
import os
import logging

from src.camera import VideoStream
from src.vision import HybridVision
from src.tracker import TrackerMachine
from src import config

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.TEMP_FACES_DIR
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Wspoldzielone instancje
stream = None
vision = None
tracker = None
shared_frame_lock = threading.Lock()
shared_encoded_frame = None
init_event = threading.Event()

def require_init():
    """Zwraca odpowiedz 503 jesli system nie jest jeszcze zainicjalizowany, None jesli gotowy."""
    if not init_event.is_set():
        return jsonify({"error": "System uruchamia sie..."}), 503
    return None

def shutdown():
    """Graceful shutdown — zatrzymuje watki, zwalnia kamere, odlacza serwa."""
    logger.info("Rozpoczynam graceful shutdown...")
    if tracker is not None:
        tracker.is_running = False
    if stream is not None:
        stream.stop()
    if tracker is not None:
        tracker.hardware.detach_servos()
    logger.info("Shutdown zakończony.")

def generate_frames() -> Generator[bytes, None, None]:
    """Generates JPEG boundaries for Multipart MJPEG stream"""
    global shared_encoded_frame
    while True:
        with shared_frame_lock:
            if shared_encoded_frame is None:
                continue
            frame_bytes = shared_encoded_frame.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    """Glowy widok Panelu. Wymagane utworzenie pliku web/templates/index.html"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """MJPEG endpoint"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/upload_target', methods=['POST'])
def upload_target():
    """API dla wgrania nowego pliku"""
    guard = require_init()
    if guard is not None:
        return guard
    if 'file' not in request.files:
        return jsonify({"error": "Brak pliku"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Pusty plik"}), 400
        
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Podmain w locie w module wizyjnym
    success = vision.load_target_image(filepath)
    if success:
        return jsonify({"status": "OK", "msg": "Target wgrany i zaaplikowany!"})
    else:
        return jsonify({"error": "Zdjecie nie zawiera twarzy badz jest uszkodzone."}), 400

@app.route('/api/state')
def get_state():
    """Pobieranie aktualnego stanu serwera do odswiezania zakladki HUD na zywo z frontu"""
    guard = require_init()
    if guard is not None:
        return guard
    return jsonify({"state": tracker.state})

@app.route('/api/command', methods=['POST'])
def handle_command():
    guard = require_init()
    if guard is not None:
        return guard
    data = request.json
    cmd = data.get('cmd')
    if cmd == 'CENTER':
        logger.info("Powrot do Centrum")
        tracker.state = config.STATE_IDLE
        threading.Thread(target=tracker.hardware.smooth_move_to, args=(0, 0), daemon=True).start()
    elif cmd == 'START':
        tracker.state = config.STATE_SCANNING
    elif cmd == 'STOP':
        tracker.state = config.STATE_IDLE
        tracker.hardware.detach_servos()
    return jsonify({"status": "OK"})

def main_loop():
    """Watek wykonujący pętlę logiki czasu rzeczywistego (przechwytywanie z kamery, logika, sterowanie)"""
    global shared_encoded_frame
    
    # Start maszyn
    stream.start()
    tracker.start_pipeline()
    init_event.set()

    # Load default if exists
    default_img = os.path.join(app.config['UPLOAD_FOLDER'], config.DEFAULT_TARGET_IMAGE)
    if os.path.exists(default_img):
        vision.load_target_image(default_img)
        
    frame_w = int(stream.stream.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(stream.stream.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    while tracker.is_running:
        frame = stream.read()
        if frame is None:
            time.sleep(0.01)
            continue
            
        display_frame = frame.copy()
        
        # Odtwarzaj wizje
        bbox, is_target = vision.process_frame(frame)
        
        # Pchaj stan do logiki sledzenia (PID + Skanowanie)
        tracker.logic_tick(bbox, frame_w, frame_h, is_target)
        
        # Rysuj ramki HUD
        if bbox is not None:
            x, y, w, h = bbox
            color = (0, 255, 0) if is_target else (0, 0, 255)
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(display_frame, "Target" if is_target else "Unknown", (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        
        # Celownik
        cx, cy = frame_w // 2, frame_h // 2
        cv2.drawMarker(display_frame, (cx, cy), (255, 0, 0), cv2.MARKER_CROSS, 20, 2)
        
        # Napis UI
        cv2.putText(display_frame, f"STATUS: {tracker.state}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    
        # Encode To HTTP
        ret, buffer = cv2.imencode('.jpg', display_frame)
        if ret:
            with shared_frame_lock:
                shared_encoded_frame = buffer
                
        time.sleep(1/config.CAMERA_FPS)

def start_server_and_logic():
    global stream, vision, tracker
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    stream = VideoStream()
    vision = HybridVision()
    tracker = TrackerMachine()
    
    logic_thread = threading.Thread(target=main_loop, daemon=True)
    logic_thread.start()

    # Rejestracja signal handlers dla graceful shutdown
    signal.signal(signal.SIGINT, lambda s, f: shutdown())
    signal.signal(signal.SIGTERM, lambda s, f: shutdown())

    # Odpalamy strone we Flasku, to blokuje glowny watek (nasluch 0.0.0.0 pozwala dzialac po wifi RPi)
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    finally:
        shutdown()
