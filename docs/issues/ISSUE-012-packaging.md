## Lot
**Lot 5** — Packaging et nettoyage

## Constats liés
C18, C19, C20

## Description
- `pyproject.toml` : `package-data` vide
- Chemins en dur : `C:\Users\xmaqu\Documents\etaComp.svg`, `src/etacomp/resources/...`
- `fidelity_gap.py` orphelin ; `apply_session_to_ui` no-op
- Autosave annoncé mais non implémenté

## Périmètre
- `pyproject.toml`, `app.py`, `main_window.py`
- Suppression `fidelity_gap.py`, `apply_session_to_ui`
- `settings.py` autosave

## Tâches
- [ ] `package-data` : `resources/**`, `help/**`
- [ ] `importlib.resources` pour logo et aide
- [ ] Supprimer code mort
- [ ] Autosave : implémenter minimal OU retirer de l'UI + CHANGELOG

## Critères d'acceptation
- [ ] `pip install .` + `etacomp` : ressources accessibles
- [ ] Pas de chemin absolu utilisateur dans le code livré

## Estimation
**M**
