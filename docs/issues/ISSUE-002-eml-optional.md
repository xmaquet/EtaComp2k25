## Lot
**Lot 1** — Fiabilité du verdict métrologique

## Constats liés
C6

## Description
- `RuleEditDialog.result_rule()` force toujours `Eml=eml.value()` → **0.0 par défaut** pour faible/limitée
- Édition d'une règle avec `Eml=None` → `self.eml.setValue(None)` → **crash** `TypeError`
- Verdict compare `Eml=0` comme limite active → **faux NON CONFORME**

## Risque métier
Comparateurs faible/limitée systématiquement déclarés non conformes.

## Périmètre technique
- `src/etacomp/ui/tabs/settings_rules.py` (`RuleEditDialog`)
- `src/etacomp/rules/tolerance_engine.py` (load JSON)
- `src/etacomp/rules/verdict.py`

## Tâches
- [ ] Masquer spin Eml ou case « Eml non applicable » pour familles faible/limitée
- [ ] `result_rule()` : omettre `Eml` du JSON si N/A
- [ ] Pré-remplissage : si `initial.Eml is None`, ne pas appeler `setValue`
- [ ] Verdict : ne tester Eml que si présente sur la règle

## Critères d'acceptation
- [ ] Création/édition règle faible sans crash
- [ ] JSON sans clé `Eml` → verdict ignore Eml
- [ ] Distinction documentée `None` vs `0.0`

## Tests
- `test_tolerance_eml_optional_faible_limitee`

## Dépendances
- Souvent même PR que **ISSUE-001**

## Estimation
**S**
