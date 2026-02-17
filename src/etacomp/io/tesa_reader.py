from __future__ import annotations

import threading
import time
import re
from typing import Callable, Optional

from .serialio import SerialConnection


class TesaSerialReader:
    """
    Lecteur TESA (mode bouton) avec assemblage de trames par silence inter‑octets ou EOL.

    Callbacks:
    - on_value(value_float, display_str, raw_hex, raw_ascii, timestamp)
    - on_debug(msg)
    - on_error(msg)
    """
    def __init__(
        self,
        conn: SerialConnection,
        *,
        on_value: Callable[[float, str, str, str, float], None],
        on_debug: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        frame_mode: str = "silence",           # "silence" | "eol"
        silence_ms: int = 120,
        eol: str = "CRLF",                     # "CR" | "LF" | "CRLF"
        mask_7bit: bool = True,
        strip_chars: str = "\r\n\0 ",
        value_regex: str = r"[-+]?\d+(?:[.,]\d+)?|[-+]?[.,]\d+",
        decimals: int = 3,
        decimal_display: str = "dot",          # "dot" | "comma"
    ):
        self._conn = conn
        self._on_value = on_value
        self._on_debug = on_debug
        self._on_error = on_error

        self._frame_mode = frame_mode.lower()
        self._silence_s = max(0, float(silence_ms) / 1000.0)
        self._eol_mode = eol.upper()
        self._mask_7bit = bool(mask_7bit)
        self._strip = strip_chars
        self._value_re = re.compile(value_regex)
        self._decimals = int(decimals)
        self._decimal_display = decimal_display

        self._buf = bytearray()
        self._last_rx = 0.0
        self._stop = threading.Event()
        self._th: Optional[threading.Thread] = None

    def start(self):
        if self._th and self._th.is_alive():
            return
        self._stop.clear()
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()
        self._dbg("TesaSerialReader started")

    def stop(self):
        self._stop.set()
        if self._th:
            self._th.join(timeout=1.0)
        self._th = None
        self._dbg("TesaSerialReader stopped")

    # ----- internals -----
    def _dbg(self, m: str):
        if self._on_debug:
            try: self._on_debug(m)
            except Exception: pass

    def _err(self, m: str):
        if self._on_error:
            try: self._on_error(m)
            except Exception: pass

    def _now(self) -> float:
        return time.perf_counter()

    def _emit_frame(self, data: bytes):
        if not data:
            return
        raw_hex = " ".join(f"{b:02X}" for b in data)
        if self._mask_7bit:
            data = bytes((b & 0x7F) for b in data)
        try:
            raw_ascii = data.decode("ascii", errors="replace")
        except Exception:
            raw_ascii = ""
        txt = raw_ascii.strip(self._strip or "")

        # Extraction
        value = None
        m = self._value_re.search(txt)
        if m:
            token = m.group(0).replace(",", ".")
            try:
                value = float(token)
            except Exception:
                value = None

        ts = time.time()
        if value is None:
            self._dbg(f"frame invalid: '{txt}' HEX[{raw_hex}]")
            return

        # Normalisation
        display = f"{value:.{self._decimals}f}"
        try:
            normalized = float(display)
        except Exception:
            normalized = value
        if (self._decimal_display or "dot") == "comma":
            display = display.replace(".", ",")

        try:
            self._on_value(normalized, display, raw_hex, txt, ts)
        except Exception as e:
            self._err(f"on_value failed: {e!r}")

    def _run(self):
        try:
            if self._frame_mode == "eol":
                self._run_eol()
            else:
                self._run_silence()
        except Exception as e:
            self._err(f"tesa thread crash: {e!r}")

    def _run_silence(self):
        self._buf.clear()
        self._last_rx = 0.0
        while not self._stop.is_set():
            chunk = self._conn.read_chunk()
            now = self._now()
            if chunk:
                self._buf.extend(chunk)
                self._last_rx = now
            else:
                if self._buf and self._last_rx and (now - self._last_rx) >= self._silence_s:
                    frame = bytes(self._buf)
                    self._buf.clear()
                    self._emit_frame(frame)
                else:
                    time.sleep(0.005)

    def _eol_bytes(self) -> bytes:
        if self._eol_mode == "CRLF":
            return b"\r\n"
        if self._eol_mode == "CR":
            return b"\r"
        return b"\n"

    def _run_eol(self):
        self._buf.clear()
        term = self._eol_bytes()
        while not self._stop.is_set():
            chunk = self._conn.read_chunk()
            if not chunk:
                time.sleep(0.005)
                continue
            # Appliquer masque si nécessaire avant détection EOL
            if self._mask_7bit:
                chunk = bytes((b & 0x7F) for b in chunk)
            self._buf.extend(chunk)
            while True:
                idx = self._buf.find(term)
                if idx < 0:
                    break
                frame = bytes(self._buf[:idx+len(term)])
                del self._buf[:idx+len(term)]
                self._emit_frame(frame)

