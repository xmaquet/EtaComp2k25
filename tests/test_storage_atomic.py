"""Issue #10 — écriture atomique et noms de fichiers sûrs."""

import json
import os
from pathlib import Path

import pytest

from src.etacomp.io.atomic_write import atomic_write
from src.etacomp.io.safe_filename import sanitize_filename
from src.etacomp.io.storage import save_model
from src.etacomp.models.comparator import Comparator


def test_sanitize_filename_special_chars():
    assert sanitize_filename('REF/with:bad*chars?') == "REF_with_bad_chars_"
    assert sanitize_filename("  ") == "sans_ref"
    assert sanitize_filename("CON") == "_CON"
    assert sanitize_filename("normal ref") == "normal ref"


def test_storage_atomic_write_replaces_content(tmp_path: Path):
    target = tmp_path / "data.json"
    atomic_write(target, '{"v": 1}')
    atomic_write(target, '{"v": 2}')
    assert json.loads(target.read_text(encoding="utf-8"))["v"] == 2
    assert not (tmp_path / "data.json.tmp").exists()


def test_atomic_write_preserves_target_on_replace_failure(tmp_path: Path, monkeypatch):
    target = tmp_path / "data.json"
    target.write_text('{"ok": true}', encoding="utf-8")

    def _fail_replace(src, dst):
        raise OSError("simulated failure")

    monkeypatch.setattr(os, "replace", _fail_replace)
    with pytest.raises(OSError, match="simulated"):
        atomic_write(target, '{"broken": true}')
    assert target.read_text(encoding="utf-8") == '{"ok": true}'


def test_save_comparator_uses_safe_filename(tmp_path: Path, monkeypatch):
    import src.etacomp.io.storage as storage_mod

    monkeypatch.setattr(storage_mod, "get_data_dir", lambda: tmp_path)
    c = Comparator(
        reference="A/B:C*test",
        manufacturer="M",
        graduation=0.01,
        course=10.0,
        targets=[float(i) for i in range(11)],
        range_type="normale",
        periodicite_controle_mois=12,
    )
    path = storage_mod.save_comparator(c)
    assert path.name == "A_B_C_test.json"
    assert path.exists()
