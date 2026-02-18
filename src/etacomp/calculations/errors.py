from __future__ import annotations
"""
Nouveau pont de calcul d'erreurs: délègue au CalculationEngine basé sur le modèle SessionV2.
Conserve une API minimale pour compatibilité là où nécessaire.
"""
from dataclasses import dataclass
from typing import Dict, Optional

from ..core.calculation_engine import CalculationEngine, CalculatedResults
from ..core.session_adapter import build_session_from_runtime
from ..models.session import Session as RuntimeSession


@dataclass
class ErrorResultsCompat:
    """Compatibilité minimale avec l'ancienne structure de résultats."""
    Emt: float  # Erreur totale
    Eml: float  # Erreur locale
    Ef: float   # Fidélité (std)
    Eh: float   # Hystérésis max

    def to_dict(self) -> Dict[str, float]:
        return {"Emt": self.Emt, "Eml": self.Eml, "Ef": self.Ef, "Eh": self.Eh}


def compute_from_runtime_session(rt_session: RuntimeSession) -> tuple[CalculatedResults, ErrorResultsCompat]:
    """Construit une SessionV2 depuis le runtime et calcule les erreurs principales."""
    v2 = build_session_from_runtime(rt_session)
    engine = CalculationEngine()
    res = engine.compute(v2)
    compat = ErrorResultsCompat(
        Emt=res.total_error_mm,
        Eml=res.local_error_mm,
        Ef=res.fidelity_std_mm or 0.0,
        Eh=res.hysteresis_max_mm,
    )
    return res, compat
