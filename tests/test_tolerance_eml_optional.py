"""Issue #3 — Eml optionnelle pour faible / limitée."""

import json
from pathlib import Path

from src.etacomp.rules.tolerance_engine import ToleranceRule, ToleranceRuleEngine
from src.etacomp.rules.verdict import evaluate_tolerances, VerdictStatus
from src.etacomp.core.calculation_engine import CalculatedResults


def test_tolerance_eml_optional_faible_limitee(tmp_path: Path):
    data = {
        "faible": [
            {"graduation": 0.001, "Emt": 0.008, "Ef": 0.002, "Eh": 0.006},
        ],
        "limitee": [
            {"graduation": 0.001, "Emt": 0.005, "Ef": 0.0015, "Eh": 0.004},
        ],
        "normale": [],
        "grande": [],
    }
    p = tmp_path / "rules_no_eml.json"
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    eng = ToleranceRuleEngine.load(p)
    rule_f = eng.match("faible", 0.001, None)
    assert rule_f is not None
    assert rule_f.Eml is None

    profile = {"range_type": "faible", "graduation": 0.001, "course": 0.5}
    results = CalculatedResults(
        total_error_mm=0.005,
        total_error_location={},
        local_error_mm=0.050,
        local_error_location={},
        hysteresis_max_mm=0.004,
        hysteresis_location={},
        fidelity_std_mm=0.001,
        fidelity_context=None,
        calibration_points=[],
    )
    ver = evaluate_tolerances(profile, results, eng)
    assert ver.status == VerdictStatus.CONFORME
    assert "Eml" not in ver.limits
    assert "Eml" not in ver.exceed


def test_tolerance_eml_zero_is_active_limit(tmp_path: Path):
    """Eml=0.0 dans le JSON est une limite réelle (distinct de None)."""
    data = {
        "faible": [
            {"graduation": 0.001, "Emt": 0.008, "Eml": 0.0, "Ef": 0.002, "Eh": 0.006},
        ],
        "normale": [],
        "grande": [],
        "limitee": [],
    }
    p = tmp_path / "rules_eml_zero.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    eng = ToleranceRuleEngine.load(p)
    rule = eng.match("faible", 0.001, None)
    assert rule is not None
    assert rule.Eml == 0.0

    profile = {"range_type": "faible", "graduation": 0.001, "course": 0.5}
    results = CalculatedResults(
        total_error_mm=0.001,
        total_error_location={},
        local_error_mm=0.001,
        local_error_location={},
        hysteresis_max_mm=0.001,
        hysteresis_location={},
        fidelity_std_mm=0.001,
        fidelity_context=None,
        calibration_points=[],
    )
    ver = evaluate_tolerances(profile, results, eng)
    assert ver.status == VerdictStatus.NON_CONFORME
    assert "Eml" in ver.exceed


def test_tolerance_rule_construct_without_eml():
    rule = ToleranceRule(graduation=0.001, Emt=0.008, Ef=0.002, Eh=0.006)
    assert rule.Eml is None
