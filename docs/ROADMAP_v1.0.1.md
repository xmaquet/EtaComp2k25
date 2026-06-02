# Roadmap de stabilisation EtaComp2K25 — v1.0.1

> Document de pilotage dérivé de la review v1.0.0 (juin 2026).  
> Statut actuel : **Non livrable sans corrections** → cible : **Livrable avec réserves**.

---

## A. Résumé de la stratégie

1. Rétablir la confiance dans les tests (CI verte, fixtures).
2. Corriger ce qui fausse le verdict (tolérances, point critique, cycles, Eml, `abs(value)`).
3. Rendre le constat PDF exploitable (sans TODO, tableau métrologique).
4. Garantir la reproductibilité (snapshot session, fidélité non globale).
5. Stabiliser runtime et persistance (série, JSON atomique, erreurs visibles).
6. Nettoyer packaging et dette technique.

**Recommandation v1.0.1** : limiter explicitement la campagne à **2 cycles** (S1–S4).

---

## B. Découpage en lots

| Lot | Nom | Constats | Effort |
|-----|-----|----------|--------|
| 0 | Préparation et garde-fous | C5 | 1–2 j |
| 1 | Fiabilité du verdict métrologique | C1, C4, C6, C7, C11, C12 | 5–8 j |
| 2 | Reproductibilité et traçabilité | C8, C9 | 3–5 j |
| 3 | Constat PDF professionnel | C2, C3 | 2–4 j |
| 4 | Robustesse runtime et fichiers | C10, C13–C17 | 3–5 j |
| 5 | Packaging et nettoyage | C18–C20 | 1–3 j |

**Total estimé : 15–27 j-h**

---

## C. Constats de référence

| ID | Résumé |
|----|--------|
| C1 | Double moteur de tolérances divergent |
| C2 | PDF : bloc TODO imprimé |
| C3 | PDF : absence tableau Emt/Eml/Eh/Ef |
| C4 | Plafonnement silencieux à 2 cycles |
| C5 | Suite de tests en échec (11/50) |
| C6 | Eml forcée à 0 + crash `setValue(None)` |
| C7 | Point critique : tie-break UI/moteur |
| C8 | Snapshot / SessionV2 non persisté |
| C9 | `_last_fidelity` état global |
| C10 | Port/thread série non fermés |
| C11 | `abs(value)` sur lectures |
| C12 | Défaut 1 cycle, libellé ambigu |
| C13 | JSON non atomique |
| C14 | Noms de fichiers non assainis |
| C15 | Exceptions silencieuses |
| C16 | `utcnow` déprécié, date figée à l'import |
| C17 | Crash Library si targets ≠ 11 |
| C18 | Packaging / chemins en dur |
| C19 | Code mort (`fidelity_gap`, `apply_session_to_ui`) |
| C20 | Autosave non implémenté |

---

## D. Issues GitHub (backlog)

| ID | Titre | Priorité | Lot | Constats |
|----|-------|----------|-----|----------|
| #005 | Réparer la suite de tests et mettre la CI au vert | P0 | 0 | C5 |
| #001 | Unifier le moteur de tolérances UI/runtime | P0 | 1 | C1 |
| #002 | Corriger Eml optionnelle (faible / limitée) | P0 | 1 | C6 |
| #003 | Centraliser la détermination du point critique | P0 | 1 | C7 |
| #004 | Traiter explicitement les cycles > 2 | P0 | 1 | C4, C12 |
| #013 | Supprimer `abs(value)` non contrôlé | P0 | 1 | C11 |
| #011 | Corriger dates par défaut et défaut cycles | P1 | 1/4 | C12, C16 |
| #006 | Constat PDF : TODO + tableau métrologique | P0 | 3 | C2, C3 |
| #007 | Persister un snapshot complet de session | P1 | 2 | C8 |
| #008 | Supprimer l'état global `_last_fidelity` | P1 | 2 | C9 |
| #009 | Fermer proprement port série et threads | P1 | 4 | C10 |
| #010 | Sécuriser persistance JSON | P1 | 4 | C13–C15 |
| #014 | Library : message si targets ≠ 11 | P2 | 4 | C17 |
| #012 | Packaging, ressources et code mort | P2 | 5 | C18–C20 |

*(Les numéros #001–#014 sont des identifiants documentaires ; les numéros GitHub réels sont listés après création.)*

---

## E. Ordre d'exécution

```
ISSUE-005 → ISSUE-001 → ISSUE-002 → ISSUE-004 → ISSUE-011 → ISSUE-013
         → ISSUE-003 → ISSUE-008 → ISSUE-007 → ISSUE-006
         → ISSUE-009, ISSUE-010, ISSUE-014 (parallèle possible)
         → ISSUE-012
```

---

## F. Matrice de dépendances

| Issue | Dépend de | Bloque |
|-------|-----------|--------|
| 005 | — | Tous |
| 001 | 005 | 006 |
| 002 | 001 | — |
| 003 | 005 | 008, 006 |
| 004 | 005 | — |
| 006 | 001, 003, 005 | Tag v1.0.1 |
| 007 | 003, 005 | Tests reproductibilité |
| 008 | 003 | — |

---

## G. Stratégie de tests

### Unitaires (priorité)

- `test_tolerance_boundary_same_in_ui_and_runtime`
- `test_tolerance_eml_optional_faible_limitee`
- `test_session_adapter_mapping_four_series`
- `test_session_adapter_more_than_two_cycles`
- `test_calculation_engine_critical_point_tiebreak`
- `test_fidelity_wrong_direction_is_indeterminate`
- `test_fidelity_wrong_target_is_indeterminate`
- `test_storage_roundtrip_session_with_fidelity`
- `test_comparator_modified_after_session_does_not_change_results`
- `test_pdf_export_smoke`
- `test_storage_atomic_write`

### Intégration

- `test_full_campaign_conforme_with_fidelity`
- `test_full_campaign_indeterminate_without_fidelity`
- `test_full_campaign_non_conforme`
- `test_loaded_session_recomputes_same_results`

### Manuels (12 scénarios)

Voir section I du rapport de review ; checklist obligatoire avant tag.

---

## H. Stratégie Git

```
main
└── stabilisation/v1.0.1
    ├── fix/005-tests-ci
    ├── fix/001-tolerance-engine
    ├── fix/003-critical-point
    ├── fix/006-pdf-report
    ├── fix/007-session-snapshot
    └── ...
```

Tag final : `v1.0.1` après critères de sortie ci-dessous.

---

## I. Critères de sortie v1.0.1

- [ ] Tous les tests automatisés passent ; CI verte
- [ ] Issues P0 fermées (001, 002, 003, 004, 005, 006, 013)
- [ ] Issues P1 verdict/session fermées (007, 008)
- [ ] PDF sans TODO ; tableau Emt/Eml/Eh/Ef + limites
- [ ] Session rechargée → mêmes résultats (snapshot)
- [ ] Tolérances UI = runtime aux bornes
- [ ] Campagne limitée à 2 cycles (UI)
- [ ] S5 = point critique moteur
- [ ] 12 scénarios manuels validés

**Statut cible : Livrable avec réserves**

---

## J. Estimation

| Lot | j-h |
|-----|-----|
| 0 | 1–2 |
| 1 | 5–8 |
| 2 | 3–5 |
| 3 | 2–4 |
| 4 | 3–5 |
| 5 | 1–3 |
| **Total** | **15–27** |

---

## K. Risques résiduels post v1.0.1

- Logique campagne dans `MeasuresTab` → refactor v1.1
- Pas de support > 2 cycles → documenter ; v1.1 si besoin
- Couverture UI faible → checklist release
- Validation TESA sur matériel réel → tests terrain
- Packaging Windows → v1.1

---

## Annexe — Création des issues GitHub

### Fichiers livrés

| Chemin | Rôle |
|--------|------|
| `docs/ROADMAP_v1.0.1.md` | Ce document |
| `docs/issues/manifest.json` | Liste des 14 issues + labels + milestone |
| `docs/issues/ISSUE-*.md` | Corps détaillés (prêts à coller dans GitHub) |
| `scripts/create_stabilisation_issues.ps1` | Script de création automatique |

### Création automatique (recommandé)

1. Installer [GitHub CLI](https://cli.github.com/)
2. `gh auth login`
3. Depuis la racine du dépôt :

```powershell
# Aperçu sans création
.\scripts\create_stabilisation_issues.ps1 -DryRun

# Création réelle (dépôt par défaut : xmaquet/EtaComp2k25)
.\scripts\create_stabilisation_issues.ps1
```

Le script crée le milestone **v1.0.1-stabilisation**, les labels, puis les 14 issues.

### Création manuelle

Pour chaque fichier dans `docs/issues/ISSUE-*.md`, créer une issue GitHub et coller le corps. Associer au milestone **v1.0.1-stabilisation**.

### Branche de travail

```bash
git checkout -b stabilisation/v1.0.1
```

---

## Annexe — Détail des issues

Corps complets : `docs/issues/`. Après création GitHub, noter ici les numéros réels :

| Doc ID | Titre court | GitHub # |
|--------|-------------|----------|
| 005 | Tests / CI | [#1](https://github.com/xmaquet/EtaComp2k25/issues/1) |
| 001 | Tolérances unifiées | [#2](https://github.com/xmaquet/EtaComp2k25/issues/2) |
| 002 | Eml optionnelle | [#3](https://github.com/xmaquet/EtaComp2k25/issues/3) |
| 003 | Point critique | [#4](https://github.com/xmaquet/EtaComp2k25/issues/4) |
| 004 | Cycles max 2 | [#5](https://github.com/xmaquet/EtaComp2k25/issues/5) |
| 013 | abs(value) | [#6](https://github.com/xmaquet/EtaComp2k25/issues/6) |
| 011 | Dates / défauts | [#7](https://github.com/xmaquet/EtaComp2k25/issues/7) |
| 006 | PDF | [#12](https://github.com/xmaquet/EtaComp2k25/issues/12) |
| 007 | Snapshot session | [#13](https://github.com/xmaquet/EtaComp2k25/issues/13) |
| 008 | _last_fidelity | [#8](https://github.com/xmaquet/EtaComp2k25/issues/8) |
| 009 | Fermeture série | [#9](https://github.com/xmaquet/EtaComp2k25/issues/9) |
| 010 | JSON atomique | [#10](https://github.com/xmaquet/EtaComp2k25/issues/10) |
| 014 | Library targets | [#11](https://github.com/xmaquet/EtaComp2k25/issues/11) |
| 012 | Packaging | [#14](https://github.com/xmaquet/EtaComp2k25/issues/14) |

**Milestone** : [v1.0.1-stabilisation](https://github.com/xmaquet/EtaComp2k25/milestone/1)
