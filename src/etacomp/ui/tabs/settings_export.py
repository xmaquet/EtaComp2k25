"""Onglet Paramètres > Éléments d'export : entité, image, titre, référence, texte de normes."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QFileDialog, QSizePolicy
)

from ...config.export_config import ExportConfig, load_export_config, save_export_config


class SettingsExportTab(QWidget):
    """Onglet de configuration des éléments pour les exports (PDF, etc.)."""
    export_config_changed = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        g_export = QGroupBox("Éléments pour les exports")
        g_export.setToolTip("Ces éléments seront utilisés lors de l'export PDF ou HTML des résultats de session.")
        form = QFormLayout(g_export)

        self.ed_entite = QLineEdit()
        self.ed_entite.setPlaceholderText("Ex: 14eBSMAT, Atelier de métrologie…")
        self.ed_entite.setToolTip("Nom de l'entité (organisation, service)")
        form.addRow("Entité", self.ed_entite)

        img_row = QHBoxLayout()
        self.ed_image = QLineEdit()
        self.ed_image.setPlaceholderText("Chemin vers l'image (logo, écusson)")
        self.ed_image.setReadOnly(True)
        self.btn_browse_image = QPushButton("Parcourir…")
        self.btn_browse_image.clicked.connect(self._browse_image)
        self.btn_clear_image = QPushButton("Effacer")
        self.btn_clear_image.clicked.connect(lambda: self.ed_image.setText(""))
        img_row.addWidget(self.ed_image)
        img_row.addWidget(self.btn_browse_image)
        img_row.addWidget(self.btn_clear_image)
        form.addRow("Image (logo / écusson)", img_row)

        self.lbl_image_preview = QLabel()
        self.lbl_image_preview.setMinimumHeight(60)
        self.lbl_image_preview.setMaximumHeight(120)
        self.lbl_image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image_preview.setStyleSheet("QLabel { border: 1px solid #ccc; background: #f8f8f8; }")
        self.lbl_image_preview.setText("Aperçu")
        form.addRow("Aperçu", self.lbl_image_preview)

        self.ed_document_title = QLineEdit()
        self.ed_document_title.setPlaceholderText("Ex: Rapport de vérification — Comparateur")
        self.ed_document_title.setToolTip("Titre affiché sur le document exporté")
        form.addRow("Titre du document", self.ed_document_title)

        self.ed_document_reference = QLineEdit()
        self.ed_document_reference.setPlaceholderText("Ex: EtaComp-REP-2025")
        self.ed_document_reference.setToolTip("Référence du document exporté")
        form.addRow("Référence du document", self.ed_document_reference)

        self.ed_texte_normes = QTextEdit()
        self.ed_texte_normes.setPlaceholderText(
            "Ex: Les essais ont été réalisés conformément à la norme NF EN ISO 10360-5…"
        )
        self.ed_texte_normes.setToolTip("Bloc de texte pour les normes applicables (multi-lignes)")
        self.ed_texte_normes.setMinimumHeight(80)
        self.ed_texte_normes.setMaximumHeight(150)
        form.addRow("Texte de normes", self.ed_texte_normes)

        layout.addWidget(g_export)

        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_save = QPushButton("Enregistrer")
        self.btn_save.clicked.connect(self._save)
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)

        self._load()
        self.ed_image.textChanged.connect(self._update_preview)

    def _load(self):
        cfg = load_export_config()
        self.ed_entite.setText(cfg.entite or "")
        self.ed_image.setText(cfg.image_path or "")
        self.ed_document_title.setText(cfg.document_title or "")
        self.ed_document_reference.setText(cfg.document_reference or "")
        self.ed_texte_normes.setPlainText(cfg.texte_normes or "")
        self._update_preview()

    def _update_preview(self):
        from PySide6.QtGui import QPixmap
        path = self.ed_image.text().strip()
        self.lbl_image_preview.clear()
        self.lbl_image_preview.setStyleSheet("QLabel { border: 1px solid #ccc; background: #f8f8f8; }")
        if not path:
            self.lbl_image_preview.setText("Aucune image")
            return
        p = Path(path)
        if not p.exists():
            self.lbl_image_preview.setText("Fichier introuvable")
            return
        try:
            pix = QPixmap(str(p))
            if pix.isNull():
                self.lbl_image_preview.setText("Image non lisible")
                return
            scaled = pix.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_image_preview.setPixmap(scaled)
        except Exception:
            self.lbl_image_preview.setText("Aperçu indisponible")

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir une image (logo, écusson)",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;Tous les fichiers (*)"
        )
        if path:
            self.ed_image.setText(path)

    def _save(self):
        cfg = ExportConfig(
            entite=(self.ed_entite.text() or "").strip(),
            image_path=(self.ed_image.text() or "").strip() or None,
            document_title=(self.ed_document_title.text() or "").strip(),
            document_reference=(self.ed_document_reference.text() or "").strip(),
            texte_normes=(self.ed_texte_normes.toPlainText() or "").strip(),
        )
        save_export_config(cfg)
        self.export_config_changed.emit()
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Exports", "Configuration enregistrée.")

    def refresh(self):
        self._load()
