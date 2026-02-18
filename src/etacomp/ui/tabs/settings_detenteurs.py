"""Onglet Paramètres > Détenteurs : gestion des détenteurs (code ES + libellé)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QAbstractItemView, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QHeaderView
)

from ...models.detenteur import Detenteur
from ...io.storage import list_detenteurs, save_detenteurs, add_detenteur, delete_detenteur_by_code


class DetenteurEditDialog(QDialog):
    """Dialogue d'ajout/édition d'un détenteur."""
    def __init__(self, parent=None, *, initial: Detenteur | None = None):
        super().__init__(parent)
        self.setWindowTitle("Éditer le détenteur" if initial else "Ajouter un détenteur")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.code_es = QLineEdit()
        self.code_es.setPlaceholderText("Ex: ES12345")
        self.code_es.setMaxLength(32)
        self.code_es.setToolTip("Code ES (identifiant unique)")
        self.libelle = QLineEdit()
        self.libelle.setPlaceholderText("Ex: Atelier mécanique principal")
        self.libelle.setToolTip("Libellé descriptif")
        form.addRow("Code ES", self.code_es)
        form.addRow("Libellé", self.libelle)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        if initial:
            self.code_es.setText(initial.code_es)
            self.code_es.setReadOnly(True)
            self.libelle.setText(initial.libelle)

    def _on_accept(self):
        code = self.code_es.text().strip()
        lib = self.libelle.text().strip()
        if not code:
            QMessageBox.warning(self, "Erreur", "Le code ES est obligatoire.")
            return
        self._result = Detenteur(code_es=code, libelle=lib or code)
        self.accept()

    def result_detenteur(self) -> Detenteur | None:
        return getattr(self, "_result", None)


class SettingsDetenteursTab(QWidget):
    """Onglet de gestion des détenteurs (Paramètres > Détenteurs)."""
    detenteurs_changed = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        from PySide6.QtWidgets import QLabel
        lbl = QLabel("Détenteurs = code ES + libellé. Utilisés pour identifier le propriétaire du comparateur en session.")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Code ES", "Libellé"])
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
        self._detenteurs = list_detenteurs()
        self._update_table()

    def refresh(self):
        """Rafraîchit le tableau (appelé depuis l'extérieur, ex. quand un détenteur est créé depuis Session)."""
        self._load()

    def _update_table(self):
        self.table.setRowCount(len(self._detenteurs))
        for row, d in enumerate(self._detenteurs):
            self.table.setItem(row, 0, QTableWidgetItem(d.code_es))
            self.table.setItem(row, 1, QTableWidgetItem(d.libelle))

    def _add(self):
        dlg = DetenteurEditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.result_detenteur()
            if d:
                add_detenteur(d)
                self._load()
                self.detenteurs_changed.emit()
                QMessageBox.information(self, "Détenteurs", f"Détenteur {d.code_es} ajouté.")

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Sélectionnez un détenteur à éditer.")
            return
        d = self._detenteurs[row]
        dlg = DetenteurEditDialog(self, initial=d)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_d = dlg.result_detenteur()
            if new_d:
                lst = [x for x in self._detenteurs if x.code_es != d.code_es]
                lst.append(new_d)
                save_detenteurs(lst)
                self._load()
                self.detenteurs_changed.emit()
                QMessageBox.information(self, "Détenteurs", f"Détenteur {new_d.code_es} modifié.")

    def _delete(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Sélectionnez un détenteur à supprimer.")
            return
        d = self._detenteurs[row]
        if QMessageBox.question(self, "Confirmer", f"Supprimer le détenteur {d.code_es} ?") == QMessageBox.StandardButton.Yes:
            delete_detenteur_by_code(d.code_es)
            self._load()
            self.detenteurs_changed.emit()
            QMessageBox.information(self, "Détenteurs", "Détenteur supprimé.")
