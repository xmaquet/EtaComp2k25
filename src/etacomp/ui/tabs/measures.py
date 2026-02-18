from __future__ import annotations

import time
from typing import List, Dict, Optional, Tuple

from PySide6.QtCore import QTimer, QCoreApplication
from PySide6.QtGui import QColor, QBrush, QTextCursor, QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QPushButton,
    QMessageBox, QTextEdit, QLabel, QTableWidget, QTableWidgetItem, QCheckBox,
    QStyledItemDelegate
)

from ...models.session import MeasureSeries
from ...state.session_store import session_store
from ...io.serial_manager import serial_manager
from ...io.storage import list_comparators
from ..sound import play_beep


BTN_PRIMARY_CSS = (
    "QPushButton{background:#0d6efd;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
    "QPushButton:hover{background:#0b5ed7;}"
)
BTN_DANGER_CSS = (
    "QPushButton{background:#dc3545;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
    "QPushButton:hover{background:#bb2d3b;}"
)

# Texte foncé pour cellules à fond clair (vert, jaune, gris) — lisible en mode dark
TEXT_ON_LIGHT_BG = QColor(33, 37, 41)


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
        # Délégué pour encadrer la cellule en override
        self._override_delegate = self._OverrideCellDelegate(self.table)
        self.table.setItemDelegate(self._override_delegate)
        vtab.addWidget(self.table)

        # ===== Logger brut =====
        g_log = QGroupBox("Flux série (lignes brutes)")
        v3 = QVBoxLayout(g_log)
        log_bar = QHBoxLayout()
        self.log_view = QTextEdit(); self.log_view.setReadOnly(True); self.log_view.setMaximumHeight(160)
        self.chk_raw_debug = QCheckBox("Mode debug (flux brut)"); self.chk_raw_debug.setToolTip("Affiche le flux série brut, sans parsing ni normalisation (non actif par défaut).")
        self.btn_clear_log = QPushButton("Effacer le log")
        log_bar.addWidget(self.chk_raw_debug)
        log_bar.addStretch(); log_bar.addWidget(self.btn_clear_log)
        v3.addWidget(self.log_view)
        v3.addLayout(log_bar)

        # Assemble
        root.addWidget(g_cfg)
        root.addWidget(g_table)
        root.addWidget(g_log)

        # Donner plus d'espace vertical au tableau des mesures
        try:
            root.setStretch(0, 0)
            root.setStretch(1, 5)  # tableau prioritaire
            root.setStretch(2, 1)  # log compact
        except Exception:
            pass

        # ===== état interne =====
        self.targets: List[float] = []
        self.cycles: int = 0
        self.row_avg_up_index: int = -1
        self.row_avg_down_index: int = -1
        self.row_index_line: int = -1  # ligne d'indices des cibles
        self.campaign_running: bool = False
        self.current_cycle: int = 1
        self.current_phase_up: bool = True
        self.current_col: int = 0
        self.waiting_zero: bool = True
        self.by_target: Dict[float, MeasureSeries] = {}
        self._hl_last: Optional[Tuple[int, int]] = None  # (row, col) dernière cellule surlignée
        # Édition dirigée par opérateur (override d'une cellule existante)
        self._override_cell: Optional[Tuple[int, int]] = None  # (row, col) en attente de nouvelle valeur
        self._locked_after_stop: bool = False

        # init
        self._rebuild_from_session()

        # connexions UI
        self.btn_start.clicked.connect(self._start_campaign)
        self.btn_stop.clicked.connect(self._stop_campaign)
        self.btn_clear.clicked.connect(self._clear_all)
        self.btn_clear_log.clicked.connect(self._clear_log)
        self.btn_probe.clicked.connect(self._probe_3s)
        self.chk_raw_debug.toggled.connect(self._toggle_raw_debug)
        # Sélection cellule pour correction / repositionnement
        try:
            self.table.cellClicked.connect(self._on_cell_clicked)
        except Exception:
            pass

        # session store
        session_store.session_changed.connect(self._on_session_changed)
        session_store.measures_updated.connect(self._on_session_changed)

        # serial manager
        serial_manager.line_received.connect(lambda raw, val: self._on_line_from_serial(raw, val))
        serial_manager.debug.connect(lambda m: self.log_view.append(f"[DBG] {m}"))
        serial_manager.error.connect(lambda m: self.log_view.append(f"[ERR] {m}"))
        serial_manager.raw.connect(self._on_raw_chunk)

    # ------------- helpers -------------
    def _safe_send_config(self):
        """Retourne (mode, trig, eol_bytes) en tolérant une ancienne version du SerialManager."""
        try:
            mode, trig, _ = serial_manager.get_send_config()
            eol = serial_manager.eol_bytes()
            return mode, trig, eol
        except Exception:
            return "Manuel", "", None

    # ------------- session -> table -------------
    def _rebuild_from_session(self):
        s = session_store.current

        # Colonnes (cibles) — priorité au profil comparateur; fallback: déduire depuis la session chargée
        self.targets = self._targets_from_comparator(s.comparator_ref)
        if not self.targets:
            seen = set()
            derived = []
            for ms in (s.series or []):
                try:
                    t = float(ms.target)
                except Exception:
                    continue
                if t not in seen:
                    seen.add(t)
                    derived.append(t)
            self.targets = sorted(derived)
        # Forcer 0 en première colonne
        if 0.0 not in self.targets:
            self.targets = [0.0] + sorted([t for t in self.targets if abs(t) > self.ZERO_TOL])
        else:
            others = [t for t in self.targets if abs(t) > self.ZERO_TOL]
            self.targets = [0.0] + sorted(others)

        # Lignes : montantes (N), moyenne montantes, descendantes (N), moyenne descendantes, indices
        self.cycles = max(1, s.series_count or 1)
        rows = self.cycles * 2 + 3
        cols = len(self.targets)

        self.table.clear()
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        self.table.setHorizontalHeaderLabels([str(t) for t in self.targets])

        # Entêtes de lignes: montantes (1..N), moyenne ↑, descendantes (1..N), moyenne ↓
        for i in range(1, self.cycles + 1):
            self.table.setVerticalHeaderItem(i - 1, QTableWidgetItem(f"{i}↑"))
        self.row_avg_up_index = self.cycles
        self.table.setVerticalHeaderItem(self.row_avg_up_index, QTableWidgetItem("Moyenne ↑ (µm)"))
        for i in range(1, self.cycles + 1):
            self.table.setVerticalHeaderItem(self.row_avg_up_index + i, QTableWidgetItem(f"{i}↓"))
        self.row_avg_down_index = self.row_avg_up_index + self.cycles + 1
        self.table.setVerticalHeaderItem(self.row_avg_down_index, QTableWidgetItem("Moyenne ↓ (µm)"))

        # Ligne d'indices sous le tableau
        self.row_index_line = self.row_avg_down_index + 1
        self.table.setVerticalHeaderItem(self.row_index_line, QTableWidgetItem("Index"))

        # Réinjecter éventuelles mesures
        self.by_target = {t: MeasureSeries(target=t, readings=[]) for t in self.targets}
        for ms in s.series:
            if ms.target in self.by_target:
                for pos, val in enumerate(ms.readings):
                    row = self._row_for_state((pos // 2) + 1, pos % 2 == 0)
                    col = self._col_for_target(ms.target)
                    if row is not None and col is not None and row not in (self.row_avg_up_index, self.row_avg_down_index, self.row_index_line):
                        self._ensure_item(row, col).setText(str(val))
                        self._color_filled_cell(row, col, self.targets[col], float(val))
                self.by_target[ms.target].readings = list(ms.readings)

        # Remplir la ligne d'indices (1..N) et appliquer un style différenciant
        for c in range(self.table.columnCount()):
            it = self._ensure_item(self.row_index_line, c)
            it.setText(str(c + 1))
            it.setBackground(QBrush(QColor(230, 230, 230)))  # gris clair
            it.setForeground(QBrush(TEXT_ON_LIGHT_BG))
            f = it.font(); f.setBold(True); it.setFont(f)
            it.setToolTip("Index de colonne (cible #)")

        # Reset capture
        self.campaign_running = False
        self.current_cycle = 1
        self.current_phase_up = True
        self.current_col = 0
        self.waiting_zero = True
        self._hl_last = None

        self._recompute_means2()
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
        self._locked_after_stop = False
        self._override_cell = None
        self._rebuild_from_session()
        # Vérifier qu'il y a au moins 2 cibles (0 et au moins une valeur > 0)
        if len(self.targets) < 2:
            QMessageBox.information(
                self,
                "Configuration incomplète",
                "Aucun profil de comparateur sélectionné avec des cibles > 0.\n\n"
                "Sélectionne un comparateur dans l’onglet Session (Bibliothèque → 11 cibles dont 0)."
            )
            return
        self.campaign_running = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._update_status()

        # Si mode 'À la demande', envoie la première commande
        mode, trig, eol = self._safe_send_config()
        if mode == "À la demande":
            serial_manager.send_text(trig, eol)

    def _stop_campaign(self):
        self.campaign_running = False
        self._override_cell = None
        self._locked_after_stop = True
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._update_status()

    def _clear_all(self):
        for r in range(self.table.rowCount()):
            if r in (self.row_avg_up_index, self.row_avg_down_index, self.row_index_line):
                continue
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

    def _toggle_raw_debug(self, enabled: bool):
        try:
            serial_manager.set_raw_debug(bool(enabled))
            if enabled:
                self.log_view.append("[DBG] Mode brut activé — affichage du flux sans parsing")
            else:
                self.log_view.append("[DBG] Mode brut désactivé")
        except Exception as e:
            self.log_view.append(f"[ERR] Raw debug: {e}")

    def _on_raw_chunk(self, s: str):
        if self.chk_raw_debug.isChecked():
            # Afficher tel quel, sans normalisation
            self.log_view.moveCursor(QTextCursor.End)
            self.log_view.insertPlainText(s)

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

        # Mode correction opérateur: si une cellule est ciblée, écrire ici en priorité
        if self._override_cell and value is not None:
            row, col = self._override_cell
            wrote = self._write_specific_cell(row, col, value)
            if wrote:
                # Fin du mode override; ne pas avancer le pointeur automatique
                self._clear_override_visual()
                self._override_cell = None
                self._update_status()
            return

        if not self.campaign_running or value is None:
            # mode 'À la demande' : renvoyer une commande pour forcer la suivante
            mode, trig, eol = self._safe_send_config()
            if self.campaign_running and mode == "À la demande":
                serial_manager.send_text(trig, eol)
            return

        # Démarrage de cycle : exiger ~0 au début
        if self.waiting_zero:
            if self.current_phase_up and self.current_col == 0 and abs(value) <= self.ZERO_TOL:
                wrote = self._write_current_cell(value)
                self.waiting_zero = False
                if wrote:
                    finished = self._advance_after_write()
                    if finished:
                        self._stop_campaign()
                    else:
                        mode, trig, eol = self._safe_send_config()
                        if mode == "À la demande":
                            serial_manager.send_text(trig, eol)
                self._update_status()
            else:
                mode, trig, eol = self._safe_send_config()
                if mode == "À la demande":
                    serial_manager.send_text(trig, eol)
                self._update_status()
            return

        # Écriture normale
        wrote = self._write_current_cell(value)
        if wrote:
            finished = self._advance_after_write()
            if finished:
                self._stop_campaign()
            else:
                mode, trig, eol = self._safe_send_config()
                if mode == "À la demande":
                    serial_manager.send_text(trig, eol)
        self._update_status()

    # ------------- Sélection / Override -------------
    def _on_cell_clicked(self, row: int, col: int):
        """Gestion du clic opérateur sur une cellule du tableau."""
        # Si verrouillé (après arrêt), aucune modification autorisée
        if self._locked_after_stop:
            return
        # Clic pendant la campagne:
        if self.campaign_running:
            # Si clic sur une cellule REMPLIE: activer une correction dirigée
            it = self.table.item(row, col)
            if it and it.text().strip():
                self._set_override_visual(row, col)
                self.lbl_next.setText(f"Correction sur R{row+1} C{col+1} — En attente d'une nouvelle valeur…")
                return
            # Si clic sur une cellule VIDE: si c'est la prochaine case vide logique, repositionner le pointeur
            if self._is_cell_empty(row, col):
                # Repositionner l'état si la cellule est cohérente
                ok = self._set_state_from_cell(row, col)
                if ok:
                    self._override_cell = None
                    self._update_status()
                return
            # Sinon, ignorer
            return
        # Campagne non active: autoriser modification de toute cellule (override ponctuel)
        it = self.table.item(row, col)
        if it and it.text().strip():
            self._set_override_visual(row, col)
            self.lbl_next.setText(f"Correction (campagne arrêtée) sur R{row+1} C{col+1} — En attente d'une nouvelle valeur…")
        else:
            self._clear_override_visual()
            self._update_status()

    def _is_cell_empty(self, row: int, col: int) -> bool:
        it = self.table.item(row, col)
        return not (it and it.text().strip())

    def _set_state_from_cell(self, row: int, col: int) -> bool:
        """Repositionne le pointeur courant (cycle/phase/col) pour reprendre sur la cellule donnée si possible."""
        # Interdire lignes de moyenne et ligne d'index
        if row in (self.row_avg_up_index, self.row_avg_down_index, self.row_index_line):
            return False
        # Déduire phase/cycle depuis la ligne
        if row < self.row_avg_up_index:
            up = True
            cyc = row + 1
        else:
            up = False
            cyc = row - self.row_avg_up_index
        # Valider bornes
        if cyc < 1 or cyc > self.cycles:
            return False
        self.current_cycle = cyc
        self.current_phase_up = up
        self.current_col = col
        # Attente zéro uniquement si on est au début d'une montée et colonne 0
        self.waiting_zero = bool(self.current_phase_up and self.current_col == 0)
        # Sortir d'un override éventuel si on repositionne
        self._clear_override_visual()
        return True

    # ------------- Table & Store -------------
    def _row_for_state(self, cycle: int, up: bool) -> int:
        # Nouvelle disposition: montantes (0..N-1), moyenne ↑ (N), descendantes (N+1..2N), moyenne ↓ (2N+1)
        if up:
            return (cycle - 1)
        else:
            return self.row_avg_up_index + 1 + (cycle - 1)

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
        it.setForeground(QBrush(TEXT_ON_LIGHT_BG))
        delta = measured - target
        it.setToolTip(f"Cible: {target}\nMesuré: {measured}\nÉcart (mesuré - cible): {delta:+.6f}")

    def _restore_cell_background(self, row: int, col: int):
        it = self._ensure_item(row, col)
        if it.text():
            it.setBackground(QBrush(QColor(212, 237, 218)))
            it.setForeground(QBrush(TEXT_ON_LIGHT_BG))
        else:
            it.setBackground(QBrush())
            it.setForeground(QBrush())

    def _write_current_cell(self, value: float) -> bool:
        # Prendre la valeur absolue (certains bancs renvoient des valeurs négatives selon le sens)
        try:
            value = abs(float(value))
        except Exception:
            pass
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
            self._recompute_means2()
            # Son bref à chaque enregistrement
            play_beep()
            return True
        return False

    def _write_specific_cell(self, row: int, col: int, value: float) -> bool:
        """Écrit/écrase une valeur à la cellule spécifiée, met à jour le store et recalcule les moyennes."""
        try:
            value = abs(float(value))
        except Exception:
            pass
        # Interdire écriture sur lignes moyennes/index
        if row in (self.row_avg_up_index, self.row_avg_down_index, self.row_index_line):
            return False
        # Déterminer target
        if col < 0 or col >= len(self.targets):
            return False
        target = self.targets[col]
        # Déterminer cycle/phase à partir de la ligne
        if row < self.row_avg_up_index:
            up = True
            cyc = row + 1
        else:
            up = False
            cyc = row - self.row_avg_up_index
        if cyc < 1:
            return False
        # Écrire dans la table
        self._ensure_item(row, col).setText(str(value))
        self._color_filled_cell(row, col, target, float(value))
        # Mettre à jour readings
        readings = self.by_target[target].readings
        pos = (cyc - 1) * 2 + (0 if up else 1)
        while len(readings) <= pos:
            readings.append(None)
        readings[pos] = value
        while readings and readings[-1] is None:
            readings.pop()
        self._push_series_to_store()
        self._recompute_means2()
        play_beep()
        return True

    def _recompute_means2(self):
        """Calcule les moyennes des écarts (µm) pour montée/descente et met à jour l'UI, puis surligne le point critique."""
        # Conserver les valeurs numériques (µm) pour mise en évidence du point critique
        self._mean_up_um = [None] * self.table.columnCount()
        self._mean_down_um = [None] * self.table.columnCount()
        for c in range(self.table.columnCount()):
            target = self.targets[c] if c < len(self.targets) else 0.0
            # Moyenne montantes
            vals_up = []
            for r in range(0, self.row_avg_up_index):
                it = self.table.item(r, c)
                if it and it.text():
                    try:
                        vals_up.append(float(it.text()))
                    except ValueError:
                        pass
            mean_up_txt = ""
            if vals_up:
                mean_err_up = sum((v - target) for v in vals_up) / len(vals_up)
                mean_up_um = mean_err_up * 1000.0
                mean_up_txt = f"{mean_up_um:+.1f}"
                self._mean_up_um[c] = mean_up_um
            self._ensure_item(self.row_avg_up_index, c).setText(mean_up_txt)
            it_up = self._ensure_item(self.row_avg_up_index, c)
            f_up = it_up.font(); f_up.setBold(True); it_up.setFont(f_up)
            it_up.setForeground(QBrush())  # reset couleur

            # Moyenne descendantes
            vals_down = []
            for r in range(self.row_avg_up_index + 1, self.row_avg_down_index):
                it = self.table.item(r, c)
                if it and it.text():
                    try:
                        vals_down.append(float(it.text()))
                    except ValueError:
                        pass
            mean_down_txt = ""
            if vals_down:
                mean_err_down = sum((v - target) for v in vals_down) / len(vals_down)
                mean_down_um = mean_err_down * 1000.0
                mean_down_txt = f"{mean_down_um:+.1f}"
                self._mean_down_um[c] = mean_down_um
            self._ensure_item(self.row_avg_down_index, c).setText(mean_down_txt)
            it_dn = self._ensure_item(self.row_avg_down_index, c)
            f_dn = it_dn.font(); f_dn.setBold(True); it_dn.setFont(f_dn)
            it_dn.setForeground(QBrush())  # reset couleur
        # Surligner la plus grande valeur d'écart (absolu) entre ↑ et ↓
        best = None  # tuple (abs_val, dir, col, other_abs)
        for c in range(self.table.columnCount()):
            up = self._mean_up_um[c]
            dn = self._mean_down_um[c]
            if up is not None:
                other = abs(dn) if dn is not None else 0.0
                t = (abs(up), "up", c, other)
                if (best is None) or (t[0] > best[0] or (t[0] == best[0] and t[3] > best[3])):
                    best = t
            if dn is not None:
                other = abs(up) if up is not None else 0.0
                t = (abs(dn), "down", c, other)
                if (best is None) or (t[0] > best[0] or (t[0] == best[0] and t[3] > best[3])):
                    best = t
        if best:
            _, d, col, _ = best
            r = self.row_avg_up_index if d == "up" else self.row_avg_down_index
            it = self._ensure_item(r, col)
            it.setForeground(QBrush(QColor(220, 53, 69)))


    class _OverrideCellDelegate(QStyledItemDelegate):
        """Délégué qui dessine un encadrement pointillé épais autour de la cellule en override."""
        def __init__(self, parent=None):
            super().__init__(parent)
            self._row = None
            self._col = None

        def set_target(self, row: int, col: int):
            self._row = int(row)
            self._col = int(col)

        def clear_target(self):
            self._row = None
            self._col = None

        def paint(self, painter, option, index):
            # Peinture standard
            super().paint(painter, option, index)
            try:
                if self._row is None or self._col is None:
                    return
                if index.row() == self._row and index.column() == self._col:
                    from PySide6.QtGui import QPen, QColor
                    from PySide6.QtCore import Qt
                    painter.save()
                    pen = QPen(QColor(13, 110, 253))  # bleu primaire
                    pen.setWidth(3)
                    pen.setStyle(Qt.PenStyle.DotLine)
                    painter.setPen(pen)
                    r = option.rect.adjusted(2, 2, -2, -2)
                    painter.drawRect(r)
                    painter.restore()
            except Exception:
                # Ne pas bloquer l'affichage si un souci survient
                pass

    # ----- Override visuals -----
    def _set_override_visual(self, row: int, col: int):
        # Enregistrer
        self._override_cell = (row, col)
        # Délégué: cible
        try:
            self._override_delegate.set_target(row, col)
            self.table.viewport().update()
        except Exception:
            pass
        # Tooltip "modification"
        try:
            it = self._ensure_item(row, col)
            it.setToolTip("modification")
        except Exception:
            pass

    def _clear_override_visual(self):
        if not self._override_cell:
            return
        row, col = self._override_cell
        try:
            # Retirer tooltip
            it = self._ensure_item(row, col)
            it.setToolTip("")
        except Exception:
            pass
        try:
            self._override_delegate.clear_target()
            self.table.viewport().update()
        except Exception:
            pass
        self._override_cell = None

    def _push_series_to_store(self):
        ordered = [self.by_target[t] for t in self.targets]
        session_store.set_series(ordered)

    def _recompute_means(self):
        # Conserver les valeurs numériques (µm) pour mise en évidence du point critique
        self._mean_up_um: List[Optional[float]] = [None] * self.table.columnCount()
        self._mean_down_um: List[Optional[float]] = [None] * self.table.columnCount()
        for c in range(self.table.columnCount()):
            target = self.targets[c] if c < len(self.targets) else 0.0
            # Moyenne montantes
            vals_up = []
            for r in range(0, self.row_avg_up_index):
                it = self.table.item(r, c)
                if it and it.text():
                    try:
                        vals_up.append(float(it.text()))
                    except ValueError:
                        pass
            # moyenne des écarts (mesuré - cible)
            mean_up_txt = ""
            if vals_up:
                mean_err_up = sum((v - target) for v in vals_up) / len(vals_up)
                mean_up_um = mean_err_up * 1000.0
                mean_up_txt = f"{mean_up_um:+.1f}"
                self._mean_up_um[c] = mean_up_um
            self._ensure_item(self.row_avg_up_index, c).setText(mean_up_txt)
            # µm: rendre en gras (ligne moyenne ↑)
            it_up = self._ensure_item(self.row_avg_up_index, c)
            f_up = it_up.font(); f_up.setBold(True); it_up.setFont(f_up)

            # Moyenne descendantes
            vals_down = []
            for r in range(self.row_avg_up_index + 1, self.row_avg_down_index):
                it = self.table.item(r, c)
                if it and it.text():
                    try:
                        vals_down.append(float(it.text()))
                    except ValueError:
                        pass
            # moyenne des écarts (mesuré - cible)
            mean_down_txt = ""
            if vals_down:
                mean_err_down = sum((v - target) for v in vals_down) / len(vals_down)
                mean_down_um = mean_err_down * 1000.0
                mean_down_txt = f"{mean_down_um:+.1f}"
                self._mean_down_um[c] = mean_down_um
            self._ensure_item(self.row_avg_down_index, c).setText(mean_down_txt)
            # µm: rendre en gras (ligne moyenne ↓)
            it_dn = self._ensure_item(self.row_avg_down_index, c)
            f_dn = it_dn.font(); f_dn.setBold(True); it_dn.setFont(f_dn)
        # Mettre en évidence la plus grande valeur d'écart (par les moyennes)
        self._highlight_max_mean_error()

    def _clear_mean_highlights(self):
        # Réinitialise le style des lignes de moyennes
        for c in range(self.table.columnCount()):
            for r in (self.row_avg_up_index, self.row_avg_down_index):
                it = self._ensure_item(r, c)
                it.setForeground(QBrush())  # couleur par défaut

    def _highlight_max_mean_error(self):
        self._clear_mean_highlights()
        # Construire la liste des candidats (valeur absolue en µm)
        candidates: List[Tuple[float, str, int, float]] = []  # (abs_val, dir, col, other_abs)
        for c in range(self.table.columnCount()):
            up = self._mean_up_um[c]
            dn = self._mean_down_um[c]
            if up is not None:
                other = abs(dn) if dn is not None else 0.0
                candidates.append((abs(up), "up", c, other))
            if dn is not None:
                other = abs(up) if up is not None else 0.0
                candidates.append((abs(dn), "down", c, other))
        if not candidates:
            return
        # Chercher le max; en cas d'égalité, privilégier celle dont l'autre sens a l'écart le plus grand
        candidates.sort(key=lambda t: (t[0], t[3]), reverse=True)
        _, best_dir, best_col, _ = candidates[0]
        r = self.row_avg_up_index if best_dir == "up" else self.row_avg_down_index
        it = self._ensure_item(r, best_col)
        f = it.font(); f.setBold(True); it.setFont(f)
        it.setForeground(QBrush(QColor(220, 53, 69)))  # rouge

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
        if row in (self.row_avg_up_index, self.row_avg_down_index, self.row_index_line):
            self._clear_highlight(); return
        self._clear_highlight()
        it = self._ensure_item(row, col)
        it.setBackground(QBrush(QColor(255, 249, 196)))  # jaune doux = prochaine mesure
        it.setForeground(QBrush(TEXT_ON_LIGHT_BG))
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

    # ------------- Réactions session -------------

    def _on_session_changed(self, _s):
        # Ne pas reconstruire la table en plein enregistrement d'une campagne,
        # sinon la campagne passe à l'état "arrêtée" à chaque nouvelle valeur.
        if self.campaign_running:
            return
        self._rebuild_from_session()

    # ------------- Nettoyage -------------
    def deleteLater(self):
        try:
            self._stop_campaign()
        finally:
            super().deleteLater()
