#!/usr/bin/env python3
"""
Punkt wejścia Test Trackera v1.6 — standalone, bez Flaska.

Użycie:
    python3 run_test_tracker.py

Na RPi4:
    sudo pigpiod
    python3 run_test_tracker.py
"""

import sys
import signal
import logging

from src.modes.test_tracker import TestTracker

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
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

    signal.signal(signal.SIGINT, _obsluga_sygnalu)
    signal.signal(signal.SIGTERM, _obsluga_sygnalu)

    logger.info("=== ARIES-LITE Test Tracker v1.6 ===")

    tracker = TestTracker()
    try:
        tracker.uruchom()
    finally:
        tracker.zatrzymaj()


if __name__ == "__main__":
    main()
