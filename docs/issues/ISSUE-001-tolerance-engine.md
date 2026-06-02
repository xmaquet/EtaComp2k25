## Lot
**Lot 1** — Fiabilité du verdict métrologique

## Constats liés
C1

## Description
Deux moteurs de tolérances coexistent :
- `rules/tolerances.py` — édition UI, bornes **inclusives** (`course_min <= course <= course_max`)
- `rules/tolerance_engine.py` — verdict runtime, bornes **demi-ouvertes** (1ère ligne inclusive, suivantes `> min`)

**Preuve** : pour règles `[0,10]` et `[10,20]`, `course=10.0` → overlap côté UI, match unique côté runtime.

## Risque métier
Verdict basé sur une règle différente de celle affichée à l'opérateur.

## Périmètre technique
- `src/etacomp/rules/tolerance_engine.py`
- `src/etacomp/rules/tolerances.py`
- `src/etacomp/rules/verdict.py`
- `src/etacomp/ui/tabs/settings_rules.py`
- `src/etacomp/ui/results_provider.py`
- `tests/test_tolerance_engine*.py`, `tests/test_tolerances_engine.py`

## Tâches
- [ ] Conserver `tolerance_engine.py` (demi-ouvert) comme **source unique** de matching
- [ ] Adapter `SettingsRulesTab` et `ResultsProvider` pour utiliser ce moteur
- [ ] Déprécier le `ToleranceRuleEngine` redondant dans `tolerances.py` (garder `create_default_rules`, helpers UI)
- [ ] Unifier la dataclass `ToleranceRule` si possible
- [ ] Aligner l'interprétation affichée dans le tableau UI (colonne « Interprétation »)
- [ ] Mettre à jour `test_tolerances_engine.py` vers la sémantique runtime

## Critères d'acceptation
- [ ] Règle sauvegardée par l'UI = règle utilisée par le verdict
- [ ] Bornes testées : `course=5.0`, `5.000001`, `10.0` sur règles adjacentes
- [ ] Chevauchements détectés à la validation
- [ ] Aucun import du moteur legacy pour le verdict

## Tests à ajouter
- `test_tolerance_boundary_same_in_ui_and_runtime`
- `test_tolerance_overlap_detected`
- `test_tolerance_faible_without_course`
- `test_tolerance_limitee_without_course`

## Dépendances
- Dépend partiellement de **ISSUE-005**
- **Bloque** **ISSUE-006** (PDF limites)

## Estimation
**M**
