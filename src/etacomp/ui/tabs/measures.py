from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QSpinBox,
    QDoubleSpinBox, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QMessageBox
)

from ...models.session import MeasureSeries
from ...state.session_store import session_store


class MeasuresTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)

        # Zone 1 : sélection d'une série (index) + cible
        g_series = QGroupBox("Série")
        f1 = QFormLayout(g_series)
        self.spin_index = QSpinBox(); self.spin_index.setRange(0, 999)
        self.target = QDoubleSpinBox(); self.target.setRange(-1e6, 1e6); self.target.setDecimals(6)
        f1.addRow("Index de série", self.spin_index)
        f1.addRow("Cible (mm)", self.target)

        # Zone 2 : relevés (liste)
        g_readings = QGroupBox("Relevés (mm)")
        v2 = QVBoxLayout(g_readings)
        self.input_reading = QLineEdit(); self.input_reading.setPlaceholderText("Saisir une valeur (mm) puis Ajouter")
        self.btn_add = QPushButton("Ajouter")
        self.btn_clear_list = QPushButton("Effacer la série")
        top = QHBoxLayout()
        top.addWidget(self.input_reading); top.addWidget(self.btn_add); top.addStretch(); top.addWidget(self.btn_clear_list)

        self.list = QListWidget()
        v2.addLayout(top)
        v2.addWidget(self.list)

        # Actions globales
        actions = QHBoxLayout()
        self.btn_apply_series = QPushButton("Appliquer la série")
        self.btn_save_session = QPushButton("Enregistrer la session…")
        self.btn_save_session.setStyleSheet("QPushButton{background:#28a745;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}QPushButton:hover{background:#218838;}")
        actions.addStretch()
        actions.addWidget(self.btn_apply_series)
        actions.addWidget(self.btn_save_session)

        root.addWidget(g_series)
        root.addWidget(g_readings)
        root.addLayout(actions)
        root.addStretch()

        # Events
        self.btn_add.clicked.connect(self._add_reading)
        self.btn_clear_list.clicked.connect(self._clear_series)
        self.btn_apply_series.clicked.connect(self._apply_series)
        self.btn_save_session.clicked.connect(self._save_session)

        session_store.session_changed.connect(self._pull_from_store)
        session_store.measures_updated.connect(self._pull_from_store)

        self._pull_from_store(session_store.current)

    # helpers
    def _pull_from_store(self, s):
        # rien à forcer ici, l’utilisateur pilote la série active
        pass

    def _current_series_from_ui(self) -> MeasureSeries:
        readings = []
        for i in range(self.list.count()):
            readings.append(float(self.list.item(i).text()))
        return MeasureSeries(target=float(self.target.value()), readings=readings)

    def _add_reading(self):
        txt = self.input_reading.text().strip()
        if not txt:
            return
        try:
            val = float(txt)
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Valeur invalide.")
            return
        self.list.addItem(QListWidgetItem(f"{val}"))
        self.input_reading.clear()

    def _clear_series(self):
        self.list.clear()

    def _apply_series(self):
        idx = int(self.spin_index.value())
        ser = self._current_series_from_ui()
        session_store.add_or_replace_series(idx, ser)
        QMessageBox.information(self, "Mesures", f"Série {idx} appliquée ({len(ser.readings)} relevés).")

    def _save_session(self):
        if not session_store.can_save():
            QMessageBox.warning(self, "Impossible", "Aucune mesure dans la session — enregistrement interdit.")
            return
        try:
            path = session_store.save()
            QMessageBox.information(self, "Session", f"Session enregistrée :\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Échec de l’enregistrement :\n{e}")
