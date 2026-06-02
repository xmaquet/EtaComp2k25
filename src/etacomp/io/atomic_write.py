"""Écriture atomique de fichiers texte (tmp + os.replace)."""
from __future__ import annotations

import os
from pathlib import Path


def atomic_write(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """
    Écrit le contenu de façon atomique : fichier .tmp puis renommage.

    En cas d'échec avant le replace, le fichier cible existant est conservé.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    try:
        tmp_path.write_text(content, encoding=encoding)
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise
