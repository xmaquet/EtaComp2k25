from PySide6.QtWidgets import QApplication
from .ui.main_window import MainWindow
from .ui.themes import load_theme_qss
from .config.prefs import load_prefs


def run():
    import sys
    app = QApplication(sys.argv)

    # Thème (depuis préférences)
    prefs = load_prefs()
    qss = load_theme_qss(prefs.theme)
    if qss:
        app.setStyleSheet(qss)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
