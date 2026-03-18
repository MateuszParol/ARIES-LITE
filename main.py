"""
Smart Pan-Tilt Face Tracker
Wejsciowy punkt startowy aplikacji. Zestawia podzial modulu WEB API dla operatora 
oraz proces czasu real-time, zapobiegajac wieszaniu interfejsu przy obliczeniach obrazu.
"""

from web.server import start_server_and_logic
import logging

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    logger = logging.getLogger("MAIN")
    
    logger.info("Rozgrzewanie algorytmow Smart Face Tracker...")
    # Blokuje main watek serwerem Flask, kamera leci w deamonach
    start_server_and_logic()
