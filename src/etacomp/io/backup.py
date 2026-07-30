"""Sauvegarde et restauration des données utilisateur (~/.EtaComp2K25/)."""
from __future__ import annotations

import json
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional

from .. import __version__
from ..config.export_config import EXPORT_CONFIG_FILE
from ..config.paths import APP_DIRNAME, get_data_dir
from .atomic_write import atomic_write

BACKUP_VERSION = 1
MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class BackupCategory:
    id: str
    label: str
    default: bool
    paths: tuple[str, ...]


BACKUP_CATEGORIES: tuple[BackupCategory, ...] = (
    BackupCategory(
        "config",
        "Configuration",
        True,
        ("config.json", "tesa_config.json", EXPORT_CONFIG_FILE),
    ),
    BackupCategory(
        "comparators",
        "Comparateurs",
        True,
        ("comparators",),
    ),
    BackupCategory(
        "sessions",
        "Sessions",
        True,
        ("sessions",),
    ),
    BackupCategory(
        "rules",
        "Règles de tolérances",
        True,
        ("rules",),
    ),
    BackupCategory(
        "detenteurs_bancs",
        "Détenteurs et bancs étalon",
        True,
        ("detenteurs.json", "bancs_etalon.json"),
    ),
    BackupCategory(
        "autosave",
        "Autosave (brouillon)",
        False,
        ("autosave",),
    ),
    BackupCategory(
        "exports",
        "Constats PDF exportés",
        False,
        ("exports",),
    ),
    BackupCategory(
        "assets",
        "Assets (sons, images)",
        False,
        ("assets",),
    ),
)

CATEGORY_BY_ID = {c.id: c for c in BACKUP_CATEGORIES}


@dataclass
class CategoryStats:
    category_id: str
    label: str
    file_count: int
    total_bytes: int


@dataclass
class ExportResult:
    archive_path: Path
    file_count: int
    total_bytes: int
    categories: list[str]


@dataclass
class RestoreResult:
    categories: list[str]
    file_count: int
    safety_backup_path: Optional[Path] = None


@dataclass
class BackupManifest:
    app: str
    app_version: str
    backup_version: int
    created_at: str
    categories: list[str]
    files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "app": self.app,
            "app_version": self.app_version,
            "backup_version": self.backup_version,
            "created_at": self.created_at,
            "categories": self.categories,
            "files": self.files,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BackupManifest":
        return cls(
            app=str(data.get("app", APP_DIRNAME)),
            app_version=str(data.get("app_version", "")),
            backup_version=int(data.get("backup_version", 0)),
            created_at=str(data.get("created_at", "")),
            categories=list(data.get("categories") or []),
            files=list(data.get("files") or []),
        )


ProgressCallback = Callable[[str], None]


def default_category_ids() -> list[str]:
    return [c.id for c in BACKUP_CATEGORIES if c.default]


def _iter_category_paths(data_dir: Path, category: BackupCategory) -> Iterator[Path]:
    for rel in category.paths:
        path = data_dir / rel
        if not path.exists():
            continue
        if path.is_dir():
            for fp in sorted(path.rglob("*")):
                if fp.is_file():
                    yield fp
        elif path.is_file():
            yield path


def category_stats(data_dir: Optional[Path] = None) -> list[CategoryStats]:
    base = data_dir or get_data_dir()
    stats: list[CategoryStats] = []
    for cat in BACKUP_CATEGORIES:
        files = list(_iter_category_paths(base, cat))
        total = sum(fp.stat().st_size for fp in files)
        stats.append(
            CategoryStats(
                category_id=cat.id,
                label=cat.label,
                file_count=len(files),
                total_bytes=total,
            )
        )
    return stats


def list_removable_mounts() -> list[tuple[str, Path]]:
    """Retourne (libellé, chemin) des volumes externes probables."""
    mounts: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    user = os.environ.get("USER") or Path.home().name

    roots: list[Path] = []
    if os.name == "nt":
        import string

        for letter in string.ascii_uppercase:
            root = Path(f"{letter}:/")
            if root.exists():
                roots.append(root)
    else:
        roots.extend(
            [
                Path("/media") / user,
                Path("/run/media") / user,
                Path("/mnt"),
            ]
        )

    for root in roots:
        if not root.exists():
            continue
        if root in (Path("/"), Path.home()):
            continue
        try:
            children = [root] if root.name not in ("media", "mnt") and root.is_dir() else list(root.iterdir())
        except OSError:
            continue
        for child in children:
            if not child.is_dir():
                continue
            try:
                resolved = child.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            label = f"{child.name}  ({resolved})"
            mounts.append((label, resolved))

    return mounts


def default_backup_filename() -> str:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    return f"EtaComp_backup_{stamp}.zip"


def read_manifest(archive_path: Path) -> BackupManifest:
    with zipfile.ZipFile(archive_path, "r") as zf:
        try:
            raw = zf.read(MANIFEST_NAME).decode("utf-8")
        except KeyError as exc:
            raise ValueError("Archive invalide : manifest.json absent") from exc
    data = json.loads(raw)
    manifest = BackupManifest.from_dict(data)
    if manifest.app not in (APP_DIRNAME, "EtaComp2K25", "EtaComp2k25"):
        raise ValueError(f"Archive incompatible : application « {manifest.app} »")
    if manifest.backup_version > BACKUP_VERSION:
        raise ValueError(
            f"Archive créée avec une version de sauvegarde plus récente ({manifest.backup_version})"
        )
    return manifest


def _archive_name(data_dir: Path, file_path: Path) -> str:
    rel = file_path.relative_to(data_dir).as_posix()
    return rel


def _collect_files(data_dir: Path, category_ids: Iterable[str]) -> list[tuple[Path, str]]:
    collected: list[tuple[Path, str]] = []
    for cid in category_ids:
        cat = CATEGORY_BY_ID.get(cid)
        if cat is None:
            raise ValueError(f"Catégorie inconnue : {cid}")
        for fp in _iter_category_paths(data_dir, cat):
            collected.append((fp, _archive_name(data_dir, fp)))
    # dédoublonnage stable
    seen: set[str] = set()
    unique: list[tuple[Path, str]] = []
    for fp, name in collected:
        if name in seen:
            continue
        seen.add(name)
        unique.append((fp, name))
    return unique


def export_backup(
    archive_path: Path,
    category_ids: Iterable[str],
    *,
    data_dir: Optional[Path] = None,
    progress: Optional[ProgressCallback] = None,
) -> ExportResult:
    base = data_dir or get_data_dir()
    categories = list(category_ids)
    if not categories:
        raise ValueError("Aucune catégorie sélectionnée")

    files = _collect_files(base, categories)
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = BackupManifest(
        app=APP_DIRNAME,
        app_version=__version__,
        backup_version=BACKUP_VERSION,
        created_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        categories=categories,
        files=[name for _, name in files],
    )

    if progress:
        progress(f"Création de {archive_path.name}…")

    total_bytes = 0
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps(manifest.to_dict(), indent=2))
        for fp, name in files:
            if progress:
                progress(f"Ajout : {name}")
            zf.write(fp, arcname=name)
            total_bytes += fp.stat().st_size

    if progress:
        progress(f"Terminé — {len(files)} fichier(s).")

    return ExportResult(
        archive_path=archive_path,
        file_count=len(files),
        total_bytes=total_bytes,
        categories=categories,
    )


def _validate_json_file(path: Path) -> None:
    json.loads(path.read_text(encoding="utf-8"))


def _safety_backup_path(data_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return data_dir.parent / f".{APP_DIRNAME}.pre_restore_{stamp}"


def restore_backup(
    archive_path: Path,
    category_ids: Optional[Iterable[str]] = None,
    *,
    data_dir: Optional[Path] = None,
    create_safety_backup: bool = True,
    progress: Optional[ProgressCallback] = None,
) -> RestoreResult:
    base = data_dir or get_data_dir()
    archive_path = Path(archive_path)
    manifest = read_manifest(archive_path)

    selected = list(category_ids) if category_ids is not None else list(manifest.categories)
    if not selected:
        raise ValueError("Aucune catégorie à restaurer")

    allowed_prefixes: set[str] = set()
    for cid in selected:
        cat = CATEGORY_BY_ID.get(cid)
        if cat is None:
            raise ValueError(f"Catégorie inconnue : {cid}")
        allowed_prefixes.update(cat.paths)

    safety_path: Optional[Path] = None
    if create_safety_backup and base.exists() and any(base.iterdir()):
        safety_path = _safety_backup_path(base)
        if progress:
            progress(f"Sauvegarde de sécurité : {safety_path.name}")
        shutil.copytree(base, safety_path)

    restored = 0
    with zipfile.ZipFile(archive_path, "r") as zf:
        names = [
            n
            for n in zf.namelist()
            if n != MANIFEST_NAME and not n.endswith("/")
        ]
        for name in names:
            if not any(name == p or name.startswith(p.rstrip("/") + "/") for p in allowed_prefixes):
                continue
            if progress:
                progress(f"Restauration : {name}")
            dest = base / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            data = zf.read(name)
            if name.endswith(".json"):
                text = data.decode("utf-8")
                json.loads(text)
                atomic_write(dest, text)
            else:
                dest.write_bytes(data)
            restored += 1

    if progress:
        progress(f"Restauration terminée — {restored} fichier(s).")

    return RestoreResult(
        categories=selected,
        file_count=restored,
        safety_backup_path=safety_path,
    )


def format_bytes(num: int) -> str:
    if num < 1024:
        return f"{num} o"
    if num < 1024 * 1024:
        return f"{num / 1024:.1f} Ko"
    return f"{num / (1024 * 1024):.1f} Mo"
