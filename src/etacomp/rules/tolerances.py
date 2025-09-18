from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Literal, Any

from ..models.comparator import RangeType


@dataclass
class ToleranceRule:
    """Une règle de tolérance pour une famille donnée."""
    graduation_min: float  # mm
    graduation_max: float  # mm
    course_min: float      # mm
    course_max: float      # mm
    Emt: float            # mm - Erreur de mesure totale
    Eml: float            # mm - Erreur de mesure locale
    Ef: float             # mm - Erreur de fidélité
    Eh: float             # mm - Erreur d'hystérésis

    def __post_init__(self):
        """Validation des bornes."""
        if self.graduation_min > self.graduation_max:
            raise ValueError(f"graduation_min ({self.graduation_min}) > graduation_max ({self.graduation_max})")
        if self.course_min > self.course_max:
            raise ValueError(f"course_min ({self.course_min}) > course_max ({self.course_max})")
        for name, val in [("Emt", self.Emt), ("Eml", self.Eml), ("Ef", self.Ef), ("Eh", self.Eh)]:
            if val <= 0:
                raise ValueError(f"{name} doit être > 0 (actuel: {val})")

    def matches(self, graduation: float, course: float) -> bool:
        """Vérifie si cette règle s'applique à graduation/course."""
        return (self.graduation_min <= graduation <= self.graduation_max and
                self.course_min <= course <= self.course_max)

    def overlaps(self, other: ToleranceRule) -> bool:
        """Vérifie si cette règle chevauche avec other."""
        return (self.graduation_min <= other.graduation_max and
                other.graduation_min <= self.graduation_max and
                self.course_min <= other.course_max and
                other.course_min <= self.course_max)


@dataclass
class Verdict:
    """Résultat d'évaluation des tolérances."""
    status: Literal["apte", "inapte", "indetermine"]
    rule: Optional[ToleranceRule] = None
    exceed: Optional[Dict[str, float]] = None  # mm au-delà des limites
    messages: List[str] = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []


class ConfigurationOverlapError(Exception):
    """Erreur de configuration : chevauchement de règles."""
    pass


class ToleranceRuleEngine:
    """Moteur de règles de tolérances."""
    
    def __init__(self):
        self.rules: Dict[RangeType, List[ToleranceRule]] = {
            rt: [] for rt in RangeType
        }

    def load(self, path: Path) -> None:
        """Charge les règles depuis un fichier JSON."""
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self.rules.clear()
        for family_str, rules_list in data.items():
            try:
                family = RangeType(family_str)
                self.rules[family] = []
                for rule_dict in rules_list:
                    rule = ToleranceRule(**rule_dict)
                    self.rules[family].append(rule)
            except (ValueError, KeyError) as e:
                raise ValueError(f"Règle invalide pour famille '{family_str}': {e}")

    def save(self, path: Path) -> None:
        """Sauvegarde les règles dans un fichier JSON."""
        data = {}
        for family, rules_list in self.rules.items():
            data[family.value] = [
                {
                    "graduation_min": r.graduation_min,
                    "graduation_max": r.graduation_max,
                    "course_min": r.course_min,
                    "course_max": r.course_max,
                    "Emt": r.Emt,
                    "Eml": r.Eml,
                    "Ef": r.Ef,
                    "Eh": r.Eh,
                }
                for r in rules_list
            ]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def validate(self) -> List[str]:
        """Valide la configuration et retourne les erreurs."""
        errors = []
        for family, rules_list in self.rules.items():
            # Vérifier les chevauchements
            for i, rule1 in enumerate(rules_list):
                for j, rule2 in enumerate(rules_list[i+1:], i+1):
                    if rule1.overlaps(rule2):
                        errors.append(
                            f"Famille {family.value}: chevauchement entre règles {i+1} et {j+1}"
                        )
        return errors

    def match(self, family: RangeType, graduation: float, course: float) -> Optional[ToleranceRule]:
        """Trouve la règle applicable pour family/graduation/course."""
        candidates = []
        for rule in self.rules[family]:
            if rule.matches(graduation, course):
                candidates.append(rule)
        
        if len(candidates) > 1:
            raise ConfigurationOverlapError(
                f"Plusieurs règles matchent pour {family.value}, graduation {graduation:.3f}, course {course:.3f}"
            )
        return candidates[0] if candidates else None

    def evaluate(self, profile, errors: Dict[str, float]) -> Verdict:
        """Évalue les erreurs contre les règles applicables."""
        if not profile.graduation or not profile.course or not profile.range_type:
            return Verdict(
                status="indetermine",
                messages=["Profil incomplet : graduation, course ou famille manquants"]
            )
        
        try:
            rule = self.match(profile.range_type, profile.graduation, profile.course)
        except ConfigurationOverlapError as e:
            return Verdict(
                status="indetermine",
                messages=[f"Configuration invalide : {e}"]
            )
        
        if rule is None:
            return Verdict(
                status="indetermine",
                messages=[
                    f"Aucune règle de tolérance ne couvre {profile.range_type.value}, "
                    f"graduation {profile.graduation:.3f} mm, course {profile.course:.3f} mm. "
                    f"Veuillez compléter les règles dans Paramètres ▸ Règles."
                ]
            )
        
        # Comparer les erreurs aux limites
        exceed = {}
        messages = []
        status = "apte"
        
        for error_name, limit_name in [("Emt", "Emt"), ("Eml", "Eml"), ("Ef", "Ef"), ("Eh", "Eh")]:
            if error_name in errors:
                measured = errors[error_name]
                limit = getattr(rule, limit_name)
                if measured > limit:
                    delta = measured - limit
                    exceed[error_name] = delta
                    status = "inapte"
                    messages.append(
                        f"{error_name} dépasse la limite de {limit:.3f} mm "
                        f"(limite {limit:.3f} mm, mesuré {measured:.3f} mm)"
                    )
        
        return Verdict(
            status=status,
            rule=rule,
            exceed=exceed if exceed else None,
            messages=messages
        )


def get_default_rules_path() -> Path:
    """Chemin par défaut du fichier de règles."""
    from ..config.paths import get_data_dir
    return get_data_dir() / "rules" / "tolerances.json"


def create_default_rules() -> ToleranceRuleEngine:
    """Crée un moteur avec des règles par défaut."""
    engine = ToleranceRuleEngine()
    
    # Règles par défaut pour famille "normale"
    engine.rules[RangeType.NORMALE] = [
        ToleranceRule(
            graduation_min=0.005, graduation_max=0.01,
            course_min=5.0, course_max=20.0,
            Emt=0.013, Eml=0.010, Ef=0.003, Eh=0.010
        )
    ]
    
    return engine
