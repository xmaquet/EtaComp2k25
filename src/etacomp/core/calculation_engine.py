from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math

from ..models.session import SessionV2, SeriesKind, Direction


@dataclass
class CalculatedResults:
    total_error_mm: float
    total_error_location: Dict
    local_error_mm: float
    local_error_location: Dict
    hysteresis_max_mm: float
    hysteresis_location: Dict
    fidelity_std_mm: Optional[float]
    fidelity_context: Optional[Dict]
    calibration_points: List[Dict]


class CalculationEngine:
    """
    Calcule les erreurs principales à partir d'une SessionV2 canonique.
    Règles:
    - Référence = cible (mm)
    - Moyennes montée/descente sur S1+S3 et S2+S4
    - Erreur totale = max absolu des erreurs (moyennes) sur les deux sens
    - Hystérésis = |mean_up - mean_down| par cible; on garde le max
    - Erreur locale = max des variations entre erreurs successives sur la courbe up et sur la courbe down
    - Fidélité = écart‑type (ddof=0) des 5 mesures sur le point critique si S5 existe
    """
    def compute(self, session: SessionV2) -> CalculatedResults:
        # Organiser données des séries principales
        # target -> lists for up, down
        up_vals: Dict[float, List[float]] = {}
        down_vals: Dict[float, List[float]] = {}
        targets: List[float] = []

        for s in session.series:
            if s.kind != SeriesKind.MAIN:
                continue
            if not targets and s.targets_mm:
                targets = list(s.targets_mm)
            for m in s.measurements:
                if m.direction == Direction.UP:
                    up_vals.setdefault(m.target_mm, []).append(m.value_mm)
                else:
                    down_vals.setdefault(m.target_mm, []).append(m.value_mm)

        # Moyennes par cible
        def mean(lst: List[float]) -> Optional[float]:
            return sum(lst) / len(lst) if lst else None

        calib_rows: List[Dict] = []
        total_error_mm = 0.0
        total_loc: Dict = {}

        # Pour calcul local error besoin des erreurs successives
        up_errors: List[Tuple[float, float]] = []   # (target, error)
        down_errors: List[Tuple[float, float]] = []

        hysteresis_max = 0.0
        hysteresis_loc: Dict = {}

        for t in targets:
            up_m = mean(up_vals.get(t, []))
            down_m = mean(down_vals.get(t, []))
            up_err = (up_m - t) if up_m is not None else None
            down_err = (down_m - t) if down_m is not None else None

            if up_err is not None:
                up_errors.append((t, up_err))
                if abs(up_err) > abs(total_error_mm):
                    total_error_mm = float(up_err)
                    total_loc = {
                        "target_mm": t, "direction": "up",
                        "measured_mm": up_m, "reference_mm": t,
                        "error_mm": up_err
                    }
            if down_err is not None:
                down_errors.append((t, down_err))
                if abs(down_err) > abs(total_error_mm):
                    total_error_mm = float(down_err)
                    total_loc = {
                        "target_mm": t, "direction": "down",
                        "measured_mm": down_m, "reference_mm": t,
                        "error_mm": down_err
                    }

            hyst = None
            if (up_m is not None) and (down_m is not None):
                hyst = abs(up_m - down_m)
                if hyst > hysteresis_max:
                    hysteresis_max = hyst
                    hysteresis_loc = {
                        "target_mm": t,
                        "up_mm": up_m, "down_mm": down_m,
                        "hysteresis_mm": hyst
                    }

            calib_rows.append({
                "target_mm": t,
                "up_mean_mm": up_m,
                "down_mean_mm": down_m,
                "up_error_mm": up_err,
                "down_error_mm": down_err,
                "hysteresis_mm": hyst,
            })

        # Erreur locale (variations successives)
        def max_step_err(errs: List[Tuple[float, float]]) -> Tuple[float, Dict]:
            best = 0.0
            loc = {}
            for i in range(len(errs) - 1):
                t0, e0 = errs[i]
                t1, e1 = errs[i + 1]
                d = abs(e1 - e0)
                if d > best:
                    best = d
                    loc = {"target_a": t0, "target_b": t1, "delta_error_mm": d}
            return best, loc

        up_step, up_loc = max_step_err(up_errors)
        dn_step, dn_loc = max_step_err(down_errors)
        if up_step >= dn_step:
            local_error_mm = up_step
            local_loc = up_loc
        else:
            local_error_mm = dn_step
            local_loc = dn_loc

        # Fidélité (série 5)
        fidelity_std = None
        fidelity_ctx = None
        if total_loc:
            crit_target = total_loc.get("target_mm")
            crit_dir = total_loc.get("direction")
            # Chercher série kind=FIDELITY avec même direction
            for s in session.series:
                if s.kind == SeriesKind.FIDELITY and s.direction.value == crit_dir:
                    samples = [m.value_mm for m in s.measurements if abs(m.target_mm - crit_target) < 1e-9]
                    if len(samples) >= 2:
                        mean_s = sum(samples) / len(samples)
                        var = sum((x - mean_s) ** 2 for x in samples) / len(samples)  # ddof=0
                        std = math.sqrt(var)
                        fidelity_std = std
                        fidelity_ctx = {
                            "target_mm": crit_target,
                            "direction": crit_dir,
                            "samples": samples,
                            "mean_mm": mean_s,
                            "std_mm": std
                        }
                    break

        return CalculatedResults(
            total_error_mm=abs(total_error_mm),
            total_error_location=total_loc,
            local_error_mm=local_error_mm,
            local_error_location=local_loc,
            hysteresis_max_mm=hysteresis_max,
            hysteresis_location=hysteresis_loc,
            fidelity_std_mm=fidelity_std,
            fidelity_context=fidelity_ctx,
            calibration_points=calib_rows,
        )

