#!/usr/bin/env python3
"""
Script de migration des profils de comparateurs.

Migre les anciens fichiers JSON de comparateurs vers le nouveau schéma
avec validation stricte et déduction des champs manquants.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.etacomp.io.storage import list_comparator_files
from src.etacomp.models.comparator import ComparatorProfile, RangeType


def migrate_file(fp: Path, *, dry_run: bool, backup: bool) -> Tuple[bool, str]:
    """
    Migre un fichier de comparateur.
    
    Args:
        fp: Chemin du fichier à migrer
        dry_run: Si True, ne fait que simuler la migration
        backup: Si True, crée une sauvegarde
    
    Returns:
        Tuple (succès, message)
    """
    try:
        # Charger le fichier original
        raw = json.loads(fp.read_text(encoding="utf-8"))
        before = raw.copy()
        
        # Migration avec déduction des champs manquants
        migrated_data = migrate_comparator_data(raw)
        
        # Validation avec le nouveau modèle
        profile = ComparatorProfile.model_validate(migrated_data)
        after = json.loads(profile.model_dump_json(indent=2))
        
        if before == after:
            return True, f"✅ {fp.name} (aucun changement nécessaire)"
        
        if dry_run:
            return True, f"🔄 {fp.name} -> migration nécessaire"
        
        # Créer une sauvegarde si demandé
        if backup:
            backup_path = fp.with_suffix(fp.suffix + '.backup')
            shutil.copy2(fp, backup_path)
        
        # Écrire le fichier migré
        fp.write_text(json.dumps(after, indent=2), encoding="utf-8")
        return True, f"✅ {fp.name} migré avec succès"
        
    except Exception as e:
        return False, f"❌ {fp.name}: {e}"


def migrate_comparator_data(data: dict) -> dict:
    """
    Migre les données d'un comparateur vers le nouveau schéma.
    
    Args:
        data: Données du comparateur à migrer
    
    Returns:
        Données migrées
    """
    migrated = data.copy()
    
    # Déduire graduation si manquante
    if "graduation" not in migrated or migrated["graduation"] is None:
        if "targets" in migrated and len(migrated["targets"]) >= 2:
            graduation = _deduce_graduation(migrated["targets"])
            migrated["graduation"] = graduation
            print(f"  📏 Graduation déduite : {graduation:.3f} mm")
        else:
            raise ValueError("Impossible de déduire la graduation : targets insuffisants")
    
    # Déduire course si manquante
    if "course" not in migrated or migrated["course"] is None:
        if "targets" in migrated:
            course = max(migrated["targets"])
            migrated["course"] = course
            print(f"  📐 Course déduite : {course:.3f} mm")
        else:
            raise ValueError("Impossible de déduire la course : targets manquants")
    
    # Déduire range_type si manquant
    if "range_type" not in migrated or migrated["range_type"] is None:
        course = migrated["course"]
        range_type = _deduce_range_type(course)
        migrated["range_type"] = range_type.value
        print(f"  🏷️  Famille déduite : {range_type.value}")
    
    return migrated


def _deduce_graduation(targets: List[float]) -> float:
    """Déduit la graduation à partir des cibles."""
    if not targets or len(targets) < 2:
        return 0.01  # Valeur par défaut
    
    # Calculer les écarts entre cibles consécutives
    diffs = []
    for i in range(1, len(targets)):
        diff = abs(targets[i] - targets[i-1])
        if diff > 1e-6:  # Ignorer les écarts trop petits
            diffs.append(diff)
    
    if not diffs:
        return 0.01
    
    # Prendre le plus petit écart comme graduation probable
    min_diff = min(diffs)
    
    # Arrondir aux valeurs usuelles
    candidates = [0.001, 0.01, 0.02, 0.05, 0.1]
    best = min(candidates, key=lambda x: abs(x - min_diff))
    
    return best


def _deduce_range_type(course: float) -> RangeType:
    """Déduit le type de comparateur à partir de la course."""
    if course <= 0.5:
        return RangeType.LIMITEE
    elif course <= 1.0:
        return RangeType.FAIBLE
    elif course <= 20.0:
        return RangeType.NORMALE
    else:
        return RangeType.GRANDE


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Migre les profils de comparateurs vers le nouveau schéma",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python migrate_comparators.py
  python migrate_comparators.py --dry-run
  python migrate_comparators.py --backup
        """
    )
    
    parser.add_argument("--dry-run", action="store_true", 
                       help="Simule la migration sans écrire de fichiers")
    parser.add_argument("--backup", action="store_true",
                       help="Crée une sauvegarde (.backup) avant migration")
    
    args = parser.parse_args()
    
    print("🔄 Migration des profils de comparateurs")
    
    # Trouver les fichiers à migrer
    files = list_comparator_files()
    if not files:
        print("📁 Aucun fichier de comparateur trouvé.")
        return 0
    
    print(f"📁 {len(files)} fichier(s) trouvé(s)")
    
    # Migrer chaque fichier
    success_count = 0
    for fp in files:
        print(f"\n📄 Traitement de {fp.name}...")
        success, message = migrate_file(fp, dry_run=args.dry_run, backup=args.backup)
        print(f"  {message}")
        if success:
            success_count += 1
    
    # Résumé
    print(f"\n📊 Résumé : {success_count}/{len(files)} fichiers traités avec succès")
    
    if args.dry_run:
        print("🔍 Mode simulation terminé")
    else:
        print("✅ Migration terminée")
    
    return 0 if success_count == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())


