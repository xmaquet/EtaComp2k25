"""Horodatage UTC (remplace datetime.utcnow(), déprécié en Python 3.12+)."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def utc_session_id_suffix() -> str:
    return utc_now().strftime("%Y%m%d%H%M%S")


def runtime_created_iso(date: datetime | None) -> str:
    """ISO pour SessionV2 à partir de la date de session runtime (locale ou aware)."""
    if date is None:
        return utc_now_iso()
    if date.tzinfo is None:
        return date.isoformat()
    return date.astimezone(timezone.utc).isoformat()
