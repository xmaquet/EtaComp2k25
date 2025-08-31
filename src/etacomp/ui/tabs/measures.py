from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QSpinBox,
    QDoubleSpinBox, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QMessageBox, QComboBox, QTextEdit
)

from ...models.session import MeasureSeries
from ...state.session_store import session_store
from ...io.serialio import list_serial_ports, SerialConnection, SerialReaderThread


class MeasuresTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)

        # ===== Zone 0 : Connexion série (COM) =====
        g_conn = QGroupBox("Connexion au dispositif étalon (port série)")
        f0 = QFormLayout(g_conn)

        self.combo_port = QComboBox()
        self.btn_refresh_ports = QPushButton("↻")
        pbar = QHBoxLayout()
        pbar.addWidget(self.combo_port)
        pbar.addWidget(self.btn_refresh_ports)

        self.combo_baud = QComboBox()
        self.combo_baud.addItems(["4800", "9600", "19200", "38400", "57600", "115200"])
        self.combo_baud.setCurrentText("4800")

        self.btn_connect = QPushButton("Connecter")
        self.btn_disconnect = QPushButton("Déconnecter")
        self.btn_disconnect.setEnabled(False)

        f0.addRow("Port", QWidget())
        f0.itemAt(f0.rowCount()-1, QFormLayout.FieldRole).widget().setLayout(pbar)
        f0.addRow("Baudrate", self.combo_baud)
        hb = QHBoxLayout()
        hb.addWidget(self.btn_connect)
        hb.addWidget(self.btn_disconnect)
        hb.addStretch()
        f0.addRow("", QWidget())
        f0.itemAt(f0.rowCount()-1, QFormLayout.FieldRole).widget().setLayout(hb)

        # ===== Zone 1 : Paramètres de série =====
        g_series = QGroupBox("Série")
        f1 = QFormLayout(g_series)
        self.spin_index = QSpinBox(); self.spin_index.setRange(0, 999)
        self.target = QDoubleSpinBox(); self.target.setRange(-1e6, 1e6); self.target.setDecimals(6)
        self.planned_count = QSpinBox(); self.planned_count.setRange(1, 1000)
        self.btn_start_series = QPushButton("Démarrer la série")
        self.btn_stop_series = QPushButton("Arrêter la série"); self.btn_stop_series.setEnabled(False)

        f1.addRow("Index de série", self.spin_index)
        f1.addRow("Cible (mm)", self.target)
        f1.addRow("Mesures attendues", self.planned_count)
        hb2 = QHBoxLayout()
        hb2.addWidget(self.btn_start_series)
        hb2.addWidget(self.btn_stop_series)
        hb2.addStretch()
        f1.addRow("", QWidget())
        f1.itemAt(f1.rowCount()-1, QFormLayout.FieldRole).widget().setLayout(hb2)

        # ===== Zone 2 : Relevés =====
        g_readings = QGroupBox("Relevés (mm)")
        v2 = QVBoxLayout(g_readings)
        top = QHBoxLayout()
        self.input_reading = QLineEdit(); self.input_reading.setPlaceholderText("Saisir une valeur (mm) puis Ajouter")
        self.btn_add = QPushButton("Ajouter")
        self.btn_clear_list = QPushButton("Effacer la série")
        top.addWidget(self.input_reading); top.addWidget(self.btn_add); top.addStretch(); top.addWidget(self.btn_clear_list)

        self.list = QListWidget()
        v2.addLayout(top)
        v2.addWidget(self.list)

        # ===== Zone 3 : Logger brut =====
        g_log = QGroupBox("Flux série (lignes brutes)")
        v3 = QVBoxLayout(g_log)
        log_bar = QHBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        self.btn_clear_log = QPushButton("Effacer le log")   # ⬅️ NOUVEAU
        log_bar.addStretch()
        log_bar.addWidget(self.btn_clear_log)
        v3.addWidget(self.log_view)
        v3.addLayout(log_bar)

        # ===== Actions globales =====
        actions = QHBoxLayout()
        self.btn_apply_series = QPushButton("Appliquer la série")
        self.btn_save_session = QPushButton("Enregistrer la session…")
        self.btn_save_session.setStyleSheet(
            "QPushButton{background:#28a745;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
            "QPushButton:hover{background:#218838;}"
        )
        actions.addStretch()
        actions.addWidget(self.btn_apply_series)
        actions.addWidget(self.btn_save_session)

        root.addWidget(g_conn)
        root.addWidget(g_series)
        root.addWidget(g_readings)
        root.addWidget(g_log)
        root.addLayout(actions)
        root.addStretch()

        # ===== État interne =====
        self._conn = SerialConnection()
        self._reader: SerialReaderThread | None = None
        self._capturing = False

        # Init UI
        self._refresh_ports()
        self._load_defaults_from_session()

        # Events
        self.btn_refresh_ports.clicked.connect(self._refresh_ports)
        self.btn_connect.clicked.connect(self._do_connect)
        self.btn_disconnect.clicked.connect(self._do_disconnect)

        self.btn_start_series.clicked.connect(self._start_capture)
        self.btn_stop_series.clicked.connect(self._stop_capture)

        self.btn_add.clicked.connect(self._add_reading_manual)
        self.btn_clear_list.clicked.connect(self._clear_series)
        self.btn_apply_series.clicked.connect(self._apply_series)
        self.btn_save_session.clicked.connect(self._save_session)
        self.btn_clear_log.clicked.connect(self._clear_log)   # ⬅️ NOUVEAU

        # Store events
        session_store.session_changed.connect(self._on_session_changed)
        session_store.measures_updated.connect(self._on_session_changed)

    # ---------- Connexion série ----------
    def _refresh_ports(self):
        ports = list_serial_ports()
        self.combo_port.clear()
        if not ports:
            self.combo_port.addItem("(aucun port détecté)")
            self.btn_connect.setEnabled(False)
        else:
            self.combo_port.addItems(ports)
            self.btn_connect.setEnabled(True)

    def _do_connect(self):
        if self._conn.is_open():
            return
        port = self.combo_port.currentText()
        if not port or "(aucun" in port:
            QMessageBox.information(self, "Série", "Aucun port valide sélectionné.")
            return
        baud = int(self.combo_baud.currentText())
        try:
            self._conn.open(port=port, baudrate=baud)
        except Exception as e:
            QMessageBox.warning(self, "Connexion série", f"Échec de connexion sur {port} @ {baud} :\n{e}")
            return

        self._reader = SerialReaderThread(self._conn, self._on_line_from_serial)
        self._reader.start()
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)
        QMessageBox.information(self, "Série", f"Connecté à {port} @ {baud}.")

    def _do_disconnect(self):
        self._stop_capture()
        if self._reader:
            self._reader.stop()
            self._reader = None
        self._conn.close()
        self.btn_disconnect.setEnabled(False)
        self.btn_connect.setEnabled(True)

    # ---------- Capture d'une série ----------
    def _load_defaults_from_session(self):
        s = session_store.current
        self.planned_count.setValue(max(1, s.measures_per_series or 1))

    def _start_capture(self):
        if not self._conn.is_open():
            QMessageBox.information(self, "Série", "Connecte d’abord le dispositif (port série).")
            return
        self.list.clear()
        self._load_defaults_from_session()
        self._capturing = True
        self.btn_start_series.setEnabled(False)
        self.btn_stop_series.setEnabled(True)

    def _stop_capture(self):
        self._capturing = False
        self.btn_start_series.setEnabled(True)
        self.btn_stop_series.setEnabled(False)

    # ---------- Callback série ----------
    def _on_line_from_serial(self, raw: str, value: float | None):
        QTimer.singleShot(0, lambda: self._append_line(raw, value))

    def _append_line(self, raw: str, value: float | None):
        self.log_view.append(raw)
        if self._capturing and value is not None:
            self.list.addItem(QListWidgetItem(f"{value}"))
            if self.list.count() >= int(self.planned_count.value()):
                self._stop_capture()

    # ---------- Édition manuelle ----------
    def _add_reading_manual(self):
        txt = self.input_reading.text().strip().replace(",", ".")
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

    def _clear_log(self):
        self.log_view.clear()

    # ---------- Intégration store ----------
    def _current_series_from_ui(self) -> MeasureSeries:
        readings = []
        for i in range(self.list.count()):
            readings.append(float(self.list.item(i).text()))
        return MeasureSeries(target=float(self.target.value()), readings=readings)

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

    def _on_session_changed(self, _s):
        pass

    # ---------- Nettoyage ----------
    def deleteLater(self):
        try:
            self._stop_capture()
            if self._reader:
                self._reader.stop()
            self._conn.close()
        finally:
            super().deleteLater()
