from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QCheckBox,
    QMessageBox, QFileDialog, QAbstractItemView,
    QDialog, QFormLayout, QDoubleSpinBox, QComboBox, QDialogButtonBox
)

from ...rules.tolerances import ToleranceRuleEngine, ToleranceRule
from ...config.paths import get_data_dir


class RuleEditDialog(QDialog):
    """Dialogue d'édition d'une règle de tolérance."""
    
    def __init__(self, parent=None, *, initial: Optional[ToleranceRule] = None, family: str = "normale"):
        super().__init__(parent)
        self.setWindowTitle("Édition règle de tolérance")
        self.setMinimumWidth(500)
        
        self.family = family
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Graduation (toujours présent)
        self.graduation = QDoubleSpinBox()
        self.graduation.setRange(0.001, 1.0)
        self.graduation.setDecimals(3)
        self.graduation.setSingleStep(0.001)
        self.graduation.setToolTip("Graduation en millimètres (valeur unique)")
        
        # Course min/max (seulement pour normale/grande)
        self.course_min = QDoubleSpinBox()
        self.course_min.setRange(0.0, 100.0)
        self.course_min.setDecimals(3)
        self.course_min.setSingleStep(0.1)
        self.course_min.setToolTip("Course minimale en millimètres")
        
        self.course_max = QDoubleSpinBox()
        self.course_max.setRange(0.0, 100.0)
        self.course_max.setDecimals(3)
        self.course_max.setSingleStep(0.1)
        self.course_max.setToolTip("Course maximale en millimètres")
        
        # Limites de tolérance
        self.emt = QDoubleSpinBox()
        self.emt.setRange(0.0, 1.0)
        self.emt.setDecimals(3)
        self.emt.setSingleStep(0.001)
        self.emt.setToolTip("Erreur de mesure totale (mm)")
        
        self.eml = QDoubleSpinBox()
        self.eml.setRange(0.0, 1.0)
        self.eml.setDecimals(3)
        self.eml.setSingleStep(0.001)
        self.eml.setToolTip("Erreur de mesure locale (mm)")
        
        self.ef = QDoubleSpinBox()
        self.ef.setRange(0.0, 1.0)
        self.ef.setDecimals(3)
        self.ef.setSingleStep(0.001)
        self.ef.setToolTip("Erreur de fidélité (mm)")
        
        self.eh = QDoubleSpinBox()
        self.eh.setRange(0.0, 1.0)
        self.eh.setDecimals(3)
        self.eh.setSingleStep(0.001)
        self.eh.setToolTip("Erreur d'hystérésis (mm)")
        
        form.addRow("Graduation (mm)", self.graduation)
        
        # Ajouter course min/max seulement pour normale/grande
        if family in ("normale", "grande"):
            form.addRow("Course min (mm)", self.course_min)
            form.addRow("Course max (mm)", self.course_max)
        else:
            # Masquer les champs pour faible/limitée
            self.course_min.setVisible(False)
            self.course_max.setVisible(False)
        
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
            self.graduation.setValue(initial.graduation)
            if initial.course_min is not None:
                self.course_min.setValue(initial.course_min)
            if initial.course_max is not None:
                self.course_max.setValue(initial.course_max)
            self.emt.setValue(initial.Emt)
            self.eml.setValue(initial.Eml)
            self.ef.setValue(initial.Ef)
            self.eh.setValue(initial.Eh)
    
    def result_rule(self) -> Optional[ToleranceRule]:
        """Retourne la règle construite ou None si invalide."""
        try:
            kwargs = {
                "graduation": self.graduation.value(),
                "Emt": self.emt.value(),
                "Eml": self.eml.value(),
                "Ef": self.ef.value(),
                "Eh": self.eh.value()
            }
            
            # Ajouter course_min/max seulement pour normale/grande
            if self.family in ("normale", "grande"):
                kwargs["course_min"] = self.course_min.value()
                kwargs["course_max"] = self.course_max.value()
            
            return ToleranceRule(**kwargs)
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", f"Règle invalide : {e}")
            return None


class SettingsRulesTab(QWidget):
    """Onglet d'édition des règles de tolérances avec 4 sections."""
    
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

        # Notice d'interprétation des intervalles (normale/grande)
        info = QLabel(
            "Intervalles de course appliqués par EtaComp\n"
            "Pour une même graduation, les lignes sont interprétées dans l’ordre des courses :\n"
            "• Première ligne : course ≥ min et ≤ max (si min=0, c’est simplement ≤ max)\n"
            "• Lignes suivantes : course > min et ≤ max\n"
            "Exemple : « ≤ 5 », puis « > 5 et ≤ 10 »."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Info: configuration de base « grande » = mêmes valeurs que « normale », mais distinctes
        info2 = QLabel("Note: la configuration de base définit des valeurs identiques pour « course grande » et « course normale », mais elles restent éditables séparément.")
        info2.setWordWrap(True)
        layout.addWidget(info2)
        
        # Onglets par famille
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Créer un onglet par famille
        self.family_tables = {}
        families = ["normale", "grande", "faible", "limitee"]
        
        # Import pour accéder aux libellés complets
        from ...models.comparator import RangeType
        
        for family in families:
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            
            # Colonnes selon la famille
            if family in ("normale", "grande"):
                headers = ["Graduation (mm)", "Course min (mm)", "Course max (mm)", "Emt (µm)", "Eml (µm)", "Ef (µm)", "Eh (µm)", "Interprétation"]
            else:
                headers = ["Graduation (mm)", "Emt (µm)", "Eml (µm)", "Ef (µm)", "Eh (µm)"]
            
            # Tableau des règles
            table = QTableWidget(0, len(headers))
            table.setHorizontalHeaderLabels(headers)
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
            
            self.tabs.addTab(tab, RangeType(family).display_name)
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
    
    # (Plus de liaison automatique grande→normale; familles distinctes)
    
    def _update_tables(self):
        """Met à jour tous les tableaux."""
        for family, table in self.family_tables.items():
            rules = self.engine.rules[family]
            table.setRowCount(len(rules))

            # Construire l'interprétation stricte par graduation (ordre par course_max)
            interp_by_index = {}
            if family in ("normale", "grande"):
                grads = {}
                for idx, r in enumerate(rules):
                    grads.setdefault(f"{r.graduation:.6f}", []).append((idx, r))
                for g, lst in grads.items():
                    lst_sorted = sorted(lst, key=lambda t: (t[1].course_max, t[1].course_min))
                    for i, (row_idx, r) in enumerate(lst_sorted):
                        if i == 0:
                            if (r.course_min or 0.0) <= 0.0:
                                text = f"course ≤ {r.course_max:.3f}"
                            else:
                                text = f"course ≥ {r.course_min:.3f} et ≤ {r.course_max:.3f}"
                        else:
                            text = f"course > {r.course_min:.3f} et ≤ {r.course_max:.3f}"
                        interp_by_index[row_idx] = text

            for row, rule in enumerate(rules):
                col = 0
                table.setItem(row, col, QTableWidgetItem(f"{rule.graduation:.3f}")); col += 1
                if family in ("normale", "grande"):
                    table.setItem(row, col, QTableWidgetItem(f"{rule.course_min:.3f}" if rule.course_min is not None else "")); col += 1
                    table.setItem(row, col, QTableWidgetItem(f"{rule.course_max:.3f}" if rule.course_max is not None else "")); col += 1
                # Tolérances affichées en µm
                table.setItem(row, col, QTableWidgetItem(f"{rule.Emt*1000:.3f}")); col += 1
                eml_val = getattr(rule, "Eml", None)
                table.setItem(row, col, QTableWidgetItem(f"{eml_val*1000:.3f}" if eml_val is not None else "")); col += 1
                table.setItem(row, col, QTableWidgetItem(f"{rule.Ef*1000:.3f}")); col += 1
                table.setItem(row, col, QTableWidgetItem(f"{rule.Eh*1000:.3f}"))
                if family in ("normale", "grande"):
                    col += 1
                    table.setItem(row, col, QTableWidgetItem(interp_by_index.get(row, "")))
    
    def _update_status(self):
        """Met à jour le bandeau d'état."""
        errors = self.engine.validate()
        # Détecter des "trous" (non bloquant) sur normale/grande
        warnings = []
        for fam in ("normale", "grande"):
            rr = self.engine.rules.get(fam, [])
            grads = {}
            for r in rr:
                grads.setdefault(f"{r.graduation:.6f}", []).append(r)
            for g, lst in grads.items():
                lst_sorted = sorted(lst, key=lambda r: (r.course_max, r.course_min))
                for i in range(len(lst_sorted) - 1):
                    a = lst_sorted[i]; b = lst_sorted[i+1]
                    if a.course_max is not None and b.course_min is not None and b.course_min > a.course_max:
                        warnings.append(f"{g}: trou entre {a.course_max:.3f} et {b.course_min:.3f} mm")

        if not errors:
            if warnings:
                self.status_label.setText("Configuration valide (avec avertissements) — " + " ; ".join(warnings))
                self.status_label.setStyleSheet("QLabel { background: #fff3cd; color: #856404; padding: 8px; border-radius: 4px; }")
            else:
                self.status_label.setText("Configuration valide")
                self.status_label.setStyleSheet("QLabel { background: #d4edda; color: #155724; padding: 8px; border-radius: 4px; }")
        else:
            self.status_label.setText(f"Erreurs détectées : {'; '.join(errors)}")
            self.status_label.setStyleSheet("QLabel { background: #f8d7da; color: #721c24; padding: 8px; border-radius: 4px; }")
    
    def _add_rule(self, family: str):
        """Ajoute une nouvelle règle."""
        dlg = RuleEditDialog(self, family=family)
        if dlg.exec() == QDialog.Accepted:
            rule = dlg.result_rule()
            if rule:
                self.engine.rules[family].append(rule)
                self._update_tables()
                self._update_status()
                self.rules_changed.emit()
    
    def _edit_rule(self, family: str):
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
    
    def _duplicate_rule(self, family: str):
        """Duplique la règle sélectionnée."""
        table = self.family_tables[family]
        row = table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Sélectionnez une règle à dupliquer.")
            return
        
        rule = self.engine.rules[family][row]
        # Créer une copie avec graduation légèrement différente
        new_rule = ToleranceRule(
            graduation=rule.graduation + 0.001,
            course_min=rule.course_min,
            course_max=rule.course_max,
            Emt=rule.Emt, Eml=rule.Eml, Ef=rule.Ef, Eh=rule.Eh
        )
        self.engine.rules[family].append(new_rule)
        self._update_tables()
        self._update_status()
        self.rules_changed.emit()
    
    def _delete_rule(self, family: str):
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
