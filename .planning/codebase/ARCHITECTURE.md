# ARCHITECTURE.md — System Architecture Analysis

> Generated: 2026-03-18 | Source: main.py, src/, web/server.py

## High-Level Pattern
**Multithreaded monolith** with 4 concurrent threads sharing state via locks and global variables. No message queue or event bus — direct object references.

## Threading Model

```
Main Thread          Logic Thread (daemon)     Camera Thread (daemon)    Vision Thread (daemon)
─────────────        ─────────────────────     ──────────────────────    ─────────────────────
Flask app.run()      main_loop():              VideoStream.update():     heavy_task():
 ├─ GET /            ├─ stream.read()          └─ loop: stream.read()    └─ face_recognition
 ├─ GET /video_feed  ├─ vision.process_frame()                              .face_encodings()
 ├─ POST /upload     ├─ tracker.logic_tick()                                .compare_faces()
 ├─ GET /api/state   ├─ HUD overlay (cv2)
 └─ POST /api/cmd    └─ encode → shared_encoded_frame
```

## Data Flow

1. **Camera → VideoStream**: Continuous async frame capture (daemon thread)
2. **VideoStream → HybridVision.process_frame()**: Per-frame processing
   - HAAR cascade detection (~30 FPS)
   - CSRT tracker update (if tracking)
   - Async dlib verification trigger (spawns Vision thread)
3. **HybridVision → TrackerMachine.logic_tick()**: State machine transition
   - SAFE_START → SCANNING → TRACKING → IDLE
4. **TrackerMachine → PanTiltSystem**: PID-computed servo angles
5. **Logic thread → shared_encoded_frame**: JPEG-encoded HUD frame
6. **Flask /video_feed → Client**: MJPEG multipart stream

## Synchronization
- `shared_frame_lock` (threading.Lock): Guards encoded frame between logic thread and Flask generator
- `_async_lock` (threading.Lock): Guards target_encoding and verification results in HybridVision
- `_verifying_task_active` (bool flag): Prevents concurrent dlib verification threads

## Module Dependency Graph

```
main.py
  └─ web/server.py (Flask app + main_loop)
       ├─ src/camera.py (VideoStream)
       ├─ src/vision.py (HybridVision)
       │    └─ face_recognition / cv2
       ├─ src/tracker.py (TrackerMachine)
       │    ├─ src/hardware.py (PanTiltSystem)
       │    │    └─ gpiozero / pigpio
       │    └─ simple_pid (PID)
       └─ src/config.py (constants)
```

## State Machine (TrackerMachine)

```
SAFE_START ──smooth_move_to(0,0)──→ SCANNING
     ↑                                  │
     │                          bbox detected
     │                                  ↓
   cmd:START                     [wait for dlib]
     │                                  │
   IDLE ←──cmd:STOP──── TRACKING ←──is_target=True
     │                      │
     │                  2s timeout
     └──────────────→ SCANNING
```

## Key Architectural Decisions
1. **Globals in server.py**: stream, vision, tracker are module-level globals shared between Flask routes and logic thread
2. **Mock mode**: PanTiltSystem auto-degrades when pigpio unavailable (dev on non-RPi)
3. **No graceful shutdown**: daemon threads die with main process, no cleanup hooks
4. **Synchronous Flask**: Single werkzeug thread for HTTP, MJPEG generator blocks per-client
