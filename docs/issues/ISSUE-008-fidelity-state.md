## Lot
**Lot 2** — Reproductibilité

## Constats liés
C9

## Description
`ResultsProvider._last_fidelity` est un **attribut de classe**. Risque d'injection de la S5 d'une session précédente si même `comparator_ref`.

## Périmètre
- `src/etacomp/ui/results_provider.py`
- `src/etacomp/ui/tabs/fidelity_deviations.py`
- `src/etacomp/ui/tabs/finalization.py`

## Tâches
- [ ] Supprimer `_last_fidelity` et `remember_fidelity`
- [ ] `compute_all` lit uniquement `rt.fidelity` via `session_store`
- [ ] `new_session()` efface la fidélité
- [ ] Vérifier `set_fidelity` après capture S5

## Critères d'acceptation
- [ ] Changer de session ne réinjecte pas une S5 étrangère

## Tests
- `test_fidelity_not_leaked_across_sessions` (nouveau)

## Dépendances
- **ISSUE-003**

## Estimation
**S**
