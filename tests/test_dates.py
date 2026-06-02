"""Issue #7 — dates de session et horodatage UTC."""

import time
import warnings

from src.etacomp.models.session import Session
from src.etacomp.core.session_adapter import build_session_from_runtime
from src.etacomp.core.datetime_utils import utc_now_iso
from tests.test_ui_results_provider import make_runtime_session_basic


def test_session_date_default_factory_is_fresh():
    s1 = Session(operator="a")
    time.sleep(0.02)
    s2 = Session(operator="b")
    assert s2.date >= s1.date


def test_new_session_uses_runtime_date_in_v2():
    rt = make_runtime_session_basic()
    v2 = build_session_from_runtime(rt)
    assert rt.date is not None
    assert v2.created_at_iso.startswith(rt.date.strftime("%Y-%m-%d"))


def test_build_session_no_utcnow_deprecation():
    rt = make_runtime_session_basic()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        build_session_from_runtime(rt)
    assert not any("utcnow" in str(w.message).lower() for w in caught)


def test_utc_now_iso_has_timezone():
    iso = utc_now_iso()
    assert "+" in iso or iso.endswith("Z") or "00:00" in iso
