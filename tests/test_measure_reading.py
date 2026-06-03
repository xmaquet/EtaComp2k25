"""Normalisation lectures série → position absolue (régression issue #6 / UI Mesures)."""

import math

from src.etacomp.core.measure_reading import normalize_measured_mm, is_near_origin_mm
from src.etacomp.core.calculation_engine import CalculationEngine
from src.etacomp.models.session import (
    SessionV2,
    Series,
    SeriesKind,
    Direction,
    Measurement,
)


def test_normalize_absolute_position():
    assert math.isclose(normalize_measured_mm(9.003, 9.0), 9.003, abs_tol=1e-9)
    assert math.isclose(normalize_measured_mm(5.992, 6.0), 5.992, abs_tol=1e-9)
    assert math.isclose(normalize_measured_mm(0.006, 0.0), 0.006, abs_tol=1e-9)


def test_zero_at_origin_accepts_small_residual():
    """Banc à ~0.008 mm au repère : accepté pour nouvelle série montée (régression UI)."""
    assert is_near_origin_mm(0.0, 0.0)
    assert is_near_origin_mm(0.008, 0.0)
    assert is_near_origin_mm(-0.003, 0.0)
    assert not is_near_origin_mm(0.904, 0.0)


def test_normalize_signed_relative_reading():
    """Écart signé petit → position = cible + écart (issue #6)."""
    assert math.isclose(normalize_measured_mm(-0.015, 1.0), 0.985, abs_tol=1e-9)
    assert math.isclose(normalize_measured_mm(0.003, 9.0), 9.003, abs_tol=1e-9)


def test_mean_error_matches_february_example():
    """Moyenne ↓ col. 0 : (0.006+0.002)/2 - 0 = 0.004 mm = +4.0 µm."""
    up = [0.006, 0.002]
    target = 0.0
    mean_abs = sum(up) / len(up)
    mean_um = (mean_abs - target) * 1000.0
    assert math.isclose(mean_um, 4.0, abs_tol=0.05)


def test_engine_with_normalized_storage():
    s1 = Series(
        index=1,
        kind=SeriesKind.MAIN,
        direction=Direction.UP,
        targets_mm=[1.0],
        measurements=[
            Measurement(1.0, 0.985, Direction.UP, 1, 0, "2025-01-01T00:00:00Z"),
        ],
    )
    sess = SessionV2(
        schema_version=1,
        session_id="norm-test",
        created_at_iso="2025-01-01T00:00:00Z",
        operator="t",
        temperature_c=None,
        humidity_rh=None,
        comparator_ref="REF",
        comparator_snapshot={},
        notes="",
        series=[s1],
    )
    res = CalculationEngine().compute(sess)
    assert math.isclose(res.total_error_mm, 0.015, abs_tol=1e-9)
