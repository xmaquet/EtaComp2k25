"""Accès aux fichiers embarqués (importlib.resources) — issue #14."""
from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Iterator, Optional


def resource_path(*parts: str) -> Path:
    """Chemin vers une ressource du package etacomp (install ou editable)."""
    return Path(resources.files("etacomp")).joinpath(*parts)


def read_text_resource(*parts: str, encoding: str = "utf-8") -> str:
    ref = resources.files("etacomp").joinpath(*parts)
    return ref.read_text(encoding=encoding)


def first_existing_path(candidates: Iterator[str]) -> Optional[Path]:
    for rel in candidates:
        p = resource_path(rel)
        if p.is_file():
            return p
    return None
