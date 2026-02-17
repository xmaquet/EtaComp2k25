from __future__ import annotations

from typing import Optional, Tuple
from PySide6.QtCore import QObject, Signal

from .serialio import SerialConnection, SerialReaderThread
from .tesa_reader import TesaSerialReader


class SerialManager(QObject):
    connected_changed = Signal(bool)
    line_received = Signal(str, object)   # raw_text, parsed_value (float|None)
    raw = Signal(str)                     # flux brut (décodé latin-1, sans normalisation)
    tesa_value = Signal(float, str, str, str, float)  # value_float, display_str, raw_hex, raw_ascii, ts
    debug = Signal(str)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._conn = SerialConnection()
        self._reader: Optional[SerialReaderThread] = None

        # Parsing ASCII
        self._regex_pattern = r"^\s*[+-]?\s*(?:\d*[.,]\d+|\d+)\s*$"
        self._decimal_comma = False

        # Envoi (profil TESA ASCII)
        self._send_mode = "Manuel"   # 'Manuel' | 'À la demande'
        self._trigger_text = "M"
        self._eol_mode = "CR"        # 'Aucun' | 'CR' | 'LF' | 'CRLF'

        # Debug brut
        self._raw_debug_enabled = False

        # TESA reader config
        self._tesa_enabled = True
        self._tesa_frame_mode = "silence"
        self._tesa_silence_ms = 120
        self._tesa_eol = "CRLF"
        self._tesa_mask7 = True
        self._tesa_strip = "\r\n\0 "
        self._tesa_value_regex = r"[-+]?\d+(?:[.,]\d+)?|[-+]?[.,]\d+"
        self._tesa_decimals = 3
        self._tesa_decimal_display = "dot"

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
        # Rendre l'analyse robuste face aux libellés UI (ex: "CR (\\r)")
        text = (eol_mode or "").strip().upper()
        if "CRLF" in text:
            self._eol_mode = "CRLF"
        elif text.startswith("CR") or "(\\R" in text:  # "CR", "CR (\\r)"
            self._eol_mode = "CR"
        elif text.startswith("LF") or "(\\N" in text:  # "LF", "LF (\\n)"
            self._eol_mode = "LF"
        else:
            self._eol_mode = "Aucun"

    # --------- DEBUG BRUT ---------
    def set_raw_debug(self, enabled: bool):
        """Active/désactive l'émission du flux brut (avant parsing)."""
        self._raw_debug_enabled = bool(enabled)
        if self.is_open():
            self._stop_reader()
            self._start_reader()

    def is_raw_debug(self) -> bool:
        return self._raw_debug_enabled

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
        if self._tesa_enabled:
            self._reader = TesaSerialReader(
                self._conn,
                on_value=self._on_tesa_value,
                on_debug=self.debug.emit,
                on_error=self.error.emit,
                frame_mode=self._tesa_frame_mode,
                silence_ms=self._tesa_silence_ms,
                eol=self._tesa_eol,
                mask_7bit=self._tesa_mask7,
                strip_chars=self._tesa_strip,
                value_regex=self._tesa_value_regex,
                decimals=self._tesa_decimals,
                decimal_display=self._tesa_decimal_display,
            )
        else:
            self._reader = SerialReaderThread(
                self._conn,
                on_line=self._on_line,
                on_debug=self.debug.emit,
                on_error=self.error.emit,
                on_raw=(self._on_raw if self._raw_debug_enabled else None),
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

    def _on_raw(self, data: bytes):
        try:
            s = data.decode('latin-1', errors='ignore')
        except Exception:
            s = repr(data)
        self.raw.emit(s)

    def _on_tesa_value(self, value: float, display: str, raw_hex: str, raw_ascii: str, ts: float):
        # Compatibilité: émettre aussi line_received pour l’UI existante (MeasuresTab)
        self.line_received.emit(raw_ascii, value)
        self.tesa_value.emit(value, display, raw_hex, raw_ascii, ts)

    # --------- TESA Reader config ---------
    def set_tesa_reader_config(
        self,
        *,
        enabled: bool,
        frame_mode: str = "silence",
        silence_ms: int = 120,
        eol: str = "CRLF",
        mask_7bit: bool = True,
        strip_chars: str = "\r\n\0 ",
        value_regex: str = r"[-+]?\d+(?:[.,]\d+)?|[-+]?[.,]\d+",
        decimals: int = 3,
        decimal_display: str = "dot",
    ):
        self._tesa_enabled = bool(enabled)
        self._tesa_frame_mode = (frame_mode or "silence").lower()
        self._tesa_silence_ms = int(silence_ms)
        self._tesa_eol = (eol or "CRLF").upper()
        self._tesa_mask7 = bool(mask_7bit)
        self._tesa_strip = strip_chars or "\r\n\0 "
        self._tesa_value_regex = value_regex or r"[-+]?\d+(?:[.,]\d+)?|[-+]?[.,]\d+"
        self._tesa_decimals = int(decimals)
        self._tesa_decimal_display = (decimal_display or "dot")
        if self.is_open():
            self._stop_reader()
            self._start_reader()


# Singleton global
serial_manager = SerialManager()
