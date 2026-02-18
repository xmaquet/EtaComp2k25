"""Export PDF — rapport de vérification EtaComp2K25."""
from __future__ import annotations

import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

if TYPE_CHECKING:
    from ..config.export_config import ExportConfig
    from ..core.calculation_engine import CalculatedResults
    from ..rules.verdict import Verdict

# Marges
MARGIN_LR = 15 * mm
MARGIN_TB = 12 * mm
PAGE_W, PAGE_H = A4
CONTENT_W = PAGE_W - 2 * MARGIN_LR
CONTENT_H = PAGE_H - 2 * MARGIN_TB


def _none_str(val: Any) -> str:
    """Retourne '—' si val est None ou vide."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return "—"
    return str(val).strip()


def draw_block_title(canvas_obj, x: float, y: float, w: float, title: str) -> float:
    """Dessine le titre d'un bloc. Retourne la hauteur utilisée."""
    canvas_obj.setFont("Helvetica-Bold", 9)
    canvas_obj.drawString(x, y, title)
    return 5 * mm


def draw_kv_table(
    canvas_obj,
    x: float,
    y: float,
    w: float,
    rows: List[tuple],
    col_ratio: float = 0.4,
    label_width_mm: Optional[float] = None,
) -> float:
    """
    Dessine un tableau label/valeur. rows = [(label, value), ...]
    Si label_width_mm est fourni, les valeurs sont alignées à x + label_width_mm.
    Retourne la hauteur totale utilisée.
    """
    line_h = 4.5 * mm
    if label_width_mm is not None:
        w1 = label_width_mm * mm
    else:
        w1 = w * col_ratio
    canvas_obj.setFont("Helvetica", 8)
    val_w_max = w - w1 if w > w1 else 30 * mm  # largeur disponible pour la valeur
    for i, (label, value) in enumerate(rows):
        canvas_obj.drawString(x, y - i * line_h, _none_str(label))
        raw = _none_str(value) if value is not None else "—"
        val_str = str(raw)
        # Tronquer la valeur si elle dépasse la largeur disponible
        while val_str and canvas_obj.stringWidth(val_str, "Helvetica", 8) > val_w_max:
            val_str = val_str[:-1]
        if not val_str and raw != "—":
            val_str = "…"
        canvas_obj.drawString(x + w1, y - i * line_h, val_str or "—")
    return len(rows) * line_h


def draw_paragraph(
    canvas_obj,
    x: float,
    y: float,
    w: float,
    text: str,
    font_size: int = 8,
) -> float:
    """Dessine un paragraphe avec wrap. Retourne la hauteur utilisée."""
    if not text or not text.strip():
        return 0
    line_h = font_size * 0.4 * mm
    words = text.split()
    lines = []
    current = []
    for word in words:
        test = " ".join(current + [word])
        if canvas_obj.stringWidth(test, "Helvetica", font_size) <= w:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    canvas_obj.setFont("Helvetica", font_size)
    for i, line in enumerate(lines):
        canvas_obj.drawString(x, y - i * line_h, line[:150])
    return len(lines) * line_h


def add_plot_image(
    canvas_obj,
    x: float,
    y: float,
    w: float,
    h: float,
    png_bytes: bytes,
) -> None:
    """Insère une image PNG (bytes) dans le canvas (transparence préservée si présente)."""
    from reportlab.lib.utils import ImageReader
    buf = io.BytesIO(png_bytes)
    img = ImageReader(buf)
    canvas_obj.drawImage(img, x, y - h, width=w, height=h, mask="auto")


def _build_error_plot_png(
    calibration_points: List[Dict],
    emt_limit_mm: Optional[float] = None,
    width_inch: float = 5.0,
    height_inch: float = 2.5,
    dpi: int = 150,
) -> bytes:
    """Génère le graphique des erreurs en PNG (bytes)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not calibration_points:
        # Graphique vide minimal
        calibration_points = [{"target_mm": 0, "up_error_mm": 0, "down_error_mm": 0}]

    xs = [p["target_mm"] for p in calibration_points]
    up_err = [
        (p["up_error_mm"] * 1000.0) if p.get("up_error_mm") is not None else float("nan")
        for p in calibration_points
    ]
    down_err = [
        (p["down_error_mm"] * 1000.0) if p.get("down_error_mm") is not None else float("nan")
        for p in calibration_points
    ]

    fig, ax = plt.subplots(figsize=(width_inch, height_inch), dpi=dpi)
    ax.plot(xs, up_err, "o-", label="Montée (µm)", markersize=4)
    ax.plot(xs, down_err, "s-", label="Descente (µm)", markersize=4)
    ax.axhline(0.0, color="gray", linewidth=0.8, linestyle="--")
    if emt_limit_mm is not None and emt_limit_mm > 0:
        emt_um = emt_limit_mm * 1000.0
        ax.axhline(emt_um, color="red", linewidth=0.6, linestyle=":")
        ax.axhline(-emt_um, color="red", linewidth=0.6, linestyle=":")
    ax.set_ylabel("Erreur (µm)")
    ax.set_xlabel("Cible (mm)")
    ax.legend(loc="best", fontsize=7)
    ax.tick_params(axis="both", labelsize=7)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _get_detenteur_display(holder_ref: Optional[str]) -> str:
    """Retourne 'code_es — libellé' ou '—'."""
    if not holder_ref or not str(holder_ref).strip():
        return "—"
    from ..io.storage import list_detenteurs
    code = str(holder_ref).strip().upper()
    for d in list_detenteurs():
        if d.code_es.strip().upper() == code:
            return d.display_name()
    return str(holder_ref)


def export_pdf(
    rt_session: Any,
    export_config: "ExportConfig",
    results: "CalculatedResults",
    verdict: Optional["Verdict"],
    doc_no: int,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Exporte un rapport de vérification PDF.

    Args:
        rt_session: Session runtime (SessionStore.current)
        export_config: Configuration export (entité, image, etc.)
        results: Résultats calculés (CalculatedResults)
        verdict: Verdict tolérances ou None
        doc_no: Numéro d'ordre du document (saisi par l'utilisateur)
        output_path: Chemin de sortie optionnel

    Returns:
        Chemin du fichier PDF généré
    """
    from ..config.paths import get_data_dir
    from ..core.session_adapter import build_session_from_runtime
    from ..io.storage import get_default_banc_etalon, list_comparators

    logger.info("Export PDF : construction SessionV2")
    v2 = build_session_from_runtime(rt_session)
    now = datetime.now()
    doc_ref = f"CV{now.strftime('%y%m%d')}-{doc_no:02d}"
    logger.info("Export PDF : n° document %s", doc_ref)

    # Chemin de sortie
    if output_path is None:
        exports_dir = get_data_dir() / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        comp_ref = _none_str(rt_session.comparator_ref).replace(" ", "_") or "sans_ref"
        ts = now.strftime("%Y%m%d_%H%M%S")
        output_path = exports_dir / f"{comp_ref}_{ts}_{doc_ref}.pdf"

    logger.info("Export PDF : écriture vers %s", output_path)
    c = canvas.Canvas(str(output_path), pagesize=A4)
    c.setTitle(export_config.document_title or "Rapport de vérification")

    # Y courant (coordonnée reportlab : bas = 0)
    y = PAGE_H - MARGIN_TB
    block_gap = 4 * mm
    pad = 3 * mm

    # ---- A. CARTOUCHE TITRE ----
    c.setFillColor(colors.HexColor("#e8e8e8"))
    c.rect(MARGIN_LR, y - 25 * mm, CONTENT_W, 25 * mm, fill=1, stroke=1)
    c.setFillColor(colors.black)

    # Logo à gauche (transparence PNG préservée si présente)
    img_path = (export_config.image_path or "").strip()
    if img_path:
        try:
            p = Path(img_path)
            if p.exists():
                from reportlab.lib.utils import ImageReader
                with open(p, "rb") as f:
                    logo = ImageReader(f)
                c.drawImage(
                    logo, MARGIN_LR + pad, y - 22 * mm,
                    width=18 * mm, height=18 * mm,
                    mask="auto",
                )
        except Exception:
            pass

    # Titre
    c.setFont("Helvetica-Bold", 16)
    c.drawString(MARGIN_LR + 22 * mm, y - 8 * mm, _none_str(export_config.document_title))
    c.setFont("Helvetica", 9)
    if export_config.entite:
        c.drawString(MARGIN_LR + 22 * mm, y - 12 * mm, _none_str(export_config.entite))

    y -= 30 * mm

    # ---- B. CARTOUCHE SESSION (2 colonnes) ----
    comp = None
    comp_ref = getattr(rt_session, "comparator_ref", None)
    if comp_ref:
        for c_obj in list_comparators():
            if c_obj.reference == comp_ref:
                comp = c_obj
                break

    range_val = getattr(comp, "range_type", None) if comp else None
    family = getattr(range_val, "value", str(range_val)) if range_val else "—"
    period = getattr(comp, "periodicite_controle_mois", 12) if comp else 12
    session_date = getattr(rt_session, "date", None) or now
    if hasattr(session_date, "strftime"):
        session_dt = session_date
    else:
        session_dt = now
    try:
        if isinstance(session_dt, str):
            session_dt = datetime.fromisoformat(session_dt.replace("Z", "+00:00"))
        elif hasattr(session_dt, "replace"):
            session_dt = session_dt.replace(tzinfo=None) if session_dt.tzinfo else session_dt
    except Exception:
        session_dt = now
    next_check_str = "—"
    try:
        from datetime import date
        d = session_dt.date() if hasattr(session_dt, "date") else (session_dt if isinstance(session_dt, date) else now.date())
        year, month = d.year, d.month
        month += period
        while month > 12:
            month -= 12
            year += 1
        day = min(d.day, 28)  # éviter dépassement selon mois
        next_check_str = f"{day:02d}/{month:02d}/{year}"
    except Exception:
        pass

    banc = get_default_banc_etalon()
    banc_ref_session = getattr(rt_session, "banc_ref", None)
    banc_display = _none_str(banc_ref_session) if banc_ref_session else (banc.reference if banc else "—")

    rows_left = [
        ("Référence comparateur", comp_ref),
        ("Famille", family),
        ("Marque / Fabricant", getattr(comp, "manufacturer", None) if comp else None),
        ("Course (mm)", f"{comp.course:.2f}" if comp else "—"),
        ("Périodicité contrôle (mois)", str(period) if comp else "—"),
        ("Date prochaine vérif.", next_check_str),
    ]
    rows_right = [
        ("Température (°C)", getattr(rt_session, "temperature_c", None)),
        ("Détenteur", _get_detenteur_display(getattr(rt_session, "holder_ref", None))),
        ("Référence étalon", banc_display),
        ("Humidité (%)", getattr(rt_session, "humidity_pct", None)),
    ]

    # Alignement fixe : label 40 mm pour colonnes gauche et droite (valeurs alignées)
    label_w_mm = 40
    half_w = CONTENT_W / 2 - pad
    h1 = draw_kv_table(c, MARGIN_LR + pad, y, half_w, rows_left, label_width_mm=label_w_mm)
    draw_kv_table(c, MARGIN_LR + CONTENT_W / 2 + 4 * mm, y, half_w - 4 * mm, rows_right, label_width_mm=label_w_mm)
    block_h_b = max(h1, 4 * len(rows_right) * mm) + 10 * mm
    y -= block_h_b
    c.rect(MARGIN_LR, y, CONTENT_W, block_h_b, fill=0, stroke=1)
    y -= block_gap

    # ---- C. BLOC COURBES D'ERREUR ----
    emt_limit = None
    if verdict and verdict.limits and "Emt" in verdict.limits:
        emt_limit = verdict.limits["Emt"]
    plot_png = _build_error_plot_png(
        results.calibration_points or [],
        emt_limit_mm=emt_limit,
        width_inch=5.0,
        height_inch=2.5,
        dpi=150,
    )
    plot_h = 45 * mm
    plot_w = min(CONTENT_W, 130 * mm)

    block_c_h = 6 * mm + plot_h + 6 * mm
    draw_block_title(c, MARGIN_LR, y, CONTENT_W, "Courbe des erreurs")
    y -= 6 * mm
    add_plot_image(c, MARGIN_LR, y, plot_w, plot_h, plot_png)
    c.setFont("Helvetica", 7)
    c.drawString(MARGIN_LR, y - plot_h - 4 * mm, "Montée (•) / Descente (■) — Erreur en µm")
    y -= plot_h + 6 * mm
    c.rect(MARGIN_LR, y, CONTENT_W, block_c_h, fill=0, stroke=1)
    y -= block_gap

    # ---- D. BLOC PLACEHOLDER ----
    block_d_h = 18 * mm
    draw_block_title(c, MARGIN_LR, y, CONTENT_W, "Bloc complémentaire (à définir)")
    y -= 5 * mm
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN_LR + pad, y, "TODO")
    y -= 10 * mm
    c.rect(MARGIN_LR, y, CONTENT_W, block_d_h, fill=0, stroke=1)
    y -= block_gap

    # ---- E. BLOC OBSERVATIONS ----
    obs = getattr(rt_session, "observations", None) or getattr(v2, "notes", None) or ""
    obs_str = _none_str(obs)
    draw_block_title(c, MARGIN_LR, y, CONTENT_W, "Observations")
    y -= 5 * mm
    h_obs = draw_paragraph(c, MARGIN_LR + pad, y, CONTENT_W - 2 * pad, obs_str)
    block_e_h = 5 * mm + max(h_obs, 5 * mm) + pad
    y -= max(h_obs, 5 * mm)
    c.rect(MARGIN_LR, y, CONTENT_W, block_e_h, fill=0, stroke=1)
    y -= block_gap

    # ---- F. BLOC VERDICT ----
    status = "Indéterminé"
    if verdict:
        if verdict.status.value == "apte":
            status = "Conforme"
        elif verdict.status.value == "inapte":
            status = "Non-conforme"

    y -= 8 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN_LR + pad, y, f"Appareil : {status}")
    block_f_h = 20 * mm
    y -= 8 * mm
    c.rect(MARGIN_LR, y, CONTENT_W, block_f_h, fill=0, stroke=1)
    y -= block_gap

    # ---- G. BLOC SIGNATURE (op+date à gauche, zone blanche à droite pour signature) ----
    op = _none_str(getattr(rt_session, "operator", None))
    date_str = session_dt.strftime("%d/%m/%Y") if hasattr(session_dt, "strftime") else "—"
    y -= 3 * mm
    c.setFont("Helvetica", 9)
    line_y = y
    c.drawString(MARGIN_LR + pad, line_y, f"Opérateur : {op}")
    c.drawString(MARGIN_LR + pad, line_y - 5 * mm, f"Date vérification : {date_str}")
    block_g_h = 18 * mm
    y -= block_g_h
    c.rect(MARGIN_LR, y, CONTENT_W, block_g_h + 5 * mm, fill=0, stroke=1)
    y -= block_gap

    # ---- H. BLOC NORMES (texte en pleine largeur) ----
    normes = _none_str(export_config.texte_normes)
    draw_block_title(c, MARGIN_LR, y, CONTENT_W, "Références / Normes")
    y -= 5 * mm
    h_norm = draw_paragraph(c, MARGIN_LR, y, CONTENT_W, normes)
    block_h_h = 5 * mm + max(h_norm, 8 * mm) + pad
    y -= max(h_norm, 8 * mm)
    c.rect(MARGIN_LR, y, CONTENT_W, block_h_h, fill=0, stroke=1)

    # Vérifier si débordement page 2
    if y < MARGIN_TB + 20 * mm and h_norm > 30 * mm:
        c.showPage()
        c.setFont("Helvetica", 8)
        c.drawString(MARGIN_LR, PAGE_H - MARGIN_TB, f"{doc_ref} | {_none_str(comp_ref)} | {date_str}")
        y = PAGE_H - MARGIN_TB - 15 * mm
        draw_paragraph(c, MARGIN_LR, y, CONTENT_W, normes if normes != "—" else "—")
        c.rect(MARGIN_LR, y - 10 * mm, CONTENT_W, 40 * mm, fill=0, stroke=1)

    c.save()
    logger.info("Export PDF : terminé")
    return Path(output_path)


def _cli_last_session() -> None:
    """CLI : export avec la dernière session du disque (test manuel)."""
    import sys
    from ..config.export_config import load_export_config
    from ..core.session_adapter import build_session_from_runtime
    from ..core.calculation_engine import CalculationEngine
    from ..io.storage import list_sessions, load_session_file
    from ..rules.tolerance_engine import ToleranceRuleEngine
    from ..rules.verdict import evaluate_tolerances
    from ..rules.tolerances import get_default_rules_path

    sessions = list_sessions()
    if not sessions:
        print("Aucune session enregistrée. Enregistrez une session depuis l'application.")
        sys.exit(1)
    rt = load_session_file(sessions[0])
    if not rt.has_measures():
        print("Dernière session sans mesures.")
        sys.exit(1)

    v2 = build_session_from_runtime(rt)
    engine = CalculationEngine()
    results = engine.compute(v2)
    verdict = None
    rules_path = get_default_rules_path()
    if rules_path.exists():
        try:
            tol_engine = ToleranceRuleEngine.load(rules_path)
            verdict = evaluate_tolerances(v2.comparator_snapshot or {}, results, tol_engine)
        except Exception:
            pass

    export_config = load_export_config()

    path = export_pdf(rt, export_config, results, verdict, doc_no=1)
    print(f"PDF généré : {path}")


def main() -> None:
    """Point d'entrée CLI pour test manuel."""
    import sys
    if "--last-session" in sys.argv:
        _cli_last_session()
    else:
        print("Usage: python -m etacomp.io.pdf_exporter --last-session")


if __name__ == "__main__":
    main()
