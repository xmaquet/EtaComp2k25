from __future__ import annotations

import re
import threading
import time
from typing import Optional, Callable

import serial
from serial.tools import list_ports

# Capture le premier nombre; accepte la virgule comme décimal
FLOAT_PATTERN = re.compile(r"[-+]?\d+(?:[.,]\d+)?")

def list_serial_ports() -> list[str]:
    return [p.device for p in list_ports.comports()]

class SerialConnection:
    """Wrapper pyserial avec ouverture robuste (Arduino-friendly)."""
    def __init__(self):
        self._ser: Optional[serial.Serial] = None

    def open(self, port: str, baudrate: int = 4800, timeout: float = 0.05):
        # timeout court pour boucler souvent
        self.close()
        self._ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        # Certains Arduino se réinitialisent; on stabilise la ligne série
        try:
            # Toggle DTR/RTS pour réveiller certains adaptateurs
            self._ser.setDTR(True)
            self._ser.setRTS(True)
        except Exception:
            pass

        time.sleep(1.0)  # laisse le temps au reboot
        try:
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
        except Exception:
            pass

    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def close(self):
        try:
            if self._ser and self._ser.is_open:
                self._ser.close()
        finally:
            self._ser = None

    def read_chunk(self) -> Optional[bytes]:
        """Lit les octets disponibles sans s'arrêter sur la fin de ligne (non bloquant)."""
        if not self.is_open():
            return None
        try:
            n = self._ser.in_waiting  # octets dispo
            if n:
                return self._ser.read(n)
            # sinon, lit 1 octet (timeout court) pour garder la boucle en vie
            b = self._ser.read(1)
            return b if b else None
        except Exception:
            return None


class SerialReaderThread:
    """
    Lit en continu et assemble les lignes par CR/LF.
    Appelle on_line(raw_text, value_float_or_None) à chaque ligne complète.
    """
    def __init__(self, conn: SerialConnection, on_line: Callable[[str, Optional[float]], None]):
        self._conn = conn
        self._on_line = on_line
        self._stop = threading.Event()
        self._th: Optional[threading.Thread] = None
        self._buf = bytearray()

    def start(self):
        self._stop.clear()
        if self._th and self._th.is_alive():
            return
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()

    def stop(self):
        self._stop.set()
        if self._th:
            self._th.join(timeout=1.0)
        self._th = None

    def _emit_lines_from_buffer(self):
        """
        Découpe _buf sur \r ou \n (gère \r, \n, \r\n) et émet les lignes trouvées.
        Conserve l’éventuel fragment final non terminé.
        """
        if not self._buf:
            return
        # Remplace CRLF par LF pour simplifier, puis traite CR restant
        data = self._buf.replace(b"\r\n", b"\n")
        parts = []
        start = 0
        for i, b in enumerate(data):
            if b in (0x0A, 0x0D):  # LF ou CR
                if i > start:
                    parts.append(data[start:i])
                start = i + 1
        # Fragment final (pas encore terminé par CR/LF)
        remainder = data[start:] if start < len(data) else b""
        # Émet les lignes
        for chunk in parts:
            try:
                text = chunk.decode(errors="ignore").strip()
            except Exception:
                text = ""
            if text:
                val = self._parse_float(text)
                try:
                    self._on_line(text, val)
                except Exception:
                    pass
        # Réassigne le buffer au reste non terminé
        self._buf = bytearray(remainder)

    def _parse_float(self, text: str) -> Optional[float]:
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
            chunk = self._conn.read_chunk()
            if chunk:
                self._buf.extend(chunk)
                # Essaie d’extraire des lignes à chaque arrivée de données
                self._emit_lines_from_buffer()
            else:
                # petite pause pour éviter 100% CPU
                time.sleep(0.01)
