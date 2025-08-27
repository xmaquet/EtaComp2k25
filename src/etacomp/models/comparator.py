from pydantic import BaseModel, Field
from typing import List, Optional


class Comparator(BaseModel):
    reference: str
    manufacturer: Optional[str] = None
    description: Optional[str] = None
    # Valeurs cibles (mm) associées au comparateur
    targets: List[float] = Field(default_factory=list)

    @property
    def filename(self) -> str:
        """Nom de fichier JSON recommandé (sans espaces)."""
        base = self.reference.strip().replace(" ", "_")
        return f"{base}.json"
