"""Stabilizator stanow SKANOWANIE/SLEDZENIE z histereza dla ARIES-LITE v2.1.

Dostarcza StabilizatorStanow — klase enkapsulujaca logike przejsc miedzy
stanami SKANOWANIE i SLEDZENIE z jednostronna histereza:
- Wejscie w SLEDZENIE: natychmiastowe (DNN wystarczajaco precyzyjny)
- Wyjscie ze SLEDZENIA: dopiero po LOST_THRESHOLD kolejnych klatkach bez detekcji
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

LOST_THRESHOLD: int = 12  # Liczba kolejnych klatek bez detekcji wymagana do przejscia SLEDZENIE->SKANOWANIE (D-04: 10-15 klatek, 12 jako kompromis)


class StabilizatorStanow:
    """Histereza stanow SKANOWANIE/SLEDZENIE dla petli detekcji MozgRPi.

    Implementuje jednostronna histereze: wejscie w SLEDZENIE jest natychmiastowe
    (kazda detekcja DNN >= 0.5 confidence jest wystarczajaca), wyjscie ze SLEDZENIA
    wymaga LOST_THRESHOLD kolejnych klatek bez detekcji.

    Zapobiega migotaniu trybu TX wysylanego do Arduino przy chwilowych brakach
    detekcji (przejscie twarzy przez krawedz kadru, mrugnieciem, chwilowa okluzja).
    """

    TRYB_SKANOWANIE: str = "SKANOWANIE"
    TRYB_SLEDZENIE: str = "SLEDZENIE"

    def __init__(self, prog_utraty: int = LOST_THRESHOLD) -> None:
        """Inicjalizuje StabilizatorStanow w stanie SKANOWANIE.

        Args:
            prog_utraty: Liczba kolejnych klatek bez detekcji wymagana do
                         przejscia ze SLEDZENIA do SKANOWANIA (domyslnie LOST_THRESHOLD=12).
        """
        self._stan: str = self.TRYB_SKANOWANIE
        self._prog_utraty: int = prog_utraty
        self._klatki_bez_twarzy: int = 0

    @property
    def stan(self) -> str:
        """Zwraca aktualny stan (SKANOWANIE lub SLEDZENIE)."""
        return self._stan

    def aktualizuj(self, bbox_wykryty: bool) -> str:
        """Aktualizuje stan na podstawie obecnosci detekcji twarzy.

        Jednostronna histereza:
        - bbox_wykryty=True: natychmiastowe przejscie do SLEDZENIE, reset licznika
        - bbox_wykryty=False: inkrementuj licznik; przejscie do SKANOWANIE tylko
          gdy licznik >= prog_utraty

        Args:
            bbox_wykryty: True jezeli detektor zwrocil bbox w tej klatce, False gdy nie.

        Returns:
            Aktualny stan po aktualizacji (TRYB_SKANOWANIE lub TRYB_SLEDZENIE).
        """
        if bbox_wykryty:
            self._klatki_bez_twarzy = 0
            self._stan = self.TRYB_SLEDZENIE
        else:
            self._klatki_bez_twarzy += 1
            if self._klatki_bez_twarzy >= self._prog_utraty:
                self._stan = self.TRYB_SKANOWANIE

        return self._stan

    def resetuj(self) -> None:
        """Resetuje stabilizator do stanu poczatkowego (SKANOWANIE, licznik=0).

        Uzywany przy restarcie systemu lub gdy wymagane jest pelne zresetowanie stanu.
        """
        self._stan = self.TRYB_SKANOWANIE
        self._klatki_bez_twarzy = 0
        logger.info("StabilizatorStanow: reset do SKANOWANIE")
