from PySide6.QtWidgets import QMainWindow, QTabWidget
from .tabs.session import SessionTab
from .tabs.measures import MeasuresTab
from .tabs.library import LibraryTab
from .tabs.settings import SettingsTab
from .tabs.fidelity_gap import FidelityGapTab        # ⬅️ add
from .tabs.finalization import FinalizationTab        # ⬅️ add
from .tabs.calibration_curve import CalibrationCurveTab  # ⬅️ add
from ..config.defaults import APP_TITLE


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 800)

        tabs = QTabWidget()

        self.session_tab = SessionTab()
        self.measures_tab = MeasuresTab()
        self.library_tab = LibraryTab()
        self.settings_tab = SettingsTab()

        # Connexions existantes
        self.library_tab.comparators_changed.connect(self.session_tab.reload_comparators)

        # Onglets principaux
        tabs.addTab(self.session_tab, "Session")
        tabs.addTab(self.measures_tab, "Mesures")
        tabs.addTab(self.library_tab, "Bibliothèque des comparateurs")
        tabs.addTab(self.settings_tab, "Paramètres")

        # ✅ Nouveaux onglets visibles
        tabs.addTab(FidelityGapTab(), "Écart de fidélité")
        tabs.addTab(CalibrationCurveTab(), "Courbe d'étalonnage")
        tabs.addTab(FinalizationTab(), "Finalisation")

        self.setCentralWidget(tabs)
