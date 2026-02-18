import tempfile
import json
from pathlib import Path

from src.etacomp.rules.tolerance_engine import ToleranceRuleEngine, OverlapError
from src.etacomp.rules.verdict import evaluate_tolerances, VerdictStatus
from src.etacomp.core.calculation_engine import CalculatedResults


def make_rules(tmp: Path) -> Path:
    data = {
        "normale": [
            {"graduation": 0.01, "course_min": 0.0, "course_max": 10.0, "Emt": 0.013, "Eml": 0.010, "Ef": 0.003, "Eh": 0.010},
            {"graduation": 0.01, "course_min": 10.0, "course_max": 20.0, "Emt": 0.015, "Eml": 0.012, "Ef": 0.003, "Eh": 0.012}
        ],
        "grande": [
            {"graduation": 0.01, "course_min": 20.0, "course_max": 30.0, "Emt": 0.025, "Eml": 0.020, "Ef": 0.005, "Eh": 0.020}
        ],
        "faible": [
            {"graduation": 0.001, "Emt": 0.008, "Eml": 0.006, "Ef": 0.002, "Eh": 0.006}
        ],
        "limitee": [
            {"graduation": 0.001, "Emt": 0.005, "Eml": 0.004, "Ef": 0.0015, "Eh": 0.004}
        ]
    }
    p = tmp / "tolerances.json"
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p


def test_match_faible_without_course(tmp_path: Path):
    p = make_rules(tmp_path)
    eng = ToleranceRuleEngine.load(p)
    rule = eng.match("faible", 0.001, None)
    assert rule is not None
    assert rule.Eml == 0.006


def test_match_normale_with_course(tmp_path: Path):
    p = make_rules(tmp_path)
    eng = ToleranceRuleEngine.load(p)
    rule = eng.match("normale", 0.01, 12.0)
    assert rule is not None
    assert rule.Emt == 0.015


def test_overlap_detection(tmp_path: Path):
    data = {
        "normale": [
            {"graduation": 0.01, "course_min": 0.0, "course_max": 15.0, "Emt": 0.013, "Eml": 0.010, "Ef": 0.003, "Eh": 0.010},
            {"graduation": 0.01, "course_min": 10.0, "course_max": 20.0, "Emt": 0.015, "Eml": 0.012, "Ef": 0.003, "Eh": 0.012}
        ],
        "grande": [], "faible": [], "limitee": []
    }
    p = tmp_path / "rules_overlap.json"
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        ToleranceRuleEngine.load(p)
        assert False, "Overlap non détecté"
    except OverlapError:
        assert True


def test_verdict_apte(tmp_path: Path):
    p = make_rules(tmp_path)
    eng = ToleranceRuleEngine.load(p)
    profile = {"range_type": "normale", "graduation": 0.01, "course": 5.0}
    results = CalculatedResults(
        total_error_mm=0.010, total_error_location={},
        local_error_mm=0.008, local_error_location={},
        hysteresis_max_mm=0.008, hysteresis_location={},
        fidelity_std_mm=0.002, fidelity_context=None,
        calibration_points=[]
    )
    ver = evaluate_tolerances(profile, results, eng)
    assert ver.status == VerdictStatus.APTE
    assert not ver.exceed


def test_verdict_indetermine_no_rule(tmp_path: Path):
    p = make_rules(tmp_path)
    eng = ToleranceRuleEngine.load(p)
    profile = {"range_type": "normale", "graduation": 0.02, "course": 5.0}
    results = CalculatedResults(
        total_error_mm=0.0, total_error_location={},
        local_error_mm=0.0, local_error_location={},
        hysteresis_max_mm=0.0, hysteresis_location={},
        fidelity_std_mm=0.0, fidelity_context=None,
        calibration_points=[]
    )
    ver = evaluate_tolerances(profile, results, eng)
    assert ver.status == VerdictStatus.INDETERMINE


def test_verdict_indetermine_no_fidelity(tmp_path: Path):
    p = make_rules(tmp_path)
    eng = ToleranceRuleEngine.load(p)
    profile = {"range_type": "normale", "graduation": 0.01, "course": 5.0}
    results = CalculatedResults(
        total_error_mm=0.010, total_error_location={},
        local_error_mm=0.008, local_error_location={},
        hysteresis_max_mm=0.008, hysteresis_location={},
        fidelity_std_mm=None, fidelity_context=None,
        calibration_points=[]
    )
    ver = evaluate_tolerances(profile, results, eng)
    assert ver.status == VerdictStatus.INDETERMINE

