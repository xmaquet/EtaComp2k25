## Lot
**Lot 0** — Préparation et garde-fous

## Constats liés
C5

## Description
11 tests sur 50 échouent actuellement. Causes mixtes : bugs réels (point critique, double moteur tolérances) et tests obsolètes (sémantique inclusive de `rules/tolerances.py`).

Objectif : CI verte sur la branche `stabilisation/v1.0.1` et jeux de données de non-régression.

## Risque métier
Aucune garantie de non-régression sur les correctifs métrologiques.

## Périmètre technique
- `tests/`
- `.github/workflows/` (à créer si absent)
- `tests/fixtures/sessions/`
- `docs/STABILISATION_v1.0.1.md` (inventaire des échecs)

## Tâches
- [ ] Exécuter `pytest tests/ -v` et documenter les 11 échecs (cause / action / issue liée)
- [ ] Ajouter workflow CI `pytest` sur PR vers `stabilisation/v1.0.1`
- [ ] Créer `tests/fixtures/sessions/` (conforme, indéterminé, partiel)
- [ ] Corriger ou adapter les tests au fur et à mesure des issues Lot 1
- [ ] Objectif final : **0 échec** avant tag `v1.0.1`

## Critères d'acceptation
- [ ] `pytest tests/` passe à 100 %
- [ ] CI verte sur GitHub
- [ ] README ou doc : comment lancer les tests localement
- [ ] Inventaire des échecs initiaux archivé

## Tests à ajouter / modifier
- Tous les tests existants
- Fixtures JSON de sessions de référence

## Dépendances
- **Bloque** : validation de tous les autres lots

## Estimation
**M**
