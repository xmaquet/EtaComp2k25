import math

from src.etacomp.core.critical_point import find_critical_point, fidelity_matches_critical
from src.etacomp.core.calculation_engine import CalculationEngine
from src.etacomp.models.session import (
    SessionV2, Series, SeriesKind, Direction, Measurement,
)
from tests.test_calculation_engine import make_session_full


def test_critical_point_tiebreak_prefers_opposite_direction():
    """À |erreur| égal, le sens avec la plus grande erreur opposée l'emporte."""
    cp = find_critical_point(
        targets=[1.0],
        up_errors=[(1.0, 0.015)],
        down_errors=[(1.0, -0.010)],
    )
    assert cp is not None
    assert cp.direction == "up"
    assert math.isclose(cp.error_mm, 0.015, rel_tol=1e-9)


def test_fidelity_wrong_target_is_indeterminate():
    sess = make_session_full()
    # S5 sur mauvaise cible (2.0) alors que le critique est 1.0 montée
    sess.series = [s for s in sess.series if s.index != 5]
    sess.series.append(
        Series(
            index=5, kind=SeriesKind.FIDELITY, direction=Direction.UP,
            targets_mm=[2.0],
            measurements=[
                Measurement(2.0, v, Direction.UP, 5, i, "2025-01-01T00:00:00Z")
                for i, v in enumerate([2.0, 2.01, 1.99, 2.0, 2.0])
            ],
        )
    )
    res = CalculationEngine().compute(sess)
    assert res.fidelity_std_mm is None
    assert res.fidelity_context is None


def test_fidelity_wrong_direction_is_indeterminate():
    sess = make_session_full()
    sess.series = [s for s in sess.series if s.index != 5]
    sess.series.append(
        Series(
            index=5, kind=SeriesKind.FIDELITY, direction=Direction.DOWN,
            targets_mm=[1.0],
            measurements=[
                Measurement(1.0, v, Direction.DOWN, 5, i, "2025-01-01T00:00:00Z")
                for i, v in enumerate([0.99, 0.98, 1.0, 0.99, 1.0])
            ],
        )
    )
    res = CalculationEngine().compute(sess)
    assert res.fidelity_std_mm is None


def test_fidelity_matches_critical_helper():
    from src.etacomp.core.critical_point import CriticalPoint

    cp = CriticalPoint(1.0, "up", 1.015, 1.0, 0.015)
    assert fidelity_matches_critical(cp, target_mm=1.0, direction="up")
    assert not fidelity_matches_critical(cp, target_mm=2.0, direction="up")
    assert not fidelity_matches_critical(cp, target_mm=1.0, direction="down")
