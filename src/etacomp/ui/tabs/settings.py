from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QHBoxLayout,
    QLabel, QComboBox, QSpinBox, QCheckBox, QPushButton, QMessageBox, QApplication
)

from ...ui.themes import load_theme_qss
from ...config.prefs import load_prefs, save_prefs, Preferences
from ...config.defaults import DEFAULT_THEME
from ...config.paths import get_data_dir


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()

        self.prefs: Preferences = load_prefs()

        root = QVBoxLayout(self)
        root.setSpacing(12)

        # ====== Zone 1: Apparence ======
        g_appearance = QGroupBox("Apparence")
        f1 = QFormLayout(g_appearance)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        self.theme_combo.setCurrentText(self.prefs.theme or DEFAULT_THEME)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)

        f1.addRow("Thème", self.theme_combo)

        # (Placeholder futur : taille de police, contraste, etc.)

        # ====== Zone 2: Session (valeurs par défaut) ======
        g_session = QGroupBox("Session — valeurs par défaut")
        f2 = QFormLayout(g_session)

        self.spin_series = QSpinBox()
        self.spin_series.setRange(0, 100)
        self.spin_series.setValue(self.prefs.default_series_count)

        self.spin_measures = QSpinBox()
        self.spin_measures.setRange(0, 100)
        self.spin_measures.setValue(self.prefs.default_measures_per_series)

        f2.addRow("Nombre de séries", self.spin_series)
        f2.addRow("Mesures / série", self.spin_measures)

        # ====== Zone 3: Sauvegarde & sécurité ======
        g_save = QGroupBox("Sauvegarde & sécurité")
        f3 = QFormLayout(g_save)

        self.chk_autosave = QCheckBox("Activer la sauvegarde automatique")
        self.chk_autosave.setChecked(self.prefs.autosave_enabled)
        self.spin_autosave = QSpinBox()
        self.spin_autosave.setRange(5, 3600)
        self.spin_autosave.setSuffix(" s")
        self.spin_autosave.setValue(self.prefs.autosave_interval_s)
        self.spin_autosave.setEnabled(self.chk_autosave.isChecked())

        def _toggle_autosave(enabled: bool):
            self.spin_autosave.setEnabled(enabled)

        self.chk_autosave.toggled.connect(_toggle_autosave)

        f3.addRow(self.chk_autosave)
        f3.addRow("Intervalle", self.spin_autosave)

        # ====== Zone 4: Langue & régionalisation (placeholder) ======
        g_lang = QGroupBox("Langue & régionalisation")
        f4 = QFormLayout(g_lang)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["(par défaut)", "fr", "en"])
        # positionner sur la langue enregistrée si présente
        if self.prefs.language and self.prefs.language in ["fr", "en"]:
            self.lang_combo.setCurrentText(self.prefs.language)
        else:
            self.lang_combo.setCurrentText("(par défaut)")

        f4.addRow("Langue", self.lang_combo)

        # ====== Zone 5: Avancé ======
        g_adv = QGroupBox("Avancé")
        f5 = QFormLayout(g_adv)

        self.lbl_data_dir = QLabel(str(get_data_dir()))
        self.lbl_data_dir.setTextInteractionFlags(Qt.TextSelectableByMouse)

        f5.addRow("Dossier des données", self.lbl_data_dir)

        # Boutons d'action en bas
        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_save = QPushButton("Enregistrer les paramètres")
        self.btn_reset = QPushButton("Réinitialiser")
        btns.addWidget(self.btn_reset)
        btns.addWidget(self.btn_save)

        self.btn_save.clicked.connect(self.on_save)
        self.btn_reset.clicked.connect(self.on_reset)

        # Assembler
        root.addWidget(g_appearance)
        root.addWidget(g_session)
        root.addWidget(g_save)
        root.addWidget(g_lang)
        root.addWidget(g_adv)
        root.addLayout(btns)
        root.addStretch()

    # ====== Slots ======
    def on_theme_changed(self, theme: str):
        # Application immédiate
        qss = load_theme_qss(theme)
        QApplication.instance().setStyleSheet(qss)

    def on_save(self):
        # Enregistrer en JSON
        lang = self.lang_combo.currentText()
        lang = None if lang == "(par défaut)" else lang

        self.prefs.theme = self.theme_combo.currentText()
        self.prefs.default_series_count = int(self.spin_series.value())
        self.prefs.default_measures_per_series = int(self.spin_measures.value())
        self.prefs.autosave_enabled = self.chk_autosave.isChecked()
        self.prefs.autosave_interval_s = int(self.spin_autosave.value())
        self.prefs.language = lang

        path = save_prefs(self.prefs)
        QMessageBox.information(self, "Paramètres", f"Paramètres enregistrés :\n{path}")

    def on_reset(self):
        # Recharger depuis disque / ou valeurs par défaut si fichier absent
        self.prefs = load_prefs()

        self.theme_combo.setCurrentText(self.prefs.theme or "light")
        self.spin_series.setValue(self.prefs.default_series_count)
        self.spin_measures.setValue(self.prefs.default_measures_per_series)
        self.chk_autosave.setChecked(self.prefs.autosave_enabled)
        self.spin_autosave.setValue(self.prefs.autosave_interval_s)
        self.spin_autosave.setEnabled(self.prefs.autosave_enabled)

        if self.prefs.language in ("fr", "en"):
            self.lang_combo.setCurrentText(self.prefs.language)
        else:
            self.lang_combo.setCurrentText("(par défaut)")

        # Réappliquer le thème courant
        self.on_theme_changed(self.prefs.theme or "light")
