from __future__ import annotations

import logging
from typing import Optional

from ..models.session import (
    Session as RuntimeSession,
    SessionV2, Series, SeriesKind, Direction, Measurement
)
from ..io.storage import list_comparators
from .campaign_cycles import MAX_CAMPAIGN_CYCLES, clamp_series_count
from .datetime_utils import runtime_created_iso, utc_now_iso, utc_session_id_suffix

logger = logging.getLogger(__name__)


def capture_comparator_snapshot(ref: Optional[str]) -> Optional[dict]:
    """Capture le profil comparateur depuis la bibliothèque (à la sauvegarde / changement de ref)."""
    if not ref:
        return None
    for c in list_comparators():
        if c.reference == ref:
            return {
                "reference": c.reference,
                "manufacturer": getattr(c, "manufacturer", None),
                "description": getattr(c, "description", None),
                "graduation": c.graduation,
                "course": c.course,
                "range_type": getattr(c.range_type, "value", None),
                "targets": list(c.targets),
            }
    return None


def _snapshot_is_usable(snap: dict) -> bool:
    if not snap or not snap.get("reference"):
        return False
    return bool(snap.get("targets")) or (
        snap.get("graduation") is not None and snap.get("course") is not None
    )


def resolve_comparator_snapshot(rt: RuntimeSession) -> dict:
    """
    Profil pour calcul / verdict : snapshot session prioritaire, bibliothèque en secours.
    """
    snap = getattr(rt, "comparator_snapshot", None) or {}
    if isinstance(snap, dict) and _snapshot_is_usable(snap):
        return dict(snap)
    ref = rt.comparator_ref
    live = capture_comparator_snapshot(ref)
    if live:
        if snap:
            logger.warning(
                "Snapshot comparateur incomplet pour %s — profil bibliothèque utilisé",
                ref,
            )
        else:
            logger.warning(
                "Session sans snapshot comparateur (%s) — profil bibliothèque actuel utilisé",
                ref,
            )
        return live
    if ref:
        logger.warning("Comparateur %s introuvable — snapshot vide", ref)
    return {}


def sync_comparator_snapshot(rt: RuntimeSession) -> None:
    """Met à jour le snapshot figé sur la session runtime."""
    rt.comparator_snapshot = capture_comparator_snapshot(rt.comparator_ref)


def build_session_from_runtime(rt: RuntimeSession) -> SessionV2:
    """
    Construit un SessionV2 canonique à partir du runtime Session (pydantic) utilisé par l'UI.
    Hypothèses:
    - rt.series: liste de MeasureSeries regroupées par cible (target, readings[])
      où readings[pos] encode: pos = (cycle-1)*2 + (0 si up else 1)
    - series_count contient le nombre d'itérations montée+descente (cycles)
    """
    schema_version = 1
    created_iso = runtime_created_iso(getattr(rt, "date", None))
    sid = f"session-{rt.date.strftime('%Y%m%d%H%M%S')}" if getattr(rt, "date", None) else f"session-{utc_session_id_suffix()}"

    # Déterminer les cibles (depuis rt.series qui liste par cible)
    targets = [float(ms.target) for ms in rt.series] if rt.series else []

    main_series: list[Series] = []
    requested_cycles = max(1, int(rt.series_count or 1))
    cycles, was_clamped = clamp_series_count(requested_cycles)
    if was_clamped:
        logger.warning(
            "series_count=%s limité à %s (max %s cycles → séries S1–S4).",
            requested_cycles,
            cycles,
            MAX_CAMPAIGN_CYCLES,
        )
    for cyc in range(1, cycles + 1):
        # Série montée (index 2*cyc-1)
        up_idx = 2 * cyc - 1
        s_up = Series(
            index=up_idx, kind=SeriesKind.MAIN,
            direction=Direction.UP,
            targets_mm=list(targets),
            measurements=[]
        )
        # Série descente (index 2*cyc)
        down_idx = 2 * cyc
        s_dn = Series(
            index=down_idx, kind=SeriesKind.MAIN,
            direction=Direction.DOWN,
            targets_mm=list(targets),
            measurements=[]
        )
        main_series.extend([s_up, s_dn])

    dropped_measurements = 0
    for t_i, ms in enumerate(rt.series or []):
        for pos, val in enumerate(ms.readings or []):
            if val is None:
                continue
            cyc = (pos // 2) + 1
            up = (pos % 2 == 0)
            if cyc > cycles:
                dropped_measurements += 1
                continue
            series_index = 2 * cyc - (1 if up else 0)  # cyc:1 up->1, down->2 ; cyc:2 up->3, down->4
            direction = Direction.UP if up else Direction.DOWN
            m = Measurement(
                target_mm=float(ms.target),
                value_mm=float(val),
                direction=direction,
                series_index=series_index,
                sample_index=t_i,
                timestamp_iso=utc_now_iso(),
            )
            # Ajouter dans la bonne série
            for s in main_series:
                if s.index == series_index:
                    s.measurements.append(m)
                    break

    if dropped_measurements:
        logger.warning(
            "%s mesure(s) ignorée(s) : cycle > %s (encodage pos = (cycle-1)*2 + sens).",
            dropped_measurements,
            cycles,
        )

    # Série de fidélité si présente sur la session runtime
    series_all = list(main_series)
    try:
        fid = getattr(rt, "fidelity", None)
        if fid and fid.samples:
            dir_enum = Direction.UP if str(fid.direction).lower().startswith("u") else Direction.DOWN
            m_list: list[Measurement] = []
            for i, v in enumerate(fid.samples[:5]):
                m_list.append(Measurement(
                    target_mm=float(fid.target),
                    value_mm=float(v),
                    direction=dir_enum,
                    series_index=5,
                    sample_index=i,
                    timestamp_iso=(fid.timestamps[i] if i < len(getattr(fid, "timestamps", []) or []) else utc_now_iso()),
                ))
            s5 = Series(index=5, kind=SeriesKind.FIDELITY, direction=dir_enum, targets_mm=[float(fid.target)], measurements=m_list)
            series_all.append(s5)
    except Exception:
        pass

    v2 = SessionV2(
        schema_version=schema_version,
        session_id=sid,
        created_at_iso=created_iso,
        operator=rt.operator or "",
        temperature_c=rt.temperature_c,
        humidity_rh=rt.humidity_pct,
        comparator_ref=rt.comparator_ref or "",
        comparator_snapshot=resolve_comparator_snapshot(rt),
        notes=rt.observations or "",
        series=series_all,
    )
    return v2

