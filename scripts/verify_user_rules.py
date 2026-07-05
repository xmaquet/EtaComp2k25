#!/usr/bin/env python3
"""Vérifie la conformité de ~/.EtaComp2K25/rules/tolerances.json avec 2RMAT-MO-S4-09-B."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Racine du dépôt (scripts/ → parent)
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.etacomp.rules.tolerances import create_default_rules


def _rule_dict(rule) -> dict:
    d = {
        "graduation": rule.graduation,
        "Emt": rule.Emt,
        "Ef": rule.Ef,
        "Eh": rule.Eh,
        "Eml": rule.Eml,
    }
    if rule.course_min is not None:
        d["course_min"] = rule.course_min
    if rule.course_max is not None:
        d["course_max"] = rule.course_max
    return d


def _default_rules_json() -> dict[str, list[dict]]:
    engine = create_default_rules()
    out: dict[str, list[dict]] = {}
    for family, rules in engine.rules.items():
        out[family] = [_rule_dict(r) for r in rules]
    return out


def verify_user_rules() -> int:
    path = Path.home() / ".EtaComp2K25" / "rules" / "tolerances.json"
    if not path.exists():
        print("[OK] Fichier utilisateur introuvable — les valeurs par défaut (2RMAT) seront créées au besoin.")
        return 0

    try:
        user_rules = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERREUR] Impossible de lire {path}: {exc}")
        return 1

    ref = _default_rules_json()
    errors: list[str] = []

    for family in ("normale", "grande", "faible", "limitee"):
        user_list = user_rules.get(family, [])
        ref_list = ref.get(family, [])
        if len(user_list) != len(ref_list):
            errors.append(
                f"{family}: {len(user_list)} règle(s) utilisateur vs {len(ref_list)} attendu(s) (2RMAT)"
            )
            continue
        for i, (u, r) in enumerate(zip(user_list, ref_list)):
            for key, expected in r.items():
                actual = u.get(key)
                if actual != expected and not (actual is None and expected is None):
                    errors.append(
                        f"{family}[{i + 1}] {key}: attendu {expected} mm, obtenu {actual} mm"
                    )
            if family in ("faible", "limitee") and u.get("Eml") is not None:
                errors.append(
                    f"{family}[{i + 1}] Eml: présent en fichier utilisateur "
                    "(non applicable selon 2RMAT §7.1)"
                )
            grad = u.get("graduation", 0)
            emt = u.get("Emt")
            if grad and grad <= 0.01 and emt and emt > 0.1:
                errors.append(
                    f"{family}[{i + 1}] Emt={emt} mm suspect (graduation {grad} mm) — µm non convertis ?"
                )

    if errors:
        print("[AVERTISSEMENT] Ecarts detectes (fichier utilisateur vs 2RMAT-MO-S4-09-B / create_default_rules) :")
        for err in errors:
            print(f"   - {err}")
        return 1

    print(f"[OK] {path} conforme a 2RMAT-MO-S4-09-B (identique aux regles par defaut).")
    return 0


if __name__ == "__main__":
    raise SystemExit(verify_user_rules())
