"""Noms de fichiers sûrs pour Windows (sessions, comparateurs, exports)."""
from __future__ import annotations

import re
import unicodedata

_WINDOWS_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})


def sanitize_filename(name: str, *, fallback: str = "sans_ref", max_len: int = 120) -> str:
    """
    Retourne un segment de nom de fichier valide sous Windows.

    Caractères interdits remplacés par « _ », espaces en bordure retirés,
    noms réservés (CON, PRN, …) préfixés par « _ ».
    """
    s = unicodedata.normalize("NFKC", (name or "").strip())
    if not s:
        return fallback
    s = _WINDOWS_FORBIDDEN.sub("_", s)
    s = re.sub(r"_+", "_", s).strip(" .")
    if not s:
        return fallback
    stem = s.split(".")[0].upper()
    if stem in _RESERVED_NAMES:
        s = f"_{s}"
    if len(s) > max_len:
        s = s[:max_len].rstrip(" .")
    return s or fallback
