from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class MeasureSeries(BaseModel):
    target: float                                    # valeur cible (mm)
    readings: List[float] = Field(default_factory=list)  # relevés réels (mm)


class FidelitySeries(BaseModel):
    """Série de 5 mesures au point critique (stockage runtime)."""
    target: float
    direction: str  # "up" | "down"
    samples: List[float] = Field(default_factory=list)
    timestamps: List[str] = Field(default_factory=list)


class Session(BaseModel):
    # Métadonnées
    operator: str
    date: datetime = datetime.now()
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    comparator_ref: Optional[str] = None
    holder_ref: Optional[str] = None  # code ES du détenteur
    banc_ref: Optional[str] = None  # référence banc étalon (hors défaut)

    # Paramétrage de campagne
    series_count: int = 0
    measures_per_series: int = 0
    observations: Optional[str] = None

    # Données de mesures
    series: List[MeasureSeries] = Field(default_factory=list)
    fidelity: Optional[FidelitySeries] = None

    def has_measures(self) -> bool:
        base = any(len(s.readings) > 0 for s in self.series)
        fid = bool(self.fidelity and len(self.fidelity.samples) > 0)
        return base or fid

    def total_readings(self) -> int:
        return sum(len(s.readings) for s in self.series)

# ===== Nouveau modèle canonique (Session V2) =====
from dataclasses import dataclass, asdict
from enum import Enum
from uuid import uuid4


class Direction(str, Enum):
    UP = "up"
    DOWN = "down"


class SeriesKind(str, Enum):
    MAIN = "main"          # séries 1..4 (11 points)
    FIDELITY = "fidelity"  # série 5 (5 mesures)


@dataclass
class Measurement:
    target_mm: float
    value_mm: float
    direction: Direction
    series_index: int           # 1..4 or 5
    sample_index: int           # 0..10 (main) or 0..4 (fidelity)
    timestamp_iso: str
    display: Optional[str] = None
    raw_hex: Optional[str] = None
    raw_ascii: Optional[str] = None


@dataclass
class Series:
    index: int                  # 1..5
    kind: SeriesKind
    direction: Direction
    targets_mm: list[float]     # 11 points pour MAIN, 1 point répété pour FIDELITY
    measurements: list[Measurement]


@dataclass
class SessionV2:
    schema_version: int
    session_id: str
    created_at_iso: str
    operator: str
    temperature_c: Optional[float]
    humidity_rh: Optional[float]
    comparator_ref: str
    comparator_snapshot: dict
    notes: str
    series: list[Series]

    # ----- sérialisation -----
    def to_dict(self) -> dict:
        def _conv(obj):
            if isinstance(obj, (SessionV2, Series, Measurement)):
                d = asdict(obj)
                # Enum as value
                if isinstance(obj, Series):
                    d["kind"] = obj.kind.value
                    d["direction"] = obj.direction.value
                if isinstance(obj, Measurement):
                    d["direction"] = obj.direction.value
                return d
            if isinstance(obj, Enum):
                return obj.value
            return obj
        return _conv(self)

    @staticmethod
    def from_dict(data: dict) -> "SessionV2":
        def _mk_measure(m: dict) -> Measurement:
            return Measurement(
                target_mm=float(m["target_mm"]),
                value_mm=float(m["value_mm"]),
                direction=Direction(m["direction"]),
                series_index=int(m["series_index"]),
                sample_index=int(m["sample_index"]),
                timestamp_iso=str(m["timestamp_iso"]),
                display=m.get("display"),
                raw_hex=m.get("raw_hex"),
                raw_ascii=m.get("raw_ascii"),
            )
        def _mk_series(s: dict) -> Series:
            return Series(
                index=int(s["index"]),
                kind=SeriesKind(s["kind"]),
                direction=Direction(s["direction"]),
                targets_mm=[float(x) for x in s.get("targets_mm", [])],
                measurements=[_mk_measure(m) for m in s.get("measurements", [])],
            )
        return SessionV2(
            schema_version=int(data.get("schema_version", 1)),
            session_id=str(data.get("session_id") or str(uuid4())),
            created_at_iso=str(data.get("created_at_iso") or datetime.utcnow().isoformat()),
            operator=str(data.get("operator") or ""),
            temperature_c=data.get("temperature_c"),
            humidity_rh=data.get("humidity_rh"),
            comparator_ref=str(data.get("comparator_ref") or ""),
            comparator_snapshot=dict(data.get("comparator_snapshot") or {}),
            notes=str(data.get("notes") or ""),
            series=[_mk_series(s) for s in data.get("series", [])],
        )


def save_session_v2(path: str | "Path", session: SessionV2) -> None:
    import json
    from pathlib import Path
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")


def load_session_v2(path: str | "Path") -> SessionV2:
    import json
    from pathlib import Path
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    return SessionV2.from_dict(data)
