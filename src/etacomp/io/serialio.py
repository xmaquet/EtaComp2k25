from __future__ import annotations

import re
import threading
import time
from typing import Optional, Callable

import serial
from serial.tools import list_ports


# regex qui attrape le premier nombre (accepte , comme séparateur décimal)
FLOAT_PATTERN = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


def list_serial_ports() -> list[str]:
    """Retourne les noms de ports série disponibles (ex: COM3, COM7)."""
    ports = []
    for p in list_ports.comports():
        ports.append(p.device)
    return ports


class SerialConnection:
    """Wrapper simple autour de pyserial.Serial."""
    def __init__(self):
        self._ser: Optional[serial.Serial] = None

    def open(self, port: str, baudrate: int = 115200, timeout: float = 0.2):
        """Ouvre la connexion série sur le port demandé."""
        self.close()
        self._ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)

    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def close(self):
        """Ferme la connexion proprement."""
        try:
            if self._ser and self._ser.is_open:
                self._ser.close()
        finally:
            self._ser = None

    def readline(self) -> Optional[str]:
        """Lit une ligne (str) ou None si rien reçu."""
        if not self.is_open():
            return None
        try:
            raw = self._ser.readline()
            if not raw:
                return None
            return raw.decode(errors="ignore").strip()
        except Exception:
            return None


class SerialReaderThread:
    """
    Thread qui lit en continu sur une SerialConnection et appelle un callback
    avec chaque ligne brute reçue + une valeur numérique optionnelle extraite.
    """

    def __init__(self, conn: SerialConnection, on_line: Callable[[str, Optional[float]], None]):
        self._conn = conn
        self._on_line = on_line
        self._stop = threading.Event()
        self._th: Optional[threading.Thread] = None

    def start(self):
        """Démarre le thread de lecture."""
        self._stop.clear()
        if self._th and self._th.is_alive():
            return
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()

    def stop(self):
        """Arrête le thread."""
        self._stop.set()
        if self._th:
            self._th.join(timeout=1.0)
        self._th = None

    def _parse_float(self, text: str) -> Optional[float]:
        """Tente d’extraire un float de la ligne brute."""
        m = FLOAT_PATTERN.search(text)
        if not m:
            return None
        token = m.group(0).replace(",", ".")
        try:
            return float(token)
        except ValueError:
            return None

    def _run(self):
        while not self._stop.is_set():
            line = self._conn.readline()
            if line is None:
                time.sleep(0.01)
                continue
            val = self._parse_float(line)
            try:
                self._on_line(line, val)
            except Exception:
                # on ignore les erreurs du callback
                pass
