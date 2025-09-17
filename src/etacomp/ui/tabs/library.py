from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox,
    QAbstractItemView, QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox
)

from ...io.storage import list_comparators, upsert_comparator, delete_comparator_by_reference
from ...models.comparator import Comparator


class ComparatorEditDialog(QDialog):
    def __init__(self, parent=None, *, initial: Comparator | None = None):
        super().__init__(parent)
        self.setWindowTitle("Édition comparateur")
        layout = QVBoxLayout(self)
        self.setMinimumWidth(560)

        form = QFormLayout()
        self.ed_ref = QLineEdit()
        self.ed_man = QLineEdit()
        self.ed_desc = QLineEdit()
        self.ed_targets = QLineEdit()

        # Infobulles
        self.ed_ref.setToolTip("Identifiant unique du comparateur (ex: TESA_Mic_001)")
        self.ed_man.setToolTip("Fabricant (optionnel), ex: TESA, Mitutoyo, Mahr…")
        self.ed_desc.setToolTip("Description libre (optionnel), ex: modèle, plage, précision…")
        self.ed_targets.setToolTip("Liste de cibles en millimètres, séparées par virgules ou point-virgules (ex: 0; 1; 2)")

        form.addRow("Référence", self.ed_ref)
        form.addRow("Fabricant", self.ed_man)
        form.addRow("Description", self.ed_desc)
        form.addRow("Cibles (mm)", self.ed_targets)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        if initial is not None:
            self.ed_ref.setText(initial.reference)
            self.ed_man.setText(initial.manufacturer or "")
            self.ed_desc.setText(initial.description or "")
            self.ed_targets.setText(
                ", ".join(str(v) for v in initial.targets)
            )

    def result_model(self) -> Comparator | None:
        ref = (self.ed_ref.text() or "").strip()
        if not ref:
            return None
        man = (self.ed_man.text() or "").strip() or None
        desc = (self.ed_desc.text() or "").strip() or None
        targets_text = (self.ed_targets.text() or "").strip()
        try:
            # Séparateurs autorisés: ',' et ';'
            items: list[str] = []
            if targets_text:
                for part in targets_text.split(";"):
                    items.extend(part.split(","))
            targets = [float(tok.replace(",", ".").strip()) for tok in items if tok.strip()]
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Valeurs cibles invalides. Utilise des nombres séparés par des virgules.")
            return None
        return Comparator(reference=ref, manufacturer=man, description=desc, targets=targets)


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
        dlg = ComparatorEditDialog(self)
        if dlg.exec() == QDialog.Accepted:
            model = dlg.result_model()
            if model is None:
                return
            upsert_comparator(model)
            self.reload()
            self.comparators_changed.emit()

    def on_edit(self):
        ref = self.current_reference()
        if not ref:
            QMessageBox.information(self, "Info", "Sélectionne un comparateur dans la liste.")
            return

        # Charger le modèle existant pour pré-remplir
        existing = None
        for c in list_comparators():
            if c.reference == ref:
                existing = c
                break
        dlg = ComparatorEditDialog(self, initial=existing)
        if dlg.exec() != QDialog.Accepted:
            return
        model = dlg.result_model()
        if model is None:
            return
        if model.reference != ref:
            delete_comparator_by_reference(ref)
        upsert_comparator(model)
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
