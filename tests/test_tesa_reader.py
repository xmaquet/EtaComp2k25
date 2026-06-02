"""Issue #6 — conservation du signe des valeurs série."""

import math

from src.etacomp.io.tesa_reader import TesaSerialReader
from src.etacomp.core.calculation_engine import CalculationEngine
from src.etacomp.models.session import (
    SessionV2,
    Series,
    SeriesKind,
    Direction,
    Measurement,
)


class _DummyConn:
    def read_chunk(self):
        return b""


def test_tesa_reader_extracts_negative_value():
    captured: list[float] = []

    reader = TesaSerialReader(
        _DummyConn(),
        on_value=lambda v, *_: captured.append(v),
        decimals=3,
    )
    reader._emit_frame(b"-0.015\r\n")
    reader._emit_frame(b"+1.250\r\n")

    assert len(captured) == 2
    assert captured[0] == -0.015
    assert captured[1] == 1.25


def test_signed_readings_error_is_measured_minus_target():
    """Erreur signée = mesuré − cible ; |Emt| pour le verdict."""
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
        session_id="sign-test",
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
    loc = res.total_error_location
    assert loc is not None
    assert math.isclose(loc["error_mm"], -0.015, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(res.total_error_mm, 0.015, rel_tol=0, abs_tol=1e-9)
