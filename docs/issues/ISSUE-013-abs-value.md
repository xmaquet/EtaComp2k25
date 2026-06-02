## Lot
**Lot 1** — Fiabilité du verdict métrologique

## Constats liés
C11

## Description
`MeasuresTab._write_current_cell` et `FidelityDeviationsTab._on_line` appliquent `abs(float(value))` avant stockage. Masque le signe et peut fausser erreurs et point critique.

Fichiers : `measures.py` (~498, ~525), `fidelity_deviations.py` (~261).

## Risque métier
Erreurs et point critique incorrects si le dispositif renvoie des valeurs signées.

## Tâches
- [ ] Retirer `abs()` ou limiter au seul zéro initial si justifié métier
- [ ] Valider avec trames TESA réelles
- [ ] Documenter convention opérateur si valeurs toujours positives attendues

## Critères d'acceptation
- [ ] Valeurs signées conservées en `readings` et S5
- [ ] Calculs Emt/Eh cohérents avec « mesuré − cible »

## Tests
- `test_tesa_reader_extracts_negative_value`

## Dépendances
- Recommandé après **ISSUE-003**

## Estimation
**S**
