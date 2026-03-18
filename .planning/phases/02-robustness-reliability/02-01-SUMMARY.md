---
phase: 2
plan: 1
name: "Robustness & Reliability Fixes"
status: complete
---

# Summary: 02-01 Robustness & Reliability Fixes

## What was built
Three independent robustness fixes in `web/server.py`:

1. **Graceful Shutdown (REQ-13)**: `shutdown()` function sets `tracker.is_running = False`, calls `stream.stop()`, calls `tracker.hardware.detach_servos()`. Signal handlers for SIGINT/SIGTERM registered. `app.run()` wrapped in try/finally.

2. **Non-blocking CENTER (REQ-15)**: `smooth_move_to(0,0)` call in handle_command() replaced with `threading.Thread(target=..., daemon=True).start()` — Flask thread returns immediately.

3. **Init Gate (REQ-16)**: `init_event = threading.Event()` at module level. `require_init()` guard returns 503 JSON on all API routes during startup. `init_event.set()` called in `main_loop()` after `stream.start()` and `tracker.start_pipeline()`.

## Key files
- **modified**: `web/server.py` — all three fixes

## Deviations
None. `main.py` was not modified as `start_server_and_logic()` already handles signal registration and shutdown.

## Self-Check: PASSED
- `grep "signal.SIGINT" web/server.py` → found
- `grep "def shutdown" web/server.py` → found
- `grep "detach_servos" web/server.py` → found in shutdown
- `grep "stream.stop" web/server.py` → found in shutdown
- `grep "threading.Thread" web/server.py` → found for CENTER
- `grep "init_event" web/server.py` → 3 matches (decl, set, check)
- `grep "503" web/server.py` → found
