from __future__ import annotations
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, Signal

from ..models.session import Session, MeasureSeries
from ..config.prefs import load_prefs
from ..io.storage import list_sessions, load_session_file, save_session_file


class SessionStore(QObject):
    session_changed = Signal(Session)     # métadonnées changées / session chargée
    measures_updated = Signal(Session)    # séries/mesures modifiées
    saved = Signal(Path)                  # fichier de sauvegarde écrit

    def __init__(self):
        super().__init__()
        self._current: Session = self._new_session_from_prefs()

    def _new_session_from_prefs(self) -> Session:
        prefs = load_prefs()
        return Session(
            operator="",
            series_count=prefs.default_series_count,
            measures_per_series=prefs.default_measures_per_series,
        )

    def new_session(self):
        self._current = self._new_session_from_prefs()
        self.session_changed.emit(self._current)

    @property
    def current(self) -> Session:
        return self._current

    def update_metadata(
        self,
        operator: str,
        temperature_c: float | None,
        humidity_pct: float | None,
        comparator_ref: str | None,
        series_count: int,
        measures_per_series: int,
        observations: str | None,
    ):
        s = self._current
        s.operator = operator
        s.temperature_c = temperature_c
        s.humidity_pct = humidity_pct
        s.comparator_ref = comparator_ref
        s.series_count = series_count
        s.measures_per_series = measures_per_series
        s.observations = observations
        self.session_changed.emit(s)

    def set_series(self, series: List[MeasureSeries]):
        self._current.series = series
        self.measures_updated.emit(self._current)

    def add_or_replace_series(self, index: int, series: MeasureSeries):
        cur = self._current.series
        while len(cur) <= index:
            cur.append(MeasureSeries(target=0.0, readings=[]))
        cur[index] = series
        self.measures_updated.emit(self._current)

    def can_save(self) -> bool:
        return self._current.has_measures()

    def save(self) -> Path:
        if not self.can_save():
            raise RuntimeError("Impossible d’enregistrer : aucune mesure.")
        p = save_session_file(self._current)
        self.saved.emit(p)
        return p

    def list_history(self):
        return list_sessions()

    def load_from_file(self, path: Path):
        self._current = load_session_file(path)
        self.session_changed.emit(self._current)
        self.measures_updated.emit(self._current)


session_store = SessionStore()
