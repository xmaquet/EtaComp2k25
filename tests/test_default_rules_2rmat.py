"""Tests de conformité des règles par défaut avec 2RMAT-MO-S4-09-B §7.2."""

from __future__ import annotations

from typing import Any

import pytest

from src.etacomp.rules.tolerances import ToleranceRule, create_default_rules

# Valeurs attendues (mm) — 2RMAT-MO-S4-09-B tableaux p. 4–5 (µm → mm).
EXPECTED_NORMALE: list[dict[str, Any]] = [
    {
        "graduation": 0.001,
        "course_min": 0.0,
        "course_max": 1.0,
        "Emt": 0.005,
        "Eml": 0.003,
        "Ef": 0.00025,
        "Eh": 0.002,
    },
    {
        "graduation": 0.001,
        "course_min": 1.0,
        "course_max": 10.0,
        "Emt": 0.010,
        "Eml": 0.003,
        "Ef": 0.00025,
        "Eh": 0.002,
    },
    {
        "graduation": 0.01,
        "course_min": 0.0,
        "course_max": 5.0,
        "Emt": 0.015,
        "Eml": 0.010,
        "Ef": 0.0015,
        "Eh": 0.006,
    },
    {
        "graduation": 0.01,
        "course_min": 5.0,
        "course_max": 10.0,
        "Emt": 0.015,
        "Eml": 0.010,
        "Ef": 0.0025,
        "Eh": 0.010,
    },
    {
        "graduation": 0.01,
        "course_min": 10.0,
        "course_max": 30.0,
        "Emt": 0.020,
        "Eml": 0.010,
        "Ef": 0.005,
        "Eh": 0.010,
    },
    {
        "graduation": 0.01,
        "course_min": 30.0,
        "course_max": 50.0,
        "Emt": 0.025,
        "Eml": 0.010,
        "Ef": 0.005,
        "Eh": 0.010,
    },
    {
        "graduation": 0.01,
        "course_min": 50.0,
        "course_max": 100.0,
        "Emt": 0.030,
        "Eml": 0.015,
        "Ef": 0.005,
        "Eh": 0.020,
    },
    {
        "graduation": 0.1,
        "course_min": 0.0,
        "course_max": 30.0,
        "Emt": 0.150,
        "Eml": 0.100,
        "Ef": 0.015,
        "Eh": 0.060,
    },
]

EXPECTED_FAIBLE: list[dict[str, Any]] = [
    {
        "graduation": 0.001,
        "course_min": None,
        "course_max": None,
        "Emt": 0.0015,
        "Eml": None,
        "Ef": 0.0005,
        "Eh": 0.0006,
    },
]

EXPECTED_LIMITEE: list[dict[str, Any]] = [
    {
        "graduation": 0.001,
        "course_min": None,
        "course_max": None,
        "Emt": 0.002,
        "Eml": None,
        "Ef": 0.0005,
        "Eh": 0.0006,
    },
    {
        "graduation": 0.01,
        "course_min": None,
        "course_max": None,
        "Emt": 0.010,
        "Eml": None,
        "Ef": 0.003,
        "Eh": 0.004,
    },
]


def _rule_to_dict(rule: ToleranceRule) -> dict[str, Any]:
    return {
        "graduation": rule.graduation,
        "course_min": rule.course_min,
        "course_max": rule.course_max,
        "Emt": rule.Emt,
        "Eml": rule.Eml,
        "Ef": rule.Ef,
        "Eh": rule.Eh,
    }


def _sort_key(item: dict[str, Any]) -> tuple:
    return (
        item["graduation"],
        item["course_min"] if item["course_min"] is not None else -1.0,
        item["course_max"] if item["course_max"] is not None else -1.0,
    )


def _assert_rules_match(family: str, actual_rules: list[ToleranceRule], expected: list[dict[str, Any]]) -> None:
    actual = sorted((_rule_to_dict(r) for r in actual_rules), key=_sort_key)
    exp = sorted(expected, key=_sort_key)
    assert len(actual) == len(exp), (
        f"{family}: nombre de règles attendu {len(exp)}, obtenu {len(actual)}"
    )
    for i, (a, e) in enumerate(zip(actual, exp)):
        for key in ("graduation", "course_min", "course_max", "Emt", "Eml", "Ef", "Eh"):
            assert a[key] == e[key], (
                f"{family}[{i}] {key}: attendu {e[key]!r}, obtenu {a[key]!r}"
            )


@pytest.fixture
def default_engine():
    return create_default_rules()


def test_normale_rules_match_2rmat(default_engine):
    """Règles normale — 2RMAT-MO-S4-09-B §7.2 (course normale et grande course)."""
    _assert_rules_match("normale", default_engine.rules["normale"], EXPECTED_NORMALE)


def test_grande_rules_match_2rmat(default_engine):
    """Grande course : même tableau que normale dans le MO."""
    _assert_rules_match("grande", default_engine.rules["grande"], EXPECTED_NORMALE)


def test_faible_rules_match_2rmat(default_engine):
    """Faible course — Eml non applicable (§7.1)."""
    _assert_rules_match("faible", default_engine.rules["faible"], EXPECTED_FAIBLE)


def test_limitee_rules_match_2rmat(default_engine):
    """Course limitée — Eml non applicable (§7.1)."""
    _assert_rules_match("limitee", default_engine.rules["limitee"], EXPECTED_LIMITEE)
