from __future__ import annotations

from pathlib import Path
from typing import Literal
import json

from .paths import get_data_dir


TesaDecimalDisplay = Literal["dot", "comma"]
TesaFrameMode = Literal["silence", "eol"]
TesaEol = Literal["CR", "LF", "CRLF"]


DEFAULT_TESA_CONFIG = {
    "enabled": True,
    "frame_mode": "silence",                 # "silence" | "eol"
    "silence_ms": 120,
    "eol": "CRLF",                           # "CR" | "LF" | "CRLF"
    "mask_7bit": True,
    "strip_chars": "\\r\\n\\0 ",
    "value_regex": r"[-+]?\d+(?:[.,]\d+)?|[-+]?[.,]\d+",
    "decimals": 3,
    "decimal_display": "dot",                # "dot" | "comma"
}


def _tesa_path() -> Path:
    return get_data_dir() / "tesa_config.json"


def load_tesa_config() -> dict:
    """Charge la configuration TESA depuis ~/.EtaComp2K25/tesa_config.json ou retourne les valeurs par défaut."""
    path = _tesa_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Merge avec défauts pour tolérer champs manquants
            merged = {**DEFAULT_TESA_CONFIG, **(data or {})}
            return merged
        except Exception:
            return DEFAULT_TESA_CONFIG.copy()
    return DEFAULT_TESA_CONFIG.copy()


def save_tesa_config(cfg: dict) -> Path:
    """Sauvegarde la configuration TESA."""
    path = _tesa_path()
    # Merge avant sauvegarde pour garantir cohérence
    data = {**DEFAULT_TESA_CONFIG, **(cfg or {})}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path

