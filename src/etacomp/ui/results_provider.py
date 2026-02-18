from __future__ import annotations

"""
ResultsProvider — point d'entrée unique pour les onglets d'analyse.

Fournit:
  compute_all(rt_session) -> (SessionV2, CalculatedResults, Verdict|None)

Sources:
  - runtime_session (UI) → SessionV2 via session_adapter
  - CalculationEngine → CalculatedResults
  - ToleranceRuleEngine (+ evaluate_tolerances) → Verdict (optionnel si règles absentes)
"""

from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path

from ..core.session_adapter import build_session_from_runtime
from ..core.calculation_engine import CalculationEngine, CalculatedResults
from ..models.session import SessionV2, Series, SeriesKind, Direction, Measurement
from ..rules.tolerance_engine import ToleranceRuleEngine
from ..rules.verdict import evaluate_tolerances, Verdict
from ..rules.tolerances import get_default_rules_path


class ResultsProvider:
    """Agrège la construction de SessionV2, les calculs et le verdict de tolérances."""

    def __init__(self, rules_path: Optional[Path] = None) -> None:
        self.rules_path = rules_path or get_default_rules_path()
        self._tol_engine: Optional[ToleranceRuleEngine] = None
        self._load_rules()
        # Mémoire volatile de la dernière S5 capturée (pour croiser avec Finalisation)
        # Format: {"comparator_ref": str|None, "target_mm": float, "direction": "up"|"down", "samples": [float], "timestamps": [str]}
        if not hasattr(ResultsProvider, "_last_fidelity"):
            ResultsProvider._last_fidelity: Optional[Dict[str, Any]] = None

    def _load_rules(self) -> None:
        try:
            if self.rules_path.exists():
                self._tol_engine = ToleranceRuleEngine.load(self.rules_path)
            else:
                self._tol_engine = None
        except Exception:
            # En cas d'erreur de lecture, désactiver les tolérances pour ne pas bloquer l'UI
            self._tol_engine = None

    def compute_all(self, rt_session) -> Tuple[SessionV2, CalculatedResults, Optional[Verdict]]:
        """
        Construit une SessionV2, calcule les résultats et tente une évaluation de tolérances.
        """
        v2 = build_session_from_runtime(rt_session)
        calc = CalculationEngine()
        results = calc.compute(v2)
        # Si pas de série 5 intégrée mais une capture S5 récente existe pour ce profil, l'injecter virtuellement
        if results.fidelity_std_mm is None and getattr(ResultsProvider, "_last_fidelity", None):
            lf = ResultsProvider._last_fidelity
            try:
                if (rt_session.comparator_ref or None) == lf.get("comparator_ref"):
                    v2, results, _ = self.compute_with_fidelity(
                        rt_session,
                        target_mm=float(lf["target_mm"]),
                        direction=str(lf["direction"]),
                        samples_mm=list(lf["samples"]),
                        timestamps_iso=list(lf.get("timestamps") or []),
                    )
            except Exception:
                pass
        verdict = None
        if self._tol_engine is not None:
            try:
                verdict = evaluate_tolerances(v2.comparator_snapshot or {}, results, self._tol_engine)
            except Exception:
                verdict = None
        return v2, results, verdict

    def compute_with_fidelity(
        self,
        rt_session,
        *,
        target_mm: float,
        direction: str,  # "up" | "down"
        samples_mm: List[float],
        timestamps_iso: Optional[List[str]] = None,
    ) -> Tuple[SessionV2, CalculatedResults, Optional[Verdict]]:
        """
        Variante: injecte une série 5 (fidélité) construite à partir des 5 mesures collectées.
        N'affecte pas l'état runtime; l'injection est locale pour le calcul/affichage.
        """
        v2 = build_session_from_runtime(rt_session)
        # Construire S5
        dir_enum = Direction.UP if str(direction).lower().startswith("u") else Direction.DOWN
        ts = timestamps_iso or []
        m_list: List[Measurement] = []
        for i, v in enumerate(samples_mm[:5]):
            m_list.append(Measurement(
                target_mm=float(target_mm),
                value_mm=float(v),
                direction=dir_enum,
                series_index=5,
                sample_index=i,
                timestamp_iso=ts[i] if i < len(ts) else __import__("datetime").datetime.utcnow().isoformat(),
            ))
        s5 = Series(index=5, kind=SeriesKind.FIDELITY, direction=dir_enum, targets_mm=[float(target_mm)], measurements=m_list)
        v2.series.append(s5)
        calc = CalculationEngine()
        results = calc.compute(v2)
        verdict = None
        if self._tol_engine is not None:
            try:
                verdict = evaluate_tolerances(v2.comparator_snapshot or {}, results, self._tol_engine)
            except Exception:
                verdict = None
        return v2, results, verdict

    def remember_fidelity(
        self,
        *,
        comparator_ref: Optional[str],
        target_mm: float,
        direction: str,
        samples_mm: List[float],
        timestamps_iso: Optional[List[str]] = None,
    ) -> None:
        """Mémorise temporairement une série 5 capturée, pour réutilisation dans Finalisation."""
        ResultsProvider._last_fidelity = {
            "comparator_ref": comparator_ref or None,
            "target_mm": float(target_mm),
            "direction": "up" if str(direction).lower().startswith("u") else "down",
            "samples": list(samples_mm[:5]),
            "timestamps": list((timestamps_iso or [])[:5]),
        }

