from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


TOL = 1e-6


class RangeType(str, Enum):
    NORMALE = "normale"
    GRANDE = "grande"
    FAIBLE = "faible"
    LIMITEE = "limitee"


class Comparator(BaseModel):
    reference: str
    manufacturer: Optional[str] = None
    description: Optional[str] = None

    graduation: Optional[float] = Field(default=None, description="Échelon (mm)")
    course: Optional[float] = Field(default=None, description="Course nominale (mm)")
    range_type: Optional[RangeType] = Field(default=None)

    # 11 cibles (mm)
    targets: List[float] = Field(default_factory=list)

    @property
    def filename(self) -> str:
        base = self.reference.strip().replace(" ", "_")
        return f"{base}.json"

    @model_validator(mode="after")
    def _validate_profile(self):
        # targets présents
        if not self.targets:
            raise ValueError("Aucune cible n’est définie.")
        # déductions si manquants (migration)
        if self.course is None:
            self.course = max(self.targets)
        if self.graduation is None:
            self.graduation = _infer_graduation(self.targets)
        if self.range_type is None:
            self.range_type = _infer_range_type(self.course)

        # validations
        if self.graduation is None or self.graduation <= 0:
            raise ValueError("La graduation doit être > 0.")
        if self.course is None or self.course <= 0:
            raise ValueError("La course doit être > 0.")
        if len(self.targets) != 11:
            raise ValueError(f"Le profil doit contenir 11 cibles (actuel: {len(self.targets)}).")
        # 0 présent avec tolérance
        if min(self.targets) > 0 + TOL or all(abs(t - 0.0) > TOL for t in self.targets):
            raise ValueError("La cible 0.0 mm doit être présente.")
        # bornes et ordre
        last = None
        for i, t in enumerate(self.targets, start=1):
            if t < -TOL or t > self.course + TOL:
                raise ValueError(f"La cible n°{i} ({t:.3f} mm) dépasse la course {self.course:.3f} mm.")
            if last is not None and t + TOL < last:
                raise ValueError(f"Les cibles doivent être non décroissantes (position {i}).")
            last = t
        return self


def _infer_graduation(targets: List[float]) -> float:
    if not targets or len(targets) == 1:
        return 0.01
    # calcul d’incrément médian
    diffs = []
    for a, b in zip(targets, targets[1:]):
        d = abs(b - a)
        if d > TOL:
            diffs.append(d)
    if not diffs:
        return 0.01
    avg = sum(diffs) / len(diffs)
    # arrondi aux valeurs usuelles
    candidates = [0.001, 0.01, 0.02, 0.05, 0.1]
    best = min(candidates, key=lambda x: abs(x - avg))
    return best


def _infer_range_type(course: float) -> RangeType:
    if course <= 0.5 + TOL:
        return RangeType.LIMITEE
    if course <= 1.0 + TOL:
        return RangeType.FAIBLE
    if course <= 20.0 + TOL:
        return RangeType.NORMALE
    return RangeType.GRANDE
