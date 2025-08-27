from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QPushButton, QVBoxLayout, QMessageBox
)

from ...io.storage import list_comparators, save_session
from ...models.session import Session


class SessionTab(QWidget):
    def __init__(self):
        super().__init__()

        self.operator = QLineEdit()
        self.date = QLineEdit(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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

        form = QFormLayout()
        form.addRow("Opérateur", self.operator)
        form.addRow("Date", self.date)
        form.addRow("Température", self.temp)
        form.addRow("Humidité", self.humi)
        form.addRow("Comparateur", self.comparator_combo)
        form.addRow("Nb séries", self.series)
        form.addRow("Mesures / série", self.measures)
        form.addRow("Observations", self.obs)

        self.btn_save = QPushButton("Enregistrer la session")
        self.btn_save.clicked.connect(self.on_save)

        wrapper = QVBoxLayout(self)
        wrapper.addLayout(form)
        wrapper.addWidget(self.btn_save)
        wrapper.addStretch()

    # appelé depuis MainWindow quand la bibliothèque change
    def reload_comparators(self):
        self.comparator_combo.clear()
        comps = list_comparators()
        self.comparator_combo.addItem("(aucun)", userData=None)
        for c in comps:
            self.comparator_combo.addItem(c.reference, userData=c.reference)

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
