"""Lanceur autonome — sauvegarde / restauration EtaComp."""
from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .config.prefs import load_prefs
from .package_resources import first_existing_path
from .ui.backup_window import BackupWindow
from .ui.themes import load_theme_qss


def _apply_app_icon(app: QApplication) -> None:
    icon_path = first_existing_path(
        (
            "resources/etaCompBackup.svg",
            "resources/etaCompBackup.png",
            "resources/etaComp.svg",
        )
    )
    if icon_path is None:
        return
    try:
        app.setWindowIcon(QIcon(str(icon_path)))
    except Exception:
        pass


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    app = QApplication(sys.argv)
    app.setApplicationName("EtaComp Backup")

    prefs = load_prefs()
    qss = load_theme_qss(prefs.theme)
    if qss:
        app.setStyleSheet(qss)

    _apply_app_icon(app)

    window = BackupWindow()
    window.resize(580, 540)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
