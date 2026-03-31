"""Interfejs szeregowy RPi → Arduino. Protokol ARIES-LITE v1.0."""

import struct
import logging

import serial

logger = logging.getLogger(__name__)


class SerialInterface:
    """Interfejs szeregowy RPi → Arduino. Protokol ARIES-LITE v1.0.

    Klasa OOP opakowujaca pyserial do wysylania ramek binarnych 8B
    zgodnych z PROTOCOL_SPEC.md. Obsluguje otwarcie portu, DTR=False
    (zapobiega resetowi Leonardo), tryb niskich opoznien oraz heartbeat.
    """

    BAUDRATE: int = 115200
    START_MARKER: int = 0xAA
    FRAME_SIZE: int = 8

    def __init__(self, port: str = "/dev/ttyACM0", timeout: float = 1.0) -> None:
        """Inicjalizuje SerialInterface bez otwierania portu.

        Args:
            port: Sciezka do portu szeregowego (domyslnie /dev/ttyACM0).
            timeout: Timeout odczytu w sekundach (domyslnie 1.0 s).
        """
        self._port: str = port
        self._timeout: float = timeout
        self._ser: serial.Serial | None = None

    def open(self) -> None:
        """Otwiera port szeregowy z DTR=False i trybem niskich opoznien.

        DTR=False musi byc ustawione PRZED otwarciem portu — zapobiega
        automatycznemu resetowi Arduino Leonardo przy polaczeniu USB CDC
        (Caterina bootloader). Po otwarciu wlacza tryb niskich opoznien
        przez pyserial 3.5 set_low_latency_mode (TIOCGSERIAL ioctl,
        bez potrzeby sudo ani setserial).

        Raises:
            serial.SerialException: Gdy port nie moze zostac otwarty.
        """
        # Tworz obiekt bez natychmiastowego otwarcia (open=False)
        ser = serial.Serial()
        ser.port = self._port
        ser.baudrate = self.BAUDRATE
        ser.bytesize = serial.EIGHTBITS
        ser.parity = serial.PARITY_NONE
        ser.stopbits = serial.STOPBITS_ONE
        ser.timeout = self._timeout

        # DTR=False PRZED open() — zapobiega resetowi Leonardo (Caterina bootloader)
        ser.dtr = False

        ser.open()

        # Tryb niskich opoznien — pyserial 3.5 wbudowane ioctl (bez subprocess+setserial)
        try:
            ser.set_low_latency_mode(True)
        except ValueError as e:
            logger.warning(
                f"set_low_latency_mode niedostepny na tym systemie: {e}. "
                "Latency moze byc wyzsza."
            )

        self._ser = ser
        logger.info(f"Port {self._port} otwarty @ {self.BAUDRATE} baud.")

    def send_frame(
        self, mode: int, error_x: int, error_y: int, face_size: int
    ) -> None:
        """Wysyla ramke 8B zgodna z PROTOCOL_SPEC.md.

        Args:
            mode: Tryb pracy (0=IDLE, 1=SCAN, 2=TRACK).
            error_x: Blad poziomy w pikselach (int16, -160..+160).
            error_y: Blad pionowy w pikselach (int16, -160..+160).
            face_size: Rozmiar twarzy jako procent * 255/100 (0..255).

        Raises:
            serial.SerialException: Gdy port nie jest otwarty.
        """
        if self._ser is None or not self._ser.is_open:
            raise serial.SerialException("Port nie jest otwarty.")

        ramka = self._buduj_ramke(mode, error_x, error_y, face_size)
        self._ser.write(ramka)

    def send_heartbeat(self) -> None:
        """Wysyla ramke heartbeat (IDLE, wszystkie pola zero).

        Alias na send_frame(mode=0, error_x=0, error_y=0, face_size=0) per D-11.
        Arduino traktuje kazda poprawna ramke jako dowod zywotnosci RPi.
        """
        self.send_frame(mode=0, error_x=0, error_y=0, face_size=0)

    def close(self) -> None:
        """Zamyka port szeregowy jesli jest otwarty."""
        if self._ser and self._ser.is_open:
            self._ser.close()
            logger.info(f"Port {self._port} zamkniety.")
        self._ser = None

    @staticmethod
    def _buduj_ramke(
        mode: int, error_x: int, error_y: int, face_size: int
    ) -> bytes:
        """Buduje 8-bajtowa ramke protokolu ARIES-LITE v1.0.

        Format ramki:
            [0xAA, mode(u8), error_x_lo, error_x_hi, error_y_lo, error_y_hi,
             face_size(u8), checksum(u8)]

        Checksum = XOR bajtow 1-6 (bez start markera 0xAA).

        Args:
            mode: Tryb pracy (0=IDLE, 1=SCAN, 2=TRACK).
            error_x: Blad poziomy (int16 little-endian, -160..+160 px).
            error_y: Blad pionowy (int16 little-endian, -160..+160 px).
            face_size: Rozmiar twarzy 0..255.

        Returns:
            Ramka binarna 8 bajtow.
        """
        # Pakuj payload: mode (uint8), error_x (int16 LE), error_y (int16 LE), face_size (uint8)
        payload = struct.pack('<BhhB', mode, error_x, error_y, face_size)

        # Oblicz checksum XOR bajtow payload (bajty 1-6 pelnej ramki)
        checksum: int = 0
        for bajt in payload:
            checksum ^= bajt

        # Pelna ramka: start marker + payload + checksum
        return bytes([0xAA]) + payload + bytes([checksum])
