from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QPushButton, QHBoxLayout,
    QTextEdit, QTableWidget, QTableWidgetItem, QMessageBox, QSizePolicy
)

from ...core.calculation_engine import CalculatedResults
from ..results_provider import ResultsProvider
from ...rules.verdict import VerdictStatus
from ...state.session_store import session_store


class FinalizationTab(QWidget):
    """Onglet de finalisation avec évaluation des tolérances."""
    
    def __init__(self):
        super().__init__()
        self.current_results: Optional[CalculatedResults] = None
        self.provider = ResultsProvider()
        
        layout = QVBoxLayout(self)
        
        # Le provider charge déjà le moteur de règles de façon interne
        
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
        # Laisse la table grandir (pas de hauteur max)
        self.errors_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        summary_layout.addWidget(self.errors_table)
        
        # Messages détaillés
        self.messages_text = QTextEdit()
        # Laisse le panneau messages grandir (pas de hauteur max)
        self.messages_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.messages_text.setReadOnly(True)
        summary_layout.addWidget(self.messages_text)
        
        # Donne le maximum d'espace vertical au bloc de synthèse
        layout.addWidget(self.summary_group, stretch=1)
        
        # Boutons d'action
        action_layout = QHBoxLayout()
        self.btn_calculate = QPushButton("Calculer les erreurs")
        # Bouton 'primaire' mieux visible
        self.btn_calculate.setStyleSheet(
            "QPushButton{background:#0d6efd;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
            "QPushButton:hover{background:#0b5ed7;}"
        )
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
        
        # Connecter aux changements de session
        session_store.session_changed.connect(self._on_session_changed)
    
    def _on_session_changed(self):
        """Appelé quand la session change."""
        self._update_display()
    
    def _update_display(self):
        """Met à jour l'affichage selon l'état actuel."""
        session = session_store.current
        if session is None or not session.has_measures():
            self.verdict_label.setText("Aucune mesure disponible")
            self.verdict_label.setStyleSheet("QLabel { padding: 12px; font-size: 14px; font-weight: bold; }")
            self.errors_table.setRowCount(0)
            self.messages_text.clear()
            return

        if self.current_results:
            self._display_results()
    
    def _calculate_errors(self):
        """Calcule les erreurs via CalculationEngine à partir du runtime Session."""
        rt = session_store.current
        if rt is None or not rt.has_measures():
            QMessageBox.warning(self, "Erreur", "Aucune session active ou aucune mesure.")
            return
        try:
            v2, results, verdict = self.provider.compute_all(rt)
            self.current_results = results
            # Afficher erreurs et verdict/limites
            self._display_results()
            if verdict:
                self._display_verdict_and_limits(verdict)
            else:
                self.messages_text.append("\nAvertissement: Règles introuvables ou non valides. Complétez Paramètres ▸ Règles.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de calculer les erreurs :\n{e}")
    
    def _display_results(self):
        """Affiche les résultats des calculs d'erreurs."""
        res = self.current_results
        if not res:
            return
        # Tableau des erreurs principales
        rows = [
            ("Erreur totale (|mm|)", res.total_error_mm),
            ("Erreur locale (|Δerr|)", res.local_error_mm),
            ("Hystérésis max", res.hysteresis_max_mm),
            ("Fidélité (σ, 5 pts)", res.fidelity_std_mm if res.fidelity_std_mm is not None else None),
        ]
        self.errors_table.setRowCount(len(rows))
        for i, (label, val) in enumerate(rows):
            self.errors_table.setItem(i, 0, QTableWidgetItem(label))
            if val is None:
                self.errors_table.setItem(i, 1, QTableWidgetItem("—"))
            else:
                # Utiliser un QLabel pour afficher µm en gras
                from PySide6.QtWidgets import QLabel
                w = QLabel(f"{val:.6f} mm (<b>{val*1000.0:.1f} µm</b>)")
                w.setTextFormat(Qt.RichText)
                self.errors_table.setCellWidget(i, 1, w)

        # Messages synthèse
        msgs = []
        if res.total_error_location:
            loc = res.total_error_location
            msgs.append(
                f"Point critique: cible {loc.get('target_mm'):.3f} mm, sens {loc.get('direction')}, "
                f"mesuré {loc.get('measured_mm'):.6f} mm (err {loc.get('error_mm'):+.6f} mm)."
            )
        if res.hysteresis_location:
            hl = res.hysteresis_location
            msgs.append(
                f"Hystérésis max sur {hl.get('target_mm'):.3f} mm: "
                f"{hl.get('hysteresis_mm'):.6f} mm."
            )
        if res.fidelity_context:
            fc = res.fidelity_context
            msgs.append(
                f"Fidélité (5 pts) sur {fc.get('target_mm'):.3f} mm ({fc.get('direction')}): "
                f"σ={res.fidelity_std_mm:.6f} mm (μ={fc.get('mean_mm'):.6f} mm)."
            )
        if not msgs:
            msgs.append("Campagne partielle — calcule avec les données disponibles.")
        # Utiliser HTML pour mettre en gras les µm
        html = "<br/>".join(msgs)
        self.messages_text.setHtml(html)
        # Bandeau neutre; coloré après verdict
        self.verdict_label.setText("Calcul terminé — voir verdict ci‑dessous")
        self.verdict_label.setStyleSheet("QLabel { padding: 12px; font-size: 14px; font-weight: bold; }")
    
    def _export_pdf(self):
        QMessageBox.information(self, "Export PDF", "Fonctionnalité d'export PDF à implémenter.")
    
    def _export_html(self):
        QMessageBox.information(self, "Export HTML", "Fonctionnalité d'export HTML à implémenter.")

    # ----- Verdict & limites -----
    def _display_verdict_and_limits(self, verdict):
        # Bandeau coloré
        if verdict.status == VerdictStatus.APTE:
            self.verdict_label.setText("✅ CONFORME")
            self.verdict_label.setStyleSheet("QLabel { background: #d4edda; color: #155724; padding: 12px; font-size: 14px; font-weight: bold; border-radius: 4px; }")
        elif verdict.status == VerdictStatus.INAPTE:
            self.verdict_label.setText("❌ NON CONFORME")
            self.verdict_label.setStyleSheet("QLabel { background: #f8d7da; color: #721c24; padding: 12px; font-size: 14px; font-weight: bold; border-radius: 4px; }")
        else:
            self.verdict_label.setText("⚠️ VERDICT INDÉTERMINÉ")
            self.verdict_label.setStyleSheet("QLabel { background: #fff3cd; color: #856404; padding: 12px; font-size: 14px; font-weight: bold; border-radius: 4px; }")

        lines = []
        # Règle
        if verdict.rule:
            r = verdict.rule
            lines.append("Règle appliquée:")
            lines.append(f"  • Famille: {self._family_label()}")
            lines.append(f"  • Graduation: {r.graduation:.3f} mm")
            if r.course_min is not None and r.course_max is not None:
                lines.append(f"  • Plage de course: {r.course_min:.3f} – {r.course_max:.3f} mm")
            # Limites: afficher uniquement celles présentes
            lims = []
            lims.append(f"Emt={getattr(r, 'Emt', None):.3f}")
            if getattr(r, "Eml", None) is not None:
                lims.append(f"Eml={r.Eml:.3f}")
            lims.append(f"Ef={getattr(r, 'Ef', None):.3f}")
            lims.append(f"Eh={getattr(r, 'Eh', None):.3f}")
            lines.append("  • Limites: " + " ; ".join(lims) + " mm")
        else:
            lines.append("Aucune règle appliquée.")

        # Comparaisons
        if verdict.measured:
            lines.append("\nRésultats vs limites:")
            # Afficher uniquement les critères présents dans les limites
            for key in ("Emt", "Eml", "Ef", "Eh"):
                if key not in verdict.limits:
                    continue
                m = verdict.measured.get(key, None)
                lim = verdict.limits.get(key, None)
                if m is None:
                    lines.append(f"  • Erreur {self._label_fr(key)}: requise mais indisponible")
                else:
                    delta = m - lim
                    sign = f" (dépassement {delta:.3f} mm / {delta*1000.0:.1f} µm)" if delta > 1e-9 else ""
                    lines.append(
                        f"  • Erreur {self._label_fr(key)}: {m:.3f} mm ({m*1000.0:.1f} µm) ; "
                        f"limite {lim:.3f} mm ({lim*1000.0:.1f} µm){sign}"
                    )

        # Messages du verdict
        if verdict.messages:
            lines.append("\nNotes:")
            lines.extend(verdict.messages)

        self.messages_text.append("<br/>" + "<br/>".join(lines))

    def _label_fr(self, key: str) -> str:
        return {
            "Emt": "totale",
            "Eml": "locale",
            "Eh": "d'hystérésis",
            "Ef": "de fidélité"
        }.get(key, key)

    def _family_label(self) -> str:
        return "selon profil"  # Placeholder; on pourrait passer family depuis snapshot si nécessaire
