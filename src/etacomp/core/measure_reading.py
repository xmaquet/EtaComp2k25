"""Normalisation des lectures série → position absolue (mm)."""

from __future__ import annotations


def normalize_measured_mm(value: float, target_mm: float) -> float:
    """
    Convertit une valeur TESA en position absolue sur l'échelle (mm).

    - Lecture « grande » (ex. 9.003 à cible 9.0) : position absolue → abs(v).
    - Lecture « petite » relative à la cible (ex. -0.015 à cible 1.0) : écart signé
      → cible + v (issue #6, moteur erreur = mesuré − cible).

    L'affichage opérateur et les moyennes (µm) utilisent toujours des positions absolues.
    """
    v = float(value)
    rel_threshold = max(0.25, abs(target_mm) * 0.15)
    if abs(v) <= rel_threshold and (abs(target_mm) <= 1e-9 or abs(v) < abs(target_mm) * 0.5):
        return target_mm + v
    return abs(v)


# Tolérance « zéro » au repère (mm) — le banc renvoie souvent 0.000–0.01, pas 1e-6.
ZERO_AT_ORIGIN_TOL_MM = 0.05


def is_near_origin_mm(
    value: float,
    target_mm: float = 0.0,
    *,
    tol_mm: float = ZERO_AT_ORIGIN_TOL_MM,
) -> bool:
    """True si la lecture normalisée est au voisinage du repère 0 mm."""
    return abs(normalize_measured_mm(value, target_mm)) <= tol_mm
