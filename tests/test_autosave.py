"""Issue #14 — sauvegarde automatique minimale."""

from datetime import datetime

import pytest

from src.etacomp.io.storage import AUTOSAVE_FILENAME, save_autosave_session
from src.etacomp.models.session import MeasureSeries, Session


def test_save_autosave_session_writes_file(tmp_path, monkeypatch):
    import src.etacomp.io.storage as storage_mod

    monkeypatch.setattr(storage_mod, "get_data_dir", lambda: tmp_path)
    s = Session(
        operator="op",
        date=datetime(2025, 6, 2, 12, 0, 0),
        series=[MeasureSeries(target=0.0, readings=[0.01])],
    )
    path = save_autosave_session(s)
    assert path is not None
    assert path.name == AUTOSAVE_FILENAME
    assert path.exists()


def test_save_autosave_skips_empty_session(tmp_path, monkeypatch):
    import src.etacomp.io.storage as storage_mod

    monkeypatch.setattr(storage_mod, "get_data_dir", lambda: tmp_path)
    s = Session(operator="op", date=datetime(2025, 6, 2, 12, 0, 0))
    assert save_autosave_session(s) is None
