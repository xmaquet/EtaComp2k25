from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..models.session import (
    Session as RuntimeSession,
    SessionV2, Series, SeriesKind, Direction, Measurement
)
from ..io.storage import list_comparators


def _snapshot_comparator(ref: Optional[str]) -> dict:
    if not ref:
        return {}
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
    return {}


def build_session_from_runtime(rt: RuntimeSession) -> SessionV2:
    """
    Construit un SessionV2 canonique à partir du runtime Session (pydantic) utilisé par l'UI.
    Hypothèses:
    - rt.series: liste de MeasureSeries regroupées par cible (target, readings[])
      où readings[pos] encode: pos = (cycle-1)*2 + (0 si up else 1)
    - series_count contient le nombre d'itérations montée+descente (cycles)
    """
    schema_version = 1
    sid = f"session-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    created_iso = datetime.utcnow().isoformat()

    # Déterminer les cibles (depuis rt.series qui liste par cible)
    targets = [float(ms.target) for ms in rt.series] if rt.series else []

    # Construire 4 séries MAIN si possible (ou plus si series_count>2)
    main_series: list[Series] = []
    cycles = max(1, int(rt.series_count or 1))
    # Pour compat métier standard (S1..S4), on ne prend que les deux premiers cycles si >2
    cycles = min(cycles, 2)
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

    # Remplir les mesures si données présentes
    # pos -> cycle index (1-based), direction
    for t_i, ms in enumerate(rt.series or []):
        for pos, val in enumerate(ms.readings or []):
            if val is None:
                continue
            cyc = (pos // 2) + 1
            up = (pos % 2 == 0)
            if cyc > cycles:
                # ignorer cycles > 2 dans ce modèle standard
                continue
            series_index = 2 * cyc - (1 if up else 0)  # cyc:1 up->1, down->2 ; cyc:2 up->3, down->4
            direction = Direction.UP if up else Direction.DOWN
            m = Measurement(
                target_mm=float(ms.target),
                value_mm=float(val),
                direction=direction,
                series_index=series_index,
                sample_index=t_i,
                timestamp_iso=datetime.utcnow().isoformat(),
            )
            # Ajouter dans la bonne série
            for s in main_series:
                if s.index == series_index:
                    s.measurements.append(m)
                    break

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
                    timestamp_iso=(fid.timestamps[i] if i < len(getattr(fid, "timestamps", []) or []) else datetime.utcnow().isoformat()),
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
        comparator_snapshot=_snapshot_comparator(rt.comparator_ref),
        notes=rt.observations or "",
        series=series_all,
    )
    return v2


def apply_session_to_ui(session_v2: SessionV2, ui_state) -> None:
    """
    Place‑holder: applique une session V2 vers l’état UI si besoin (non utilisé pour le moment).
    """
    # Intégration future: reconstruire tables, etc.
    return

