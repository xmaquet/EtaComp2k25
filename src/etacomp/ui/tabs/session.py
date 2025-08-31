from __future__ import annotations
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox
)

from ...io.storage import list_comparators
from ...state.session_store import session_store


BTN_PRIMARY_CSS = (
    "QPushButton{background:#0d6efd;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
    "QPushButton:hover{background:#0b5ed7;}"
)
BTN_NEUTRAL_CSS = (
    "QPushButton{background:#6c757d;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
    "QPushButton:hover{background:#5c636a;}"
)


class SessionTab(QWidget):
    def __init__(self):
        super().__init__()

        # Champs métadonnées
        self.operator = QLineEdit()
        self.operator.setToolTip("Nom de l’opérateur effectuant la session.")

        self.date = QLineEdit()
        self.date.setReadOnly(True)
        self.date.setToolTip("Date/heure de création de la session (définie automatiquement).")

        self.temp = QDoubleSpinBox()
        self.temp.setRange(-50.0, 100.0)
        self.temp.setSuffix(" °C")
        self.temp.setDecimals(1)
        self.temp.setToolTip("Température ambiante lors de la session.")

        self.humi = QDoubleSpinBox()
        self.humi.setRange(0.0, 100.0)
        self.humi.setSuffix(" %")
        self.humi.setDecimals(1)
        self.humi.setToolTip("Humidité relative lors de la session.")

        self.comparator_combo = QComboBox()
        self.comparator_combo.setToolTip("Sélectionne le comparateur (dispositif étalon) utilisé.")

        self.series = QSpinBox()
        self.series.setRange(1, 999)
        self.series.setToolTip("Nombre d’itérations à jouer (montant puis descendant).")

        self.measures = QSpinBox()
        self.measures.setRange(1, 1000)
        self.measures.setToolTip("Nombre de mesures prévues par série (à titre indicatif).")

        self.obs = QTextEdit()
        self.obs.setToolTip("Observations libres (conditions particulières, remarques, etc.).")

        # Formulaire
        form = QFormLayout()
        form.addRow("Opérateur", self.operator)
        form.addRow("Date", self.date)
        form.addRow("Température", self.temp)
        form.addRow("Humidité", self.humi)
        form.addRow("Comparateur", self.comparator_combo)
        form.addRow("Itérations (séries)", self.series)
        form.addRow("Mesures / série (prévu)", self.measures)
        form.addRow("Observations", self.obs)

        # Boutons
        self.btn_new = QPushButton("Nouvelle session")
        self.btn_new.setStyleSheet(BTN_PRIMARY_CSS)
        self.btn_new.setToolTip("Réinitialise une nouvelle session avec les valeurs par défaut (Paramètres).")

        self.btn_load = QPushButton("Charger session…")
        self.btn_load.setStyleSheet(BTN_NEUTRAL_CSS)
        self.btn_load.setToolTip("Charge une session précédemment enregistrée (JSON).")

        bar = QHBoxLayout()
        bar.addWidget(self.btn_new)
        bar.addWidget(self.btn_load)
        bar.addStretch()

        wrapper = QVBoxLayout(self)
        wrapper.addLayout(form)
        wrapper.addLayout(bar)
        wrapper.addStretch()

        # Connexions boutons
        self.btn_new.clicked.connect(self.new_session)
        self.btn_load.clicked.connect(self.load_session)

        # Connexions champs → mise à jour automatique du store
        self.operator.textChanged.connect(self._push_metadata_from_ui)
        self.temp.valueChanged.connect(self._push_metadata_from_ui)
        self.humi.valueChanged.connect(self._push_metadata_from_ui)
        self.comparator_combo.currentIndexChanged.connect(self._push_metadata_from_ui)
        self.series.valueChanged.connect(self._push_metadata_from_ui)
        self.measures.valueChanged.connect(self._push_metadata_from_ui)
        self.obs.textChanged.connect(self._push_metadata_from_ui)

        # Écoute du store (chargement/nouvelle session)
        session_store.session_changed.connect(self._refresh_from_store)
        session_store.measures_updated.connect(self._refresh_from_store)

        # Init
        self.reload_comparators()
        self._refresh_from_store(session_store.current)

    # ----- helpers -----
    def reload_comparators(self):
        current_ref = self.comparator_combo.currentData()
        self.comparator_combo.clear()
        self.comparator_combo.addItem("(aucun)", userData=None)
        for c in list_comparators():
            self.comparator_combo.addItem(c.reference, userData=c.reference)
        if current_ref is not None:
            idx = self.comparator_combo.findData(current_ref)
            if idx >= 0:
                self.comparator_combo.setCurrentIndex(idx)

    def _refresh_from_store(self, s):
        # Remplit l’UI depuis la session courante (sans reboucler inutilement)
        self.operator.blockSignals(True)
        self.temp.blockSignals(True)
        self.humi.blockSignals(True)
        self.series.blockSignals(True)
        self.measures.blockSignals(True)
        self.comparator_combo.blockSignals(True)
        self.obs.blockSignals(True)

        self.operator.setText(s.operator or "")
        self.date.setText(s.date.strftime("%Y-%m-%d %H:%M:%S"))
        self.temp.setValue(s.temperature_c or 0.0)
        self.humi.setValue(s.humidity_pct or 0.0)
        # comparator
        if s.comparator_ref:
            idx = self.comparator_combo.findData(s.comparator_ref)
            self.comparator_combo.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self.comparator_combo.setCurrentIndex(0)
        # séries/mesures prévues
        self.series.setValue(max(1, s.series_count or 1))
        self.measures.setValue(max(1, s.measures_per_series or 1))
        self.obs.setPlainText(s.observations or "")

        self.operator.blockSignals(False)
        self.temp.blockSignals(False)
        self.humi.blockSignals(False)
        self.series.blockSignals(False)
        self.measures.blockSignals(False)
        self.comparator_combo.blockSignals(False)
        self.obs.blockSignals(False)

    def _push_metadata_from_ui(self):
        # Pousse immédiatement les métadonnées du formulaire vers le store
        session_store.update_metadata(
            operator=self.operator.text().strip(),
            temperature_c=self.temp.value(),
            humidity_pct=self.humi.value(),
            comparator_ref=self.comparator_combo.currentData(),
            series_count=int(self.series.value()),
            measures_per_series=int(self.measures.value()),
            observations=self.obs.toPlainText().strip() or None,
        )

    # ----- actions -----
    def new_session(self):
        session_store.new_session()
        # Date affichée à maintenant pour la nouvelle session
        self.date.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.reload_comparators()

    def load_session(self):
        files = "Sessions (*.json)"
        start_dir = str(Path.home() / ".EtaComp2K25" / "sessions")
        path, _ = QFileDialog.getOpenFileName(self, "Charger une session", start_dir, files)
        if path:
            try:
                from pathlib import Path as _P
                session_store.load_from_file(_P(path))
                self.reload_comparators()
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Impossible de charger :\n{e}")
