"""Onglet Paramètres > Bancs étalon : bibliothèque des bancs (réf, marque capteur, date validité)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QAbstractItemView, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QHeaderView, QCheckBox, QLabel
)

from ...models.banc_etalon import BancEtalon
from ...io.storage import list_bancs_etalon, save_bancs_etalon


class BancEtalonEditDialog(QDialog):
    """Dialogue d'ajout/édition d'un banc étalon."""
    def __init__(self, parent=None, *, initial: BancEtalon | None = None):
        super().__init__(parent)
        self.setWindowTitle("Éditer le banc étalon" if initial else "Ajouter un banc étalon")
        self.setMinimumWidth(450)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.ed_ref = QLineEdit()
        self.ed_ref.setPlaceholderText("Ex: BE-001")
        self.ed_ref.setToolTip("Référence unique du banc")
        self.ed_marque = QLineEdit()
        self.ed_marque.setPlaceholderText("Ex: TESA, Mitutoyo…")
        self.ed_marque.setToolTip("Marque du capteur")
        self.ed_date_validite = QLineEdit()
        self.ed_date_validite.setPlaceholderText("Ex: 2025-12-31 ou DD/MM/YYYY")
        self.ed_date_validite.setToolTip("Date de validité du banc")
        self.chk_default = QCheckBox("Banc par défaut (utilisé pour l'export PDF)")
        self.chk_default.setToolTip("Un seul banc peut être par défaut. N'apparaît pas dans l'onglet Session.")
        form.addRow("Référence", self.ed_ref)
        form.addRow("Marque du capteur", self.ed_marque)
        form.addRow("Date de validité", self.ed_date_validite)
        form.addRow("", self.chk_default)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        if initial:
            self.ed_ref.setText(initial.reference)
            self.ed_marque.setText(initial.marque_capteur)
            self.ed_date_validite.setText(initial.date_validite)
            self.chk_default.setChecked(initial.is_default)
            self.ed_ref.setReadOnly(True)

    def _on_accept(self):
        ref = self.ed_ref.text().strip()
        if not ref:
            QMessageBox.warning(self, "Erreur", "La référence est obligatoire.")
            return
        self._result = BancEtalon(
            reference=ref,
            marque_capteur=self.ed_marque.text().strip() or ref,
            date_validite=self.ed_date_validite.text().strip() or "—",
            is_default=self.chk_default.isChecked(),
        )
        self.accept()

    def result_banc(self) -> BancEtalon | None:
        return getattr(self, "_result", None)


class SettingsBancsEtalonTab(QWidget):
    """Onglet de gestion des bancs étalon (Paramètres > Bancs étalon)."""
    bancs_changed = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        lbl = QLabel(
            "Bancs étalon : référence, marque du capteur, date de validité. "
            "Le banc par défaut sert à l'export PDF et n'apparaît pas dans l'onglet Session."
        )
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Référence", "Marque capteur", "Date validité", "Par défaut"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Ajouter")
        btn_edit = QPushButton("Éditer")
        btn_del = QPushButton("Supprimer")
        btn_add.clicked.connect(self._add)
        btn_edit.clicked.connect(self._edit)
        btn_del.clicked.connect(self._delete)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_del)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._load()

    def _load(self):
        self._bancs = list_bancs_etalon()
        self._update_table()

    def refresh(self):
        self._load()

    def _update_table(self):
        self.table.setRowCount(len(self._bancs))
        for row, b in enumerate(self._bancs):
            self.table.setItem(row, 0, QTableWidgetItem(b.reference))
            self.table.setItem(row, 1, QTableWidgetItem(b.marque_capteur))
            self.table.setItem(row, 2, QTableWidgetItem(b.date_validite))
            default_it = QTableWidgetItem("✓" if b.is_default else "")
            default_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, default_it)

    def _add(self):
        dlg = BancEtalonEditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_b = dlg.result_banc()
            if new_b:
                self._save_with_new_default(new_b, None)
                QMessageBox.information(self, "Bancs étalon", f"Banc {new_b.reference} ajouté.")

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Sélectionnez un banc à éditer.")
            return
        b = self._bancs[row]
        dlg = BancEtalonEditDialog(self, initial=b)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_b = dlg.result_banc()
            if new_b:
                self._save_with_new_default(new_b, b.reference)
                QMessageBox.information(self, "Bancs étalon", f"Banc {new_b.reference} modifié.")

    def _save_with_new_default(self, new_b: BancEtalon, old_ref: str | None):
        """Sauvegarde en gérant le flag is_default (un seul à True)."""
        lst = [x for x in self._bancs if x.reference != (old_ref or "")]
        lst.append(new_b)
        if new_b.is_default:
            lst = [
                BancEtalon(reference=x.reference, marque_capteur=x.marque_capteur, date_validite=x.date_validite, is_default=(x.reference == new_b.reference))
                for x in lst
            ]
        save_bancs_etalon(lst)
        self._load()
        self.bancs_changed.emit()

    def _delete(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Sélectionnez un banc à supprimer.")
            return
        b = self._bancs[row]
        if QMessageBox.question(self, "Confirmer", f"Supprimer le banc {b.reference} ?") == QMessageBox.StandardButton.Yes:
            lst = [x for x in self._bancs if x.reference != b.reference]
            save_bancs_etalon(lst)
            self._load()
            self.bancs_changed.emit()
            QMessageBox.information(self, "Bancs étalon", "Banc supprimé.")
