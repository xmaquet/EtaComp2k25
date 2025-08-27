from PySide6.QtWidgets import QMainWindow, QTabWidget
from .tabs.session import SessionTab
from .tabs.measures import MeasuresTab
from .tabs.library import LibraryTab
from .tabs.settings import SettingsTab
from ..config.defaults import APP_TITLE

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 800)

        tabs = QTabWidget()
        tabs.addTab(SessionTab(), "Session")
        tabs.addTab(MeasuresTab(), "Mesures")
        tabs.addTab(LibraryTab(), "Bibliothèque des comparateurs")
        tabs.addTab(SettingsTab(), "Paramètres")

        self.setCentralWidget(tabs)
