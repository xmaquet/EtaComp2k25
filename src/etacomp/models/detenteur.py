"""Modèle détenteur : code ES + libellé."""
from __future__ import annotations
from pydantic import BaseModel


class Detenteur(BaseModel):
    """Un détenteur est identifié par son code ES avec un libellé descriptif."""
    code_es: str
    libelle: str

    def display_name(self) -> str:
        """Retourne 'code_es — libelle' pour affichage."""
        return f"{self.code_es} — {self.libelle}"
