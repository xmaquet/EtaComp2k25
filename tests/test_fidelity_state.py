"""Issue #8 — pas de fuite de S5 entre sessions via _last_fidelity."""

from src.etacomp.models.session import MeasureSeries
from src.etacomp.state.session_store import SessionStore
from src.etacomp.ui.results_provider import ResultsProvider


def _minimal_main_series():
    return [MeasureSeries(target=0.0, readings=[0.01, -0.01, 0.02, -0.02])]


def test_fidelity_not_leaked_across_sessions_same_comparator():
    """Même comparateur : une nouvelle session ne doit pas réutiliser la S5 précédente."""
    store = SessionStore()
    store._current.comparator_ref = "COMP-A"
    store._current.series = _minimal_main_series()
    store._current.series_count = 2
    store.set_fidelity(
        1.0,
        "up",
        [1.0, 1.01, 0.99, 1.0, 1.0],
        ["2025-01-01T00:00:00Z"] * 5,
    )

    prov = ResultsProvider()
    _, res_with, _ = prov.compute_all(store.current)
    assert res_with.fidelity_std_mm is not None

    store.new_session()
    store._current.comparator_ref = "COMP-A"
    store._current.series = [MeasureSeries(target=0.0, readings=[0.01, -0.01])]
    store._current.series_count = 1

    _, res_fresh, _ = prov.compute_all(store.current)
    assert res_fresh.fidelity_std_mm is None
    assert store.current.fidelity is None


def test_fidelity_persisted_in_current_session():
    store = SessionStore()
    store._current.comparator_ref = "COMP-B"
    store._current.series = _minimal_main_series()
    store._current.series_count = 2
    store.set_fidelity(0.0, "up", [0.0, 0.001, -0.001, 0.0, 0.0], [])

    _, res, _ = ResultsProvider().compute_all(store.current)
    assert res.fidelity_std_mm is not None


def test_remember_fidelity_removed():
    assert not hasattr(ResultsProvider(), "remember_fidelity")
