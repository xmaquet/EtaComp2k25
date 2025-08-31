from __future__ import annotations

from typing import List, Dict, Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QPushButton,
    QMessageBox, QComboBox, QTextEdit, QLabel, QTableWidget, QTableWidgetItem
)

from ...models.session import MeasureSeries
from ...state.session_store import session_store
from ...io.serialio import list_serial_ports, SerialConnection, SerialReaderThread
from ...io.storage import list_comparators


class MeasuresTab(QWidget):
    """
    Organisation du tableau :
      - Colonnes = cibles (avec 0 forcé en première colonne).
      - Lignes = 2 x N itérations : 1↑, 1↓, 2↑, 2↓, ..., puis une ligne 'Moyenne'.
      - Un cycle (itération) joue successivement : montant (0→max) puis descendant (max→0).
      - La première valeur de chaque cycle doit être ~0 (démarrage à zéro).
      - Aucune saisie manuelle : remplissage uniquement depuis le port série.
      - Le store de session est mis à jour après chaque valeur acceptée :
          un MeasureSeries par cible, readings ordonnées : 1↑, 1↓, 2↑, 2↓, ...
    """

    ZERO_TOL = 1e-6  # tolérance pour tester ~0

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)

        # ===== Connexion série =====
        g_conn = QGroupBox("Connexion au dispositif étalon (port série)")
        f0 = QFormLayout(g_conn)

        self.combo_port = QComboBox()
        self.btn_refresh_ports = QPushButton("↻")
        pbar = QHBoxLayout()
        pbar.addWidget(self.combo_port)
        pbar.addWidget(self.btn_refresh_ports)

        self.combo_baud = QComboBox()
        # par défaut 4800 (dispositif de test)
        self.combo_baud.addItems(["4800", "9600", "19200", "38400", "57600", "115200"])
        self.combo_baud.setCurrentText("4800")

        self.btn_connect = QPushButton("Connecter")
        self.btn_disconnect = QPushButton("Déconnecter")
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
        self.btn_start = QPushButton("Démarrer")
        self.btn_stop = QPushButton("Arrêter"); self.btn_stop.setEnabled(False)
        self.btn_clear = QPushButton("Effacer toutes les mesures")
        topbar = QHBoxLayout()
        topbar.addWidget(self.btn_start)
        topbar.addWidget(self.btn_stop)
        topbar.addStretch()
        topbar.addWidget(self.btn_clear)
        f1.addRow("Statut", self.lbl_next)
        f1.addRow("", QWidget()); f1.itemAt(f1.rowCount()-1, QFormLayout.FieldRole).widget().setLayout(topbar)

        # ===== Tableau mesures =====
        g_table = QGroupBox("Mesures")
        vtab = QVBoxLayout(g_table)
        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        vtab.addWidget(self.table)

        # ===== Logger brut =====
        g_log = QGroupBox("Flux série (lignes brutes)")
        v3 = QVBoxLayout(g_log)
        log_bar = QHBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        self.btn_clear_log = QPushButton("Effacer le log")
        log_bar.addStretch()
        log_bar.addWidget(self.btn_clear_log)
        v3.addWidget(self.log_view)
        v3.addLayout(log_bar)

        # ===== Actions =====
        actions = QHBoxLayout()
        self.btn_save_session = QPushButton("Enregistrer la session…")
        self.btn_save_session.setStyleSheet(
            "QPushButton{background:#28a745;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
            "QPushButton:hover{background:#218838;}"
        )
        actions.addStretch()
        actions.addWidget(self.btn_save_session)

        # Assemble
        root.addWidget(g_conn)
        root.addWidget(g_cfg)
        root.addWidget(g_table)
        root.addWidget(g_log)
        root.addLayout(actions)
        root.addStretch()

        # ===== État interne =====
        self._conn = SerialConnection()
        self._reader: Optional[SerialReaderThread] = None

        # Colonnes (cibles) & lignes (itérations)
        self.targets: List[float] = []       # colonnes, 0 inclus en col0
        self.cycles: int = 0                 # nb d’itérations (series_count)
        self.row_avg_index: int = -1         # index de la ligne "Moyenne"

        # Position de capture
        self.campaign_running: bool = False
        self.current_cycle: int = 1          # 1..cycles
        self.current_phase_up: bool = True   # True=montant, False=descendant
        self.current_col: int = 0            # index de colonne dans targets
        self.waiting_zero: bool = True       # impose ~0 au début de CHAQUE cycle

        # Données par cible
        self.by_target: Dict[float, MeasureSeries] = {}

        # Init UI
        self._refresh_ports()
        self._rebuild_from_session()

        # Connexions
        self.btn_refresh_ports.clicked.connect(self._refresh_ports)
        self.btn_connect.clicked.connect(self._do_connect)
        self.btn_disconnect.clicked.connect(self._do_disconnect)

        self.btn_start.clicked.connect(self._start_campaign)
        self.btn_stop.clicked.connect(self._stop_campaign)
        self.btn_clear.clicked.connect(self._clear_all)

        self.btn_clear_log.clicked.connect(self._clear_log)
        self.btn_save_session.clicked.connect(self._save_session)

        session_store.session_changed.connect(self._on_session_changed)
        session_store.measures_updated.connect(self._on_session_changed)

    # ---------- session -> table ----------
    def _rebuild_from_session(self):
        s = session_store.current

        # Colonnes (cibles) depuis le comparateur
        self.targets = self._targets_from_comparator(s.comparator_ref)
        # Forcer 0 en première colonne
        if 0.0 not in self.targets:
            self.targets = [0.0] + sorted([t for t in self.targets if abs(t) > self.ZERO_TOL])
        else:
            # assurer 0 en tête
            t0 = [t for t in self.targets if abs(t) <= self.ZERO_TOL]
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
                # Remplir colonne par colonne (ordre 1↑,1↓,2↑,2↓,…)
                for col, val in enumerate(ms.readings):
                    row = self._row_for_col_index(col)
                    if row is not None and row < self.row_avg_index and col < self.table.columnCount():
                        self.table.setItem(row, col % self.table.columnCount(), QTableWidgetItem(str(val)))
                # Conserver readings (normalisé à plat)
                self.by_target[ms.target].readings = list(ms.readings)

        # Reset position capture
        self.campaign_running = False
        self.current_cycle = 1
        self.current_phase_up = True
        self.current_col = 0
        self.waiting_zero = True

        # Recalcul des moyennes
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

    # ---------- COM ----------
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
        self._stop_campaign()
        if self._reader:
            self._reader.stop()
            self._reader = None
        self._conn.close()
        self.btn_disconnect.setEnabled(False)
        self.btn_connect.setEnabled(True)

    # ---------- Campagne ----------
    def _start_campaign(self):
        if not self._conn.is_open():
            QMessageBox.information(self, "Série", "Connecte d’abord le dispositif (port série).")
            return
        # Reconstruire selon session (au cas où comparateur / cycles ont changé)
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
        # Efface toutes les mesures (garde cibles/structure)
        for r in range(self.table.rowCount() - 1):  # ne touche pas la ligne "Moyenne"
            for c in range(self.table.columnCount()):
                self.table.setItem(r, c, QTableWidgetItem(""))
        for t in self.by_target.values():
            t.readings.clear()
        # Reset position
        self.campaign_running = False
        self.current_cycle = 1
        self.current_phase_up = True
        self.current_col = 0
        self.waiting_zero = True
        self._push_series_to_store()
        self._recompute_means()
        self._update_status()

    # ---------- Logger ----------
    def _clear_log(self):
        self.log_view.clear()

    # ---------- Réception série ----------
    def _on_line_from_serial(self, raw: str, value: float | None):
        QTimer.singleShot(0, lambda: self._append_line(raw, value))

    def _append_line(self, raw: str, value: float | None):
        # log brut
        self.log_view.append(raw)

        if not self.campaign_running or value is None:
            return

        # Démarrage de cycle : exiger ~0 sur la première colonne de la phase montante
        if self.waiting_zero:
            if abs(value) <= self.ZERO_TOL and self.current_phase_up and self.current_col == 0:
                self._write_current_cell(value)
                self.waiting_zero = False
                self._advance_after_write()
            # sinon on ignore jusqu'à réception de ~0
            self._update_status()
            return

        # En régime normal : écrire la valeur dans la cellule attendue
        self._write_current_cell(value)
        finished = self._advance_after_write()
        if finished:
            self._stop_campaign()
        self._update_status()

    # ---------- Table & Store ----------
    def _row_for_state(self, cycle: int, up: bool) -> int:
        # lignes : (cycle-1)*2 + (0 si up else 1)
        return (cycle - 1) * 2 + (0 if up else 1)

    def _row_for_col_index(self, col_index: int) -> Optional[int]:
        """
        Convertit l'indice "col" vu comme progression globale (0..2*cycles-1, 2 colonnes par cycle)
        en index de ligne. Utile pour recharger des readings linéarisés.
        """
        # Ici, on considère que 'col_index' encode l'ordre 1↑,1↓,2↑,2↓, etc.
        cycle = (col_index // 2) + 1
        up = (col_index % 2 == 0)
        if 1 <= cycle <= self.cycles:
            return self._row_for_state(cycle, up)
        return None

    def _write_current_cell(self, value: float):
        row = self._row_for_state(self.current_cycle, self.current_phase_up)
        col = self.current_col
        # Ne pas écraser si déjà rempli (au cas où)
        item = self.table.item(row, col)
        if item is None or not item.text():
            self.table.setItem(row, col, QTableWidgetItem(str(value)))
            # Mettre à jour by_target[target].readings (ordre 1↑,1↓,2↑,2↓,...)
            target = self.targets[col]
            readings = self.by_target[target].readings
            # position canonique = (current_cycle-1)*2 + (0 si up else 1)
            pos = (self.current_cycle - 1) * 2 + (0 if self.current_phase_up else 1)
            while len(readings) <= pos:
                readings.append(None)
            readings[pos] = value
            # Nettoyer None de fin
            while readings and readings[-1] is None:
                readings.pop()
            self._push_series_to_store()
            self._recompute_means()

    def _push_series_to_store(self):
        ordered = [self.by_target[t] for t in self.targets]
        session_store.set_series(ordered)

    def _recompute_means(self):
        # Par colonne : moyenne des valeurs (toutes lignes de mesures, on ignore vides)
        for c in range(self.table.columnCount()):
            vals = []
            for r in range(self.table.rowCount() - 1):  # ignorer ligne "Moyenne"
                it = self.table.item(r, c)
                if it and it.text():
                    try:
                        vals.append(float(it.text()))
                    except ValueError:
                        pass
            mean_txt = "" if not vals else f"{sum(vals)/len(vals):.6f}"
            self.table.setItem(self.row_avg_index, c, QTableWidgetItem(mean_txt))

    # ---------- Avancement ----------
    def _advance_after_write(self) -> bool:
        """
        Avance à la prochaine cellule (respecte le motif 0..max puis max..0).
        Retourne True si toute la campagne est terminée.
        """
        last_col = self.table.columnCount() - 1

        if self.current_phase_up:
            # Montant
            if self.current_col < last_col:
                self.current_col += 1
                return False
            else:
                # Passer au descendant, on reste sur la dernière colonne
                self.current_phase_up = False
                # next write sera sur la même colonne (max)
                return False
        else:
            # Descendant
            if self.current_col > 0:
                self.current_col -= 1
                return False
            else:
                # Fin du cycle (on termine sur 0)
                if self.current_cycle < self.cycles:
                    self.current_cycle += 1
                    self.current_phase_up = True
                    self.current_col = 0
                    self.waiting_zero = True  # nouveau cycle => exiger 0
                    return False
                else:
                    # Fin de campagne
                    return True

    def _update_status(self):
        if not self.campaign_running:
            self.lbl_next.setText("Prochaine cible : — (campagne arrêtée)")
            return
        arrow = "↑" if self.current_phase_up else "↓"
        target = self.targets[self.current_col] if self.targets else 0.0
        if self.waiting_zero:
            self.lbl_next.setText(f"Prochaine cible : 0  (Cycle {self.current_cycle}/{self.cycles}, {arrow})")
        else:
            self.lbl_next.setText(f"Prochaine cible : {target}  (Cycle {self.current_cycle}/{self.cycles}, {arrow})")

    # ---------- Sauvegarde ----------
    def _save_session(self):
        if not session_store.can_save():
            QMessageBox.warning(self, "Impossible", "Aucune mesure dans la session — enregistrement interdit.")
            return
        try:
            path = session_store.save()
            QMessageBox.information(self, "Session", f"Session enregistrée :\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Échec de l’enregistrement :\n{e}")

    # ---------- Réactions session ----------
    def _on_session_changed(self, _s):
        # Si comparateur / nb cycles changent : reconstruire
        self._rebuild_from_session()
        # On ne démarre pas la campagne automatiquement

    # ---------- Nettoyage ----------
    def deleteLater(self):
        try:
            self._stop_campaign()
            if self._reader:
                self._reader.stop()
            self._conn.close()
        finally:
            super().deleteLater()
