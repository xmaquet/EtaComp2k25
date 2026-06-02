## Lot
**Lot 1** — Fiabilité du verdict métrologique

## Constats liés
C4, C12 (partiel)

## Description
- UI : `series` jusqu'à **999** (`session.py`)
- `session_adapter` : `cycles = min(cycles, 2)` et ignore mesures au-delà **sans alerte**
- Défaut prefs : **1 cycle** (S1+S2 seulement)

## Recommandation v1.0.1
**Limiter explicitement à 2 cycles** (métier S1–S4). Support N cycles → v1.1.

## Périmètre technique
- `src/etacomp/ui/tabs/session.py`
- `src/etacomp/ui/tabs/measures.py`
- `src/etacomp/core/session_adapter.py`
- `src/etacomp/config/prefs.py`

## Tâches
- [ ] `QSpinBox series` : `setRange(1, 2)` + tooltip explicite
- [ ] `default_series_count = 2` dans `Preferences`
- [ ] Libellé : « Cycles montée/descente (max. 2) »
- [ ] Session chargée avec `series_count > 2` : avertissement + clamp
- [ ] Log warning dans adapter si données ignorées

## Critères d'acceptation
- [ ] Impossible de configurer 3+ cycles en usage normal
- [ ] Aucune mesure ignorée silencieusement
- [ ] `test_session_adapter_more_than_two_cycles` passe

## Tests
- `test_session_adapter_more_than_two_cycles`
- `test_session_adapter_mapping_four_series`

## Estimation
**S**
