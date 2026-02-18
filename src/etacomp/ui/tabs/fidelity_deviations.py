from __future__ import annotations

from typing import Callable, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
import time

from ..results_provider import ResultsProvider
from ...io.serial_manager import serial_manager
from ...state.session_store import session_store


REMINDER_TEXT = (
    "Déroulement de cette phase :\n"
    "Effectuer la première série de onze mesures croissantes (dont le zéro), puis la première série de mesures "
    "décroissantes, puis les deuxièmes séries de mesures croissantes et décroissantes.\n"
    "À l’issue de cette première phase, le logiciel détermine l’erreur de mesure totale (la plus grande erreur) "
    "et demande la réalisation d’une série de cinq mesures successives au point et dans le sens où cette erreur a été constatée.\n"
    "Avec toutes les données, le logiciel calcule ensuite l’erreur totale, l’erreur locale, l’erreur de fidélité "
    "et l’erreur d’hystérésis, et trace la courbe d’étalonnage."
)


class FidelityDeviationsTab(QWidget):
    """
    Onglet “Écarts de fidélité”.
    Affiche la série 5 (5 mesures) et les statistiques (moyenne, écart-type), ainsi que la limite Ef si disponible.
    """
    def __init__(
        self,
        *,
        get_runtime_session: Callable[[], object],
        go_to_session_tab: Optional[Callable[[], None]] = None
    ):
        super().__init__()
        self.get_runtime_session = get_runtime_session
        self.go_to_session_tab = go_to_session_tab
        self.provider = ResultsProvider()

        root = QVBoxLayout(self)

        # Rappel
        reminder = QGroupBox("Rappel du déroulement")
        vrem = QVBoxLayout(reminder)
        lab_rem = QLabel(REMINDER_TEXT)
        lab_rem.setWordWrap(True)
        vrem.addWidget(lab_rem)
        root.addWidget(reminder)

        # Contexte du point critique
        ctx_box = QGroupBox("Point critique (erreur totale)")
        vctx = QVBoxLayout(ctx_box)
        self.lbl_ctx = QLabel("Indisponible")
        vctx.addWidget(self.lbl_ctx)
        root.addWidget(ctx_box)

        # Tableau 5 mesures
        table_box = QGroupBox("Série de cinq mesures successives")
        vtab = QVBoxLayout(table_box)
        lay_h = QHBoxLayout()
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Index", "Valeur (mm)", "Horodatage"])
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay_h.addWidget(self.table, stretch=3)
        # Panneau de résumé à droite
        self.lbl_sequence = QLabel("Série 5: —")
        self.lbl_sequence.setWordWrap(True)
        self.lbl_sequence.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_sequence.setStyleSheet("QLabel{font-size:16px;font-weight:700;padding:8px;}")
        side_box = QVBoxLayout()
        side_box.addWidget(self.lbl_sequence)
        side_wrap = QGroupBox("Résumé")
        side_wrap.setLayout(side_box)
        lay_h.addWidget(side_wrap, stretch=1)
        vtab.addLayout(lay_h)
        root.addWidget(table_box, stretch=1)

        # Stats + tolérance
        stats_box = QGroupBox("Statistiques et tolérance")
        vstats = QVBoxLayout(stats_box)
        self.lbl_stats = QLabel("—")
        self.lbl_tol = QLabel("—")
        vstats.addWidget(self.lbl_stats)
        vstats.addWidget(self.lbl_tol)
        root.addWidget(stats_box)

        # Boutons / capture S5
        btns = QHBoxLayout()
        self.btn_refresh = QPushButton("Rafraîchir")
        self.btn_refresh.setStyleSheet(
            "QPushButton{background:#0d6efd;color:#fff;font-weight:600;padding:6px 12px;border-radius:6px;}"
            "QPushButton:hover{background:#0b5ed7;}"
        )
        self.btn_start = QPushButton("Démarrer série 5"); 
        self.btn_stop = QPushButton("Arrêter"); self.btn_stop.setEnabled(False)
        self.btn_clear = QPushButton("Effacer")
        btns.addWidget(self.btn_refresh)
        btns.addWidget(self.btn_start)
        btns.addWidget(self.btn_stop)
        btns.addWidget(self.btn_clear)
        btns.addStretch()
        self.btn_go_session = QPushButton("Aller à la Session")
        btns.addWidget(self.btn_go_session)
        root.addLayout(btns)

        self.btn_refresh.clicked.connect(self.refresh)
        if self.go_to_session_tab:
            self.btn_go_session.clicked.connect(self.go_to_session_tab)
        else:
            self.btn_go_session.setEnabled(False)
        self.btn_start.clicked.connect(self._start_capture)
        self.btn_stop.clicked.connect(self._stop_capture)
        self.btn_clear.clicked.connect(self._clear_samples)

        # État de capture
        self._capturing = False
        self._samples: list[float] = []
        self._timestamps: list[str] = []
        self._crit_target: Optional[float] = None
        self._crit_dir: Optional[str] = None
        self._last_sample_val: Optional[float] = None
        self._last_sample_ts: float = 0.0
        self._dedup_window_s: float = 0.12  # fenêtre anti-doublon (120 ms)

    def refresh(self):
        """Recalcule et met à jour l'UI à partir de la session courante."""
        rt = self.get_runtime_session()
        v2, results, verdict = self.provider.compute_all(rt)

        # Contexte point critique
        if results.total_error_location:
            loc = results.total_error_location
            self.lbl_ctx.setText(
                f"Cible: {loc.get('target_mm'):.3f} mm ; sens: {loc.get('direction')} ; "
                f"mesuré: {loc.get('measured_mm'):.6f} mm ; erreur: {loc.get('error_mm'):+.6f} mm"
            )
            # Mettre à jour le résumé
            self.lbl_sequence.setText(
                f"Série 5 — Point critique\n"
                f"• Cible: {loc.get('target_mm'):.3f} mm\n"
                f"• Sens: {loc.get('direction')}\n"
                f"• Écart max: {loc.get('error_mm'):+.6f} mm (<b>{loc.get('error_mm')*1000.0:+.1f} µm</b>)\n"
                f"• État: prêt à démarrer"
            )
        else:
            self.lbl_ctx.setText("Indisponible — la campagne semble incomplète.")
            self.lbl_sequence.setText("Série 5 — Indisponible\nCompléter les séries 1 à 4.")

        # Série 5 (fidélité)
        self.table.setRowCount(0)
        if results.fidelity_context and results.fidelity_context.get("samples"):
            samples = results.fidelity_context["samples"]
            # On n'a pas les timestamp individuels dans CalculatedResults; on met un placeholder si indisponible
            for i, val in enumerate(samples):
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(i)))
                self.table.setItem(row, 1, QTableWidgetItem(f"{val:.6f}"))
                self.table.setItem(row, 2, QTableWidgetItem(results.fidelity_context.get("timestamp", "—")))

            mean_mm = results.fidelity_context.get("mean_mm")
            std_mm = results.fidelity_context.get("std_mm")
            # Afficher la moyenne des écarts (mesuré − cible), pas la moyenne brute des mesures
            target_mm = results.fidelity_context.get("target_mm")
            if target_mm is None and results.total_error_location:
                target_mm = results.total_error_location.get("target_mm")
            if mean_mm is not None and target_mm is not None:
                mean_err = mean_mm - float(target_mm)
            else:
                mean_err = None
            dispersion = "dispersion faible" if (std_mm is not None and std_mm < 0.001) else "dispersion élevée"
            if mean_err is not None and std_mm is not None:
                self.lbl_stats.setText(
                    f"Moyenne des écarts: {mean_err:+.6f} mm ({mean_err*1000.0:+.1f} µm) ; "
                    f"Écart-type (σ): {std_mm:.6f} mm ({std_mm*1000.0:.1f} µm) — {dispersion}"
                )
            elif std_mm is not None:
                self.lbl_stats.setText(
                    f"Écart-type (σ): {std_mm:.6f} mm ({std_mm*1000.0:.1f} µm) — {dispersion}"
                )
            else:
                self.lbl_stats.setText("Statistiques indisponibles.")
        else:
            self.lbl_stats.setText(
                "La série de cinq mesures successives n’a pas été réalisée. "
                "Utiliser le bouton ‘Aller à la Session’ pour compléter la campagne."
            )

        # Tolérance Ef si dispo
        if verdict and verdict.rule and ("Ef" in verdict.limits):
            lim = verdict.limits["Ef"]
            ef = results.fidelity_std_mm
            if ef is None:
                self.lbl_tol.setText(f"Limite de fidélité (Ef): {lim:.6f} mm ({lim*1000.0:.1f} µm) — mesure indisponible.")
            else:
                dep = ef - lim
                extra = f" (dépassement {dep:.6f} mm / {dep*1000.0:.1f} µm)" if dep > 1e-9 else ""
                self.lbl_tol.setText(
                    f"Limite de fidélité (Ef): {lim:.6f} mm ({lim*1000.0:.1f} µm) — "
                    f"mesuré: {ef:.6f} mm ({ef*1000.0:.1f} µm){extra}"
                )
        else:
            self.lbl_tol.setText("Aucune limite de fidélité (Ef) applicable ou règles absentes.")

        # Mémoriser contexte critique pour une éventuelle capture
        if results.total_error_location:
            self._crit_target = float(results.total_error_location.get("target_mm"))
            self._crit_dir = str(results.total_error_location.get("direction"))
            self.btn_start.setEnabled(True)
        else:
            self._crit_target = None
            self._crit_dir = None
            self.btn_start.setEnabled(False)

    # ----- Capture 5 mesures -----
    def _start_capture(self):
        if not self._crit_target or not self._crit_dir:
            self.lbl_stats.setText("Point critique indisponible — compléter les séries 1 à 4.")
            return
        self._samples.clear()
        self._timestamps.clear()
        self.table.setRowCount(0)
        self._capturing = True
        self._last_sample_val = None
        self._last_sample_ts = 0.0
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        try:
            serial_manager.line_received.connect(self._on_line)
        except Exception:
            pass
        self.lbl_stats.setText("Acquisition en cours: enregistrez 5 mesures successives (point critique).")
        self._update_sequence_status()

    def _stop_capture(self):
        self._capturing = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        try:
            serial_manager.line_received.disconnect(self._on_line)
        except Exception:
            pass

    def _clear_samples(self):
        self._samples.clear()
        self._timestamps.clear()
        self._last_sample_val = None
        self._last_sample_ts = 0.0
        self.table.setRowCount(0)
        self.lbl_stats.setText("—")
        self._update_sequence_status()

    def _on_line(self, raw: str, value: float | None):
        if not self._capturing or value is None:
            return
        # Enregistrer
        try:
            v = abs(float(value))
        except Exception:
            return
        # Anti-doublon: ignorer si même valeur reçue dans une petite fenêtre temporelle
        now = time.perf_counter()
        if self._last_sample_val is not None:
            if abs(v - float(self._last_sample_val)) <= 1e-6 and (now - self._last_sample_ts) < self._dedup_window_s:
                return
        self._last_sample_val = v
        self._last_sample_ts = now
        self._samples.append(v)
        from datetime import datetime
        self._timestamps.append(datetime.utcnow().isoformat())
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(row)))
        self.table.setItem(row, 1, QTableWidgetItem(f"{v:.6f}"))
        self.table.setItem(row, 2, QTableWidgetItem(self._timestamps[-1]))
        # Son bref à chaque mesure
        try:
            from ..sound import play_beep as _play_beep
            _play_beep()
        except Exception:
            try:
                QGuiApplication.beep()
            except Exception:
                pass
        self._update_sequence_status()
        if len(self._samples) >= 5:
            self._stop_capture()
            # Injecter dans le calcul
            try:
                rt = self.get_runtime_session()
                _, results, verdict = self.provider.compute_with_fidelity(
                    rt,
                    target_mm=float(self._crit_target),
                    direction=str(self._crit_dir),
                    samples_mm=list(self._samples[:5]),
                    timestamps_iso=list(self._timestamps[:5]),
                )
                # Mémoriser S5 pour que Finalisation l'intègre également
                try:
                    self.provider.remember_fidelity(
                        comparator_ref=getattr(rt, "comparator_ref", None),
                        target_mm=float(self._crit_target),
                        direction=str(self._crit_dir),
                        samples_mm=list(self._samples[:5]),
                        timestamps_iso=list(self._timestamps[:5]),
                    )
                    # Persister dans la session runtime pour sauvegarde
                    try:
                        session_store.set_fidelity(
                            target=float(self._crit_target),
                            direction=str(self._crit_dir),
                            samples=list(self._samples[:5]),
                            timestamps=list(self._timestamps[:5]),
                        )
                    except Exception:
                        pass
                except Exception:
                    pass
                # Mettre à jour stats/limites comme dans refresh()
                if results.fidelity_context and results.fidelity_context.get("samples"):
                    samples = results.fidelity_context["samples"]
                    mean_mm = results.fidelity_context.get("mean_mm")
                    std_mm = results.fidelity_context.get("std_mm")
                    target_mm = results.fidelity_context.get("target_mm", self._crit_target)
                    mean_err = None
                    if mean_mm is not None and target_mm is not None:
                        mean_err = mean_mm - float(target_mm)
                    dispersion = "dispersion faible" if (std_mm is not None and std_mm < 0.001) else "dispersion élevée"
                    if mean_err is not None and std_mm is not None:
                        self.lbl_stats.setText(
                            f"Moyenne des écarts: {mean_err:+.6f} mm ({mean_err*1000.0:+.1f} µm) ; "
                            f"Écart-type (σ): {std_mm:.6f} mm ({std_mm*1000.0:.1f} µm) — {dispersion}"
                        )
                    elif std_mm is not None:
                        self.lbl_stats.setText(
                            f"Écart-type (σ): {std_mm:.6f} mm ({std_mm*1000.0:.1f} µm) — {dispersion}"
                        )
                    else:
                        self.lbl_stats.setText("Statistiques indisponibles.")
                if verdict and verdict.rule and ("Ef" in verdict.limits):
                    lim = verdict.limits["Ef"]
                    ef = results.fidelity_std_mm
                    if ef is None:
                        self.lbl_tol.setText(f"Limite de fidélité (Ef): {lim:.6f} mm ({lim*1000.0:.1f} µm) — mesure indisponible.")
                    else:
                        dep = ef - lim
                        extra = f" (dépassement {dep:.6f} mm / {dep*1000.0:.1f} µm)" if dep > 1e-9 else ""
                        self.lbl_tol.setText(
                            f"Limite de fidélité (Ef): {lim:.6f} mm ({lim*1000.0:.1f} µm) — "
                            f"mesuré: {ef:.6f} mm ({ef*1000.0:.1f} µm){extra}"
                        )
                self._update_sequence_status(done=True)
            except Exception:
                pass

    def _update_sequence_status(self, done: bool = False):
        total = len(self._samples)
        remain = max(0, 5 - total)
        tgt = self._crit_target
        direc = self._crit_dir
        if tgt and direc:
            state = "terminée" if done or total >= 5 else "en cours"
            self.lbl_sequence.setText(
                f"Série 5 — {state}\n"
                f"• Cible: {tgt:.3f} mm\n"
                f"• Sens: {direc}\n"
                f"• Progression: {total}/5 (reste {remain})"
            )
        else:
            self.lbl_sequence.setText("Série 5 — Indisponible\nCompléter les séries 1 à 4.")
