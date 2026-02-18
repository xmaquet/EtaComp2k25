from __future__ import annotations

from typing import Callable, Optional, List, Dict
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QComboBox, QSpinBox, QLabel, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QSizePolicy
from PySide6.QtCore import Qt

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ..results_provider import ResultsProvider

REMINDER_TEXT = (
    "Déroulement de cette phase :\n"
    "Effectuer la première série de onze mesures croissantes (dont le zéro), puis la première série de mesures "
    "décroissantes, puis les deuxièmes séries de mesures croissantes et décroissantes.\n"
    "À l’issue de cette première phase, le logiciel détermine l’erreur de mesure totale (la plus grande erreur) "
    "et demande la réalisation d’une série de cinq mesures successives au point et dans le sens où cette erreur a été constatée.\n"
    "Avec toutes les données, le logiciel calcule ensuite l’erreur totale, l’erreur locale, l’erreur de fidélité "
    "et l’erreur d’hystérésis, et trace la courbe d’étalonnage."
)


class CalibrationCurveTab(QWidget):
    """
    Onglet “Courbe d’étalonnage”.
    Trace la courbe (erreurs ou mesures) + tableau récapitulatif, avec seuils si disponibles.
    """
    def __init__(self, *, get_runtime_session: Callable[[], object]):
        super().__init__()
        self.get_runtime_session = get_runtime_session
        self.provider = ResultsProvider()
        self.mode_errors = True  # défaut: courbe des erreurs

        root = QVBoxLayout(self)

        # 1) Modèle
        g_model = QGroupBox("Courbe d'étalonnage")
        f1 = QFormLayout(g_model)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Courbe des erreurs (mesuré − cible)", "Courbe des mesures (mesuré)"])
        f1.addRow("Afficher", self.mode_combo)

        # 2) Données & rendu
        g_plot = QGroupBox("Points & courbe")
        v2 = QVBoxLayout(g_plot)
        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v2.addWidget(self.canvas)

        # Tableau sous le graphe
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Cible (mm)", "Moyenne ↑ (mm)", "Moyenne ↓ (mm)", "Erreur ↑ (µm)", "Erreur ↓ (µm)", "Hystérésis (µm)"])
        v2.addWidget(self.table)

        # 3) Actions
        bar = QHBoxLayout()
        self.btn_refresh = QPushButton("Rafraîchir")
        self.btn_refresh.setStyleSheet(
            "QPushButton{background:#0d6efd;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
            "QPushButton:hover{background:#0b5ed7;}"
        )
        bar.addStretch()
        bar.addWidget(self.btn_refresh)

        root.addWidget(g_model)
        root.addWidget(g_plot, stretch=1)
        root.addLayout(bar)
        root.addStretch()

        # Rappel
        g_info = QGroupBox("Rappel du déroulement")
        vinfo = QVBoxLayout(g_info)
        lab = QLabel(REMINDER_TEXT); lab.setWordWrap(True)
        vinfo.addWidget(lab)
        root.addWidget(g_info)

        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.btn_refresh.clicked.connect(self.refresh)

    def _on_mode_changed(self, _i: int):
        self.mode_errors = (self.mode_combo.currentIndex() == 0)
        self.refresh()

    def refresh(self):
        """Recalcule et met à jour le graphe/tableau à partir de la session courante."""
        rt = self.get_runtime_session()
        v2, results, verdict = self.provider.compute_all(rt)

        points: List[Dict] = results.calibration_points or []
        xs = [p["target_mm"] for p in points]
        up_mean = [p["up_mean_mm"] for p in points]
        down_mean = [p["down_mean_mm"] for p in points]
        up_err = [p["up_error_mm"] for p in points]
        down_err = [p["down_error_mm"] for p in points]

        # Graphe
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        if self.mode_errors:
            # Tracer erreurs en µm
            up_err_um = [None if v is None else v * 1000.0 for v in up_err]
            down_err_um = [None if v is None else v * 1000.0 for v in down_err]
            # Remplacer None par NaN pour matplotlib
            import math
            up_plot = [math.nan if v is None else v for v in up_err_um]
            dn_plot = [math.nan if v is None else v for v in down_err_um]
            ax.plot(xs, up_plot, marker="o", label="Erreur montée (µm)")
            ax.plot(xs, dn_plot, marker="s", label="Erreur descente (µm)")
            ax.axhline(0.0, color="gray", linewidth=1, linestyle="--")
            # Seuils ±Emt si dispo
            if verdict and verdict.rule and ("Emt" in verdict.limits):
                emt = verdict.limits["Emt"] * 1000.0
                ax.axhline(+emt, color="red", linewidth=1, linestyle=":")
                ax.axhline(-emt, color="red", linewidth=1, linestyle=":")
            ax.set_ylabel("Erreur (µm)")
        else:
            ax.plot(xs, up_mean, marker="o", label="Mesuré montée")
            ax.plot(xs, down_mean, marker="s", label="Mesuré descente")
            ax.set_ylabel("Mesuré (mm)")
        ax.set_xlabel("Cible (mm)")
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)
        ax.legend(loc="best")

        # Rendre les cibles explicites sur l'axe X et par lignes guides
        if xs:
            try:
                ax.set_xticks(xs)
                ax.set_xticklabels([f"{x:.1f}" for x in xs])
            except Exception:
                pass
            # Lignes verticales légères sur chaque cible
            for x in xs:
                ax.axvline(x, color="gray", linestyle=":", linewidth=0.6, alpha=0.3, zorder=0)

        # Marquer le point critique
        if results.total_error_location:
            loc = results.total_error_location
            xt = loc.get("target_mm"); yt = None
            if self.mode_errors:
                err_mm = loc.get("error_mm")
                yt = (err_mm * 1000.0) if err_mm is not None else None
            else:
                yt = loc.get("measured_mm")
            if xt is not None and yt is not None:
                ax.scatter([xt], [yt], color="orange", s=80, zorder=5)
                ax.annotate(f"Critique ({xt:.1f})", (xt, yt), textcoords="offset points", xytext=(6, 6))

        self.canvas.draw_idle()

        # Tableau
        self.table.setRowCount(0)
        for p in points:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f"{p['target_mm']:.3f}"))
            self.table.setItem(row, 1, QTableWidgetItem("" if p["up_mean_mm"] is None else f"{p['up_mean_mm']:.6f}"))
            self.table.setItem(row, 2, QTableWidgetItem("" if p["down_mean_mm"] is None else f"{p['down_mean_mm']:.6f}"))
            # Erreurs/hystérésis en µm (1 décimale)
            self.table.setItem(row, 3, QTableWidgetItem("" if p["up_error_mm"] is None else f"{p['up_error_mm']*1000.0:.1f}"))
            self.table.setItem(row, 4, QTableWidgetItem("" if p["down_error_mm"] is None else f"{p['down_error_mm']*1000.0:.1f}"))
            self.table.setItem(row, 5, QTableWidgetItem("" if p["hysteresis_mm"] is None else f"{p['hysteresis_mm']*1000.0:.1f}"))
            # Surligner la ligne du point critique
            if results.total_error_location and abs(p["target_mm"] - results.total_error_location.get("target_mm", -999)) < 1e-9:
                for c in range(self.table.columnCount()):
                    it = self.table.item(row, c)
                    if it:
                        it.setBackground(Qt.yellow)
