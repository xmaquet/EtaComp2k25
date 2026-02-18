"""Configuration des éléments utilisés lors des exports (PDF, etc.)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import json

from pydantic import BaseModel, Field

from .paths import get_data_dir

EXPORT_CONFIG_FILE = "export_config.json"


class ExportConfig(BaseModel):
    """Éléments pour personnaliser les documents exportés."""
    entite: str = Field("", description="Nom de l'entité (ex: 14eBSMAT)")
    image_path: Optional[str] = Field(None, description="Chemin vers l'image (logo, écusson)")
    document_title: str = Field("", description="Titre du document d'export")
    document_reference: str = Field("", description="Référence pour le document exporté")
    texte_normes: str = Field("", description="Bloc de texte (normes applicables, etc.)")


def _config_path() -> Path:
    return get_data_dir() / EXPORT_CONFIG_FILE


def load_export_config() -> ExportConfig:
    path = _config_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ExportConfig.model_validate(data)
        except Exception:
            pass
    return ExportConfig()


def save_export_config(cfg: ExportConfig) -> Path:
    path = _config_path()
    get_data_dir().mkdir(parents=True, exist_ok=True)
    path.write_text(cfg.model_dump_json(indent=2), encoding="utf-8")
    return path
