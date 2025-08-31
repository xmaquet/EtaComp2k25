from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox
)

from ...io.storage import list_comparators
from ...state.session_store import session_store


class SessionTab(QWidget):
    def __init__(self):
        super().__init__()

        # Champs métadonnées
        self.operator = QLineEdit()
        self.date = QLineEdit()
        self.date.setReadOnly(True)

        self.temp = QDoubleSpinBox()
        self.temp.setRange(-50.0, 100.0); self.temp.setSuffix(" °C"); self.temp.setDecimals(1)

        self.humi = QDoubleSpinBox()
        self.humi.setRange(0.0, 100.0); self.humi.setSuffix(" %"); self.humi.setDecimals(1)

        self.comparator_combo = QComboBox()
        self.series = QSpinBox(); self.series.setRange(0, 100)
        self.measures = QSpinBox(); self.measures.setRange(0, 100)
        self.obs = QTextEdit()

        form = QFormLayout()
        form.addRow("Opérateur", self.operator)
        form.addRow("Date", self.date)
        form.addRow("Température", self.temp)
        form.addRow("Humidité", self.humi)
        form.addRow("Comparateur", self.comparator_combo)
        form.addRow("Nb séries (prévu)", self.series)
        form.addRow("Mesures / série (prévu)", self.measures)
        form.addRow("Observations", self.obs)

        # Boutons (Nouvelle/Charger, Appliquer métadonnées)
        self.btn_new = QPushButton("Nouvelle session")
        self.btn_load = QPushButton("Charger session…")
        self.btn_apply = QPushButton("Appliquer les métadonnées")

        self.btn_new.setStyleSheet("QPushButton{background:#0d6efd;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}QPushButton:hover{background:#0b5ed7;}")
        self.btn_load.setStyleSheet("QPushButton{padding:6px 12px;}")
        self.btn_apply.setStyleSheet("QPushButton{background:#6c757d;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}QPushButton:hover{background:#5c636a;}")

        bar = QHBoxLayout()
        bar.addWidget(self.btn_new)
        bar.addWidget(self.btn_load)
        bar.addStretch()
        bar.addWidget(self.btn_apply)

        wrapper = QVBoxLayout(self)
        wrapper.addLayout(form)
        wrapper.addLayout(bar)
        wrapper.addStretch()

        # Connexions
        self.btn_new.clicked.connect(self.new_session)
        self.btn_load.clicked.connect(self.load_session)
        self.btn_apply.clicked.connect(self.apply_metadata)

        session_store.session_changed.connect(self._refresh_from_store)
        session_store.measures_updated.connect(self._refresh_from_store)

        # Init
        self.reload_comparators()
        self._refresh_from_store(session_store.current)

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
        self.operator.setText(s.operator or "")
        self.date.setText(s.date.strftime("%Y-%m-%d %H:%M:%S"))
        self.temp.setValue(s.temperature_c or 0.0)
        self.humi.setValue(s.humidity_pct or 0.0)
        # comparator
        if s.comparator_ref:
            idx = self.comparator_combo.findData(s.comparator_ref)
            if idx >= 0:
                self.comparator_combo.setCurrentIndex(idx)
        else:
            if self.comparator_combo.count() > 0:
                self.comparator_combo.setCurrentIndex(0)
        self.series.setValue(s.series_count)
        self.measures.setValue(s.measures_per_series)
        self.obs.setPlainText(s.observations or "")

    # Actions
    def new_session(self):
        session_store.new_session()
        self.reload_comparators()

    def load_session(self):
        files = "Sessions (*.json)"
        start_dir = str(Path.home() / ".EtaComp2K25" / "sessions")
        path, _ = QFileDialog.getOpenFileName(self, "Charger une session", start_dir, files)
        if path:
            try:
                session_store.load_from_file(Path(path))
                self.reload_comparators()
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Impossible de charger :\n{e}")

    def apply_metadata(self):
        session_store.update_metadata(
            operator=self.operator.text().strip(),
            temperature_c=self.temp.value(),
            humidity_pct=self.humi.value(),
            comparator_ref=self.comparator_combo.currentData(),
            series_count=int(self.series.value()),
            measures_per_series=int(self.measures.value()),
            observations=self.obs.toPlainText().strip() or None,
        )
        QMessageBox.information(self, "Session", "Métadonnées appliquées.")
