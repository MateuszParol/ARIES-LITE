---
phase: 2
name: "Robustness & Reliability"
type: plan
plan_number: 1
wave: 1
autonomous: true
status: draft
requirement_ids: [REQ-13, REQ-15, REQ-16]
files_modified: [web/server.py]
---

# Plan 02-01: Robustness & Reliability Fixes

<objective>
Implement three independent robustness fixes in web/server.py: graceful shutdown via signal handlers (REQ-13), non-blocking CENTER command (REQ-15), and initialization gate for Flask routes (REQ-16). All three prevent real-world failures on Raspberry Pi deployment.
</objective>

## Tasks

### Task 1: Graceful Shutdown via Signal Handler (REQ-13)
- **File**: `web/server.py`
- **What**: Add `shutdown()` function that stops tracker, releases camera, detaches servos. Register SIGINT/SIGTERM handlers. Wrap `app.run()` in try/finally.
- **Why**: Without this, Ctrl+C leaves servos powered (overheating risk) and camera locked.

### Task 2: Non-blocking CENTER Command (REQ-15)
- **File**: `web/server.py`
- **What**: Replace synchronous `smooth_move_to(0,0)` in handle_command() with `threading.Thread(target=..., daemon=True).start()`
- **Why**: smooth_move_to blocks up to 2 seconds, freezing the Flask request thread.

### Task 3: Initialization Gate for Flask Routes (REQ-16)
- **File**: `web/server.py`
- **What**: Add `init_event = threading.Event()` at module level. Set it in main_loop() after startup. Add `require_init()` guard returning 503 to all API routes.
- **Why**: Race condition — requests arriving before globals are assigned crash with AttributeError.

## Acceptance Criteria
- `shutdown()` function with `detach_servos()` + `stream.stop()`
- Signal handlers registered for SIGINT/SIGTERM
- CENTER command spawns background thread
- `init_event` guards all API routes with 503 during startup
