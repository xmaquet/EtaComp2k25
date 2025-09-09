from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QDialog, QLabel,
    QVBoxLayout, QPushButton
)
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtCore import Qt

from .tabs.session import SessionTab
from .tabs.measures import MeasuresTab
from .tabs.library import LibraryTab
from .tabs.settings import SettingsTab
from .tabs.fidelity_gap import FidelityGapTab
from .tabs.finalization import FinalizationTab
from .tabs.calibration_curve import CalibrationCurveTab
from ..config.defaults import APP_TITLE
from ..config.prefs import load_prefs
from .themes import apply_theme


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 800)

        # --- Onglets ---
        self.tabs = QTabWidget()
        self.session_tab = SessionTab()
        self.measures_tab = MeasuresTab()
        self.fidelity_tab = FidelityGapTab()
        self.calibration_tab = CalibrationCurveTab()
        self.finalization_tab = FinalizationTab()
        self.library_tab = LibraryTab()
        self.settings_tab = SettingsTab()

        self.tabs.addTab(self.session_tab, "Session")
        self.tabs.addTab(self.measures_tab, "Mesures")
        self.tabs.addTab(self.fidelity_tab, "Écart de fidélité")
        self.tabs.addTab(self.calibration_tab, "Courbe d'étalonnage")
        self.tabs.addTab(self.finalization_tab, "Finalisation")
        self.tabs.addTab(self.library_tab, "Bibliothèque des comparateurs")
        self.tabs.addTab(self.settings_tab, "Paramètres")
        self.setCentralWidget(self.tabs)

        # --- Appliquer le thème au démarrage ---
        prefs = load_prefs()
        apply_theme(self, getattr(prefs, "theme", "dark"))

        # --- Écouter les changements de thème depuis Paramètres ---
        try:
            self.settings_tab.themeChanged.connect(self._on_theme_changed)
        except Exception:
            pass

        # --- Menu Aide > À propos ---
        self._setup_help_menu()

    # ===== Menus =====
    def _setup_help_menu(self):
        menubar = self.menuBar()
        aide_menu = menubar.addMenu("&Aide")

        about_action = QAction("À propos…", self)
        about_action.triggered.connect(self._show_about_dialog)
        aide_menu.addAction(about_action)

    # ===== Thème =====
    def _on_theme_changed(self, theme: str):
        apply_theme(self, theme)

    # ===== À propos =====
    def _show_about_dialog(self):
        version = "v0.1.0"

        dialog = QDialog(self)
        dialog.setWindowTitle(f"À propos — {APP_TITLE}")
        dialog.resize(420, 340)

        layout = QVBoxLayout(dialog)

        # Logo (place le fichier ici : src/etacomp/resources/14eBSMAT_insigne.png)
        logo_label = QLabel()
        pixmap = QPixmap("src/etacomp/resources/14eBSMAT_insigne.png")
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaledToWidth(120, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)

        # Texte HTML
        texte = (
            f"<b>{APP_TITLE}</b><br>"
            "Outil de gestion de sessions de mesure et de comparateurs.<br><br>"
            f"<b>Version :</b> {version}<br>"
            "<b>Auteur :</b> 14eBSMAT / ICDD MAQUET Xavier<br>"
            "<b>Tech :</b> PySide6, JSON, UI modulaire<br><br>"
            "© 2025 — Tous droits réservés."
        )
        text_label = QLabel(texte)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)

        # Bouton fermer
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

        dialog.exec()
