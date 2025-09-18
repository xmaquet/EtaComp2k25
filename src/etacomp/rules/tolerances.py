from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Literal, Any

from ..models.comparator import RangeType


# Tolérance pour les comparaisons de graduation
EPS = 1e-6


def grad_eq(a: float, b: float) -> bool:
    """Compare deux graduations avec tolérance."""
    return abs(a - b) <= EPS


@dataclass
class ToleranceRule:
    """Une règle de tolérance pour une famille donnée."""
    graduation: float  # mm - valeur unique
    course_min: Optional[float] = None  # mm - seulement pour normale/grande
    course_max: Optional[float] = None  # mm - seulement pour normale/grande
    Emt: float = 0.0  # mm - Erreur de mesure totale
    Eml: float = 0.0  # mm - Erreur de mesure locale
    Ef: float = 0.0   # mm - Erreur de fidélité
    Eh: float = 0.0   # mm - Erreur d'hystérésis

    def __post_init__(self):
        """Validation des bornes."""
        if self.graduation <= 0:
            raise ValueError(f"graduation doit être > 0 (actuel: {self.graduation})")
        
        # Pour normale/grande, vérifier les bornes de course
        if self.course_min is not None and self.course_max is not None:
            if self.course_min > self.course_max:
                raise ValueError(f"course_min ({self.course_min}) > course_max ({self.course_max})")
            if self.course_min < 0 or self.course_max < 0:
                raise ValueError("course_min et course_max doivent être >= 0")
        
        # Vérifier que les limites de tolérance sont >= 0
        for name, val in [("Emt", self.Emt), ("Eml", self.Eml), ("Ef", self.Ef), ("Eh", self.Eh)]:
            if val < 0:
                raise ValueError(f"{name} doit être >= 0 (actuel: {val})")

    def matches(self, graduation: float, course: Optional[float] = None) -> bool:
        """Vérifie si cette règle s'applique à graduation/course."""
        if not grad_eq(self.graduation, graduation):
            return False
        
        # Pour normale/grande, vérifier la course
        if self.course_min is not None and self.course_max is not None:
            if course is None:
                return False
            return self.course_min <= course <= self.course_max
        
        # Pour faible/limitée, pas de vérification de course
        return True

    def overlaps(self, other: ToleranceRule) -> bool:
        """Vérifie si cette règle chevauche avec other."""
        if not grad_eq(self.graduation, other.graduation):
            return False
        
        # Si les deux ont des plages de course, vérifier le chevauchement
        if (self.course_min is not None and self.course_max is not None and
            other.course_min is not None and other.course_max is not None):
            return (self.course_min <= other.course_max and
                    other.course_min <= self.course_max)
        
        # Si l'une n'a pas de plage de course, pas de chevauchement possible
        return False


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
    """Moteur de règles de tolérances selon les nouvelles spécifications."""
    
    def __init__(self):
        self.rules: Dict[str, List[ToleranceRule]] = {
            "normale": [],
            "grande": [],
            "faible": [],
            "limitee": []
        }

    def load(self, path: Path) -> None:
        """Charge les règles depuis un fichier JSON."""
        if not path.exists():
            return
        
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.rules.clear()
            
            for family_str, rules_list in data.items():
                if family_str not in self.rules:
                    raise ValueError(f"Famille inconnue: {family_str}")
                
                self.rules[family_str] = []
                for rule_dict in rules_list:
                    rule = ToleranceRule(**rule_dict)
                    self.rules[family_str].append(rule)
                    
        except Exception as e:
            raise ValueError(f"Impossible de charger les règles depuis {path}: {e}")

    def save(self, path: Path) -> None:
        """Sauvegarde les règles dans un fichier JSON."""
        data = {}
        for family, rules_list in self.rules.items():
            data[family] = []
            for rule in rules_list:
                rule_dict = {
                    "graduation": rule.graduation,
                    "Emt": rule.Emt,
                    "Eml": rule.Eml,
                    "Ef": rule.Ef,
                    "Eh": rule.Eh,
                }
                # Ajouter course_min/max seulement si présents
                if rule.course_min is not None:
                    rule_dict["course_min"] = rule.course_min
                if rule.course_max is not None:
                    rule_dict["course_max"] = rule.course_max
                
                data[family].append(rule_dict)
        
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def validate(self) -> List[str]:
        """Valide la configuration et retourne les erreurs."""
        errors = []
        
        for family, rules_list in self.rules.items():
            # Vérifier les règles individuelles
            for i, rule in enumerate(rules_list):
                try:
                    rule.__post_init__()  # Validation de la règle
                except ValueError as e:
                    errors.append(f"{family}[{i+1}]: {e}")
            
            # Vérifier les chevauchements
            for i, rule1 in enumerate(rules_list):
                for j, rule2 in enumerate(rules_list[i+1:], i+1):
                    if rule1.overlaps(rule2):
                        errors.append(f"{family}: chevauchement entre règles {i+1} et {j+1}")
            
            # Vérifications spécifiques par famille
            if family in ("normale", "grande"):
                # Vérifier que toutes les règles ont course_min/max
                for i, rule in enumerate(rules_list):
                    if rule.course_min is None or rule.course_max is None:
                        errors.append(f"{family}[{i+1}]: course_min et course_max obligatoires")
            
            elif family in ("faible", "limitee"):
                # Vérifier qu'aucune règle n'a course_min/max
                for i, rule in enumerate(rules_list):
                    if rule.course_min is not None or rule.course_max is not None:
                        errors.append(f"{family}[{i+1}]: course_min/course_max interdits")
                
                # Vérifier l'unicité des graduations
                graduations = [rule.graduation for rule in rules_list]
                seen = set()
                for grad in graduations:
                    if any(grad_eq(grad, seen_grad) for seen_grad in seen):
                        errors.append(f"{family}: graduation {grad:.6f} mm dupliquée")
                    seen.add(grad)
        
        return errors

    def match(self, family: str, graduation: float, course: Optional[float] = None) -> Optional[ToleranceRule]:
        """Trouve la règle applicable pour family/graduation/course."""
        if family not in self.rules:
            return None
        
        candidates = []
        for rule in self.rules[family]:
            if rule.matches(graduation, course):
                candidates.append(rule)
        
        if len(candidates) > 1:
            raise ConfigurationOverlapError(
                f"Plusieurs règles matchent pour {family}, graduation {graduation:.6f} mm"
                f"{f', course {course:.6f} mm' if course is not None else ''}"
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
            rule = self.match(profile.range_type.value.lower(), profile.graduation, profile.course)
        except ConfigurationOverlapError as e:
            return Verdict(
                status="indetermine",
                messages=[f"Configuration invalide : {e}"]
            )
        
        if rule is None:
            course_info = f" et course {profile.course:.3f} mm" if profile.range_type.value.lower() in ("normale", "grande") else ""
            return Verdict(
                status="indetermine",
                messages=[
                    f"Aucune règle ne couvre la famille {profile.range_type.value} "
                    f"avec graduation {profile.graduation:.3f} mm{course_info}. "
                    f"Complétez Paramètres ▸ Règles."
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
                if measured > limit + EPS:
                    delta = measured - limit
                    exceed[error_name] = delta
                    status = "inapte"
                    messages.append(
                        f"{error_name} dépasse de {delta:.3f} mm "
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
    """Crée un moteur avec des règles par défaut selon les spécifications."""
    engine = ToleranceRuleEngine()
    
    # Règles par défaut selon l'exemple "bouchon"
    engine.rules["normale"] = [
        ToleranceRule(
            graduation=0.01, course_min=0.0, course_max=10.0,
            Emt=0.013, Eml=0.010, Ef=0.003, Eh=0.010
        ),
        ToleranceRule(
            graduation=0.01, course_min=10.0, course_max=20.0,
            Emt=0.015, Eml=0.012, Ef=0.003, Eh=0.012
        )
    ]
    
    engine.rules["grande"] = [
        ToleranceRule(
            graduation=0.01, course_min=20.0, course_max=30.0,
            Emt=0.025, Eml=0.020, Ef=0.005, Eh=0.020
        )
    ]
    
    engine.rules["faible"] = [
        ToleranceRule(
            graduation=0.001,
            Emt=0.008, Eml=0.006, Ef=0.002, Eh=0.006
        )
    ]
    
    engine.rules["limitee"] = [
        ToleranceRule(
            graduation=0.001,
            Emt=0.005, Eml=0.004, Ef=0.0015, Eh=0.004
        )
    ]
    
    return engine
