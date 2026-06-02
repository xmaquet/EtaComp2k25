"""Issue #11 — bibliothèque : 11 cibles obligatoires, pas de crash."""

import pytest
from pydantic import ValidationError

from src.etacomp.models.comparator import Comparator
from src.etacomp.ui.tabs.library import (
    TARGET_COUNT_REQUIRED,
    count_targets_field,
    format_validation_error,
    parse_targets_field,
)


def test_parse_targets_field_accepts_comma_and_semicolon():
    targets = parse_targets_field("0; 1, 2; 3")
    assert targets == [0.0, 1.0, 2.0, 3.0]


def test_parse_targets_field_invalid_token_raises():
    with pytest.raises(ValueError):
        parse_targets_field("0, abc, 2")


def test_count_targets_field():
    assert count_targets_field("0,1,2,3,4,5,6,7,8,9,10") == 11
    assert count_targets_field("0,1,2,3,4,5,6,7,8,9") == 10


def test_comparator_profile_rejects_10_targets():
    with pytest.raises(ValidationError) as exc_info:
        Comparator(
            reference="TEST-10",
            graduation=0.01,
            course=10.0,
            targets=[float(i) for i in range(10)],
            range_type="normale",
        )
    msg = format_validation_error(exc_info.value)
    assert "11" in msg


def test_try_build_model_logic_via_helpers():
    text_10 = ", ".join(str(i) for i in range(10))
    assert count_targets_field(text_10) != TARGET_COUNT_REQUIRED
