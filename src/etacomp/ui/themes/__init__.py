from __future__ import annotations

# Couleur d’accent (modifiable)
ACCENT = "#0ea5b7"

# QSS commun avec variables "placeholder" (VAR_*). Pas de f-string ici !
BASE_QSS = """
/* ====== Couleurs & bases globales ====== */
QWidget {
    color: VAR_FG;                 /* texte par défaut */
    background: VAR_WINDOW_BG;     /* fond global */
}
QMainWindow, QDialog {
    background: VAR_WINDOW_BG;
}
QTabWidget::pane {
    border: 0;
    border-top: 1px solid VAR_BORDER;    /* ligne sous la barre d'onglets */
    border-bottom: 1px solid VAR_BORDER; /* ligne en bas du contenu */
    background: VAR_WINDOW_BG;     /* fond sous les onglets */
}

/* Texte des contrôles courants */
QLabel, QCheckBox, QRadioButton, QGroupBox {
    color: VAR_FG;
}
QLabel:disabled, QCheckBox:disabled, QRadioButton:disabled {
    color: VAR_FG_DISABLED;
}
/* Indicateurs (cases à cocher / boutons radio) */
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px; height: 16px;
    border: 1px solid VAR_BORDER;
    background: VAR_INPUT_BG;
    margin-right: 6px;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background: ACCENT;
    border: 1px solid ACCENT;
}
QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
    background: VAR_INPUT_BG;
    border: 1px solid VAR_BORDER;
}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
    background: VAR_PANEL_BG;
    border: 1px solid VAR_BORDER;
}

/* ====== Onglets ====== */
QTabBar::tab {
    padding: 8px 14px;
    margin: 0 2px;
    border: 1px solid transparent;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    background: VAR_TAB_INACTIVE_BG;
    color: VAR_TAB_INACTIVE_FG;
}
/* Survol: garder un contraste net (thème-dépendant) */
QTabBar::tab:hover {
    background: VAR_TAB_HOVER_BG;
    color: VAR_TAB_HOVER_FG;
}
/* Sélectionné: pastille + soulignement fort */
QTabBar::tab:selected {
    /* Léger relief via dégradé et contour subtil */
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #10b6ca, stop:1 ACCENT);
    color: white;
    border: 1px solid ACCENT;
    border-bottom: 1px solid VAR_BORDER; /* ligne discrète en pied */
}
/* Focus clavier sur un onglet non sélectionné: fine ligne d’indication */
QTabBar::tab:!selected:focus {
    outline: none;
    border-bottom: 2px solid ACCENT;
}

/* ====== QGroupBox (titres de zones) ====== */
QGroupBox {
    border: 1px solid VAR_BORDER;
    border-radius: 10px;
    margin-top: 18px;
    padding-top: 16px;
    background: VAR_PANEL_BG;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 3px 10px;
    background: ACCENT;
    color: white;
    font-weight: 700;
    letter-spacing: 0.4px;
    border-radius: 6px;
}
QGroupBox::title:hover {
    background: #10b6ca;
}

/* ====== SectionHeader (widget optionnel) ====== */
#SectionHeaderLabel {
    font-size: 14pt;
    font-weight: 800;
    color: #ffffff;
    padding: 2px 8px;
    border-radius: 6px;
    background: ACCENT;
}
#SectionHeaderLine {
    min-height: 2px;
    background: VAR_SEP;
}

/* ====== Entrées & boutons ====== */
QPushButton {
    padding: 6px 12px;
    border-radius: 8px;
    border: 1px solid VAR_BORDER;
    background: VAR_BTN_BG;
    color: VAR_FG;
}
QPushButton:hover {
    background: VAR_BTN_HOVER;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {
    border: 1px solid VAR_BORDER;
    border-radius: 6px;
    padding: 4px 6px;
    background: VAR_INPUT_BG;
    color: VAR_FG;
}

/* ====== Tableaux / Listes ====== */
QHeaderView::section {
    background: VAR_PANEL_BG;
    color: VAR_FG;
    border: 1px solid VAR_BORDER;
    padding: 4px 6px;
}
QTableView, QTreeView {
    background: VAR_PANEL_BG;
    color: VAR_FG;
    gridline-color: VAR_BORDER;
    alternate-background-color: VAR_ALT_ROW;
}

/* ====== Tooltips ====== */
QToolTip {
    background: VAR_PANEL_BG;
    color: VAR_FG;
    border: 1px solid VAR_BORDER;
}
"""

def _fill_common(placeholders: dict[str, str]) -> str:
    """Remplace ACCENT et les VAR_* dans BASE_QSS."""
    qss = BASE_QSS.replace("ACCENT", ACCENT)
    # Important: remplacer d'abord les clés les plus longues pour éviter
    # que "VAR_FG" ne remplace partiellement "VAR_FG_DISABLED".
    for k in sorted(placeholders.keys(), key=len, reverse=True):
        qss = qss.replace(k, placeholders[k])
    return qss

def _qss_dark() -> str:
    return _fill_common({
        "VAR_WINDOW_BG": "#1e1e1e",
        "VAR_BORDER": "#3a3a3a",
        "VAR_PANEL_BG": "#232323",
        "VAR_SEP": "#404040",
        "VAR_BTN_BG": "#2d2d2d",
        "VAR_BTN_HOVER": "#383838",
        "VAR_INPUT_BG": "#2a2a2a",
        "VAR_FG": "#e6e6e6",
        "VAR_FG_DISABLED": "#9a9a9a",
        "VAR_ALT_ROW": "#1b1b1b",
        "VAR_TAB_INACTIVE_BG": "#2b2b2b",
        "VAR_TAB_INACTIVE_FG": "#c9c9c9",
        "VAR_TAB_HOVER_BG": "#3a3a3a",
        "VAR_TAB_HOVER_FG": "#ffffff",
    })

def _qss_light() -> str:
    return _fill_common({
        "VAR_WINDOW_BG": "#ffffff",
        "VAR_BORDER": "#dadada",
        "VAR_PANEL_BG": "#f6f6f6",
        "VAR_SEP": "#d0d0d0",
        "VAR_BTN_BG": "#ffffff",
        "VAR_BTN_HOVER": "#f2f2f2",
        "VAR_INPUT_BG": "#ffffff",
        "VAR_FG": "#1f1f1f",
        "VAR_FG_DISABLED": "#8a8a8a",
        "VAR_ALT_ROW": "#fafafa",
        "VAR_TAB_INACTIVE_BG": "#efefef",
        "VAR_TAB_INACTIVE_FG": "#3a3a3a",
        "VAR_TAB_HOVER_BG": "#f5f5f5",
        "VAR_TAB_HOVER_FG": "#111111",
    })

def load_theme_qss(theme: str | None) -> str:
    """Retourne le QSS complet selon le thème ('light' ou 'dark')."""
    if (theme or "").lower() == "light":
        return _qss_light()
    return _qss_dark()

def apply_theme(widget, theme: str | None):
    """Applique le QSS sur un widget racine (ex: MainWindow)."""
    widget.setStyleSheet(load_theme_qss(theme))

__all__ = ["apply_theme", "load_theme_qss", "ACCENT"]
