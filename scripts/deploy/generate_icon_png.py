#!/usr/bin/env python3
"""Génère les PNG d'icône à partir de etaComp.svg (PySide6)."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication


def main() -> int:
    app = QApplication(sys.argv)
    home = Path.home()
    src = home / "EtaComp2k25/src/etacomp/resources/etaComp.svg"
    if not src.is_file():
        print(f"SVG introuvable: {src}", file=sys.stderr)
        return 1

    base = home / ".local/share/icons/hicolor"
    icon = QIcon(str(src))
    if icon.isNull():
        print("QIcon vide — SVG non chargé", file=sys.stderr)
        return 1

    for size, sub in ((256, "256x256"), (48, "48x48")):
        out_dir = base / sub / "apps"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / "etacomp2k25.png"
        pm = icon.pixmap(QSize(size, size))
        if pm.isNull() or not pm.save(str(out), "PNG"):
            print(f"Échec écriture: {out}", file=sys.stderr)
            return 1
        print(f"OK {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
