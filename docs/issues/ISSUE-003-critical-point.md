## Lot
**Lot 1** — Fiabilité du verdict métrologique

## Constats liés
C7

## Description
- `CalculationEngine` : max par `>` strict, ordre des cibles
- `MeasuresTab._highlight_max_mean_error` : tie-break par `other` sens
- `test_engine_full_session` échoue : S5 sur 2.0 mm, moteur retient 1.0 mm → `fidelity_std_mm = None`

## Risque métier
Série 5 au mauvais point → Ef absente ou fausse → verdict indéterminé ou erroné.

## Périmètre technique
- Nouveau : `src/etacomp/core/critical_point.py` (suggéré)
- `src/etacomp/core/calculation_engine.py`
- `src/etacomp/ui/tabs/measures.py`
- `src/etacomp/ui/tabs/fidelity_deviations.py`
- `src/etacomp/io/pdf_exporter.py`

## Tâches
- [ ] Extraire `find_critical_point(...)` avec tie-break **documenté**
- [ ] Proposition tie-break : max |erreur| ; égalité → sens avec plus grand |erreur opposé| ; puis cible max
- [ ] Utiliser dans moteur, highlight UI, onglet fidélité, PDF
- [ ] Corriger `test_engine_full_session`

## Critères d'acceptation
- [ ] UI, moteur et PDF : même cible + sens
- [ ] Tests d'égalité passent
- [ ] S5 toujours alignée sur le point critique moteur

## Tests
- `test_calculation_engine_critical_point_tiebreak`
- `test_fidelity_wrong_direction_is_indeterminate`
- `test_fidelity_wrong_target_is_indeterminate`

## Dépendances
- **ISSUE-005**
- **Bloque** **ISSUE-008**, **ISSUE-006** (section Ef)

## Estimation
**M**
