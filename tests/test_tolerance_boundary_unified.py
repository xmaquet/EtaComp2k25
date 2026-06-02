"""Vérifie que tolerances.py et tolerance_engine.py matchent aux mêmes bornes."""

from src.etacomp.rules.tolerances import ToleranceRuleEngine as LegacyEngine, ToleranceRule as LegacyRule
from src.etacomp.rules.tolerance_engine import ToleranceRuleEngine as RuntimeEngine, ToleranceRule as RuntimeRule


def _make_pair():
    rules_normale = [
        LegacyRule(graduation=0.01, course_min=0.0, course_max=10.0, Emt=0.013, Eml=0.010, Ef=0.003, Eh=0.010),
        LegacyRule(graduation=0.01, course_min=10.0, course_max=20.0, Emt=0.015, Eml=0.012, Ef=0.003, Eh=0.012),
    ]
    legacy = LegacyEngine()
    legacy.rules["normale"] = list(rules_normale)

    runtime_rules = [
        RuntimeRule(graduation=0.01, course_min=0.0, course_max=10.0, Emt=0.013, Eml=0.010, Ef=0.003, Eh=0.010),
        RuntimeRule(graduation=0.01, course_min=10.0, course_max=20.0, Emt=0.015, Eml=0.012, Ef=0.003, Eh=0.012),
    ]
    runtime = RuntimeEngine({"normale": runtime_rules, "grande": [], "faible": [], "limitee": []})
    runtime.validate()
    return legacy, runtime


def test_tolerance_boundary_same_in_ui_and_runtime():
    legacy, runtime = _make_pair()
    cases = [
        (5.0, 10.0),
        (10.0, 10.0),
        (10.001, 20.0),
    ]
    for course, expected_max in cases:
        lr = legacy.match("normale", 0.01, course)
        rr = runtime.match("normale", 0.01, course)
        assert lr is not None and rr is not None
        assert lr.course_max == expected_max
        assert rr.course_max == expected_max
