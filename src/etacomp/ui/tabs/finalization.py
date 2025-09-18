from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QPushButton, QHBoxLayout,
    QTextEdit, QTableWidget, QTableWidgetItem, QMessageBox
)

from ...calculations.errors import calculate_comparator_errors, ErrorResults
from ...rules.tolerances import ToleranceRuleEngine, get_default_rules_path
from ...state.session_store import session_store
from ...io.storage import list_comparators


class FinalizationTab(QWidget):
    """Onglet de finalisation avec évaluation des tolérances."""
    
    def __init__(self):
        super().__init__()
        self.engine = ToleranceRuleEngine()
        self.current_results: Optional[ErrorResults] = None
        
        layout = QVBoxLayout(self)
        
        # Charger le moteur de règles
        self._load_tolerance_engine()
        
        # Groupe de synthèse
        self.summary_group = QGroupBox("Synthèse des mesures")
        summary_layout = QVBoxLayout(self.summary_group)
        
        # Bandeau de verdict
        self.verdict_label = QLabel("Aucune mesure disponible")
        self.verdict_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verdict_label.setStyleSheet("QLabel { padding: 12px; font-size: 14px; font-weight: bold; }")
        summary_layout.addWidget(self.verdict_label)
        
        # Tableau des erreurs calculées
        self.errors_table = QTableWidget(0, 2)
        self.errors_table.setHorizontalHeaderLabels(["Erreur", "Valeur (mm)"])
        self.errors_table.setMaximumHeight(150)
        summary_layout.addWidget(self.errors_table)
        
        # Messages détaillés
        self.messages_text = QTextEdit()
        self.messages_text.setMaximumHeight(100)
        self.messages_text.setReadOnly(True)
        summary_layout.addWidget(self.messages_text)
        
        layout.addWidget(self.summary_group)
        
        # Groupe de rapport
        self.report_group = QGroupBox("Rapport")
        report_layout = QVBoxLayout(self.report_group)
        
        # Statistiques par cible
        self.target_stats_table = QTableWidget(0, 7)
        self.target_stats_table.setHorizontalHeaderLabels([
            "Cible (mm)", "Moyenne (mm)", "Écart-type (mm)", 
            "Min (mm)", "Max (mm)", "Erreur (mm)", "Plage (mm)"
        ])
        report_layout.addWidget(self.target_stats_table)
        
        layout.addWidget(self.report_group)
        
        # Boutons d'action
        action_layout = QHBoxLayout()
        self.btn_calculate = QPushButton("Calculer les erreurs")
        self.btn_export_pdf = QPushButton("Exporter PDF")
        self.btn_export_html = QPushButton("Exporter HTML")
        
        self.btn_calculate.clicked.connect(self._calculate_errors)
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        self.btn_export_html.clicked.connect(self._export_html)
        
        action_layout.addWidget(self.btn_calculate)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_export_html)
        action_layout.addWidget(self.btn_export_pdf)
        
        layout.addLayout(action_layout)
        layout.addStretch()
        
        # Connecter aux changements de session
        session_store.session_changed.connect(self._on_session_changed)
    
    def _load_tolerance_engine(self):
        """Charge le moteur de règles de tolérances."""
        try:
            rules_path = get_default_rules_path()
            self.engine.load(rules_path)
        except Exception as e:
            # Créer des règles par défaut si le fichier n'existe pas
            from ...rules.tolerances import create_default_rules
            self.engine = create_default_rules()
    
    def _on_session_changed(self):
        """Appelé quand la session change."""
        self._update_display()
    
    def _update_display(self):
        """Met à jour l'affichage selon l'état actuel."""
        session = session_store.current_session
        if not session or not session.comparator_profile:
            self.verdict_label.setText("Aucune mesure disponible")
            self.verdict_label.setStyleSheet("QLabel { padding: 12px; font-size: 14px; font-weight: bold; }")
            self.errors_table.setRowCount(0)
            self.target_stats_table.setRowCount(0)
            self.messages_text.clear()
            return
        
        # Si des erreurs ont été calculées, les afficher
        if self.current_results:
            self._display_results()
    
    def _calculate_errors(self):
        """Calcule les erreurs et évalue les tolérances."""
        session = session_store.current_session
        if not session or not session.comparator_profile:
            QMessageBox.warning(self, "Erreur", "Aucune session ou profil de comparateur sélectionné.")
            return
        
        if not session.measure_series:
            QMessageBox.warning(self, "Erreur", "Aucune série de mesures disponible.")
            return
        
        try:
            # Calculer les erreurs
            self.current_results = calculate_comparator_errors(
                session.comparator_profile, 
                session.measure_series
            )
            
            # Évaluer les tolérances
            errors_dict = self.current_results.to_dict()
            verdict = self.engine.evaluate(session.comparator_profile, errors_dict)
            
            # Afficher les résultats
            self._display_results()
            self._display_verdict(verdict)
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de calculer les erreurs : {e}")
    
    def _display_results(self):
        """Affiche les résultats des calculs d'erreurs."""
        if not self.current_results:
            return
        
        # Tableau des erreurs principales
        self.errors_table.setRowCount(4)
        
        errors_data = [
            ("Emt (Erreur totale)", self.current_results.Emt),
            ("Eml (Erreur locale)", self.current_results.Eml),
            ("Ef (Erreur fidélité)", self.current_results.Ef),
            ("Eh (Erreur hystérésis)", self.current_results.Eh)
        ]
        
        for row, (name, value) in enumerate(errors_data):
            self.errors_table.setItem(row, 0, QTableWidgetItem(name))
            self.errors_table.setItem(row, 1, QTableWidgetItem(f"{value:.6f}"))
        
        # Tableau des statistiques par cible
        stats = self.current_results.target_stats
        self.target_stats_table.setRowCount(len(stats))
        
        for row, stat in enumerate(stats):
            self.target_stats_table.setItem(row, 0, QTableWidgetItem(f"{stat['target']:.3f}"))
            self.target_stats_table.setItem(row, 1, QTableWidgetItem(f"{stat['mean']:.6f}"))
            self.target_stats_table.setItem(row, 2, QTableWidgetItem(f"{stat['std_dev']:.6f}"))
            self.target_stats_table.setItem(row, 3, QTableWidgetItem(f"{stat['min']:.6f}"))
            self.target_stats_table.setItem(row, 4, QTableWidgetItem(f"{stat['max']:.6f}"))
            self.target_stats_table.setItem(row, 5, QTableWidgetItem(f"{stat['error']:.6f}"))
            self.target_stats_table.setItem(row, 6, QTableWidgetItem(f"{stat['range']:.6f}"))
    
    def _display_verdict(self, verdict):
        """Affiche le verdict de tolérance."""
        if verdict.status == "apte":
            self.verdict_label.setText("✅ COMPARATEUR APTE")
            self.verdict_label.setStyleSheet(
                "QLabel { background: #d4edda; color: #155724; padding: 12px; "
                "font-size: 14px; font-weight: bold; border-radius: 4px; }"
            )
        elif verdict.status == "inapte":
            self.verdict_label.setText("❌ COMPARATEUR INAPTE")
            self.verdict_label.setStyleSheet(
                "QLabel { background: #f8d7da; color: #721c24; padding: 12px; "
                "font-size: 14px; font-weight: bold; border-radius: 4px; }"
            )
        else:  # indéterminé
            self.verdict_label.setText("⚠️ VERDICT INDÉTERMINÉ")
            self.verdict_label.setStyleSheet(
                "QLabel { background: #fff3cd; color: #856404; padding: 12px; "
                "font-size: 14px; font-weight: bold; border-radius: 4px; }"
            )
        
        # Messages détaillés
        messages = []
        if verdict.messages:
            messages.extend(verdict.messages)
        
        if verdict.exceed:
            messages.append("\nDépassements détectés :")
            for error_name, delta in verdict.exceed.items():
                messages.append(f"  • {error_name}: +{delta:.3f} mm")
        
        self.messages_text.setPlainText("\n".join(messages))
    
    def _export_pdf(self):
        """Exporte le rapport en PDF."""
        QMessageBox.information(self, "Export PDF", "Fonctionnalité d'export PDF à implémenter.")
    
    def _export_html(self):
        """Exporte le rapport en HTML."""
        QMessageBox.information(self, "Export HTML", "Fonctionnalité d'export HTML à implémenter.")
