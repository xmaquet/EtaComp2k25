from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


TOL = 1e-6


class RangeType(str, Enum):
    NORMALE = "normale"
    GRANDE = "grande"
    FAIBLE = "faible"
    LIMITEE = "limitee"
    
    @property
    def display_name(self) -> str:
        """Retourne le libellé complet de la famille de course."""
        labels = {
            "normale": "Course normale",
            "grande": "Course longue",
            "faible": "Course faible", 
            "limitee": "Course limitée"
        }
        return labels[self.value]


class ComparatorProfile(BaseModel):
    """Profil de comparateur avec validation stricte selon les spécifications."""
    
    reference: str = Field(..., min_length=1, description="Référence unique du comparateur")
    manufacturer: Optional[str] = Field(None, description="Fabricant")
    description: Optional[str] = Field(None, description="Description")
    graduation: float = Field(..., gt=0, description="Graduation en millimètres (valeur unique)")
    course: float = Field(..., gt=0, description="Course maximale en millimètres")
    range_type: RangeType = Field(..., description="Type de comparateur")
    targets: List[float] = Field(..., min_length=11, max_length=11, description="Liste des 11 cibles en millimètres")
    
    @property
    def filename(self) -> str:
        base = self.reference.strip().replace(" ", "_")
        return f"{base}.json"

    @model_validator(mode="after")
    def _validate_profile(self):
        """Validation stricte selon les spécifications."""
        targets = self.targets
        
        # Vérifier qu'il y a exactement 11 cibles
        if len(targets) != 11:
            raise ValueError(f"Le profil doit contenir exactement 11 cibles (actuel: {len(targets)})")
        
        # Vérifier que la première cible est 0 (avec tolérance)
        if abs(min(targets) - 0.0) > TOL:
            raise ValueError(f"La première cible doit être 0.0 mm (actuel: {min(targets):.6f} mm)")
        
        # Vérifier que toutes les cibles sont dans la plage [0, course]
        for i, target in enumerate(targets, start=1):
            if target < -TOL or target > self.course + TOL:
                raise ValueError(f"Cible {i}: {target:.6f} mm hors plage [0, {self.course:.6f}] mm")
        
        # Vérifier que les cibles sont non-décroissantes (croissantes ou égales)
        for i in range(1, len(targets)):
            if targets[i] + TOL < targets[i-1]:
                raise ValueError(f"Cibles non ordonnées: {targets[i-1]:.6f} mm > {targets[i]:.6f} mm")
        
        return self


def load_profile(path: Path) -> Optional[ComparatorProfile]:
    """Charge un profil de comparateur depuis un fichier JSON."""
    if not path.exists():
        return None
    
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        return ComparatorProfile.model_validate(data)
    except Exception as e:
        raise ValueError(f"Impossible de charger le profil depuis {path}: {e}")


def save_profile(path: Path, profile: ComparatorProfile) -> None:
    """Sauvegarde un profil de comparateur dans un fichier JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        import json
        path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    except Exception as e:
        raise ValueError(f"Impossible de sauvegarder le profil vers {path}: {e}")


# Alias pour compatibilité avec l'ancien code
Comparator = ComparatorProfile
