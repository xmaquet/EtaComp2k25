from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from .tolerance_engine import ToleranceRule, ToleranceRuleEngine
from ..core.calculation_engine import CalculatedResults


class VerdictStatus(str, Enum):
    APTE = "apte"
    INAPTE = "inapte"
    INDETERMINE = "indetermine"


@dataclass
class Verdict:
    status: VerdictStatus
    rule: Optional[ToleranceRule]
    messages: list[str]
    exceed: Dict[str, float]
    measured: Dict[str, float]
    limits: Dict[str, float]


def _fmt_mm(x: float) -> str:
    return f"{x:.3f}"


def evaluate_tolerances(
    profile: Dict,              # comparator_snapshot
    results: CalculatedResults,
    engine: ToleranceRuleEngine
) -> Verdict:
    """
    Compare les erreurs calculées aux règles et produit un verdict opérateur.
    Règle: sans fidélité (Ef) disponible -> statut INDETERMINE.
    """
    family = str(profile.get("range_type") or "").lower()
    graduation = float(profile.get("graduation") or 0.0)
    course = float(profile.get("course") or 0.0) if family in ("normale", "grande") else None

    measured = {
        "Emt": results.total_error_mm,
        "Eml": results.local_error_mm,
        "Eh": results.hysteresis_max_mm,
        "Ef": results.fidelity_std_mm if results.fidelity_std_mm is not None else None,
    }

    # Chercher la règle
    rule = engine.match(family, graduation, course)
    if rule is None:
        msgs = [
            "Aucune règle de tolérance correspondante.",
            f"Famille: {family or '(inconnue)'} ; graduation: {_fmt_mm(graduation)} mm"
            + (f" ; course: {_fmt_mm(course)} mm" if course is not None else ""),
            "Compléter Paramètres ▸ Règles pour cette configuration."
        ]
        return Verdict(
            status=VerdictStatus.INDETERMINE,
            rule=None,
            messages=msgs,
            exceed={},
            measured={k: v for k, v in measured.items() if v is not None},
            limits={}
        )

    # Construire limits uniquement avec les clés réellement présentes sur la règle
    limits = {}
    for k in ("Emt", "Eml", "Ef", "Eh"):
        v = getattr(rule, k, None)
        if v is not None:
            limits[k] = v
    exceed: Dict[str, float] = {}
    messages: list[str] = []

    # Comparaisons
    status = VerdictStatus.APTE
    criteria = [k for k in ("Emt", "Eml", "Ef", "Eh") if k in limits]
    for key in criteria:
        m = measured[key]
        lim = limits[key]
        # Si la limite existe mais la mesure est absente -> indéterminé
        if m is None:
            messages.append(f"L'erreur {label_fr(key)} est requise par la règle, mais indisponible. Compléter la campagne.")
            status = VerdictStatus.INDETERMINE
            continue
        if m > lim + 1e-9:
            exceed[key] = m - lim
            messages.append(
                f"Erreur {label_fr(key)} mesurée: {_fmt_mm(m)} mm ; "
                f"limite: {_fmt_mm(lim)} mm ; dépassement: {_fmt_mm(m - lim)} mm."
            )
            status = VerdictStatus.INAPTE

    # Fidélité
    ef = measured["Ef"]
    # Cas spécifique Ef: déjà géré par boucle criteria si la règle contient Ef;
    # conserver message dédié si Ef requise mais absente
    if ("Ef" in limits) and (ef is None):
        messages.append("Erreur de fidélité indisponible: réaliser la série 5 (fidélité) au point critique.")
        if status == VerdictStatus.APTE:
            status = VerdictStatus.INDETERMINE

    if status == VerdictStatus.APTE:
        messages.append("Toutes les erreurs mesurées respectent les limites de tolérance. Comparateur APTE.")

    return Verdict(
        status=status,
        rule=rule,
        messages=messages,
        exceed=exceed,
        measured={k: v for k, v in measured.items() if v is not None},
        limits=limits,
    )


def label_fr(key: str) -> str:
    return {
        "Emt": "totale",
        "Eml": "locale",
        "Eh": "d'hystérésis",
        "Ef": "de fidélité"
    }.get(key, key)

