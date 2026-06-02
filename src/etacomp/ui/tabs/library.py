from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox,
    QAbstractItemView, QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
    QDoubleSpinBox, QSpinBox, QComboBox, QLabel
)
from pydantic import ValidationError

from ...io.storage import list_comparators, upsert_comparator, delete_comparator_by_reference
from ...models.comparator import Comparator, RangeType

TARGET_COUNT_REQUIRED = 11


def parse_targets_field(text: str) -> list[float]:
    """Parse les cibles (séparateurs , et ;). Lève ValueError si token invalide."""
    items: list[str] = []
    raw = (text or "").strip()
    if raw:
        for part in raw.split(";"):
            items.extend(part.split(","))
    return [float(tok.replace(",", ".").strip()) for tok in items if tok.strip()]


def count_targets_field(text: str) -> int:
    try:
        return len(parse_targets_field(text))
    except ValueError:
        return -1


def format_validation_error(exc: ValidationError) -> str:
    lines = [str(e.get("msg", "")) for e in exc.errors() if e.get("msg")]
    return "\n".join(lines) if lines else "Profil comparateur invalide."


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
        # Ajouter les libellés complets mais garder les valeurs courtes
        for rt in RangeType:
            self.ed_range.addItem(rt.display_name, rt.value)
        self.ed_periodicite = QSpinBox()
        self.ed_periodicite.setRange(1, 120)
        self.ed_periodicite.setValue(12)
        self.ed_periodicite.setSuffix(" mois")
        self.ed_periodicite.setToolTip("Périodicité de contrôle (utilisée dans l'export des résultats)")
        self.ed_targets = QLineEdit()
        self.lbl_targets_count = QLabel("0 cible")
        self.lbl_targets_count.setStyleSheet("color: #6c757d; font-size: 0.9em;")
        self.ed_targets.textChanged.connect(self._update_targets_count)

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
        form.addRow("Périodicité de contrôle", self.ed_periodicite)
        form.addRow("Cibles (mm)", self.ed_targets)
        form.addRow("", self.lbl_targets_count)  # compteur sous le champ

        layout.addLayout(form)

        self._validated_model: Comparator | None = None
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._ok_button = btns.button(QDialogButtonBox.StandardButton.Ok)
        btns.accepted.connect(self._on_ok_clicked)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.ed_ref.textChanged.connect(self._update_targets_count)

        if initial is not None:
            self.ed_ref.setText(initial.reference)
            self.ed_man.setText(initial.manufacturer or "")
            self.ed_desc.setText(initial.description or "")
            self.ed_grad.setValue(initial.graduation or 0.01)
            self.ed_course.setValue(initial.course or 1.0)
            if initial.range_type:
                # Trouver l'index correspondant à la valeur
                for i in range(self.ed_range.count()):
                    if self.ed_range.itemData(i) == initial.range_type.value:
                        self.ed_range.setCurrentIndex(i)
                        break
            self.ed_periodicite.setValue(getattr(initial, "periodicite_controle_mois", 12))
            self.ed_targets.setText(
                ", ".join(str(v) for v in initial.targets)
            )
        self._update_targets_count()

    def _update_targets_count(self):
        """Compte les cibles saisies et active OK seulement si 11 cibles + référence."""
        text = (self.ed_targets.text() or "").strip()
        count = count_targets_field(text)
        if count < 0:
            txt = "Valeurs invalides"
            style = "color: #dc3545; font-size: 0.9em; font-weight: 600;"
        elif count == 0:
            txt = "0 cible"
            style = "color: #dc3545; font-size: 0.9em;"
        elif count == 1:
            txt = "1 cible"
            style = "color: #dc3545; font-size: 0.9em;"
        elif count == TARGET_COUNT_REQUIRED:
            txt = f"{count} cibles"
            style = "color: #198754; font-size: 0.9em; font-weight: 600;"
        else:
            txt = f"{count} cibles (il en faut {TARGET_COUNT_REQUIRED})"
            style = "color: #dc3545; font-size: 0.9em; font-weight: 600;"
        self.lbl_targets_count.setText(txt)
        self.lbl_targets_count.setStyleSheet(style)
        has_ref = bool((self.ed_ref.text() or "").strip())
        if self._ok_button is not None:
            self._ok_button.setEnabled(has_ref and count == TARGET_COUNT_REQUIRED)

    def _try_build_model(self) -> tuple[Comparator | None, str | None]:
        ref = (self.ed_ref.text() or "").strip()
        if not ref:
            return None, "La référence est obligatoire."
        try:
            targets = parse_targets_field(self.ed_targets.text())
        except ValueError:
            return None, "Valeurs cibles invalides. Utilise des nombres séparés par des virgules ou des points-virgules."
        if len(targets) != TARGET_COUNT_REQUIRED:
            return None, (
                f"Le profil doit contenir exactement {TARGET_COUNT_REQUIRED} cibles "
                f"(actuel : {len(targets)})."
            )
        try:
            model = Comparator(
                reference=ref,
                manufacturer=(self.ed_man.text() or "").strip() or None,
                description=(self.ed_desc.text() or "").strip() or None,
                graduation=self.ed_grad.value(),
                course=self.ed_course.value(),
                range_type=RangeType(self.ed_range.currentData()),
                targets=targets,
                periodicite_controle_mois=self.ed_periodicite.value(),
            )
        except ValidationError as exc:
            return None, format_validation_error(exc)
        return model, None

    def _on_ok_clicked(self):
        model, err = self._try_build_model()
        if err:
            QMessageBox.warning(self, "Profil comparateur", err)
            return
        self._validated_model = model
        self.accept()

    def result_model(self) -> Comparator | None:
        return self._validated_model


class LibraryTab(QWidget):
    comparators_changed = Signal()  # émis après ajout/édition/suppression

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Référence", "Fabricant", "Graduation (mm)", "Course (mm)", "Famille", "Périodicité", "Cibles"])
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
            self.table.setItem(row, 4, QTableWidgetItem(c.range_type.display_name if c.range_type else ""))
            period = getattr(c, "periodicite_controle_mois", 12)
            self.table.setItem(row, 5, QTableWidgetItem(f"{period} mois"))
            # Afficher la liste complète des cibles avec formatage cohérent
            targets_text = ", ".join(f"{t:.3f}" for t in c.targets)
            self.table.setItem(row, 6, QTableWidgetItem(targets_text))

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
            QMessageBox.information(self, "Bibliothèque", f"Comparateur {model.reference} enregistré.")

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
        QMessageBox.information(self, "Bibliothèque", f"Comparateur {model.reference} enregistré.")

    def on_delete(self):
        ref = self.current_reference()
        if not ref:
            QMessageBox.information(self, "Info", "Sélectionne un comparateur.")
            return
        if QMessageBox.question(self, "Confirmer", f"Supprimer '{ref}' ?") == QMessageBox.StandardButton.Yes:
            delete_comparator_by_reference(ref)
            self.reload()
            self.comparators_changed.emit()
            QMessageBox.information(self, "Bibliothèque", "Comparateur supprimé.")
