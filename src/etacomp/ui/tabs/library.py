from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QInputDialog, QMessageBox,
    QAbstractItemView
)

from ...io.storage import list_comparators, upsert_comparator, delete_comparator_by_reference
from ...models.comparator import Comparator


class LibraryTab(QWidget):
    comparators_changed = Signal()  # émis après ajout/édition/suppression

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Référence", "Fabricant", "Description", "Cibles (mm)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        # Boutons
        btns = QHBoxLayout()
        self.btn_add = QPushButton("Ajouter")
        self.btn_edit = QPushButton("Éditer")
        self.btn_del = QPushButton("Supprimer")
        btns.addWidget(self.btn_add)
        btns.addWidget(self.btn_edit)
        btns.addWidget(self.btn_del)
        btns.addStretch()
        layout.addLayout(btns)

        # Connexions
        self.btn_add.clicked.connect(self.on_add)
        self.btn_edit.clicked.connect(self.on_edit)
        self.btn_del.clicked.connect(self.on_delete)

        # Initial load
        self.reload()

    # --------- helpers ---------
    def current_reference(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.table.item(row, 0).text()

    def reload(self):
        comps = list_comparators()
        self.table.setRowCount(0)
        for c in comps:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(c.reference))
            self.table.setItem(row, 1, QTableWidgetItem(c.manufacturer or ""))
            self.table.setItem(row, 2, QTableWidgetItem(c.description or ""))
            self.table.setItem(row, 3, QTableWidgetItem(", ".join([str(v) for v in c.targets])))

    # --------- actions ---------
    def on_add(self):
        ref, ok = QInputDialog.getText(self, "Nouveau comparateur", "Référence :")
        if not ok or not ref.strip():
            return
        man, _ = QInputDialog.getText(self, "Fabricant", "Fabricant (optionnel) :")
        desc, _ = QInputDialog.getText(self, "Description", "Description (optionnel) :")
        targets_text, _ = QInputDialog.getText(self, "Cibles (mm)", "Liste séparée par des virgules (ex: 0, 1, 2) :")
        try:
            targets = [float(x.strip()) for x in targets_text.split(",")] if targets_text.strip() else []
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Valeurs cibles invalides.")
            return

        c = Comparator(reference=ref.strip(), manufacturer=man or None, description=desc or None, targets=targets)
        upsert_comparator(c)
        self.reload()
        self.comparators_changed.emit()

    def on_edit(self):
        ref = self.current_reference()
        if not ref:
            QMessageBox.information(self, "Info", "Sélectionne un comparateur dans la liste.")
            return

        new_ref, ok = QInputDialog.getText(self, "Éditer", "Référence :", text=ref)
        if not ok or not new_ref.strip():
            return
        man, _ = QInputDialog.getText(self, "Éditer", "Fabricant (optionnel) :")
        desc, _ = QInputDialog.getText(self, "Éditer", "Description (optionnel) :")
        targets_text, _ = QInputDialog.getText(self, "Éditer", "Cibles (mm) séparées par virgules :")
        try:
            targets = [float(x.strip()) for x in targets_text.split(",")] if targets_text.strip() else []
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Valeurs cibles invalides.")
            return

        if new_ref.strip() != ref:
            delete_comparator_by_reference(ref)

        upsert_comparator(Comparator(reference=new_ref.strip(), manufacturer=man or None, description=desc or None, targets=targets))
        self.reload()
        self.comparators_changed.emit()

    def on_delete(self):
        ref = self.current_reference()
        if not ref:
            QMessageBox.information(self, "Info", "Sélectionne un comparateur.")
            return
        if QMessageBox.question(self, "Confirmer", f"Supprimer '{ref}' ?") == QMessageBox.StandardButton.Yes:
            delete_comparator_by_reference(ref)
            self.reload()
            self.comparators_changed.emit()
