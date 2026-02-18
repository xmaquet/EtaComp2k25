from src.etacomp.ui.results_provider import ResultsProvider
from src.etacomp.models.session import Session as RuntimeSession, MeasureSeries


def make_runtime_session_basic():
    # Two targets, two cycles (S1..S4 encoded per target in readings)
    # readings[pos]: pos = (cycle-1)*2 + (0 if up else 1)
    targets = [0.0, 1.0]
    series = []
    for t in targets:
        readings = [
            t + 0.01,   # S1 up
            t - 0.01,   # S2 down
            t + 0.02,   # S3 up
            t - 0.02,   # S4 down
        ]
        series.append(MeasureSeries(target=t, readings=readings))
    rt = RuntimeSession(
        operator="test",
        series_count=2,
        measures_per_series=11,
        comparator_ref=None,
        series=series,
    )
    return rt


def test_provider_compute_all_basic():
    rt = make_runtime_session_basic()
    prov = ResultsProvider()
    v2, results, verdict = prov.compute_all(rt)
    assert v2 is not None
    assert results is not None
    # calibration points should reflect our two targets
    assert isinstance(results.calibration_points, list)
    assert len(results.calibration_points) == 2
    # No fidelity series -> std None
    assert results.fidelity_std_mm is None
    # Verdict may be None if no rules file is present
    assert verdict is None or getattr(verdict, "status", None) is not None

