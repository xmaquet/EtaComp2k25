"""Modèle banc étalon : référence, marque du capteur, date de validité."""
from __future__ import annotations
from pydantic import BaseModel


class BancEtalon(BaseModel):
    """Un banc étalon de calibration."""
    reference: str
    marque_capteur: str
    date_validite: str  # format YYYY-MM-DD ou texte libre
    is_default: bool = False

    def display_name(self) -> str:
        """Retourne une représentation courte pour affichage."""
        return f"{self.reference} — {self.marque_capteur}"
