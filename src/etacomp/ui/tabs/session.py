from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
)

from ...io.storage import list_comparators, save_session
from ...models.session import Session
from ...config.prefs import load_prefs


class SessionTab(QWidget):
    def __init__(self):
        super().__init__()

        # Champs
        self.operator = QLineEdit()
        self.date = QLineEdit()
        self.date.setReadOnly(True)

        self.temp = QDoubleSpinBox()
        self.temp.setRange(-50.0, 100.0)
        self.temp.setSuffix(" °C")
        self.temp.setDecimals(1)

        self.humi = QDoubleSpinBox()
        self.humi.setRange(0.0, 100.0)
        self.humi.setSuffix(" %")
        self.humi.setDecimals(1)

        self.comparator_combo = QComboBox()
        self.reload_comparators()

        self.series = QSpinBox()
        self.series.setRange(0, 100)

        self.measures = QSpinBox()
        self.measures.setRange(0, 100)

        self.obs = QTextEdit()

        # Formulaire
        form = QFormLayout()
        form.addRow("Opérateur", self.operator)
        form.addRow("Date", self.date)
        form.addRow("Température", self.temp)
        form.addRow("Humidité", self.humi)
        form.addRow("Comparateur", self.comparator_combo)
        form.addRow("Nb séries", self.series)
        form.addRow("Mesures / série", self.measures)
        form.addRow("Observations", self.obs)

        # Boutons d'action
        self.btn_new = QPushButton("Nouvelle session")
        self.btn_save = QPushButton("Enregistrer la session")

        # Styles (couleurs)
        self.btn_new.setStyleSheet(
            "QPushButton{background-color:#0d6efd;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
            "QPushButton:hover{background-color:#0b5ed7;}"
        )
        self.btn_save.setStyleSheet(
            "QPushButton{background-color:#28a745;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
            "QPushButton:hover{background-color:#218838;}"
        )

        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(self.btn_new)
        btns.addWidget(self.btn_save)

        wrapper = QVBoxLayout(self)
        wrapper.addLayout(form)
        wrapper.addLayout(btns)
        wrapper.addStretch()

        # Connexions
        self.btn_new.clicked.connect(self.new_session)
        self.btn_save.clicked.connect(self.on_save)

        # Initialisation : appliquer les préférences à l’ouverture
        self.new_session()

    # appelé par MainWindow quand la bibliothèque change (ajout/suppression)
    def reload_comparators(self):
        current_ref = self.comparator_combo.currentData()
        self.comparator_combo.clear()
        comps = list_comparators()
        self.comparator_combo.addItem("(aucun)", userData=None)
        for c in comps:
            self.comparator_combo.addItem(c.reference, userData=c.reference)
        # si possible, conserver la sélection précédente
        if current_ref is not None:
            idx = self.comparator_combo.findData(current_ref)
            if idx >= 0:
                self.comparator_combo.setCurrentIndex(idx)

    def new_session(self):
        """Réinitialise le formulaire avec les valeurs par défaut des préférences."""
        prefs = load_prefs()
        self.operator.clear()
        self.date.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.temp.setValue(0.0)
        self.humi.setValue(0.0)
        self.series.setValue(prefs.default_series_count)
        self.measures.setValue(prefs.default_measures_per_series)
        self.obs.clear()
        # sélectionne '(aucun)' par défaut
        if self.comparator_combo.count() > 0:
            self.comparator_combo.setCurrentIndex(0)

    def on_save(self):
        s = Session(
            operator=self.operator.text().strip() or "inconnu",
            temperature_c=self.temp.value(),
            humidity_pct=self.humi.value(),
            comparator_ref=self.comparator_combo.currentData(),
            series_count=int(self.series.value()),
            measures_per_series=int(self.measures.value()),
            observations=self.obs.toPlainText() or None,
        )
        path = save_session(s)
        QMessageBox.information(self, "Session", f"Session enregistrée :\n{path}")
