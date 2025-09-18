from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from ..io.storage import list_comparator_files
from ..models.comparator import Comparator


def migrate_file(fp: Path, *, dry_run: bool, backup: bool) -> bool:
    try:
        raw = json.loads(fp.read_text(encoding="utf-8"))
        before = raw.copy()
        # Validation + complétion via modèle
        profile = Comparator.model_validate(raw)
        after = json.loads(profile.model_dump_json(indent=2))
        if before == after:
            print(f"OK: {fp.name} (aucun changement)")
            return True
        if dry_run:
            print(f"DIFF: {fp.name} -> mise à jour nécessaire")
            return True
        if backup:
            shutil.copy2(fp, fp.with_suffix(fp.suffix + ".bak"))
        fp.write_text(json.dumps(after, indent=2), encoding="utf-8")
        print(f"MIGRÉ: {fp.name}")
        return True
    except Exception as e:
        print(f"ERREUR: {fp.name}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="Migration des fichiers comparateurs vers le nouveau schéma")
    ap.add_argument("--dry-run", action="store_true", help="Ne pas écrire, seulement signaler les changements")
    ap.add_argument("--backup", action="store_true", help="Sauvegarder un .bak avant d'écrire")
    args = ap.parse_args()

    files = list_comparator_files()
    if not files:
        print("Aucun fichier à migrer.")
        return 0
    ok = 0
    for fp in files:
        ok += 1 if migrate_file(fp, dry_run=args.dry_run, backup=args.backup) else 0
    print(f"Terminé: {ok}/{len(files)} fichiers traités")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


