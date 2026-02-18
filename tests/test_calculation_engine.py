import math
from src.etacomp.models.session import SessionV2, Series, SeriesKind, Direction, Measurement
from src.etacomp.core.calculation_engine import CalculationEngine


def make_session_full():
    targets = [0.0, 1.0, 2.0]
    # S1 up: measured = target + 0.01
    s1 = Series(
        index=1, kind=SeriesKind.MAIN, direction=Direction.UP,
        targets_mm=list(targets),
        measurements=[Measurement(t, t + 0.01, Direction.UP, 1, i, "2025-01-01T00:00:00Z") for i, t in enumerate(targets)]
    )
    # S2 down: measured = target - 0.02
    s2 = Series(
        index=2, kind=SeriesKind.MAIN, direction=Direction.DOWN,
        targets_mm=list(targets),
        measurements=[Measurement(t, t - 0.02, Direction.DOWN, 2, i, "2025-01-01T00:00:00Z") for i, t in enumerate(targets)]
    )
    # S3 up: measured = target + 0.02
    s3 = Series(
        index=3, kind=SeriesKind.MAIN, direction=Direction.UP,
        targets_mm=list(targets),
        measurements=[Measurement(t, t + 0.02, Direction.UP, 3, i, "2025-01-01T00:00:00Z") for i, t in enumerate(targets)]
    )
    # S4 down: measured = target - 0.01
    s4 = Series(
        index=4, kind=SeriesKind.MAIN, direction=Direction.DOWN,
        targets_mm=list(targets),
        measurements=[Measurement(t, t - 0.01, Direction.DOWN, 4, i, "2025-01-01T00:00:00Z") for i, t in enumerate(targets)]
    )
    # Fidelity (S5): at target 2.0, direction UP, samples with small spread
    s5 = Series(
        index=5, kind=SeriesKind.FIDELITY, direction=Direction.UP,
        targets_mm=[2.0],
        measurements=[Measurement(2.0, v, Direction.UP, 5, i, "2025-01-01T00:00:00Z") for i, v in enumerate([2.00, 2.01, 1.99, 2.00, 2.00])]
    )
    sess = SessionV2(
        schema_version=1, session_id="test", created_at_iso="2025-01-01T00:00:00Z",
        operator="op", temperature_c=None, humidity_rh=None,
        comparator_ref="REF", comparator_snapshot={"targets": targets, "graduation": 0.01, "course": 2.0, "range_type": "normale", "reference": "REF"},
        notes="", series=[s1, s2, s3, s4, s5]
    )
    return sess


def test_engine_full_session():
    sess = make_session_full()
    eng = CalculationEngine()
    res = eng.compute(sess)
    # Means: up mean error = +0.015 ; down mean error = -0.015
    assert math.isclose(res.hysteresis_max_mm, 0.03, rel_tol=1e-6)
    assert res.total_error_mm > 0
    # Fidelity std exists
    assert res.fidelity_std_mm is not None
    assert res.fidelity_context is not None


def test_engine_partial_session():
    sess = make_session_full()
    # Drop S3/S4 to simulate partial
    sess.series = [s for s in sess.series if s.index in (1, 2)]
    eng = CalculationEngine()
    res = eng.compute(sess)
    assert res.total_error_mm >= 0
    # Fidelity None
    assert res.fidelity_std_mm is None
    assert res.fidelity_context is None

