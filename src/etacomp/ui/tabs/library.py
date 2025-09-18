from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox,
    QAbstractItemView, QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox,
    QDoubleSpinBox, QComboBox
)

from ...io.storage import list_comparators, upsert_comparator, delete_comparator_by_reference
from ...models.comparator import Comparator, RangeType


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
        self.ed_grad = QDoubleSpinBox()
        self.ed_grad.setRange(0.001, 1.0)
        self.ed_grad.setDecimals(3)
        self.ed_grad.setSingleStep(0.001)
        self.ed_course = QDoubleSpinBox()
        self.ed_course.setRange(0.1, 100.0)
        self.ed_course.setDecimals(3)
        self.ed_course.setSingleStep(0.1)
        self.ed_range = QComboBox()
        self.ed_range.addItems([t.value for t in RangeType])
        self.ed_targets = QLineEdit()

        # Infobulles
        self.ed_ref.setToolTip("Identifiant unique du comparateur (ex: TESA_Mic_001)")
        self.ed_man.setToolTip("Fabricant (optionnel), ex: TESA, Mitutoyo, Mahr…")
        self.ed_desc.setToolTip("Description libre (optionnel), ex: modèle, plage, précision…")
        self.ed_grad.setToolTip("Échelon de graduation en millimètres (ex: 0.01)")
        self.ed_course.setToolTip("Course nominale maximale en millimètres")
        self.ed_range.setToolTip("Famille de comparateur selon la course")
        self.ed_targets.setToolTip("Liste de cibles en millimètres, séparées par virgules ou point-virgules (ex: 0; 1; 2)")

        form.addRow("Référence", self.ed_ref)
        form.addRow("Fabricant", self.ed_man)
        form.addRow("Description", self.ed_desc)
        form.addRow("Graduation (mm)", self.ed_grad)
        form.addRow("Course (mm)", self.ed_course)
        form.addRow("Famille", self.ed_range)
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
            self.ed_grad.setValue(initial.graduation or 0.01)
            self.ed_course.setValue(initial.course or 1.0)
            if initial.range_type:
                idx = list(RangeType).index(initial.range_type)
                self.ed_range.setCurrentIndex(idx)
            self.ed_targets.setText(
                ", ".join(str(v) for v in initial.targets)
            )

    def result_model(self) -> Comparator | None:
        ref = (self.ed_ref.text() or "").strip()
        if not ref:
            return None
        man = (self.ed_man.text() or "").strip() or None
        desc = (self.ed_desc.text() or "").strip() or None
        grad = self.ed_grad.value()
        course = self.ed_course.value()
        range_type = RangeType(self.ed_range.currentText())
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
        return Comparator(
            reference=ref, manufacturer=man, description=desc,
            graduation=grad, course=course, range_type=range_type, targets=targets
        )


class LibraryTab(QWidget):
    comparators_changed = Signal()  # émis après ajout/édition/suppression

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Référence", "Fabricant", "Graduation (mm)", "Course (mm)", "Famille", "Cibles"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # Permettre le retour à la ligne automatique pour la colonne des cibles
        self.table.setWordWrap(True)
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
            self.table.setItem(row, 2, QTableWidgetItem(f"{c.graduation:.3f}" if c.graduation else ""))
            self.table.setItem(row, 3, QTableWidgetItem(f"{c.course:.3f}" if c.course else ""))
            self.table.setItem(row, 4, QTableWidgetItem(c.range_type.value if c.range_type else ""))
            # Afficher la liste complète des cibles avec formatage cohérent
            targets_text = ", ".join(f"{t:.3f}" for t in c.targets)
            self.table.setItem(row, 5, QTableWidgetItem(targets_text))

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
