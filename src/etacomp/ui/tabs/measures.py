from __future__ import annotations

import time
from typing import List, Dict, Optional, Tuple

from PySide6.QtCore import QTimer, QCoreApplication
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QPushButton,
    QMessageBox, QComboBox, QTextEdit, QLabel, QTableWidget, QTableWidgetItem
)

from ...models.session import MeasureSeries
from ...state.session_store import session_store
from ...io.serialio import list_serial_ports, SerialConnection, SerialReaderThread
from ...io.storage import list_comparators


BTN_PRIMARY_CSS = (
    "QPushButton{background:#0d6efd;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
    "QPushButton:hover{background:#0b5ed7;}"
)
BTN_DANGER_CSS = (
    "QPushButton{background:#dc3545;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
    "QPushButton:hover{background:#bb2d3b;}"
)
BTN_SUCCESS_CSS = (
    "QPushButton{background:#28a745;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
    "QPushButton:hover{background:#218838;}"
)


class MeasuresTab(QWidget):
    ZERO_TOL = 1e-6  # tolérance pour tester ~0

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)

        # ===== Connexion série =====
        g_conn = QGroupBox("Connexion au dispositif étalon (port série)")
        f0 = QFormLayout(g_conn)

        self.combo_port = QComboBox()
        self.combo_port.setToolTip("Port série du dispositif étalon (ex: COM3).")
        self.btn_refresh_ports = QPushButton("↻")
        self.btn_refresh_ports.setToolTip("Rafraîchir la liste des ports COM détectés.")
        pbar = QHBoxLayout()
        pbar.addWidget(self.combo_port)
        pbar.addWidget(self.btn_refresh_ports)

        self.combo_baud = QComboBox()
        self.combo_baud.addItems(["4800", "9600", "19200", "38400", "57600", "115200"])
        self.combo_baud.setCurrentText("4800")
        self.combo_baud.setToolTip("Vitesse de communication en bauds (par défaut 4800).")

        self.btn_connect = QPushButton("Connecter")
        self.btn_connect.setStyleSheet(BTN_PRIMARY_CSS)
        self.btn_connect.setToolTip("Ouvrir la connexion série et démarrer l’écoute.")
        self.btn_disconnect = QPushButton("Déconnecter")
        self.btn_disconnect.setStyleSheet(BTN_DANGER_CSS)
        self.btn_disconnect.setToolTip("Fermer la connexion série.")
        self.btn_disconnect.setEnabled(False)

        f0.addRow("Port", QWidget())
        f0.itemAt(f0.rowCount() - 1, QFormLayout.FieldRole).widget().setLayout(pbar)
        f0.addRow("Baudrate", self.combo_baud)
        hb = QHBoxLayout()
        hb.addWidget(self.btn_connect)
        hb.addWidget(self.btn_disconnect)
        hb.addStretch()
        f0.addRow("", QWidget())
        f0.itemAt(f0.rowCount() - 1, QFormLayout.FieldRole).widget().setLayout(hb)

        # ===== Déroulé / statut =====
        g_cfg = QGroupBox("Déroulé de la campagne")
        f1 = QFormLayout(g_cfg)
        self.lbl_next = QLabel("Prochaine cible : —")
        self.lbl_next.setToolTip("Indique la cible à afficher sur le comparateur pour la prochaine mesure.")
        self.btn_start = QPushButton("Démarrer")
        self.btn_start.setStyleSheet(BTN_PRIMARY_CSS)
        self.btn_start.setToolTip("Démarrer la campagne de mesures (montant puis descendant).")
        self.btn_stop = QPushButton("Arrêter")
        self.btn_stop.setStyleSheet(BTN_DANGER_CSS)
        self.btn_stop.setToolTip("Arrêter la campagne en cours.")
        self.btn_stop.setEnabled(False)
        self.btn_clear = QPushButton("Effacer toutes les mesures")
        self.btn_clear.setStyleSheet(BTN_DANGER_CSS)
        self.btn_clear.setToolTip("Effacer toutes les mesures du tableau.")
        self.btn_probe = QPushButton("Test 3 s")
        self.btn_probe.setToolTip("Lire le port pendant 3 secondes et afficher ce qui arrive (diagnostic).")
        topbar = QHBoxLayout()
        topbar.addWidget(self.btn_start)
        topbar.addWidget(self.btn_stop)
        topbar.addWidget(self.btn_probe)
        topbar.addStretch()
        topbar.addWidget(self.btn_clear)
        f1.addRow("Statut", self.lbl_next)
        f1.addRow("", QWidget()); f1.itemAt(f1.rowCount()-1, QFormLayout.FieldRole).widget().setLayout(topbar)

        # ===== Tableau mesures =====
        g_table = QGroupBox("Mesures")
        vtab = QVBoxLayout(g_table)
        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setToolTip("Tableau des mesures captées automatiquement depuis le dispositif étalon.")
        vtab.addWidget(self.table)

        # ===== Logger brut =====
        g_log = QGroupBox("Flux série (lignes brutes)")
        v3 = QVBoxLayout(g_log)
        log_bar = QHBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(140)
        self.log_view.setToolTip("Affiche toutes les lignes brutes et les messages de debug/erreur du port COM.")
        self.btn_clear_log = QPushButton("Effacer le log")
        self.btn_clear_log.setToolTip("Effacer le contenu du log série.")
        log_bar.addStretch()
        log_bar.addWidget(self.btn_clear_log)
        v3.addWidget(self.log_view)
        v3.addLayout(log_bar)

        # ===== Actions =====
        actions = QHBoxLayout()
        self.btn_save_session = QPushButton("Enregistrer la session…")
        self.btn_save_session.setStyleSheet(BTN_SUCCESS_CSS)
        self.btn_save_session.setToolTip("Enregistre la session courante (nécessite des mesures valides).")
        actions.addStretch()
        actions.addWidget(self.btn_save_session)

        # Assemble
        root.addWidget(g_conn)
        root.addWidget(g_cfg)
        root.addWidget(g_table)
        root.addWidget(g_log)
        root.addLayout(actions)
        root.addStretch()

        # ===== état interne =====
        self._conn = SerialConnection()
        self._reader: Optional[SerialReaderThread] = None
        self.targets: List[float] = []
        self.cycles: int = 0
        self.row_avg_index: int = -1
        self.campaign_running: bool = False
        self.current_cycle: int = 1
        self.current_phase_up: bool = True
        self.current_col: int = 0
        self.waiting_zero: bool = True
        self.by_target: Dict[float, MeasureSeries] = {}
        self._hl_last: Optional[Tuple[int, int]] = None  # (row, col) dernière cellule surlignée

        # init
        self._refresh_ports()
        self._rebuild_from_session()

        # connexions
        self.btn_refresh_ports.clicked.connect(self._refresh_ports)
        self.btn_connect.clicked.connect(self._do_connect)
        self.btn_disconnect.clicked.connect(self._do_disconnect)
        self.btn_start.clicked.connect(self._start_campaign)
        self.btn_stop.clicked.connect(self._stop_campaign)
        self.btn_clear.clicked.connect(self._clear_all)
        self.btn_clear_log.clicked.connect(self._clear_log)
        self.btn_save_session.clicked.connect(self._save_session)
        self.btn_probe.clicked.connect(self._probe_3s)
        session_store.session_changed.connect(self._on_session_changed)
        session_store.measures_updated.connect(self._on_session_changed)

    # ------------- helpers log -------------
    def _log_debug(self, msg: str):
        self.log_view.append(f"[DBG] {msg}")

    def _log_error(self, msg: str):
        self.log_view.append(f"[ERR] {msg}")

    # ------------- session -> table -------------
    def _rebuild_from_session(self):
        s = session_store.current

        # Colonnes (cibles) depuis le comparateur
        self.targets = self._targets_from_comparator(s.comparator_ref)
        # Forcer 0 en première colonne
        if 0.0 not in self.targets:
            self.targets = [0.0] + sorted([t for t in self.targets if abs(t) > self.ZERO_TOL])
        else:
            # assurer 0 en tête
            others = [t for t in self.targets if abs(t) > self.ZERO_TOL]
            self.targets = [0.0] + sorted(others)

        # Lignes : 2 par itération + 1 ligne "Moyenne"
        self.cycles = max(1, s.series_count or 1)
        rows = self.cycles * 2 + 1
        cols = len(self.targets)

        self.table.clear()
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)

        # En-têtes colonnes (cibles)
        self.table.setHorizontalHeaderLabels([str(t) for t in self.targets])

        # En-têtes lignes (itérations)
        r = 0
        for i in range(1, self.cycles + 1):
            self.table.setVerticalHeaderItem(r, QTableWidgetItem(f"{i}↑")); r += 1
            self.table.setVerticalHeaderItem(r, QTableWidgetItem(f"{i}↓")); r += 1
        self.row_avg_index = rows - 1
        self.table.setVerticalHeaderItem(self.row_avg_index, QTableWidgetItem("Moyenne"))

        # by_target (réinjecter éventuelles mesures chargées)
        self.by_target = {t: MeasureSeries(target=t, readings=[]) for t in self.targets}
        for ms in s.series:
            if ms.target in self.by_target:
                for pos, val in enumerate(ms.readings):
                    row = self._row_for_state((pos // 2) + 1, pos % 2 == 0)
                    col = self._col_for_target(ms.target)
                    if row is not None and col is not None and row < self.row_avg_index:
                        self._ensure_item(row, col).setText(str(val))
                        self._color_filled_cell(row, col, self.targets[col], float(val))
                self.by_target[ms.target].readings = list(ms.readings)

        # Reset position capture
        self.campaign_running = False
        self.current_cycle = 1
        self.current_phase_up = True
        self.current_col = 0
        self.waiting_zero = True
        self._hl_last = None

        # Recalcul des moyennes + highlight initial
        self._recompute_means()
        self._update_status()

    def _targets_from_comparator(self, comp_ref: Optional[str]) -> List[float]:
        if not comp_ref:
            return []
        for c in list_comparators():
            if c.reference == comp_ref:
                try:
                    return sorted([float(x) for x in c.targets if x is not None])
                except Exception:
                    return []
        return []

    # ------------- COM -------------
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

        # Thread série avec callbacks debug/erreur vers le logger
        self._reader = SerialReaderThread(
            self._conn,
            self._on_line_from_serial,
            on_debug=lambda m: QTimer.singleShot(0, lambda: self._log_debug(m)),
            on_error=lambda m: QTimer.singleShot(0, lambda: self._log_error(m)),
        )
        self._reader.start()
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)
        QMessageBox.information(self, "Série", f"Connecté à {port} @ {baud}.")

    def _do_disconnect(self):
        self._stop_campaign()
        if self._reader:
            self._reader.stop()
            self._reader = None
        self._conn.close()
        self.btn_disconnect.setEnabled(False)
        self.btn_connect.setEnabled(True)

    # ------------- Campagne -------------
    def _start_campaign(self):
        if not self._conn.is_open():
            QMessageBox.information(self, "Série", "Connecte d’abord le dispositif (port série).")
            return
        self._rebuild_from_session()
        self.campaign_running = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._update_status()

    def _stop_campaign(self):
        self.campaign_running = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._update_status()

    def _clear_all(self):
        for r in range(self.table.rowCount() - 1):
            for c in range(self.table.columnCount()):
                self.table.setItem(r, c, QTableWidgetItem(""))
        for t in self.by_target.values():
            t.readings.clear()
        self.campaign_running = False
        self.current_cycle = 1
        self.current_phase_up = True
        self.current_col = 0
        self.waiting_zero = True
        self._hl_last = None
        self._push_series_to_store()
        self._recompute_means()
        self._update_status()

    # ------------- Logger & Probe -------------
    def _clear_log(self):
        self.log_view.clear()

    def _probe_3s(self):
        """Lecture synchrone pendant 3s pour diag direct (contourne le thread)."""
        if not self._conn.is_open():
            QMessageBox.information(self, "Test 3 s", "Connecte d’abord le port série.")
            return
        self._log_debug("=== PROBE 3s start ===")
        end = time.time() + 3.0
        got = 0
        buf = bytearray()
        while time.time() < end:
            chunk = self._conn.read_chunk()
            if chunk:
                got += len(chunk)
                buf.extend(chunk.replace(b"\r\n", b"\n"))
                # Tentative extraction lignes
                while b"\n" in buf or b"\r" in buf:
                    buf[:] = buf.replace(b"\r\n", b"\n")
                    if b"\n" in buf:
                        line, _, rest = bytes(buf).partition(b"\n")
                    else:
                        line, _, rest = bytes(buf).partition(b"\r")
                    buf[:] = rest
                    text = line.decode(errors="ignore").strip()
                    if text:
                        self.log_view.append(text)
            else:
                QCoreApplication.processEvents()
                time.sleep(0.01)
        self._log_debug(f"=== PROBE 3s end (octets: {got}) ===")

    # ------------- Réception série (thread) -------------
    def _on_line_from_serial(self, raw: str, value: float | None):
        QTimer.singleShot(0, lambda: self._append_line(raw, value))

    def _append_line(self, raw: str, value: float | None):
        # log brut de chaque ligne
        self.log_view.append(raw)

        if not self.campaign_running or value is None:
            return

        # Démarrage de cycle : exiger ~0 au début
        if self.waiting_zero:
            if self.current_phase_up and self.current_col == 0 and abs(value) <= self.ZERO_TOL:
                self._write_current_cell(value)
                self.waiting_zero = False
                finished = self._advance_after_write()
                if finished:
                    self._stop_campaign()
                self._update_status()
            else:
                self._update_status()
            return

        # Écriture normale
        self._write_current_cell(value)
        finished = self._advance_after_write()
        if finished:
            self._stop_campaign()
        self._update_status()

    # ------------- Table & Store -------------
    def _row_for_state(self, cycle: int, up: bool) -> int:
        return (cycle - 1) * 2 + (0 if up else 1)

    def _col_for_target(self, target: float) -> Optional[int]:
        try:
            return self.targets.index(target)
        except ValueError:
            return None

    def _ensure_item(self, row: int, col: int) -> QTableWidgetItem:
        it = self.table.item(row, col)
        if it is None:
            it = QTableWidgetItem("")
            self.table.setItem(row, col, it)
        return it

    def _color_filled_cell(self, row: int, col: int, target: float, measured: float):
        """Colore en vert et fixe une infobulle avec écart."""
        it = self._ensure_item(row, col)
        it.setBackground(QBrush(QColor(212, 237, 218)))  # vert doux
        delta = measured - target
        it.setToolTip(f"Cible: {target}\nMesuré: {measured}\nÉcart (mesuré - cible): {delta:+.6f}")

    def _restore_cell_background(self, row: int, col: int):
        """Restaure le fond après suppression du highlight:
           - vert si la cellule est remplie
           - transparent sinon
        """
        it = self._ensure_item(row, col)
        if it.text():
            it.setBackground(QBrush(QColor(212, 237, 218)))  # vert
        else:
            it.setBackground(QBrush())  # reset

    def _write_current_cell(self, value: float):
        row = self._row_for_state(self.current_cycle, self.current_phase_up)
        col = self.current_col
        it = self.table.item(row, col)
        if it is None or not it.text():
            self._ensure_item(row, col).setText(str(value))
            # Colorer + tooltip d’écart
            self._color_filled_cell(row, col, self.targets[col], float(value))
            # Mettre à jour by_target[target].readings
            target = self.targets[col]
            readings = self.by_target[target].readings
            pos = (self.current_cycle - 1) * 2 + (0 if self.current_phase_up else 1)
            while len(readings) <= pos:
                readings.append(None)
            readings[pos] = value
            while readings and readings[-1] is None:
                readings.pop()
            self._push_series_to_store()
            self._recompute_means()

    def _push_series_to_store(self):
        ordered = [self.by_target[t] for t in self.targets]
        session_store.set_series(ordered)

    def _recompute_means(self):
        for c in range(self.table.columnCount()):
            vals = []
            for r in range(self.table.rowCount() - 1):
                it = self.table.item(r, c)
                if it and it.text():
                    try:
                        vals.append(float(it.text()))
                    except ValueError:
                        pass
            mean_txt = "" if not vals else f"{sum(vals)/len(vals):.6f}"
            self._ensure_item(self.row_avg_index, c).setText(mean_txt)

    # ------------- Avancement & Highlight -------------
    def _advance_after_write(self) -> bool:
        last_col = self.table.columnCount() - 1

        if self.current_phase_up:
            if self.current_col < last_col:
                self.current_col += 1
                return False
            else:
                self.current_phase_up = False
                return False
        else:
            if self.current_col > 0:
                self.current_col -= 1
                return False
            else:
                if self.current_cycle < self.cycles:
                    self.current_cycle += 1
                    self.current_phase_up = True
                    self.current_col = 0
                    self.waiting_zero = True
                    return False
                else:
                    return True

    def _clear_highlight(self):
        if not self._hl_last:
            return
        r, c = self._hl_last
        self._restore_cell_background(r, c)
        self._hl_last = None

    def _highlight_current_cell(self):
        if self.table.rowCount() == 0 or self.table.columnCount() == 0:
            self._clear_highlight()
            return
        if not self.campaign_running:
            self._clear_highlight()
            return
        if self.waiting_zero:
            row = self._row_for_state(self.current_cycle, True); col = 0
        else:
            row = self._row_for_state(self.current_cycle, self.current_phase_up)
            col = self.current_col
        if row >= self.row_avg_index:
            self._clear_highlight(); return
        self._clear_highlight()
        it = self._ensure_item(row, col)
        it.setBackground(QBrush(QColor(255, 249, 196)))  # jaune doux = prochaine mesure
        self._hl_last = (row, col)

    def _update_status(self):
        if not self.campaign_running:
            self.lbl_next.setText("Prochaine cible : — (campagne arrêtée)")
            self._highlight_current_cell()
            return
        arrow = "↑" if self.current_phase_up else "↓"
        target = self.targets[self.current_col] if self.targets else 0.0
        self.lbl_next.setText(
            ("Prochaine cible : 0 " if self.waiting_zero else f"Prochaine cible : {target} ")
            + f"(Cycle {self.current_cycle}/{self.cycles}, {arrow})"
        )
        self._highlight_current_cell()

    # ------------- Sauvegarde -------------
    def _save_session(self):
        if not session_store.can_save():
            QMessageBox.warning(self, "Impossible", "Aucune mesure dans la session — enregistrement interdit.")
            return
        try:
            path = session_store.save()
            QMessageBox.information(self, "Session", f"Session enregistrée :\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Échec de l’enregistrement :\n{e}")

    # ------------- Réactions session -------------
    def _on_session_changed(self, _s):
        self._rebuild_from_session()

    # ------------- Nettoyage -------------
    def deleteLater(self):
        try:
            self._stop_campaign()
            if self._reader:
                self._reader.stop()
            self._conn.close()
        finally:
            super().deleteLater()
