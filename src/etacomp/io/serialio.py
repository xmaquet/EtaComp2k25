from __future__ import annotations

import re
import threading
import time
from typing import Optional, Callable

import serial
from serial.tools import list_ports

def list_serial_ports() -> list[str]:
    return [p.device for p in list_ports.comports()]

class SerialConnection:
    """Wrapper pyserial robuste (Windows/Arduino/RS232-friendly)."""
    def __init__(self):
        self._ser: Optional[serial.Serial] = None

    def open(self, port: str, baudrate: int = 4800, timeout: float = 0.05):
        self.close()
        self._ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,           # court = boucle réactive
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        try:
            # certains adaptateurs aiment DTR/RTS actifs
            self._ser.setDTR(True)
            self._ser.setRTS(True)
        except Exception:
            pass
        # Laisse le temps à un éventuel reboot (Arduino, afficheur)
        time.sleep(1.0)
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
        if not self.is_open():
            return None
        try:
            n = self._ser.in_waiting
            if n:
                return self._ser.read(n)
            b = self._ser.read(1)
            return b if b else None
        except Exception:
            return None

    def write_text(self, s: str, append_eol: Optional[bytes] = None):
        if not self.is_open():
            return
        try:
            data = s.encode()
            if append_eol:
                data += append_eol
            self._ser.write(data)
            self._ser.flush()
        except Exception:
            pass

    def write_bytes(self, b: bytes):
        if not self.is_open():
            return
        try:
            self._ser.write(b)
            self._ser.flush()
        except Exception:
            pass


class SerialReaderThread:
    """
    Lit en continu, assemble des lignes (CR/LF/CRLF), et parse selon config ASCII.
    - on_line(raw_text, parsed_float_or_None)
    - on_debug(msg), on_error(msg)
    """
    def __init__(
        self,
        conn: SerialConnection,
        on_line: Callable[[str, Optional[float]], None],
        on_debug: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_raw: Optional[Callable[[bytes], None]] = None,
        *,
        regex_pattern: str = r"[-+]?\d+(?:[.,]\d+)?",
        decimal_comma: bool = False,
    ):
        self._conn = conn
        self._on_line = on_line
        self._on_debug = on_debug
        self._on_error = on_error
        self._on_raw = on_raw
        self._stop = threading.Event()
        self._th: Optional[threading.Thread] = None
        self._buf = bytearray()
        # config ASCII
        self._pattern = re.compile(regex_pattern)
        self._decimal_comma = decimal_comma

    def start(self):
        self._stop.clear()
        if self._th and self._th.is_alive():
            return
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()
        self._dbg("SerialReaderThread started")

    def stop(self):
        self._stop.set()
        if self._th:
            self._th.join(timeout=1.0)
        self._th = None
        self._dbg("SerialReaderThread stopped")

    def _dbg(self, msg: str):
        if self._on_debug:
            try: self._on_debug(msg)
            except Exception: pass

    def _err(self, msg: str):
        if self._on_error:
            try: self._on_error(msg)
            except Exception: pass

    def _emit_lines_from_buffer(self):
        if not self._buf:
            return
        data = self._buf.replace(b"\r\n", b"\n")
        parts = []
        start = 0
        for i, b in enumerate(data):
            if b in (0x0A, 0x0D):
                if i > start:
                    parts.append(data[start:i])
                start = i + 1
        remainder = data[start:] if start < len(data) else b""
        for chunk in parts:
            try:
                text = chunk.decode(errors="ignore").strip()
            except Exception as e:
                self._err(f"decode error: {e!r}")
                text = ""
            if text:
                val = self._parse_float(text)
                try:
                    self._on_line(text, val)
                except Exception as e:
                    self._err(f"on_line callback error: {e!r}")
        self._buf = bytearray(remainder)

    def _parse_float(self, text: str) -> Optional[float]:
        # 1) Essai avec le motif configuré
        m = self._pattern.search(text)
        token = m.group(0) if m else None

        # 2) Fallback robuste: tolère espace après signe et préfère un nombre avec partie entière si dispo
        if token is None or token.lstrip(" +-").startswith((".", ",")) or " " in (token or ""):
            candidates = re.findall(r"[+-]?\s*(?:\d*[.,]\d+|\d+)", text)
            if candidates:
                # Nettoyage (supprimer espaces internes avant conversion)
                cleaned = [c.replace(" ", "") for c in candidates if c and c.strip()]
                # Heuristique de sélection:
                # - privilégier ceux avec au moins un chiffre avant la virgule/point
                def has_int_part(s: str) -> bool:
                    s2 = s.lstrip("+-")
                    if "," in s2 or "." in s2:
                        intp = s2.split("," if "," in s2 else ".")[0]
                        return any(ch.isdigit() for ch in intp)
                    return True  # nombres entiers
                with_int = [s for s in cleaned if has_int_part(s)]
                pool = with_int if with_int else cleaned
                # - parmi eux, éviter 0/0.00 si d'autres existent
                def magnitude(s: str) -> float:
                    try:
                        x = float(s.replace(",", "."))
                        return abs(x)
                    except Exception:
                        return -1.0
                nonzero = [s for s in pool if magnitude(s) > 0.0]
                pool2 = nonzero if nonzero else pool
                # - enfin, choisir le plus long (plus d'information)
                token = max(pool2, key=len)

        if not token:
            return None

        token = token.replace(" ", "")
        if self._decimal_comma:
            token = token.replace(",", ".")
        try:
            return float(token)
        except ValueError:
            return None

    def _run(self):
        try:
            while not self._stop.is_set():
                chunk = self._conn.read_chunk()
                if chunk:
                    if self._on_raw:
                        try:
                            self._on_raw(chunk)
                        except Exception:
                            pass
                    self._buf.extend(chunk)
                    self._emit_lines_from_buffer()
                else:
                    time.sleep(0.01)
        except Exception as e:
            self._err(f"serial thread crash: {e!r}")
