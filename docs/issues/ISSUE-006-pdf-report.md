## Lot
**Lot 3** — Constat PDF professionnel

## Constats liés
C2, C3

## Description
- Bloc D « Bloc complémentaire (à définir) » + texte **TODO** imprimé (`pdf_exporter.py` ~430-437)
- Absence de tableau **Emt / Eml / Eh / Ef** vs limites et dépassements

## Risque métier
Constat non utilisable en environnement réel.

## Périmètre
- `src/etacomp/io/pdf_exporter.py`
- `src/etacomp/ui/tabs/finalization.py`
- `tests/test_pdf_export_smoke.py` (à créer)

## Tâches
- [ ] Supprimer bloc D TODO
- [ ] Section « Résultats métrologiques » : tableau critère | mesuré | limite | dépassement | statut
- [ ] Utiliser `verdict.measured`, `verdict.limits`, `verdict.exceed`
- [ ] Ef absente → « Indisponible »
- [ ] Conserver courbe d'étalonnage

## Critères d'acceptation
- [ ] Aucun « TODO » dans le PDF
- [ ] Smoke test : conforme, non conforme, indéterminé, sans Ef, sans logo

## Tests
- `test_pdf_export_smoke`
- `test_pdf_export_indeterminate_without_ef`
- `test_pdf_export_non_conforme_shows_exceed`

## Dépendances
- **ISSUE-001**, **ISSUE-003**, **ISSUE-005**

## Estimation
**M**
