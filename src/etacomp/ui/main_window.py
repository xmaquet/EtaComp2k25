from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QDialog, QLabel,
    QVBoxLayout, QPushButton
)
from PySide6.QtGui import QAction, QPixmap, QCloseEvent
from PySide6.QtCore import Qt, QTimer

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
from ..io.serial_manager import serial_manager
from ..io.storage import save_autosave_session
from ..package_resources import resource_path


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

        self._setup_menus()

        # --- Autosave (Paramètres > Sauvegarde) ---
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._run_autosave)
        try:
            self.settings_tab.autosaveChanged.connect(self._reload_autosave_timer)
        except Exception:
            pass
        self._reload_autosave_timer()

    # ===== Session runtime accessors =====
    def get_rt_session(self):
        return session_store.current

    def select_session_tab(self):
        try:
            self.tabs.setCurrentWidget(self.session_tab)
        except Exception:
            pass

    # ===== Menus =====
    def _setup_menus(self):
        menubar = self.menuBar()

        fichier_menu = menubar.addMenu("&Fichier")

        new_action = QAction("&Nouvelle session", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.session_tab.new_session)
        fichier_menu.addAction(new_action)

        load_action = QAction("&Charger session…", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.session_tab.load_session)
        fichier_menu.addAction(load_action)

        save_action = QAction("&Enregistrer la session…", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.session_tab._save_session)
        fichier_menu.addAction(save_action)

        fichier_menu.addSeparator()

        export_pdf_action = QAction("Exporter le rapport &PDF…", self)
        export_pdf_action.triggered.connect(self.finalization_tab._export_pdf)
        fichier_menu.addAction(export_pdf_action)

        fichier_menu.addSeparator()

        quit_action = QAction("&Quitter", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        fichier_menu.addAction(quit_action)

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
        pixmap = QPixmap(str(resource_path("resources", "14eBSMAT_insigne.png")))
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
            "© 2026 — Tous droits réservés."
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

    def _reload_autosave_timer(self):
        prefs = load_prefs()
        if prefs.autosave_enabled and prefs.autosave_interval_s > 0:
            self._autosave_timer.start(int(prefs.autosave_interval_s) * 1000)
        else:
            self._autosave_timer.stop()

    def _run_autosave(self):
        prefs = load_prefs()
        if not prefs.autosave_enabled:
            return
        if not session_store.can_save():
            return
        try:
            path = save_autosave_session(session_store.current)
            if path:
                self.statusBar().showMessage(f"Sauvegarde auto : {path.name}", 5000)
        except Exception:
            pass

    def closeEvent(self, event: QCloseEvent):
        """Issue #9 — libère le port COM (close() est idempotent ; aussi via aboutToQuit)."""
        try:
            serial_manager.close()
        except Exception:
            pass
        super().closeEvent(event)
