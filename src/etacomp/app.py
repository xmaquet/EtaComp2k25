from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from .ui.main_window import MainWindow
from .ui.themes import load_theme_qss
from .config.prefs import load_prefs
from .package_resources import first_existing_path
from .io.serial_manager import serial_manager


def _apply_app_icon(app: QApplication) -> None:
    """Icône depuis les ressources embarquées du package."""
    icon_path = first_existing_path(
        (
            "resources/etaComp.svg",
            "resources/etaComp.png",
            "resources/14eBSMAT_insigne.png",
        )
    )
    if icon_path is None:
        return
    try:
        app.setWindowIcon(QIcon(str(icon_path)))
    except Exception:
        pass


def run():
    import sys
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    app = QApplication(sys.argv)

    def _release_serial_port() -> None:
        try:
            serial_manager.close()
        except Exception:
            pass

    app.aboutToQuit.connect(_release_serial_port)

    prefs = load_prefs()
    qss = load_theme_qss(prefs.theme)
    if qss:
        app.setStyleSheet(qss)

    _apply_app_icon(app)

    window = MainWindow()
    window.showMaximized()
    try:
        window.raise_()
        window.activateWindow()
    except Exception:
        pass
    sys.exit(app.exec())
