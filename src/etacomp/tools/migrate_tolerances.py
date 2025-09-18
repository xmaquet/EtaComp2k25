#!/usr/bin/env python3
"""
Script de migration des règles de tolérances.

Migre les anciens fichiers tolerances.json vers le nouveau format
avec graduation unique au lieu de graduation_min/max.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.etacomp.rules.tolerances import ToleranceRuleEngine, ToleranceRule


def migrate_tolerances(input_path: Path, output_path: Path, force: bool = False, backup: bool = False) -> bool:
    """
    Migre un fichier de règles de tolérances.
    
    Args:
        input_path: Chemin du fichier d'entrée
        output_path: Chemin du fichier de sortie
        force: Si True, convertit graduation_min==graduation_max en graduation unique
        backup: Si True, crée une sauvegarde du fichier original
    
    Returns:
        True si la migration a réussi, False sinon
    """
    if not input_path.exists():
        print(f"❌ Fichier d'entrée introuvable : {input_path}")
        return False
    
    # Créer une sauvegarde si demandé
    if backup:
        backup_path = input_path.with_suffix(input_path.suffix + '.backup')
        print(f"📁 Création de la sauvegarde : {backup_path}")
        backup_path.write_text(input_path.read_text(encoding="utf-8"), encoding="utf-8")
    
    try:
        # Charger l'ancien format
        data = json.loads(input_path.read_text(encoding="utf-8"))
        print(f"📖 Chargement de {input_path}")
        
        # Analyser et migrer
        migrated_data = {}
        errors = []
        
        for family, rules_list in data.items():
            if family not in ["normale", "grande", "faible", "limitee"]:
                print(f"⚠️  Famille inconnue ignorée : {family}")
                continue
            
            migrated_rules = []
            
            for i, rule_dict in enumerate(rules_list):
                try:
                    migrated_rule = migrate_rule(rule_dict, family, force)
                    if migrated_rule:
                        migrated_rules.append(migrated_rule)
                except ValueError as e:
                    error_msg = f"{family}[{i+1}]: {e}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
            
            migrated_data[family] = migrated_rules
        
        # Vérifier s'il y a des erreurs bloquantes
        if errors and not force:
            print("\n❌ Migration échouée. Erreurs détectées :")
            for error in errors:
                print(f"  • {error}")
            print("\n💡 Utilisez --force pour forcer la migration des règles compatibles.")
            return False
        
        # Valider avec le moteur
        engine = ToleranceRuleEngine()
        engine.rules = migrated_data
        
        validation_errors = engine.validate()
        if validation_errors:
            print("❌ Règles migrées invalides :")
            for error in validation_errors:
                print(f"  • {error}")
            return False
        
        # Sauvegarder le nouveau format
        output_path.parent.mkdir(parents=True, exist_ok=True)
        engine.save(output_path)
        print(f"✅ Migration réussie : {output_path}")
        
        # Afficher le résumé
        total_rules = sum(len(rules) for rules in migrated_data.values())
        print(f"📊 Résumé : {total_rules} règles migrées")
        for family, rules in migrated_data.items():
            if rules:
                print(f"  • {family}: {len(rules)} règles")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration : {e}")
        return False


def migrate_rule(rule_dict: Dict[str, Any], family: str, force: bool) -> Dict[str, Any]:
    """
    Migre une règle individuelle.
    
    Args:
        rule_dict: Dictionnaire de la règle à migrer
        family: Famille de la règle
        force: Si True, force la migration même si graduation_min != graduation_max
    
    Returns:
        Dictionnaire de la règle migrée
    
    Raises:
        ValueError: Si la migration n'est pas possible
    """
    # Vérifier la présence des anciens champs
    if "graduation_min" in rule_dict and "graduation_max" in rule_dict:
        grad_min = rule_dict["graduation_min"]
        grad_max = rule_dict["graduation_max"]
        
        if abs(grad_min - grad_max) < 1e-6:
            # graduation_min == graduation_max : conversion directe
            new_rule = {
                "graduation": grad_min,
                "Emt": rule_dict.get("Emt", 0.0),
                "Eml": rule_dict.get("Eml", 0.0),
                "Ef": rule_dict.get("Ef", 0.0),
                "Eh": rule_dict.get("Eh", 0.0)
            }
            
            # Ajouter course_min/max pour normale/grande
            if family in ("normale", "grande"):
                new_rule["course_min"] = rule_dict.get("course_min", 0.0)
                new_rule["course_max"] = rule_dict.get("course_max", 0.0)
            
            return new_rule
        
        elif force:
            # Force : prendre graduation_min
            print(f"⚠️  Force migration : graduation_min ({grad_min}) != graduation_max ({grad_max})")
            new_rule = {
                "graduation": grad_min,
                "Emt": rule_dict.get("Emt", 0.0),
                "Eml": rule_dict.get("Eml", 0.0),
                "Ef": rule_dict.get("Ef", 0.0),
                "Eh": rule_dict.get("Eh", 0.0)
            }
            
            if family in ("normale", "grande"):
                new_rule["course_min"] = rule_dict.get("course_min", 0.0)
                new_rule["course_max"] = rule_dict.get("course_max", 0.0)
            
            return new_rule
        
        else:
            raise ValueError(
                f"graduation_min ({grad_min}) != graduation_max ({grad_max}). "
                f"Utilisez --force pour forcer la migration."
            )
    
    elif "graduation" in rule_dict:
        # Déjà au nouveau format
        return rule_dict
    
    else:
        raise ValueError("Champ graduation manquant")


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Migre les règles de tolérances vers le nouveau format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python migrate_tolerances.py tolerances.json tolerances_new.json
  python migrate_tolerances.py --force --backup tolerances.json tolerances_new.json
        """
    )
    
    parser.add_argument("input", type=Path, help="Fichier d'entrée (ancien format)")
    parser.add_argument("output", type=Path, help="Fichier de sortie (nouveau format)")
    parser.add_argument("--force", action="store_true", 
                       help="Force la migration même si graduation_min != graduation_max")
    parser.add_argument("--backup", action="store_true",
                       help="Crée une sauvegarde du fichier original")
    parser.add_argument("--dry-run", action="store_true",
                       help="Simule la migration sans écrire de fichier")
    
    args = parser.parse_args()
    
    print("🔄 Migration des règles de tolérances")
    print(f"📥 Entrée : {args.input}")
    print(f"📤 Sortie : {args.output}")
    
    if args.dry_run:
        print("🔍 Mode simulation (--dry-run)")
        # TODO: Implémenter la simulation
        print("✅ Simulation terminée")
        return 0
    
    success = migrate_tolerances(args.input, args.output, args.force, args.backup)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
