from __future__ import annotations
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout as QF, QWidget as QW
)

from ...io.storage import list_comparators
from ...state.session_store import session_store
from ...io.serialio import list_serial_ports
from ...io.serial_manager import serial_manager


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
        self.operator = QLineEdit(); self.operator.setToolTip("Nom de l’opérateur effectuant la session.")
        self.date = QLineEdit(); self.date.setReadOnly(True); self.date.setToolTip("Date/heure de la session.")
        self.temp = QDoubleSpinBox(); self.temp.setRange(-50.0, 100.0); self.temp.setSuffix(" °C"); self.temp.setDecimals(1)
        self.humi = QDoubleSpinBox(); self.humi.setRange(0.0, 100.0); self.humi.setSuffix(" %"); self.humi.setDecimals(1)
        self.comparator_combo = QComboBox(); self.comparator_combo.setToolTip("Comparateur (dispositif étalon) utilisé.")
        self.series = QSpinBox(); self.series.setRange(1, 999); self.series.setToolTip("Nombre d’itérations (montée+descente).")
        self.measures = QSpinBox(); self.measures.setRange(1, 1000); self.measures.setToolTip("Nombre de mesures prévues / série.")
        self.obs = QTextEdit(); self.obs.setToolTip("Observations/conditions (libre).")

        form = QFormLayout()
        form.addRow("Opérateur", self.operator)
        form.addRow("Date", self.date)
        form.addRow("Température", self.temp)
        form.addRow("Humidité", self.humi)
        form.addRow("Comparateur", self.comparator_combo)
        form.addRow("Itérations (séries)", self.series)
        form.addRow("Mesures / série (prévu)", self.measures)
        form.addRow("Observations", self.obs)

        # ---- Connexion série (déplacée ici) ----
        self.grp_conn = QGroupBox("Connexion au dispositif (RS-232/USB)")
        fconn: QF = QF(self.grp_conn)
        self.combo_port = QComboBox(); self.combo_port.setToolTip("Port COM (ex: COM3).")
        self.btn_refresh_ports = QPushButton("↻"); self.btn_refresh_ports.setToolTip("Rafraîchir les ports détectés.")
        pbar = QHBoxLayout(); pbar.addWidget(self.combo_port); pbar.addWidget(self.btn_refresh_ports)

        self.combo_baud = QComboBox(); self.combo_baud.addItems(["4800","9600","19200","38400","57600","115200"])
        self.combo_baud.setCurrentText("4800"); self.combo_baud.setToolTip("Vitesse (bauds). Par défaut 4800.")

        self.btn_connect = QPushButton("Connecter"); self.btn_connect.setStyleSheet(BTN_PRIMARY_CSS)
        self.btn_disconnect = QPushButton("Déconnecter"); self.btn_disconnect.setStyleSheet(BTN_NEUTRAL_CSS); self.btn_disconnect.setEnabled(False)

        fconn.addRow("Port", QW()); fconn.itemAt(fconn.rowCount()-1, QF.FieldRole).widget().setLayout(pbar)
        fconn.addRow("Baudrate", self.combo_baud)
        hb = QHBoxLayout(); hb.addWidget(self.btn_connect); hb.addWidget(self.btn_disconnect); hb.addStretch()
        fconn.addRow("", QW()); fconn.itemAt(fconn.rowCount()-1, QF.FieldRole).widget().setLayout(hb)

        # Boutons
        self.btn_new = QPushButton("Nouvelle session"); self.btn_new.setStyleSheet(BTN_PRIMARY_CSS)
        self.btn_load = QPushButton("Charger session…"); self.btn_load.setStyleSheet(BTN_NEUTRAL_CSS)

        bar = QHBoxLayout(); bar.addWidget(self.btn_new); bar.addWidget(self.btn_load); bar.addStretch()

        wrapper = QVBoxLayout(self)
        wrapper.addLayout(form)
        wrapper.addWidget(self.grp_conn)
        wrapper.addLayout(bar)
        wrapper.addStretch()

        # Connexions boutons
        self.btn_new.clicked.connect(self.new_session)
        self.btn_load.clicked.connect(self.load_session)
        self.btn_refresh_ports.clicked.connect(self._refresh_ports)
        self.btn_connect.clicked.connect(self._do_connect)
        self.btn_disconnect.clicked.connect(self._do_disconnect)

        # Champs -> session automatique
        self.operator.editingFinished.connect(self._push_metadata_from_ui)
        self.temp.valueChanged.connect(self._push_metadata_from_ui)
        self.humi.valueChanged.connect(self._push_metadata_from_ui)
        self.comparator_combo.currentIndexChanged.connect(self._push_metadata_from_ui)
        self.series.valueChanged.connect(self._push_metadata_from_ui)
        self.measures.valueChanged.connect(self._push_metadata_from_ui)
        self.obs.textChanged.connect(self._push_metadata_from_ui)

        # Écoute du store
        session_store.session_changed.connect(self._refresh_from_store)
        session_store.measures_updated.connect(self._refresh_from_store)

        # État connexion
        serial_manager.connected_changed.connect(self._on_connected_changed)

        # Init
        self.reload_comparators()
        self._refresh_ports()
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

    def _refresh_ports(self):
        ports = list_serial_ports()
        self.combo_port.clear()
        if not ports:
            self.combo_port.addItem("(aucun port détecté)")
            self.btn_connect.setEnabled(False)
        else:
            self.combo_port.addItems(ports)
            self.btn_connect.setEnabled(True)

    def _on_connected_changed(self, ok: bool):
        self.btn_connect.setEnabled(not ok)
        self.btn_disconnect.setEnabled(ok)

    def _refresh_from_store(self, s):
        # Bloque les signaux le temps de remplir
        for w in (self.operator, self.temp, self.humi, self.series, self.measures, self.comparator_combo, self.obs):
            w.blockSignals(True)

        self.operator.setText(s.operator or "")
        self.date.setText(s.date.strftime("%Y-%m-%d %H:%M:%S"))
        self.temp.setValue(s.temperature_c or 0.0)
        self.humi.setValue(s.humidity_pct or 0.0)
        if s.comparator_ref:
            idx = self.comparator_combo.findData(s.comparator_ref)
            self.comparator_combo.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self.comparator_combo.setCurrentIndex(0)
        self.series.setValue(max(1, s.series_count or 1))
        self.measures.setValue(max(1, s.measures_per_series or 1))
        self.obs.setPlainText(s.observations or "")

        for w in (self.operator, self.temp, self.humi, self.series, self.measures, self.comparator_combo, self.obs):
            w.blockSignals(False)

    def _push_metadata_from_ui(self):
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

    def _do_connect(self):
        if serial_manager.is_open():
            return
        port = self.combo_port.currentText()
        if not port or "(aucun" in port:
            QMessageBox.information(self, "Série", "Aucun port valide sélectionné.")
            return
        baud = int(self.combo_baud.currentText())
        try:
            serial_manager.open(port, baud)
            QMessageBox.information(self, "Série", f"Connecté à {port} @ {baud}.")
        except Exception as e:
            QMessageBox.warning(self, "Connexion série", f"Échec :\n{e}")

    def _do_disconnect(self):
        serial_manager.close()
