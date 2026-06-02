"""Point critique (erreur totale max) — logique unique moteur / UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

TOL = 1e-9


@dataclass(frozen=True)
class CriticalPoint:
    target_mm: float
    direction: Literal["up", "down"]
    measured_mm: float
    reference_mm: float
    error_mm: float

    def to_location_dict(self) -> dict:
        return {
            "target_mm": self.target_mm,
            "direction": self.direction,
            "measured_mm": self.measured_mm,
            "reference_mm": self.reference_mm,
            "error_mm": self.error_mm,
        }


def find_critical_point(
    targets: List[float],
    up_errors: List[Tuple[float, float]],
    down_errors: List[Tuple[float, float]],
    *,
    up_means: Optional[Dict[float, float]] = None,
    down_means: Optional[Dict[float, float]] = None,
) -> Optional[CriticalPoint]:
    """
    Retourne le point où l'erreur totale |Emt| est maximale.

    Tie-break (documenté) :
    1. Plus grand |erreur| ;
    2. À égalité, sens dont l'erreur opposée (même cible) a le plus grand |erreur| ;
    3. À égalité, cible la plus grande (mm).
    """
    up_map = {t: e for t, e in up_errors}
    down_map = {t: e for t, e in down_errors}
    candidates: List[Tuple[float, float, float, str, float]] = []

    for t in targets:
        up_e = up_map.get(t)
        down_e = down_map.get(t)
        if up_e is not None:
            other = abs(down_e) if down_e is not None else 0.0
            candidates.append((abs(up_e), other, t, "up", up_e))
        if down_e is not None:
            other = abs(up_e) if up_e is not None else 0.0
            candidates.append((abs(down_e), other, t, "down", down_e))

    if not candidates:
        return None

    abs_e, _other, t, direction, signed = max(candidates, key=lambda c: (c[0], c[1], c[2]))
    means = up_means if direction == "up" else down_means
    measured = (means or {}).get(t)
    if measured is None:
        measured = t + signed
    return CriticalPoint(
        target_mm=t,
        direction=direction,  # type: ignore[arg-type]
        measured_mm=float(measured),
        reference_mm=t,
        error_mm=float(signed),
    )


def fidelity_matches_critical(
    critical: Optional[CriticalPoint],
    *,
    target_mm: float,
    direction: str,
) -> bool:
    """Vérifie que la série 5 correspond au point critique."""
    if critical is None:
        return False
    d = "up" if str(direction).lower().startswith("u") else "down"
    return (
        abs(float(target_mm) - critical.target_mm) < TOL
        and d == critical.direction
    )
