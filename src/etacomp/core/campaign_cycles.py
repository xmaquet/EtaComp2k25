"""Nombre de cycles montée/descente supportés en v1.0.1 (S1–S4)."""

from __future__ import annotations

MAX_CAMPAIGN_CYCLES = 2


def clamp_series_count(count: int | None) -> tuple[int, bool]:
    """
    Limite le nombre de cycles à MAX_CAMPAIGN_CYCLES.
    Retourne (valeur_clampée, True si la valeur demandée était supérieure).
    """
    requested = max(1, int(count or 1))
    clamped = min(requested, MAX_CAMPAIGN_CYCLES)
    return clamped, clamped != requested
