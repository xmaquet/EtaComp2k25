from __future__ import annotations
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout as QF, QWidget as QW, QLabel
)
from PySide6.QtCore import QEvent, Signal

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
BTN_SUCCESS_CSS = (
    "QPushButton{background:#28a745;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
    "QPushButton:hover{background:#218838;}"
)


class SessionTab(QWidget):
    # Émis lorsqu'un comparateur est créé depuis une session chargée
    comparator_created = Signal(str)  # reference
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
        self.obs = QTextEdit(); self.obs.setToolTip("Observations/conditions (texte libre multi‑lignes). Saisie validée à la perte de focus ou Ctrl+Entrée.")

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
        # Indicateur visuel de statut connexion
        self.lbl_conn_status = QLabel("● Déconnecté")
        self.lbl_conn_status.setToolTip("Statut de la connexion au dispositif")
        self.lbl_conn_status.setStyleSheet("color:#dc3545;font-weight:700;")  # rouge par défaut

        fconn.addRow("Port", QW()); fconn.itemAt(fconn.rowCount()-1, QF.FieldRole).widget().setLayout(pbar)
        fconn.addRow("Baudrate", self.combo_baud)
        fconn.addRow("Statut", self.lbl_conn_status)
        hb = QHBoxLayout(); hb.addWidget(self.btn_connect); hb.addWidget(self.btn_disconnect); hb.addStretch()
        fconn.addRow("", QW()); fconn.itemAt(fconn.rowCount()-1, QF.FieldRole).widget().setLayout(hb)

        # Boutons
        self.btn_new = QPushButton("Nouvelle session"); self.btn_new.setStyleSheet(BTN_PRIMARY_CSS)
        self.btn_load = QPushButton("Charger session…"); self.btn_load.setStyleSheet(BTN_NEUTRAL_CSS)
        self.btn_save_session = QPushButton("Enregistrer la session…"); self.btn_save_session.setStyleSheet(BTN_SUCCESS_CSS)

        bar = QHBoxLayout(); bar.addWidget(self.btn_new); bar.addWidget(self.btn_load); bar.addWidget(self.btn_save_session); bar.addStretch()

        wrapper = QVBoxLayout(self)
        wrapper.addLayout(form)
        wrapper.addWidget(self.grp_conn)
        wrapper.addLayout(bar)
        wrapper.addStretch()

        # Connexions boutons
        self.btn_new.clicked.connect(self.new_session)
        self.btn_load.clicked.connect(self.load_session)
        self.btn_save_session.clicked.connect(self._save_session)
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
        # Observations: on valide à la perte de focus (ou Ctrl+Entrée). On évite l'update à chaque caractère.
        self._obs_dirty = False
        self.obs.textChanged.connect(lambda: setattr(self, "_obs_dirty", True))
        self.obs.installEventFilter(self)

        # Écoute du store
        session_store.session_changed.connect(self._refresh_from_store)
        session_store.measures_updated.connect(self._refresh_from_store)

        # État connexion
        serial_manager.connected_changed.connect(self._on_connected_changed)

        # Init
        self.reload_comparators()
        self._refresh_ports()
        self._refresh_from_store(session_store.current)
        # Appliquer l'état de connexion initial
        try:
            self._on_connected_changed(serial_manager.is_open())
        except Exception:
            pass

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
        if ok:
            self.lbl_conn_status.setText("● Connecté")
            self.lbl_conn_status.setStyleSheet("color:#28a745;font-weight:700;")  # vert
        else:
            self.lbl_conn_status.setText("● Déconnecté")
            self.lbl_conn_status.setStyleSheet("color:#dc3545;font-weight:700;")  # rouge

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
        self._obs_dirty = False

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

    def _commit_observations(self):
        """Valide le champ Observations en une fois (bloc multi‑lignes)."""
        txt = (self.obs.toPlainText() or "").strip()
        session_store.update_metadata(
            operator=self.operator.text().strip(),
            temperature_c=self.temp.value(),
            humidity_pct=self.humi.value(),
            comparator_ref=self.comparator_combo.currentData(),
            series_count=int(self.series.value()),
            measures_per_series=int(self.measures.value()),
            observations=txt or None,
        )
        self._obs_dirty = False

    def eventFilter(self, obj, event):
        """Valide Observations à la perte de focus ou Ctrl+Entrée."""
        if obj is self.obs:
            et = event.type()
            if et == QEvent.FocusOut and self._obs_dirty:
                self._commit_observations()
            elif et == QEvent.KeyPress:
                try:
                    key = event.key()
                    mods = int(event.modifiers())
                    # 0x01000005 = Qt.Key_Enter, 0x01000004 = Qt.Key_Return ; 0x04000000 = Qt.ControlModifier
                    if key in (0x01000005, 0x01000004) and (mods & 0x04000000):
                        self._commit_observations()
                        return True
                except Exception:
                    pass
        return super().eventFilter(obj, event)

    # ----- actions -----
    def _save_session(self):
        if not session_store.can_save():
            QMessageBox.warning(self, "Impossible", "Aucune mesure dans la session — enregistrement interdit.")
            return
        try:
            path = session_store.save()
            QMessageBox.information(self, "Session", f"Session enregistrée :\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Échec de l'enregistrement :\n{e}")

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
                # Tenter de reconnecter le comparateur ; si manquant proposer de le recréer
                self._on_session_loaded_try_rebind_comparator()
                self.reload_comparators()
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Impossible de charger :\n{e}")

    def _on_session_loaded_try_rebind_comparator(self):
        """Au chargement d'une session, si le comparateur est introuvable, proposer une recréation minimale."""
        s = session_store.current
        if not s:
            return
        ref = s.comparator_ref or ""
        # Vérifier existence
        exists = False
        from ...io.storage import list_comparators, upsert_comparator
        for c in list_comparators():
            if c.reference == ref:
                exists = True
                break
        if exists:
            return
        # Déduire cibles depuis la session
        targets = []
        seen = set()
        for ms in (s.series or []):
            try:
                t = float(ms.target)
            except Exception:
                continue
            if t not in seen:
                seen.add(t); targets.append(t)
        targets = sorted(targets)
        if not targets:
            return
        # Déduire graduation/course/range_type minimales
        def _deduce_graduation(vals: list[float]) -> float:
            diffs = sorted({round(abs(vals[i] - vals[i-1]), 6) for i in range(1, len(vals)) if abs(vals[i] - vals[i-1]) > 1e-6})
            return diffs[0] if diffs else 0.01
        def _deduce_range_type(course: float):
            from ...models.comparator import RangeType
            if course <= 0.5: return RangeType.LIMITEE
            if course <= 1.0: return RangeType.FAIBLE
            if course <= 20.0: return RangeType.NORMALE
            return RangeType.GRANDE
        course = max(targets) if targets else 0.0
        graduation = _deduce_graduation(targets)
        from ...models.comparator import ComparatorProfile
        from ...models.comparator import RangeType
        rtype = _deduce_range_type(course)
        # Proposer recréation
        btn = QMessageBox.question(
            self,
            "Comparateur introuvable",
            f"Le comparateur '{ref or '(aucun)'}' est introuvable dans la bibliothèque.\n\n"
            f"Proposer de créer un profil à partir des données de la session :\n"
            f"- Graduation estimée: {graduation:.3f} mm\n- Course: {course:.3f} mm\n- Famille: {rtype.display_name}\n\n"
            f"Créer ce profil maintenant ?",
            QMessageBox.Yes | QMessageBox.No
        )
        if btn == QMessageBox.Yes:
            new_ref = ref or f"SESSION_{s.date.strftime('%Y%m%d_%H%M%S')}"
            try:
                profile = ComparatorProfile(
                    reference=new_ref, manufacturer=None, description="Recréé depuis session",
                    graduation=graduation, course=course, range_type=rtype, targets=targets
                )
                upsert_comparator(profile)
                s.comparator_ref = new_ref
                self.comparator_combo.addItem(new_ref, userData=new_ref)
                idx = self.comparator_combo.findData(new_ref)
                if idx >= 0:
                    self.comparator_combo.setCurrentIndex(idx)
                QMessageBox.information(self, "Bibliothèque", f"Profil recréé: {new_ref}")
                # Notifier l'onglet Bibliothèque pour rafraîchir sa liste
                try:
                    self.comparator_created.emit(new_ref)
                except Exception:
                    pass
            except Exception as e:
                QMessageBox.warning(self, "Bibliothèque", f"Impossible de créer le profil:\n{e}")

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
