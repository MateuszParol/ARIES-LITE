#!/usr/bin/env python3
"""
Punkt wejścia Test Trackera v1.6 — standalone, bez Flaska.

Użycie:
    python3 run_test_tracker.py
    python3 run_test_tracker.py --debug

Na RPi4:
    sudo pigpiod
    python3 run_test_tracker.py --debug
"""

import sys
import signal
import logging
import argparse

from src.modes.test_tracker import TestTracker

logger = logging.getLogger("run_test_tracker")

tracker: TestTracker = None


def _obsluga_sygnalu(signum, frame):
    """Handler SIGINT / SIGTERM — czyste zamknięcie."""
    nazwa = signal.Signals(signum).name
    logger.info(f"Otrzymano sygnał {nazwa} — zatrzymywanie...")
    if tracker is not None:
        tracker.zatrzymaj()
    sys.exit(0)


def main():
    global tracker

    parser = argparse.ArgumentParser(description="ARIES-LITE Test Tracker")
    parser.add_argument("--debug", action="store_true", help="Ustaw log level na DEBUG (PID per-tick logi)")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    signal.signal(signal.SIGINT, _obsluga_sygnalu)
    signal.signal(signal.SIGTERM, _obsluga_sygnalu)

    if args.debug:
        logger.info("Tryb DEBUG aktywny — PID per-tick logi widoczne")

    logger.info("=== ARIES-LITE Test Tracker v1.6 ===")

    tracker = TestTracker()
    try:
        tracker.uruchom()
    finally:
        tracker.zatrzymaj()


if __name__ == "__main__":
    main()
