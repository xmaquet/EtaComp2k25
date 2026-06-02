import logging

from src.etacomp.core.session_adapter import build_session_from_runtime
from src.etacomp.core.campaign_cycles import MAX_CAMPAIGN_CYCLES
from src.etacomp.models.session import Session as RuntimeSession, MeasureSeries
from src.etacomp.models.session import SeriesKind, Direction


def _runtime_three_cycles():
    targets = [0.0, 1.0]
    series = []
    for t in targets:
        readings = [
            t + 0.01,
            t - 0.01,
            t + 0.02,
            t - 0.02,
            t + 0.03,
            t - 0.03,
        ]
        series.append(MeasureSeries(target=t, readings=readings))
    return RuntimeSession(
        operator="test",
        series_count=3,
        measures_per_series=11,
        series=series,
    )


def test_session_adapter_more_than_two_cycles(caplog):
    rt = _runtime_three_cycles()
    with caplog.at_level(logging.WARNING):
        v2 = build_session_from_runtime(rt)

    main = [s for s in v2.series if s.kind == SeriesKind.MAIN]
    assert len(main) == MAX_CAMPAIGN_CYCLES * 2
    assert {s.index for s in main} == {1, 2, 3, 4}

    for s in main:
        assert len(s.measurements) == 2

    assert any("series_count=3" in r.message for r in caplog.records)
    assert any("ignorée" in r.message for r in caplog.records)


def test_session_adapter_mapping_four_series():
    targets = [0.0, 1.0, 2.0]
    series = []
    for t in targets:
        series.append(
            MeasureSeries(
                target=t,
                readings=[t + 0.01, t - 0.01, t + 0.02, t - 0.02],
            )
        )
    rt = RuntimeSession(operator="t", series_count=2, measures_per_series=11, series=series)
    v2 = build_session_from_runtime(rt)

    main = sorted(
        [s for s in v2.series if s.kind == SeriesKind.MAIN],
        key=lambda s: s.index,
    )
    assert len(main) == 4
    assert main[0].direction == Direction.UP and main[0].index == 1
    assert main[1].direction == Direction.DOWN and main[1].index == 2
    assert main[2].direction == Direction.UP and main[2].index == 3
    assert main[3].direction == Direction.DOWN and main[3].index == 4
    assert all(len(s.measurements) == 3 for s in main)
