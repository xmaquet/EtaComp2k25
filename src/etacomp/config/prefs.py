from __future__ import annotations

from pathlib import Path
from typing import Optional, Literal
import json

from pydantic import BaseModel, Field

from .defaults import DEFAULT_THEME
from .paths import get_data_dir


class Preferences(BaseModel):
    # Apparence
    theme: Literal["light", "dark"] = DEFAULT_THEME

    # Session par défaut
    default_series_count: int = 0
    default_measures_per_series: int = 0

    # Sauvegarde auto
    autosave_enabled: bool = False
    autosave_interval_s: int = 60  # toutes les 60s par défaut

    # Langue (placeholder)
    language: Optional[str] = Field(default=None, description="ex. 'fr', 'en'")

    # (Placeholders futurs possibles : data_dir_custom, decimal_sep, etc.)


def _config_path() -> Path:
    return get_data_dir() / "config.json"


def load_prefs() -> Preferences:
    cfg = _config_path()
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            return Preferences.model_validate(data)
        except Exception:
            pass  # on retombe sur les valeurs par défaut
    return Preferences()


def save_prefs(p: Preferences) -> Path:
    cfg = _config_path()
    cfg.write_text(p.model_dump_json(indent=2), encoding="utf-8")
    return cfg
