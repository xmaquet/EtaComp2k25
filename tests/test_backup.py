"""Tests sauvegarde / restauration (io/backup.py)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from src.etacomp.io import backup as backup_mod
from src.etacomp.io.backup import (
    BACKUP_VERSION,
    export_backup,
    read_manifest,
    restore_backup,
)


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch) -> Path:
    base = tmp_path / "profile"
    (base / "comparators").mkdir(parents=True)
    (base / "sessions").mkdir(parents=True)
    (base / "rules").mkdir(parents=True)
    (base / "config.json").write_text('{"theme": "light"}', encoding="utf-8")
    (base / "comparators" / "C1.json").write_text(
        '{"reference":"C1","manufacturer":"M","graduation":0.01,"course":10.0,"range_type":"normale","targets_count":11}',
        encoding="utf-8",
    )
    (base / "rules" / "tolerances.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(backup_mod, "get_data_dir", lambda: base)
    return base


def test_export_and_restore_round_trip(data_dir: Path, tmp_path: Path):
    archive = tmp_path / "backup.zip"
    export_backup(archive, ["config", "comparators", "rules"])

    assert archive.is_file()
    manifest = read_manifest(archive)
    assert manifest.backup_version == BACKUP_VERSION
    assert "config" in manifest.categories

    # Simuler réinstall : profil vide
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "comparators").mkdir()
    (empty / "sessions").mkdir()

    result = restore_backup(archive, ["config", "comparators", "rules"], data_dir=empty)
    assert result.file_count >= 3
    assert json.loads((empty / "config.json").read_text(encoding="utf-8"))["theme"] == "light"
    assert (empty / "comparators" / "C1.json").is_file()


def test_read_manifest_rejects_missing_manifest(tmp_path: Path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("config.json", "{}")
    with pytest.raises(ValueError, match="manifest"):
        read_manifest(archive)


def test_export_requires_categories(data_dir: Path, tmp_path: Path):
    with pytest.raises(ValueError, match="catégorie"):
        export_backup(tmp_path / "x.zip", [])


def test_list_removable_mounts_under_media_user(tmp_path: Path, monkeypatch):
    user = "testuser"
    usb = tmp_path / "media" / user / "A8FF-1F3B"
    usb.mkdir(parents=True)

    monkeypatch.setattr(backup_mod, "_current_username", lambda: user)
    monkeypatch.setattr(backup_mod, "_mounts_from_lsblk", lambda: [])

    mounts: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    parent = tmp_path / "media" / user
    for child in parent.iterdir():
        backup_mod._add_mount(mounts, seen, child)

    assert len(mounts) == 1
    assert "A8FF-1F3B" in mounts[0][0]
    assert mounts[0][1] == usb.resolve()
