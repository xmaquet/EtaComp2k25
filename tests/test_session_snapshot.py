"""Issue #13 — snapshot comparateur figé pour reproductibilité."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from src.etacomp.core.calculation_engine import CalculationEngine
from src.etacomp.core.session_adapter import (
    build_session_from_runtime,
    resolve_comparator_snapshot,
    sync_comparator_snapshot,
)
from src.etacomp.io.storage import load_session_file, save_comparator, save_session_file
from src.etacomp.models.comparator import Comparator
from src.etacomp.models.session import (
    FidelitySeries,
    MeasureSeries,
    Session as RuntimeSession,
)
from src.etacomp.rules.tolerance_engine import ToleranceRuleEngine
from src.etacomp.rules.verdict import evaluate_tolerances


def _rules_path(tmp_path: Path) -> Path:
    data = {
        "normale": [
            {
                "graduation": 0.01,
                "course_min": 0.0,
                "course_max": 10.0,
                "Emt": 0.020,
                "Eml": 0.015,
                "Ef": 0.005,
                "Eh": 0.015,
            }
        ],
        "grande": [],
        "faible": [],
        "limitee": [],
    }
    p = tmp_path / "rules.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _comparator(ref: str, *, graduation: float = 0.01, course: float = 10.0) -> Comparator:
    return Comparator(
        reference=ref,
        graduation=graduation,
        course=course,
        targets=[float(i) for i in range(11)],
        range_type="normale",
        periodicite_controle_mois=12,
    )


def _runtime_session(ref: str) -> RuntimeSession:
    targets = [0.0, 1.0, 2.0]
    series = [
        MeasureSeries(target=t, readings=[t + 0.01, t - 0.02, t + 0.02, t - 0.01])
        for t in targets
    ]
    return RuntimeSession(
        operator="op",
        date=datetime(2025, 6, 2, 12, 0, 0),
        comparator_ref=ref,
        series_count=2,
        measures_per_series=11,
        series=series,
        fidelity=FidelitySeries(
            target=1.0,
            direction="up",
            samples=[1.0, 1.01, 0.99, 1.0, 1.0],
            timestamps=[],
        ),
    )


def _compute_verdict(rt: RuntimeSession, rules_path: Path):
    v2 = build_session_from_runtime(rt)
    results = CalculationEngine().compute(v2)
    eng = ToleranceRuleEngine.load(rules_path)
    verdict = evaluate_tolerances(v2.comparator_snapshot or {}, results, eng)
    return v2, results, verdict


def test_comparator_modified_after_session_does_not_change_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    import src.etacomp.io.storage as storage_mod

    monkeypatch.setattr(storage_mod, "get_data_dir", lambda: tmp_path)
    ref = "SNAP-TEST"
    save_comparator(_comparator(ref, graduation=0.01, course=10.0))

    rt = _runtime_session(ref)
    sync_comparator_snapshot(rt)
    rules = _rules_path(tmp_path)
    _, results_before, verdict_before = _compute_verdict(rt, rules)

    save_comparator(_comparator(ref, graduation=0.05, course=10.0))

    _, results_after, verdict_after = _compute_verdict(rt, rules)
    assert results_after.total_error_mm == results_before.total_error_mm
    assert verdict_after.status == verdict_before.status
    assert verdict_after.limits == verdict_before.limits
    assert resolve_comparator_snapshot(rt)["graduation"] == 0.01

    rt.comparator_snapshot = None
    import logging

    caplog.set_level(logging.WARNING)
    v2_live = build_session_from_runtime(rt)
    assert v2_live.comparator_snapshot["graduation"] == 0.05
    assert any("sans snapshot" in r.message for r in caplog.records)


def test_storage_roundtrip_session_with_fidelity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import src.etacomp.io.storage as storage_mod

    monkeypatch.setattr(storage_mod, "get_data_dir", lambda: tmp_path)
    ref = "ROUNDTRIP"
    save_comparator(_comparator(ref))

    rt = _runtime_session(ref)
    sync_comparator_snapshot(rt)
    path = save_session_file(rt)

    loaded = load_session_file(path)
    assert loaded.comparator_snapshot is not None
    assert loaded.comparator_snapshot.get("reference") == ref
    assert loaded.fidelity is not None
    assert len(loaded.fidelity.samples) == 5

    v2_a, res_a, _ = _compute_verdict(rt, _rules_path(tmp_path))
    v2_b, res_b, _ = _compute_verdict(loaded, _rules_path(tmp_path))
    assert res_b.total_error_mm == res_a.total_error_mm
    assert res_b.fidelity_std_mm == res_a.fidelity_std_mm
    assert v2_b.comparator_snapshot == v2_a.comparator_snapshot


def test_loaded_session_recomputes_same_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import src.etacomp.io.storage as storage_mod

    monkeypatch.setattr(storage_mod, "get_data_dir", lambda: tmp_path)
    ref = "RELOAD"
    save_comparator(_comparator(ref))

    rt = _runtime_session(ref)
    sync_comparator_snapshot(rt)
    path = save_session_file(rt)
    loaded = load_session_file(path)

    rules = _rules_path(tmp_path)
    _, r1, v1 = _compute_verdict(loaded, rules)
    save_comparator(_comparator(ref, graduation=0.05, course=10.0))
    _, r2, v2 = _compute_verdict(loaded, rules)

    assert r1.total_error_mm == r2.total_error_mm
    assert r1.hysteresis_max_mm == r2.hysteresis_max_mm
    assert v1.status == v2.status
    assert v1.limits == v2.limits
