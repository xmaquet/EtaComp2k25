"""Fenêtre de sauvegarde / restauration des données EtaComp."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config.paths import get_data_dir
from ..io.backup import (
    BACKUP_CATEGORIES,
    category_stats,
    default_backup_filename,
    export_backup,
    format_bytes,
    list_removable_mounts,
    read_manifest,
    restore_backup,
)


class BackupWindow(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Sauvegarde EtaComp")
        self.setMinimumWidth(560)
        self.setMinimumHeight(520)
        self._checkboxes: dict[str, QCheckBox] = {}
        self._mount_paths: dict[str, Path] = {}
        self._build_ui()
        self._refresh_stats()
        self._refresh_mounts()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        intro = QLabel(
            "Exportez ou restaurez les données métier EtaComp vers un support externe "
            f"({get_data_dir()})."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        dest_group = QGroupBox("Destination")
        dest_layout = QVBoxLayout(dest_group)
        row = QHBoxLayout()
        self.mount_combo = QComboBox()
        self.mount_combo.setMinimumWidth(320)
        row.addWidget(self.mount_combo, stretch=1)
        btn_refresh = QPushButton("Actualiser")
        btn_refresh.clicked.connect(self._refresh_mounts)
        row.addWidget(btn_refresh)
        btn_browse = QPushButton("Parcourir…")
        btn_browse.clicked.connect(self._browse_destination_dir)
        row.addWidget(btn_browse)
        dest_layout.addLayout(row)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Nom de l'archive :"))
        self.filename_edit = QLineEdit(default_backup_filename())
        name_row.addWidget(self.filename_edit, stretch=1)
        dest_layout.addLayout(name_row)
        layout.addWidget(dest_group)

        cat_group = QGroupBox("Données à exporter / restaurer")
        cat_layout = QVBoxLayout(cat_group)
        stats = {s.category_id: s for s in category_stats()}
        for cat in BACKUP_CATEGORIES:
            st = stats[cat.category_id]
            suffix = ""
            if st.file_count:
                suffix = f" ({st.file_count} fichier{'s' if st.file_count > 1 else ''}, {format_bytes(st.total_bytes)})"
            else:
                suffix = " (vide)"
            cb = QCheckBox(f"{cat.label}{suffix}")
            cb.setChecked(cat.default and st.file_count > 0)
            cb.setEnabled(st.file_count > 0 or cat.default)
            self._checkboxes[cat.category_id] = cb
            cat_layout.addWidget(cb)

        btn_row = QHBoxLayout()
        btn_all = QPushButton("Tout sélectionner")
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none = QPushButton("Tout désélectionner")
        btn_none.clicked.connect(lambda: self._set_all(False))
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        btn_row.addStretch()
        cat_layout.addLayout(btn_row)
        layout.addWidget(cat_group)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)
        layout.addWidget(self.log)

        actions = QHBoxLayout()
        self.btn_export = QPushButton("Exporter")
        self.btn_export.clicked.connect(self._on_export)
        self.btn_restore = QPushButton("Restaurer…")
        self.btn_restore.clicked.connect(self._on_restore)
        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.accept)
        actions.addWidget(self.btn_export)
        actions.addWidget(self.btn_restore)
        actions.addStretch()
        actions.addWidget(btn_close)
        layout.addLayout(actions)

    def _append_log(self, message: str) -> None:
        self.log.append(message)

    def _selected_categories(self) -> list[str]:
        return [cid for cid, cb in self._checkboxes.items() if cb.isChecked()]

    def _set_all(self, checked: bool) -> None:
        for cb in self._checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(checked)

    def _refresh_stats(self) -> None:
        # Rebuild checkboxes labels would need full rebuild; skip for v1 after init
        pass

    def _refresh_mounts(self) -> None:
        current = self.mount_combo.currentData()
        self.mount_combo.clear()
        self._mount_paths.clear()
        self.mount_combo.addItem("— Choisir un dossier —", None)
        for label, path in list_removable_mounts():
            self.mount_combo.addItem(label, str(path))
            self._mount_paths[label] = path
        home = Path.home()
        self.mount_combo.addItem(f"Dossier personnel ({home})", str(home))
        if current:
            idx = self.mount_combo.findData(current)
            if idx >= 0:
                self.mount_combo.setCurrentIndex(idx)

    def _browse_destination_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choisir le dossier de destination")
        if not path:
            return
        label = f"Personnalisé ({path})"
        self.mount_combo.addItem(label, path)
        self.mount_combo.setCurrentIndex(self.mount_combo.count() - 1)

    def _destination_dir(self) -> Path | None:
        data = self.mount_combo.currentData()
        if not data:
            return None
        return Path(str(data))

    def _destination_archive(self) -> Path | None:
        dest_dir = self._destination_dir()
        if dest_dir is None:
            return None
        name = self.filename_edit.text().strip() or default_backup_filename()
        if not name.lower().endswith(".zip"):
            name += ".zip"
        return dest_dir / name

    def _set_busy(self, busy: bool) -> None:
        self.progress.setVisible(busy)
        self.btn_export.setEnabled(not busy)
        self.btn_restore.setEnabled(not busy)

    def _on_export(self) -> None:
        categories = self._selected_categories()
        if not categories:
            QMessageBox.warning(self, "Export", "Sélectionnez au moins une catégorie.")
            return
        archive = self._destination_archive()
        if archive is None:
            QMessageBox.warning(self, "Export", "Choisissez une destination (clé USB ou dossier).")
            return
        if archive.exists():
            ans = QMessageBox.question(
                self,
                "Écraser l'archive ?",
                f"Le fichier existe déjà :\n{archive}\n\nRemplacer ?",
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        self._set_busy(True)
        self.log.clear()
        try:
            result = export_backup(
                archive,
                categories,
                progress=self._append_log,
            )
            QMessageBox.information(
                self,
                "Export réussi",
                f"{result.file_count} fichier(s) exporté(s)\n{archive}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erreur export", str(exc))
        finally:
            self._set_busy(False)

    def _on_restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir une archive de sauvegarde",
            str(self._destination_dir() or Path.home()),
            "Archives EtaComp (*.zip)",
        )
        if not path:
            return

        try:
            manifest = read_manifest(Path(path))
        except Exception as exc:
            QMessageBox.critical(self, "Archive invalide", str(exc))
            return

        categories = self._selected_categories()
        if not categories:
            categories = manifest.categories

        msg = (
            f"Archive : {Path(path).name}\n"
            f"Créée le : {manifest.created_at}\n"
            f"Version : {manifest.app_version}\n\n"
            f"Les données actuelles seront sauvegardées avant restauration.\n"
            f"Continuer ?"
        )
        if QMessageBox.question(self, "Confirmer la restauration", msg) != QMessageBox.StandardButton.Yes:
            return

        self._set_busy(True)
        self.log.clear()
        try:
            result = restore_backup(
                Path(path),
                categories,
                progress=self._append_log,
            )
            detail = f"{result.file_count} fichier(s) restauré(s)."
            if result.safety_backup_path:
                detail += f"\nSauvegarde de sécurité :\n{result.safety_backup_path}"
            QMessageBox.information(self, "Restauration réussie", detail)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur restauration", str(exc))
        finally:
            self._set_busy(False)
