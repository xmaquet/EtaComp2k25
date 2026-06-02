"""Issue #9 — fermeture propre du port série et arrêt du thread lecteur."""

import threading
import time
from unittest.mock import MagicMock

from src.etacomp.io.serial_manager import SerialManager


class _FakeReader:
    def __init__(self):
        self._stop = threading.Event()
        self._th: threading.Thread | None = None
        self.stopped = False

    def start(self):
        self._stop.clear()
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()

    def _run(self):
        while not self._stop.is_set():
            time.sleep(0.02)

    def stop(self):
        self.stopped = True
        self._stop.set()
        if self._th:
            self._th.join(timeout=1.0)
        self._th = None


def test_serial_manager_close_joins_reader_and_closes_conn():
    mgr = SerialManager()
    conn = mgr._conn
    conn.open = MagicMock()
    conn.is_open = MagicMock(return_value=True)
    conn.close = MagicMock()
    conn.read_chunk = MagicMock(return_value=None)

    reader = _FakeReader()
    reader.start()
    mgr._reader = reader

    emitted: list[bool] = []
    mgr.connected_changed.connect(lambda v: emitted.append(v))

    mgr.close()

    conn.close.assert_called_once()
    assert mgr._reader is None
    assert reader._th is None or not reader._th.is_alive()
    assert emitted == [False]


def test_tesa_reader_stop_joins_thread():
    from src.etacomp.io.tesa_reader import TesaSerialReader

    class _Conn:
        def read_chunk(self):
            time.sleep(0.05)
            return None

    reader = TesaSerialReader(_Conn(), on_value=lambda *a: None)
    reader.start()
    th = reader._th
    assert th is not None and th.is_alive()
    reader.stop()
    assert reader._th is None
    assert not th.is_alive()
