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
from .tabs.fidelity_deviations import FidelityDeviationsTab
from .tabs.finalization import FinalizationTab
from .tabs.calibration_curve import CalibrationCurveTab
from ..config.defaults import APP_TITLE
from .. import __version__
from ..config.prefs import load_prefs
from .themes import apply_theme
from .help_dialog import HelpDialog
from ..state.session_store import session_store


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 800)
        self.statusBar().showMessage("")  # barre de statut pour feedback (export PDF, etc.)

        # --- Onglets ---
        self.tabs = QTabWidget()
        self.session_tab = SessionTab()
        self.measures_tab = MeasuresTab()
        self.fidelity_tab = FidelityDeviationsTab(
            get_runtime_session=self.get_rt_session,
            go_to_session_tab=self.select_session_tab,
        )
        self.calibration_tab = CalibrationCurveTab(
            get_runtime_session=self.get_rt_session
        )
        self.finalization_tab = FinalizationTab()
        self.library_tab = LibraryTab()
        self.settings_tab = SettingsTab()

        self.tabs.addTab(self.session_tab, "Session")
        self.tabs.addTab(self.measures_tab, "Mesures")
        self.tabs.addTab(self.fidelity_tab, "Écarts de fidélité")
        self.tabs.addTab(self.calibration_tab, "Courbe d'étalonnage")
        self.tabs.addTab(self.finalization_tab, "Finalisation")
        self.tabs.addTab(self.library_tab, "Bibliothèque des comparateurs")
        self.tabs.addTab(self.settings_tab, "Paramètres")
        self.setCentralWidget(self.tabs)

        # --- Appliquer le thème au démarrage ---
        prefs = load_prefs()
        apply_theme(self, getattr(prefs, "theme", "dark"))

        # Rafraîchir Bibliothèque quand un comparateur est créé depuis Session
        try:
            self.session_tab.comparator_created.connect(lambda _ref: self.library_tab.reload())
        except Exception:
            pass

        # Rafraîchir la liste des détenteurs dans Session quand modifiée depuis Paramètres
        try:
            self.settings_tab.detenteurs_tab.detenteurs_changed.connect(self.session_tab.reload_detenteurs)
        except Exception:
            pass

        # Rafraîchir le tableau Détenteurs quand créé depuis Session
        try:
            self.session_tab.detenteur_created.connect(self.settings_tab.detenteurs_tab.refresh)
        except Exception:
            pass

        # Rafraîchir la liste des bancs dans Session quand modifiée depuis Paramètres
        try:
            self.settings_tab.bancs_etalon_tab.bancs_changed.connect(self.session_tab.reload_bancs)
        except Exception:
            pass

        # --- Écouter les changements de thème depuis Paramètres ---
        try:
            self.settings_tab.themeChanged.connect(self._on_theme_changed)
        except Exception:
            pass

        # --- Menu Aide > À propos ---
        self._setup_help_menu()

    # ===== Session runtime accessors =====
    def get_rt_session(self):
        return session_store.current

    def select_session_tab(self):
        try:
            self.tabs.setCurrentWidget(self.session_tab)
        except Exception:
            pass

    # ===== Menus =====
    def _setup_help_menu(self):
        menubar = self.menuBar()
        aide_menu = menubar.addMenu("&Aide")

        about_action = QAction("À propos…", self)
        about_action.triggered.connect(self._show_about_dialog)
        aide_menu.addAction(about_action)

        doc_action = QAction("Documentation…", self)
        doc_action.setShortcut("F1")
        doc_action.triggered.connect(self.show_help_dialog)
        aide_menu.addAction(doc_action)

    # ===== Thème =====
    def _on_theme_changed(self, theme: str):
        apply_theme(self, theme)

    # ===== À propos =====
    def _show_about_dialog(self):
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
            f"<b>Version :</b> {__version__}<br>"
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

    def show_help_dialog(self):
        dlg = HelpDialog(self)
        dlg.setAttribute(Qt.WA_DeleteOnClose, True)
        dlg.show()
