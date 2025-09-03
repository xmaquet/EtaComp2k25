from __future__ import annotations

from typing import Optional, Tuple
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

        # Parsing ASCII
        self._regex_pattern = r"^\s*[+-]?\d+(?:[.,]\d+)?\s*$"
        self._decimal_comma = False

        # Envoi (profil TESA ASCII)
        self._send_mode = "Manuel"   # 'Manuel' | 'À la demande'
        self._trigger_text = "M"
        self._eol_mode = "CR"        # 'Aucun' | 'CR' | 'LF' | 'CRLF'

    # --------- CONFIG PARSE ASCII ---------
    def set_ascii_config(self, *, regex_pattern: str, decimal_comma: bool):
        self._regex_pattern = regex_pattern or r"^\s*[+-]?\d+(?:[.,]\d+)?\s*$"
        self._decimal_comma = bool(decimal_comma)
        if self.is_open():
            self._stop_reader()
            self._start_reader()

    def get_ascii_config(self) -> tuple[str, bool]:
        return self._regex_pattern, self._decimal_comma

    # --------- CONFIG ENVOI (TESA ASCII) ---------
    def set_send_config(self, *, mode: str, trigger_text: str, eol_mode: str):
        self._send_mode = "Manuel" if mode.startswith("Manuel") else "À la demande"
        self._trigger_text = trigger_text or ""
        if eol_mode.startswith("CRLF"):
            self._eol_mode = "CRLF"
        elif eol_mode.startswith("CR "):
            self._eol_mode = "CR"
        elif eol_mode.startswith("LF "):
            self._eol_mode = "LF"
        else:
            self._eol_mode = "Aucun"

    def get_send_config(self) -> Tuple[str, str, str]:
        """Retourne (mode, trigger_text, eol_mode)."""
        return self._send_mode, self._trigger_text, self._eol_mode

    def eol_bytes(self) -> bytes | None:
        if self._eol_mode == "CRLF":
            return b"\r\n"
        if self._eol_mode == "CR":
            return b"\r"
        if self._eol_mode == "LF":
            return b"\n"
        return None

    # --------- ÉTAT ---------
    def is_open(self) -> bool:
        return self._conn.is_open()

    # --------- OPEN/CLOSE ---------
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

    # --------- ENVOI ---------
    def send_text(self, text: str, eol: bytes | None = None):
        self._conn.write_text(text, append_eol=eol)

    # --------- DIAG ---------
    def read_chunk(self) -> bytes | None:
        return self._conn.read_chunk()

    # --------- INTERNE ---------
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


# Singleton global
serial_manager = SerialManager()
