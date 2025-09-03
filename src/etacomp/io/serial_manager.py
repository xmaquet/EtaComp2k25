from __future__ import annotations
from typing import Optional, Callable
from PySide6.QtCore import QObject, Signal

from .serialio import SerialConnection, SerialReaderThread

class SerialManager(QObject):
    connected_changed = Signal(bool)
    line_received = Signal(str, object)   # raw_text, parsed_value (float|None)
    debug = Signal(str)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._conn = SerialConnection()
        self._reader: Optional[SerialReaderThread] = None
        # config ASCII
        self._regex_pattern = r"^\s*[+-]?\d+(?:[.,]\d+)?\s*$"
        self._decimal_comma = False

    # ---- config ----
    def set_ascii_config(self, regex_pattern: str, decimal_comma: bool):
        self._regex_pattern = regex_pattern or r"^\s*[+-]?\d+(?:[.,]\d+)?\s*$"
        self._decimal_comma = bool(decimal_comma)
        # si on est déjà en train de lire, redémarrer le thread pour appliquer la config
        if self.is_open():
            self._stop_reader()
            self._start_reader()

    # ---- état ----
    def is_open(self) -> bool:
        return self._conn.is_open()

    # ---- open/close ----
    def open(self, port: str, baudrate: int):
        if self._conn.is_open():
            return
        self._conn.open(port=port, baudrate=baudrate)
        self._start_reader()
        self.connected_changed.emit(True)

    def close(self):
        self._stop_reader()
        self._conn.close()
        self.connected_changed.emit(False)

    # ---- envoi (utile si “à la demande”) ----
    def send_text(self, text: str, eol: bytes | None = None):
        self._conn.write_text(text, append_eol=eol)

    # ---- diag (pour bouton “Test 3 s”) ----
    def read_chunk(self) -> bytes | None:
        return self._conn.read_chunk()

    # ---- interne ----
    def _start_reader(self):
        self._reader = SerialReaderThread(
            self._conn,
            on_line=self._on_line,
            on_debug=self.debug.emit,
            on_error=self.error.emit,
            regex_pattern=self._regex_pattern,
            decimal_comma=self._decimal_comma,
        )
        self._reader.start()

    def _stop_reader(self):
        if self._reader:
            self._reader.stop()
            self._reader = None

    def _on_line(self, raw: str, value: float | None):
        self.line_received.emit(raw, value)


# singleton
serial_manager = SerialManager()
