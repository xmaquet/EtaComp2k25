from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import json


class ConfigurationError(Exception):
    """Erreur de configuration des règles de tolérances."""


class OverlapError(ConfigurationError):
    """Plusieurs règles correspondantes pour une même configuration."""


@dataclass(frozen=True)
class ToleranceRule:
    """Règle de tolérance à graduation unique (mm)."""
    graduation: float
    Emt: float
    Eml: float
    Ef: float
    Eh: float
    course_min: float | None = None
    course_max: float | None = None


class ToleranceRuleEngine:
    """Moteur de règles basé sur une graduation unique par famille."""

    EPS = 1e-6
    FAMILIES = ("normale", "grande", "faible", "limitee")

    def __init__(self, rules: Dict[str, List[ToleranceRule]] | None = None):
        self.rules: Dict[str, List[ToleranceRule]] = rules or {f: [] for f in self.FAMILIES}

    @classmethod
    def load(cls, path: Path) -> "ToleranceRuleEngine":
        """Charge un fichier JSON de règles et retourne un moteur initialisé."""
        raw = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw)

        def _norm_family(k: str) -> str:
            k2 = (k or "").strip().lower().lstrip("\ufeff")
            # normaliser accents éventuels
            mapping = {
                "limitée": "limitee",
                "limitée ": "limitee",
            }
            return mapping.get(k2, k2)

        rules: Dict[str, List[ToleranceRule]] = {f: [] for f in cls.FAMILIES}
        for fam_key, items in data.items():
            fam = _norm_family(fam_key)
            if fam not in cls.FAMILIES:
                raise ConfigurationError(f"Famille inconnue: {fam_key}")
            lst: List[ToleranceRule] = []
            for r in items:
                lst.append(ToleranceRule(
                    graduation=float(r["graduation"]),
                    Emt=float(r["Emt"]),
                    Eml=float(r["Eml"]) if "Eml" in r and r["Eml"] is not None else None,
                    Ef=float(r["Ef"]),
                    Eh=float(r["Eh"]),
                    course_min=float(r["course_min"]) if "course_min" in r else None,
                    course_max=float(r["course_max"]) if "course_max" in r else None,
                ))
            rules[fam] = lst
        eng = cls(rules)
        eng.validate()
        return eng

    @staticmethod
    def _feq(a: float, b: float, eps: float) -> bool:
        return abs(a - b) <= eps

    def validate(self) -> None:
        """Valide la configuration. Lève ConfigurationError/OverlapError si invalide."""
        for fam, items in self.rules.items():
            for i, r in enumerate(items):
                if r.graduation <= 0:
                    raise ConfigurationError(f"{fam}[{i+1}]: graduation doit être > 0")
                # Eml optionnelle: ne pas exiger sa présence
                for name in ("Emt", "Ef", "Eh"):
                    val = getattr(r, name, None)
                    if val is None or val < 0:
                        raise ConfigurationError(f"{fam}[{i+1}]: {name} doit être défini et >= 0")
                # Si Eml est présente, elle doit être >= 0
                if getattr(r, "Eml", None) is not None and r.Eml < 0:
                    raise ConfigurationError(f"{fam}[{i+1}]: Eml doit être >= 0 si présente")

                if fam in ("normale", "grande"):
                    if r.course_min is None or r.course_max is None:
                        raise ConfigurationError(f"{fam}[{i+1}]: course_min et course_max obligatoires")
                    if r.course_min > r.course_max:
                        raise ConfigurationError(f"{fam}[{i+1}]: course_min > course_max")
                else:
                    if r.course_min is not None or r.course_max is not None:
                        raise ConfigurationError(f"{fam}[{i+1}]: course_min/course_max interdits")

            # chevauchements (normale/grande): tolérance stricte des intervalles
            if fam in ("normale", "grande"):
                # Grouper par graduation
                grads: Dict[float, List[ToleranceRule]] = {}
                for r in items:
                    grads.setdefault(r.graduation, []).append(r)
                for g, lst in grads.items():
                    lst_sorted = sorted(lst, key=lambda rr: (rr.course_max, rr.course_min))
                    # Vérifier qu'il n'y a pas de recouvrement: next.course_min < prev.course_max interdit
                    for i in range(len(lst_sorted) - 1):
                        prev = lst_sorted[i]
                        nxt = lst_sorted[i + 1]
                        if nxt.course_min is None or prev.course_max is None:
                            continue
                        if nxt.course_min < prev.course_max - self.EPS:
                            raise OverlapError(f"{fam}: chevauchement entre règles (graduation {g:.6f})")
            else:
                # faible/limitée: graduation unique non dupliquée
                seen: List[float] = []
                for i, r in enumerate(items):
                    if any(self._feq(r.graduation, g, self.EPS) for g in seen):
                        raise OverlapError(f"{fam}: graduation {r.graduation:.6f} mm dupliquée")
                    seen.append(r.graduation)

    def _match_course_group_strict(self, rules_same_grad: List[ToleranceRule], course: float) -> List[ToleranceRule]:
        """Intervalles stricts par groupe (même graduation). Première ligne inclusive; suivantes: min exclusive, max inclusive."""
        rules_sorted = sorted(rules_same_grad, key=lambda r: (r.course_max, r.course_min))
        matches: List[ToleranceRule] = []
        for i, r in enumerate(rules_sorted):
            cmin = r.course_min if r.course_min is not None else float("-inf")
            cmax = r.course_max if r.course_max is not None else float("inf")
            if i == 0:
                if cmin - self.EPS <= course <= cmax + self.EPS:
                    matches.append(r)
            else:
                if course > cmin + self.EPS and course <= cmax + self.EPS:
                    matches.append(r)
        return matches

    def match(self, family: str, graduation: float, course: float | None) -> Optional[ToleranceRule]:
        """Retourne la règle applicable ou None. Lève OverlapError si plusieurs match."""
        if family not in self.rules:
            return None
        fam_rules = self.rules[family]
        same_grad = [r for r in fam_rules if self._feq(r.graduation, graduation, self.EPS)]
        if family in ("normale", "grande"):
            if course is None:
                return None
            matches = self._match_course_group_strict(same_grad, course)
        else:
            matches = list(same_grad)
        if len(matches) > 1:
            raise OverlapError("Plusieurs règles correspondent (graduation/course).")
        return matches[0] if matches else None

