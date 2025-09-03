from __future__ import annotations

import time
from typing import List, Dict, Optional, Tuple

from PySide6.QtCore import QTimer, QCoreApplication
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QPushButton,
    QMessageBox, QTextEdit, QLabel, QTableWidget, QTableWidgetItem
)

from ...models.session import MeasureSeries
from ...state.session_store import session_store
from ...io.serial_manager import serial_manager
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

        # ===== Déroulé / statut =====
        g_cfg = QGroupBox("Déroulé de la campagne")
        f1 = QFormLayout(g_cfg)
        self.lbl_next = QLabel("Prochaine cible : —")
        self.btn_start = QPushButton("Démarrer"); self.btn_start.setStyleSheet(BTN_PRIMARY_CSS)
        self.btn_stop = QPushButton("Arrêter"); self.btn_stop.setStyleSheet(BTN_DANGER_CSS); self.btn_stop.setEnabled(False)
        self.btn_clear = QPushButton("Effacer toutes les mesures"); self.btn_clear.setStyleSheet(BTN_DANGER_CSS)
        self.btn_probe = QPushButton("Test 3 s")
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
        vtab.addWidget(self.table)

        # ===== Logger brut =====
        g_log = QGroupBox("Flux série (lignes brutes)")
        v3 = QVBoxLayout(g_log)
        log_bar = QHBoxLayout()
        self.log_view = QTextEdit(); self.log_view.setReadOnly(True); self.log_view.setMaximumHeight(160)
        self.btn_clear_log = QPushButton("Effacer le log")
        log_bar.addStretch(); log_bar.addWidget(self.btn_clear_log)
        v3.addWidget(self.log_view)
        v3.addLayout(log_bar)

        # ===== Actions =====
        actions = QHBoxLayout()
        self.btn_save_session = QPushButton("Enregistrer la session…"); self.btn_save_session.setStyleSheet(BTN_SUCCESS_CSS)
        actions.addStretch(); actions.addWidget(self.btn_save_session)

        # Assemble
        root.addWidget(g_cfg)
        root.addWidget(g_table)
        root.addWidget(g_log)
        root.addLayout(actions)
        root.addStretch()

        # ===== état interne =====
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
        self._rebuild_from_session()

        # connexions UI
        self.btn_start.clicked.connect(self._start_campaign)
        self.btn_stop.clicked.connect(self._stop_campaign)
        self.btn_clear.clicked.connect(self._clear_all)
        self.btn_clear_log.clicked.connect(self._clear_log)
        self.btn_save_session.clicked.connect(self._save_session)
        self.btn_probe.clicked.connect(self._probe_3s)

        # session store
        session_store.session_changed.connect(self._on_session_changed)
        session_store.measures_updated.connect(self._on_session_changed)

        # serial manager
        serial_manager.line_received.connect(lambda raw, val: self._on_line_from_serial(raw, val))
        serial_manager.debug.connect(lambda m: self.log_view.append(f"[DBG] {m}"))
        serial_manager.error.connect(lambda m: self.log_view.append(f"[ERR] {m}"))

    # ------------- session -> table -------------
    def _rebuild_from_session(self):
        s = session_store.current

        # Colonnes (cibles) depuis le comparateur
        self.targets = self._targets_from_comparator(s.comparator_ref)
        # Forcer 0 en première colonne
        if 0.0 not in self.targets:
            self.targets = [0.0] + sorted([t for t in self.targets if abs(t) > self.ZERO_TOL])
        else:
            others = [t for t in self.targets if abs(t) > self.ZERO_TOL]
            self.targets = [0.0] + sorted(others)

        # Lignes : 2 par itération + 1 ligne "Moyenne"
        self.cycles = max(1, s.series_count or 1)
        rows = self.cycles * 2 + 1
        cols = len(self.targets)

        self.table.clear()
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        self.table.setHorizontalHeaderLabels([str(t) for t in self.targets])

        r = 0
        for i in range(1, self.cycles + 1):
            self.table.setVerticalHeaderItem(r, QTableWidgetItem(f"{i}↑")); r += 1
            self.table.setVerticalHeaderItem(r, QTableWidgetItem(f"{i}↓")); r += 1
        self.row_avg_index = rows - 1
        self.table.setVerticalHeaderItem(self.row_avg_index, QTableWidgetItem("Moyenne"))

        # Réinjecter éventuelles mesures
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

        # Reset capture
        self.campaign_running = False
        self.current_cycle = 1
        self.current_phase_up = True
        self.current_col = 0
        self.waiting_zero = True
        self._hl_last = None

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

    # ------------- Campagne -------------
    def _start_campaign(self):
        if not serial_manager.is_open():
            QMessageBox.information(self, "Série", "Connecte d’abord le dispositif dans l’onglet Session.")
            return
        self._rebuild_from_session()
        self.campaign_running = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._update_status()

        # Si mode 'À la demande', envoie la première commande
        mode, trig, _ = serial_manager.get_send_config()
        if mode == "À la demande":
            serial_manager.send_text(trig, serial_manager.eol_bytes())

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
        if not serial_manager.is_open():
            QMessageBox.information(self, "Test 3 s", "Connecte d’abord le port série dans l’onglet Session.")
            return
        self.log_view.append("[DBG] === PROBE 3s start ===")
        end = time.time() + 3.0
        got = 0
        buf = bytearray()
        while time.time() < end:
            chunk = serial_manager.read_chunk()
            if chunk:
                got += len(chunk)
                buf.extend(chunk.replace(b"\r\n", b"\n"))
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
        self.log_view.append(f"[DBG] === PROBE 3s end (octets: {got}) ===")

    # ------------- Réception série -------------
    def _on_line_from_serial(self, raw: str, value: float | None):
        QTimer.singleShot(0, lambda: self._append_line(raw, value))

    def _append_line(self, raw: str, value: float | None):
        self.log_view.append(raw)

        if not self.campaign_running or value is None:
            # mode 'À la demande' : renvoyer une commande pour forcer la suivante
            if self.campaign_running and serial_manager.get_send_config()[0] == "À la demande":
                serial_manager.send_text(serial_manager.get_send_config()[1], serial_manager.eol_bytes())
            return

        # Démarrage de cycle : exiger ~0 au début
        if self.waiting_zero:
            if self.current_phase_up and self.current_col == 0 and abs(value) <= self.ZERO_TOL:
                self._write_current_cell(value)
                self.waiting_zero = False
                finished = self._advance_after_write()
                if finished:
                    self._stop_campaign()
                else:
                    if serial_manager.get_send_config()[0] == "À la demande":
                        serial_manager.send_text(serial_manager.get_send_config()[1], serial_manager.eol_bytes())
                self._update_status()
            else:
                if serial_manager.get_send_config()[0] == "À la demande":
                    serial_manager.send_text(serial_manager.get_send_config()[1], serial_manager.eol_bytes())
                self._update_status()
            return

        # Écriture normale
        self._write_current_cell(value)
        finished = self._advance_after_write()
        if finished:
            self._stop_campaign()
        else:
            if serial_manager.get_send_config()[0] == "À la demande":
                serial_manager.send_text(serial_manager.get_send_config()[1], serial_manager.eol_bytes())
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
        it = self._ensure_item(row, col)
        it.setBackground(QBrush(QColor(212, 237, 218)))  # vert doux
        delta = measured - target
        it.setToolTip(f"Cible: {target}\nMesuré: {measured}\nÉcart (mesuré - cible): {delta:+.6f}")

    def _restore_cell_background(self, row: int, col: int):
        it = self._ensure_item(row, col)
        if it.text():
            it.setBackground(QBrush(QColor(212, 237, 218)))
        else:
            it.setBackground(QBrush())

    def _write_current_cell(self, value: float):
        row = self._row_for_state(self.current_cycle, self.current_phase_up)
        col = self.current_col
        it = self.table.item(row, col)
        if it is None or not it.text():
            self._ensure_item(row, col).setText(str(value))
            self._color_filled_cell(row, col, self.targets[col], float(value))
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
            self._clear_highlight(); return
        if not self.campaign_running:
            self._clear_highlight(); return
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
        finally:
            super().deleteLater()
