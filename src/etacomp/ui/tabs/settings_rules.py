from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QMessageBox, QFileDialog, QAbstractItemView,
    QDialog, QFormLayout, QDoubleSpinBox, QComboBox, QDialogButtonBox
)

from ...rules.tolerances import ToleranceRuleEngine, ToleranceRule, RangeType
from ...config.paths import get_data_dir


class RuleEditDialog(QDialog):
    """Dialogue d'édition d'une règle de tolérance."""
    
    def __init__(self, parent=None, *, initial: Optional[ToleranceRule] = None, family: RangeType = RangeType.NORMALE):
        super().__init__(parent)
        self.setWindowTitle("Édition règle de tolérance")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Famille (lecture seule si initial fourni)
        self.family_combo = QComboBox()
        self.family_combo.addItems([rt.value for rt in RangeType])
        if initial:
            idx = list(RangeType).index(initial)
            self.family_combo.setCurrentIndex(idx)
            self.family_combo.setEnabled(False)
        else:
            idx = list(RangeType).index(family)
            self.family_combo.setCurrentIndex(idx)
        
        # Plages graduation
        self.grad_min = QDoubleSpinBox()
        self.grad_min.setRange(0.001, 1.0)
        self.grad_min.setDecimals(3)
        self.grad_min.setSingleStep(0.001)
        self.grad_max = QDoubleSpinBox()
        self.grad_max.setRange(0.001, 1.0)
        self.grad_max.setDecimals(3)
        self.grad_max.setSingleStep(0.001)
        
        # Plages course
        self.course_min = QDoubleSpinBox()
        self.course_min.setRange(0.1, 100.0)
        self.course_min.setDecimals(3)
        self.course_min.setSingleStep(0.1)
        self.course_max = QDoubleSpinBox()
        self.course_max.setRange(0.1, 100.0)
        self.course_max.setDecimals(3)
        self.course_max.setSingleStep(0.1)
        
        # Limites de tolérance
        self.emt = QDoubleSpinBox()
        self.emt.setRange(0.001, 1.0)
        self.emt.setDecimals(3)
        self.emt.setSingleStep(0.001)
        self.eml = QDoubleSpinBox()
        self.eml.setRange(0.001, 1.0)
        self.eml.setDecimals(3)
        self.eml.setSingleStep(0.001)
        self.ef = QDoubleSpinBox()
        self.ef.setRange(0.001, 1.0)
        self.ef.setDecimals(3)
        self.ef.setSingleStep(0.001)
        self.eh = QDoubleSpinBox()
        self.eh.setRange(0.001, 1.0)
        self.eh.setDecimals(3)
        self.eh.setSingleStep(0.001)
        
        form.addRow("Famille", self.family_combo)
        form.addRow("Graduation min (mm)", self.grad_min)
        form.addRow("Graduation max (mm)", self.grad_max)
        form.addRow("Course min (mm)", self.course_min)
        form.addRow("Course max (mm)", self.course_max)
        form.addRow("Emt limite (mm)", self.emt)
        form.addRow("Eml limite (mm)", self.eml)
        form.addRow("Ef limite (mm)", self.ef)
        form.addRow("Eh limite (mm)", self.eh)
        
        layout.addLayout(form)
        
        # Boutons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        # Pré-remplir si initial fourni
        if initial:
            self.grad_min.setValue(initial.graduation_min)
            self.grad_max.setValue(initial.graduation_max)
            self.course_min.setValue(initial.course_min)
            self.course_max.setValue(initial.course_max)
            self.emt.setValue(initial.Emt)
            self.eml.setValue(initial.Eml)
            self.ef.setValue(initial.Ef)
            self.eh.setValue(initial.Eh)
    
    def result_rule(self) -> Optional[ToleranceRule]:
        """Retourne la règle construite ou None si invalide."""
        try:
            family = RangeType(self.family_combo.currentText())
            return ToleranceRule(
                graduation_min=self.grad_min.value(),
                graduation_max=self.grad_max.value(),
                course_min=self.course_min.value(),
                course_max=self.course_max.value(),
                Emt=self.emt.value(),
                Eml=self.eml.value(),
                Ef=self.ef.value(),
                Eh=self.eh.value()
            )
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", f"Règle invalide : {e}")
            return None


class SettingsRulesTab(QWidget):
    """Onglet d'édition des règles de tolérances."""
    
    rules_changed = Signal()  # émis après modification des règles
    
    def __init__(self):
        super().__init__()
        self.engine = ToleranceRuleEngine()
        self.rules_path = get_data_dir() / "rules" / "tolerances.json"
        
        layout = QVBoxLayout(self)
        
        # Bandeau d'état
        self.status_label = QLabel("Configuration valide")
        self.status_label.setStyleSheet("QLabel { background: #d4edda; color: #155724; padding: 8px; border-radius: 4px; }")
        layout.addWidget(self.status_label)
        
        # Onglets par famille
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Créer un onglet par famille
        self.family_tables = {}
        for family in RangeType:
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            
            # Tableau des règles
            table = QTableWidget(0, 8)
            table.setHorizontalHeaderLabels([
                "Graduation min", "Graduation max", "Course min", "Course max",
                "Emt", "Eml", "Ef", "Eh"
            ])
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            tab_layout.addWidget(table)
            
            # Boutons d'action
            btn_layout = QHBoxLayout()
            btn_add = QPushButton("Ajouter")
            btn_edit = QPushButton("Éditer")
            btn_dup = QPushButton("Dupliquer")
            btn_del = QPushButton("Supprimer")
            
            btn_add.clicked.connect(lambda checked, f=family: self._add_rule(f))
            btn_edit.clicked.connect(lambda checked, f=family: self._edit_rule(f))
            btn_dup.clicked.connect(lambda checked, f=family: self._duplicate_rule(f))
            btn_del.clicked.connect(lambda checked, f=family: self._delete_rule(f))
            
            btn_layout.addWidget(btn_add)
            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_dup)
            btn_layout.addWidget(btn_del)
            btn_layout.addStretch()
            tab_layout.addLayout(btn_layout)
            
            self.tabs.addTab(tab, family.value.title())
            self.family_tables[family] = table
        
        # Boutons globaux
        global_layout = QHBoxLayout()
        btn_import = QPushButton("Importer JSON…")
        btn_export = QPushButton("Exporter JSON…")
        btn_default = QPushButton("Restaurer par défaut")
        btn_save = QPushButton("Sauvegarder")
        
        btn_import.clicked.connect(self._import_json)
        btn_export.clicked.connect(self._export_json)
        btn_default.clicked.connect(self._restore_default)
        btn_save.clicked.connect(self._save_rules)
        
        global_layout.addWidget(btn_import)
        global_layout.addWidget(btn_export)
        global_layout.addWidget(btn_default)
        global_layout.addStretch()
        global_layout.addWidget(btn_save)
        layout.addLayout(global_layout)
        
        # Charger les règles existantes
        self._load_rules()
        self._update_tables()
        self._update_status()
    
    def _load_rules(self):
        """Charge les règles depuis le fichier."""
        if self.rules_path.exists():
            try:
                self.engine.load(self.rules_path)
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Impossible de charger les règles : {e}")
        else:
            # Créer des règles par défaut
            from ...rules.tolerances import create_default_rules
            self.engine = create_default_rules()
    
    def _update_tables(self):
        """Met à jour tous les tableaux."""
        for family, table in self.family_tables.items():
            rules = self.engine.rules[family]
            table.setRowCount(len(rules))
            
            for row, rule in enumerate(rules):
                table.setItem(row, 0, QTableWidgetItem(f"{rule.graduation_min:.3f}"))
                table.setItem(row, 1, QTableWidgetItem(f"{rule.graduation_max:.3f}"))
                table.setItem(row, 2, QTableWidgetItem(f"{rule.course_min:.3f}"))
                table.setItem(row, 3, QTableWidgetItem(f"{rule.course_max:.3f}"))
                table.setItem(row, 4, QTableWidgetItem(f"{rule.Emt:.3f}"))
                table.setItem(row, 5, QTableWidgetItem(f"{rule.Eml:.3f}"))
                table.setItem(row, 6, QTableWidgetItem(f"{rule.Ef:.3f}"))
                table.setItem(row, 7, QTableWidgetItem(f"{rule.Eh:.3f}"))
    
    def _update_status(self):
        """Met à jour le bandeau d'état."""
        errors = self.engine.validate()
        if not errors:
            self.status_label.setText("Configuration valide")
            self.status_label.setStyleSheet("QLabel { background: #d4edda; color: #155724; padding: 8px; border-radius: 4px; }")
        else:
            self.status_label.setText(f"Erreurs détectées : {'; '.join(errors)}")
            self.status_label.setStyleSheet("QLabel { background: #f8d7da; color: #721c24; padding: 8px; border-radius: 4px; }")
    
    def _add_rule(self, family: RangeType):
        """Ajoute une nouvelle règle."""
        dlg = RuleEditDialog(self, family=family)
        if dlg.exec() == QDialog.Accepted:
            rule = dlg.result_rule()
            if rule:
                self.engine.rules[family].append(rule)
                self._update_tables()
                self._update_status()
                self.rules_changed.emit()
    
    def _edit_rule(self, family: RangeType):
        """Édite la règle sélectionnée."""
        table = self.family_tables[family]
        row = table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Sélectionnez une règle à éditer.")
            return
        
        rule = self.engine.rules[family][row]
        dlg = RuleEditDialog(self, initial=rule, family=family)
        if dlg.exec() == QDialog.Accepted:
            new_rule = dlg.result_rule()
            if new_rule:
                self.engine.rules[family][row] = new_rule
                self._update_tables()
                self._update_status()
                self.rules_changed.emit()
    
    def _duplicate_rule(self, family: RangeType):
        """Duplique la règle sélectionnée."""
        table = self.family_tables[family]
        row = table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Sélectionnez une règle à dupliquer.")
            return
        
        rule = self.engine.rules[family][row]
        # Créer une copie avec des valeurs légèrement différentes
        new_rule = ToleranceRule(
            graduation_min=rule.graduation_min + 0.001,
            graduation_max=rule.graduation_max + 0.001,
            course_min=rule.course_min + 0.1,
            course_max=rule.course_max + 0.1,
            Emt=rule.Emt, Eml=rule.Eml, Ef=rule.Ef, Eh=rule.Eh
        )
        self.engine.rules[family].append(new_rule)
        self._update_tables()
        self._update_status()
        self.rules_changed.emit()
    
    def _delete_rule(self, family: RangeType):
        """Supprime la règle sélectionnée."""
        table = self.family_tables[family]
        row = table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Sélectionnez une règle à supprimer.")
            return
        
        if QMessageBox.question(self, "Confirmer", "Supprimer cette règle ?") == QMessageBox.StandardButton.Yes:
            del self.engine.rules[family][row]
            self._update_tables()
            self._update_status()
            self.rules_changed.emit()
    
    def _import_json(self):
        """Importe les règles depuis un fichier JSON."""
        file, _ = QFileDialog.getOpenFileName(self, "Importer règles", "", "JSON (*.json)")
        if file:
            try:
                self.engine.load(Path(file))
                self._update_tables()
                self._update_status()
                self.rules_changed.emit()
                QMessageBox.information(self, "Import", "Règles importées avec succès.")
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Impossible d'importer : {e}")
    
    def _export_json(self):
        """Exporte les règles vers un fichier JSON."""
        file, _ = QFileDialog.getSaveFileName(self, "Exporter règles", "tolerances.json", "JSON (*.json)")
        if file:
            try:
                self.engine.save(Path(file))
                QMessageBox.information(self, "Export", f"Règles exportées vers :\n{file}")
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Impossible d'exporter : {e}")
    
    def _restore_default(self):
        """Restaure les règles par défaut."""
        if QMessageBox.question(self, "Confirmer", "Restaurer les règles par défaut ?") == QMessageBox.StandardButton.Yes:
            from ...rules.tolerances import create_default_rules
            self.engine = create_default_rules()
            self._update_tables()
            self._update_status()
            self.rules_changed.emit()
    
    def _save_rules(self):
        """Sauvegarde les règles."""
        errors = self.engine.validate()
        if errors:
            QMessageBox.warning(self, "Erreur", f"Impossible de sauvegarder : {'; '.join(errors)}")
            return
        
        try:
            self.engine.save(self.rules_path)
            QMessageBox.information(self, "Sauvegarde", "Règles sauvegardées avec succès.")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible de sauvegarder : {e}")
