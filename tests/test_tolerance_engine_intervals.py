from src.etacomp.rules.tolerance_engine import ToleranceRuleEngine, ToleranceRule


def make_engine_simple():
    eng = ToleranceRuleEngine({
        "normale": [
            ToleranceRule(graduation=0.01, course_min=0.0, course_max=5.0, Emt=1, Eml=0.5, Ef=0.5, Eh=0.5),
            ToleranceRule(graduation=0.01, course_min=5.0, course_max=10.0, Emt=1, Eml=0.5, Ef=0.5, Eh=0.5),
        ],
        "grande": [],
        "faible": [],
        "limitee": [],
    })
    eng.validate()
    return eng


def test_intervals_normale_0_5_10():
    eng = make_engine_simple()
    # course=5 => première (≤5)
    r1 = eng.match("normale", 0.01, 5.0)
    assert r1 is not None and r1.course_max == 5.0
    # course=5.0001 => seconde (>5 et ≤10)
    r2 = eng.match("normale", 0.01, 5.0001)
    assert r2 is not None and r2.course_max == 10.0
    # course=10 => seconde
    r3 = eng.match("normale", 0.01, 10.0)
    assert r3 is not None and r3.course_max == 10.0


def test_intervals_normale_0_1_10():
    eng = ToleranceRuleEngine({
        "normale": [
            ToleranceRule(graduation=0.001, course_min=0.0, course_max=1.0, Emt=1, Eml=0.5, Ef=0.5, Eh=0.5),
            ToleranceRule(graduation=0.001, course_min=1.0, course_max=10.0, Emt=1, Eml=0.5, Ef=0.5, Eh=0.5),
        ],
        "grande": [], "faible": [], "limitee": [],
    })
    eng.validate()
    r1 = eng.match("normale", 0.001, 1.0)
    assert r1 is not None and r1.course_max == 1.0
    r2 = eng.match("normale", 0.001, 1.0001)
    assert r2 is not None and r2.course_max == 10.0
