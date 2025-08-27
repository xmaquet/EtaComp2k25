from PySide6.QtWidgets import QApplication
from .ui.main_window import MainWindow
from .config.defaults import DEFAULT_THEME
from .ui.themes import load_theme_qss


def run():
    import sys
    app = QApplication(sys.argv)

    qss = load_theme_qss(DEFAULT_THEME)
    if qss:
        app.setStyleSheet(qss)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
