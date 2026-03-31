#!/usr/bin/env python3
"""Entry point ARIES-LITE v2.0 — pi_brain: MediaPipe wizja + SerialTX do Arduino."""

import logging
import signal
import sys

from src.vision.brain import MozgRPi

# Konfiguracja loggera — format zgodny z CLAUDE.md ([LEVEL] name: message)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Uruchamia MozgRPi z obsluga sygnalow SIGINT/SIGTERM."""
    logger.info("ARIES-LITE v2.0 — pi_brain start")

    mozg = MozgRPi()

    def _obsluz_sygnal(sig: int, frame) -> None:
        """Handler SIGINT/SIGTERM — graceful shutdown.

        UWAGA: ten handler jest wywolywany z kontekstu glownego watku
        (Python signal handlers sa wykonywane w main thread), ale moze
        przerwac _petla_glowna() miedzy iteracjami. Dlatego mozg.zatrzymaj()
        ustawia self._running = False (thread-safe pod GIL) i ma guard
        _zatrzymano przeciw podwojnemu wywolaniu (signal handler + uruchom()).
        """
        logger.info(f"Sygnal {sig} odebrany — zatrzymuje system...")
        mozg.zatrzymaj()

    signal.signal(signal.SIGINT, _obsluz_sygnal)
    signal.signal(signal.SIGTERM, _obsluz_sygnal)

    try:
        mozg.uruchom()
    except Exception as e:
        logger.error(f"Blad krytyczny: {e}")
        mozg.zatrzymaj()
        sys.exit(1)

    logger.info("ARIES-LITE v2.0 — pi_brain zakonczony")


if __name__ == "__main__":
    main()
