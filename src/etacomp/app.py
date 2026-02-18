from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from pathlib import Path
from .ui.main_window import MainWindow
from .ui.themes import load_theme_qss
from .config.prefs import load_prefs


def _apply_app_icon(app: QApplication) -> None:
    """
    Tente d'appliquer l'icône de l'application.
    Priorités:
    1) C:\\Users\\xmaqu\\Documents\\etaComp.svg (fourni par l'utilisateur)
    2) src/etacomp/resources/etaComp.svg
    3) src/etacomp/resources/etaComp.png
    """
    candidates = [
        Path(r"C:\Users\xmaqu\Documents\etaComp.svg"),
        Path("src/etacomp/resources/etaComp.svg"),
        Path("src/etacomp/resources/etaComp.png"),
    ]
    for p in candidates:
        try:
            if p.exists():
                app.setWindowIcon(QIcon(str(p)))
                break
        except Exception:
            continue


def run():
    import sys
    app = QApplication(sys.argv)

    # Thème (depuis préférences)
    prefs = load_prefs()
    qss = load_theme_qss(prefs.theme)
    if qss:
        app.setStyleSheet(qss)

    # Icône d'application (si disponible)
    _apply_app_icon(app)

    window = MainWindow()
    window.showMaximized()
    try:
        window.raise_()
        window.activateWindow()
    except Exception:
        pass
    sys.exit(app.exec())
