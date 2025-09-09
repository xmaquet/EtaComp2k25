# src/etacomp/ui/themes.py
from __future__ import annotations

ACCENT = "#0ea5b7"  # couleur d’accent par défaut

BASE_QSS = f"""
/* --------- Onglets --------- */
QTabWidget::pane {{
    border: 0;
}}
QTabBar::tab {{
    padding: 8px 14px;
    margin: 0 2px;
    border: 1px solid transparent;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}
QTabBar::tab:hover {{
    color: #ffffff;
}}
QTabBar::tab:selected {{
    background: {ACCENT};
    color: white;
    border: 1px solid {ACCENT};
    border-bottom: 3px solid #ffffff; /* soulignement visible */
}}

/* --------- Titres de zones (QGroupBox) --------- */
QGroupBox {{
    border: 1px solid VAR_BORDER;
    border-radius: 10px;
    margin-top: 18px;
    padding-top: 16px;
    background: VAR_PANEL_BG;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 3px 10px;
    background: {ACCENT};
    color: white;
    font-weight: 700;
    letter-spacing: 0.4px;
    border-radius: 6px;
}}
QGroupBox::title:hover {{
    background: #10b6ca;
}}

/* --------- SectionHeader (widget optionnel) --------- */
#SectionHeaderLabel {{
    font-size: 14pt;
    font-weight: 800;
    color: #ffffff;
    padding: 2px 8px;
    border-radius: 6px;
    background: {ACCENT};
}}
#SectionHeaderLine {{
    min-height: 2px;
    background: VAR_SEP;
}}

/* --------- Boutons/Entrées (un léger lifting) --------- */
QPushButton {{
    padding: 6px 12px;
    border-radius: 8px;
    border: 1px solid VAR_BORDER;
    background: VAR_BTN_BG;
    color: VAR_FG;
}}
QPushButton:hover {{
    background: VAR_BTN_HOVER;
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    border: 1px solid VAR_BORDER;
    border-radius: 6px;
    padding: 4px 6px;
    background: VAR_INPUT_BG;
    color: VAR_FG;
}}
QLabel {{
    color: VAR_FG;
}}
"""

def _qss_dark() -> str:
    return (BASE_QSS
            .replace("VAR_BORDER", "#3a3a3a")
            .replace("VAR_PANEL_BG", "#232323")
            .replace("VAR_SEP", "#404040")
            .replace("VAR_BTN_BG", "#2d2d2d")
            .replace("VAR_BTN_HOVER", "#383838")
            .replace("VAR_INPUT_BG", "#2a2a2a")
            .replace("VAR_FG", "#e6e6e6")
            )

def _qss_light() -> str:
    return (BASE_QSS
            .replace("VAR_BORDER", "#dadada")
            .replace("VAR_PANEL_BG", "#f6f6f6")
            .replace("VAR_SEP", "#d0d0d0")
            .replace("VAR_BTN_BG", "#ffffff")
            .replace("VAR_BTN_HOVER", "#f2f2f2")
            .replace("VAR_INPUT_BG", "#ffffff")
            .replace("VAR_FG", "#1f1f1f")
            )

def load_theme_qss(theme: str | None) -> str:
    """
    Retourne le QSS complet selon le thème ('dark' ou 'light').
    Si theme est None/unknown -> dark par défaut.
    """
    if (theme or "").lower() == "light":
        return _qss_light()
    return _qss_dark()

def apply_theme(widget, theme: str | None):
    """Applique le QSS sur un widget racine (ex: MainWindow)."""
    widget.setStyleSheet(load_theme_qss(theme))
