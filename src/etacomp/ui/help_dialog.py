from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional, List, Tuple, Dict

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QAction, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QToolBar, QLineEdit, QLabel,
    QPushButton, QFileDialog, QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem,
    QTextBrowser, QWidget
)
from PySide6.QtGui import QDesktopServices

from ..config.prefs import load_prefs, save_prefs


# Regex pour extraire les titres Markdown
HEADING_RX = re.compile(r'^(#{1,3})\s+(.*)$', re.MULTILINE)


def slugify(text: str, used: Dict[str, int]) -> str:
    """Génère un slug unique à partir d'un titre."""
    # Supprimer les accents
    base = unicodedata.normalize('NFKD', text)
    base = ''.join(ch for ch in base if not unicodedata.combining(ch))
    # Garder seulement lettres, chiffres, espaces et tirets
    base = re.sub(r'[^a-zA-Z0-9\s-]', '', base).strip().lower()
    # Remplacer espaces et tirets multiples par un seul tiret
    slug = re.sub(r'[\s_-]+', '-', base)
    if not slug:
        slug = 'section'
    
    # Gérer l'unicité
    if slug in used:
        used[slug] += 1
        slug = f"{slug}-{used[slug]}"
    else:
        used[slug] = 1
    return slug


def build_toc_and_slugs(md_text: str) -> List[Dict]:
    """Construit la table des matières avec des slugs uniques."""
    used: Dict[str, int] = {}
    toc = []
    
    for match in HEADING_RX.finditer(md_text):
        level = len(match.group(1))
        title = match.group(2).strip()
        # Utiliser la même logique que Qt pour générer les ancres
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)  # Supprimer caractères spéciaux
        slug = re.sub(r'[-\s]+', '-', slug)   # Remplacer espaces/tirets par un seul tiret
        slug = slug.strip('-')                 # Supprimer tirets en début/fin
        if not slug:
            slug = 'section'
        
        # Gérer l'unicité
        if slug in used:
            used[slug] += 1
            slug = f"{slug}-{used[slug]}"
        else:
            used[slug] = 1
            
        toc.append({"level": level, "title": title, "slug": slug})
    
    return toc


def md_to_html_with_anchors(md_text: str, toc: List[Dict]) -> str:
    """Convertit Markdown en HTML - Qt génère déjà les ancres automatiquement."""
    doc = QTextDocument()
    doc.setMarkdown(md_text)
    return doc.toHtml()


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Documentation EtaComp")
        self.resize(1200, 800)

        self._prefs = load_prefs()
        self._default_md_path = Path("src/etacomp/resources/help/aid.md")
        self._current_path: Optional[Path] = None
        self._last_search: str = getattr(getattr(self._prefs, "help", {}), "last_search", "") if hasattr(self._prefs, "help") else ""
        self._last_anchor: str = getattr(getattr(self._prefs, "help", {}), "last_anchor", "") if hasattr(self._prefs, "help") else ""
        
        # Variables pour la recherche
        self._search_positions: List[int] = []
        self._current_search_index = 0
        self._highlight_format = QTextCharFormat()
        self._highlight_format.setBackground(Qt.GlobalColor.yellow)
        
        # Table des matières
        self._toc: List[Dict] = []

        root = QVBoxLayout(self)

        # Barre d'outils
        self.toolbar = QToolBar()
        root.addWidget(self.toolbar)

        # Recherche améliorée
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Rechercher (Ctrl+F)")
        self.search_edit.setText(self._last_search)
        self.search_count = QLabel("")
        self.btn_prev = QPushButton("Précédent")
        self.btn_next = QPushButton("Suivant")
        self.btn_clear = QPushButton("Effacer")
        self.btn_reload = QPushButton("Recharger")
        self.btn_print = QPushButton("Imprimer…")
        self.btn_export = QPushButton("Exporter PDF…")

        self.toolbar.addWidget(self.search_edit)
        self.toolbar.addWidget(self.search_count)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.btn_prev)
        self.toolbar.addWidget(self.btn_next)
        self.toolbar.addWidget(self.btn_clear)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.btn_print)
        self.toolbar.addWidget(self.btn_export)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.btn_reload)

        # Splitter principal : navigation + contenu
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(self.splitter)

        # Panneau de navigation (gauche)
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        
        nav_label = QLabel("Menu")
        nav_label.setStyleSheet("QLabel { font-weight: bold; padding: 4px; }")
        nav_layout.addWidget(nav_label)
        
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderHidden(True)
        self.toc_tree.setMaximumWidth(300)
        nav_layout.addWidget(self.toc_tree)
        
        self.splitter.addWidget(nav_widget)
        self.splitter.setSizes([250, 950])

        # Viewer Markdown (droite)
        self.viewer = QTextBrowser(self)
        self.viewer.setOpenLinks(False)
        self.viewer.setOpenExternalLinks(False)
        self.viewer.anchorClicked.connect(self._on_anchor_clicked)
        self.splitter.addWidget(self.viewer)

        # Raccourcis
        self.search_edit.returnPressed.connect(self._on_search_enter)
        self.search_edit.textChanged.connect(self._on_search_changed)
        self.btn_prev.clicked.connect(lambda: self._navigate_search(backwards=True))
        self.btn_next.clicked.connect(lambda: self._navigate_search(backwards=False))
        self.btn_clear.clicked.connect(self._clear_search)
        self.btn_print.clicked.connect(self._on_print)
        self.btn_export.clicked.connect(self._on_export_pdf)
        self.btn_reload.clicked.connect(self._on_reload)

        # Raccourcis clavier
        find_action = QAction(self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(lambda: self.search_edit.setFocus())
        self.addAction(find_action)
        
        next_action = QAction(self)
        next_action.setShortcut("F3")
        next_action.triggered.connect(lambda: self._navigate_search(backwards=False))
        self.addAction(next_action)
        
        prev_action = QAction(self)
        prev_action.setShortcut("Shift+F3")
        prev_action.triggered.connect(lambda: self._navigate_search(backwards=True))
        self.addAction(prev_action)

        # Charger contenu
        self.open()
        # Restaurer recherche/anchor
        if self._last_search:
            self._highlight_all(self._last_search)
        if self._last_anchor:
            self.goto_anchor(self._last_anchor)

    # API
    def open(self, path: Optional[Path] = None):
        p = Path(path) if path else self._default_md_path
        self._current_path = p
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            text = "# Aide introuvable\nLe fichier d'aide n'a pas été trouvé: " + str(p)
        
        # Charger directement le Markdown - Qt génère les ancres automatiquement
        self.viewer.setMarkdown(text)
        
        # Construire la table des matières à partir du texte Markdown
        self._toc = build_toc_and_slugs(text)
        
        # Construire le menu de navigation
        self._populate_toc_widget(self._toc)

    def goto_anchor(self, anchor: str):
        if not anchor:
            return
        self.viewer.scrollToAnchor(anchor)
        # Persistance
        self._last_anchor = anchor
        self._persist_prefs()

    def _populate_toc_widget(self, toc: List[Dict]):
        """Construit le menu de navigation à partir de la table des matières."""
        self.toc_tree.clear()
        
        # Stack pour gérer l'imbrication des niveaux
        parents = {1: self.toc_tree.invisibleRootItem()}
        parents[2] = None
        parents[3] = None
        
        for entry in toc:
            level = entry["level"]
            title = entry["title"]
            slug = entry["slug"]
            
            item = QTreeWidgetItem([title])
            item.setData(0, Qt.ItemDataRole.UserRole, slug)
            
            if level == 1:
                parents[1].addChild(item)
                parents[2] = item
                parents[3] = None
            elif level == 2:
                parent = parents[2] or parents[1]
                parent.addChild(item)
                parents[3] = item
            else:  # level == 3
                parent = parents[3] or parents[2] or parents[1]
                parent.addChild(item)
        
        # Développer tout par défaut
        self.toc_tree.expandAll()
        
        # Connecter le clic (pas besoin de déconnecter car on vient de clear())
        self.toc_tree.itemClicked.connect(self._on_toc_item_clicked)

    def _highlight_all(self, term: str):
        """Surligne toutes les occurrences du terme."""
        if not term.strip():
            self._clear_highlights()
            return
            
        # Effacer les surlignages précédents
        self._clear_highlights()
        
        # Trouver toutes les occurrences
        document = self.viewer.document()
        cursor = QTextCursor(document)
        self._search_positions = []
        
        while True:
            cursor = document.find(term, cursor, QTextDocument.FindFlag.FindCaseSensitively)
            if cursor.isNull():
                break
            self._search_positions.append(cursor.position())
            cursor.setCharFormat(self._highlight_format)
        
        # Mettre à jour le compteur
        total = len(self._search_positions)
        if total > 0:
            self._current_search_index = 0
            self.search_count.setText(f" {self._current_search_index + 1}/{total} occurrence(s)")
            self.btn_prev.setEnabled(True)
            self.btn_next.setEnabled(True)
        else:
            self.search_count.setText(" 0 occurrence(s)")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)

    def _clear_highlights(self):
        """Efface tous les surlignages."""
        document = self.viewer.document()
        cursor = QTextCursor(document)
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())
        self._search_positions = []
        self._current_search_index = 0
        self.search_count.setText("")
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)

    def _navigate_search(self, backwards: bool = False):
        """Navigue vers l'occurrence suivante/précédente."""
        if not self._search_positions:
            return
            
        if backwards:
            self._current_search_index = (self._current_search_index - 1) % len(self._search_positions)
        else:
            self._current_search_index = (self._current_search_index + 1) % len(self._search_positions)
        
        # Aller à la position
        pos = self._search_positions[self._current_search_index]
        cursor = QTextCursor(self.viewer.document())
        cursor.setPosition(pos)
        self.viewer.setTextCursor(cursor)
        self.viewer.ensureCursorVisible()
        
        # Mettre à jour le compteur
        total = len(self._search_positions)
        self.search_count.setText(f" {self._current_search_index + 1}/{total} occurrence(s)")

    # Slots
    def _on_anchor_clicked(self, url: QUrl):
        """Gère les clics sur les liens dans le document."""
        if url.isEmpty():
            return
            
        # Liens externes (http/https)
        if url.scheme() in ("http", "https"):
            QDesktopServices.openUrl(url)
            return
            
        # Ancres internes (#slug)
        fragment = url.fragment()
        if fragment:
            self.goto_anchor(fragment)
            return
            
        # Liens relatifs vers d'autres fichiers (optionnel)
        if url.isRelative() or url.scheme() == "file":
            # Pour l'instant, on ne gère que les ancres
            pass

    def _on_toc_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Slot appelé quand on clique sur un élément de la table des matières."""
        slug = item.data(0, Qt.ItemDataRole.UserRole)
        if slug:
            self.goto_anchor(slug)

    def _on_search_enter(self):
        """Slot appelé quand on appuie sur Entrée dans le champ de recherche."""
        term = self.search_edit.text().strip()
        if term:
            self._highlight_all(term)
            self._last_search = term
            self._persist_prefs()

    def _on_search_changed(self, text: str):
        """Slot appelé quand le texte de recherche change."""
        if not text.strip():
            self._clear_highlights()
        else:
            self._highlight_all(text)

    def _clear_search(self):
        """Efface la recherche et les surlignages."""
        self.search_edit.clear()
        self._clear_highlights()
        self._last_search = ""
        self._persist_prefs()

    def _on_print(self):
        try:
            self.viewer.print()
        except Exception:
            # Fallback via QPrinter
            printer = QPrinter(QPrinter.HighResolution)
            self.viewer.document().print(printer)

    def _on_export_pdf(self):
        file, _ = QFileDialog.getSaveFileName(self, "Exporter en PDF", "aide.pdf", "PDF (*.pdf)")
        if not file:
            return
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(file)
        self.viewer.document().print(printer)
        QMessageBox.information(self, "Export", f"Fichier exporté:\n{file}")

    def _on_reload(self):
        self.open(self._current_path)
        if self._last_anchor:
            self.viewer.scrollToAnchor(self._last_anchor)
        if self._last_search:
            self._highlight_all(self._last_search)

    def _persist_prefs(self):
        p = self._prefs.model_copy(deep=True)
        help_obj = getattr(p, "help", None) or {}
        # Construire un dict minimal
        help_obj = {
            "last_anchor": self._last_anchor,
            "last_search": self._last_search,
        }
        # Injecter dans le JSON final
        data = p.model_dump()
        data.setdefault("help", {})
        data["help"].update(help_obj)
        # Écrire
        from ..config.prefs import Preferences
        self._prefs = Preferences.model_validate(data)
        save_prefs(self._prefs)


