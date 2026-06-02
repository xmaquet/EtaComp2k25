from __future__ import annotations
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, Signal

from datetime import datetime

from ..models.session import Session, MeasureSeries, FidelitySeries
from ..config.prefs import load_prefs
from ..core.campaign_cycles import clamp_series_count, MAX_CAMPAIGN_CYCLES
from ..io.storage import list_sessions, load_session_file, save_session_file


class SessionStore(QObject):
    session_changed = Signal(Session)     # métadonnées changées / session chargée
    measures_updated = Signal(Session)    # séries/mesures modifiées
    saved = Signal(Path)                  # fichier de sauvegarde écrit

    def __init__(self):
        super().__init__()
        self._current: Session = self._new_session_from_prefs()
        self._cycles_clamped_on_load = False

    def _new_session_from_prefs(self) -> Session:
        prefs = load_prefs()
        return Session(
            operator="",
            date=datetime.now(),
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
        holder_ref: str | None,
        banc_ref: str | None,
        series_count: int,
        measures_per_series: int,
        observations: str | None,
    ):
        s = self._current
        s.operator = operator
        s.temperature_c = temperature_c
        s.humidity_pct = humidity_pct
        s.comparator_ref = comparator_ref
        s.holder_ref = holder_ref
        s.banc_ref = banc_ref
        cycles, _ = clamp_series_count(series_count)
        s.series_count = cycles
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

    # ----- Série de fidélité (S5) -----
    def set_fidelity(self, target: float, direction: str, samples: list[float], timestamps: list[str] | None = None):
        """Enregistre la série de 5 mesures (fidélité) au point critique."""
        from ..core.session_adapter import build_session_from_runtime
        from ..core.calculation_engine import CalculationEngine
        from ..core.critical_point import CriticalPoint

        rt = self._current
        v2 = build_session_from_runtime(rt)
        v2.series = [s for s in v2.series if s.kind.value != "fidelity"]
        calc = CalculationEngine().compute(v2)
        loc = calc.total_error_location or {}
        if loc:
            cp = CriticalPoint(
                target_mm=float(loc["target_mm"]),
                direction=loc["direction"],
                measured_mm=float(loc.get("measured_mm", loc["target_mm"])),
                reference_mm=float(loc.get("reference_mm", loc["target_mm"])),
                error_mm=float(loc.get("error_mm", 0.0)),
            )
        else:
            cp = None
        if cp is not None:
            target = cp.target_mm
            direction = cp.direction
        self._current.fidelity = FidelitySeries(
            target=float(target),
            direction="up" if str(direction).lower().startswith("u") else "down",
            samples=[float(x) for x in (samples or [])],
            timestamps=list(timestamps or []),
        )
        self.measures_updated.emit(self._current)

    def clear_fidelity(self):
        self._current.fidelity = None
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
        loaded = load_session_file(path)
        requested = loaded.series_count
        cycles, clamped = clamp_series_count(requested)
        loaded.series_count = cycles
        self._cycles_clamped_on_load = clamped
        self._current = loaded
        self.session_changed.emit(self._current)
        self.measures_updated.emit(self._current)

    def consume_cycles_clamp_warning(self) -> bool:
        """True une fois si le dernier chargement a dû réduire series_count."""
        if self._cycles_clamped_on_load:
            self._cycles_clamped_on_load = False
            return True
        return False


session_store = SessionStore()
