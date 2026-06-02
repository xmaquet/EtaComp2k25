# Changelog

## [1.0.1] — Stabilisation (2026-06)

### Ajouté

- Sauvegarde automatique optionnelle (`autosave/autosave_session.json` dans le dossier données).
- Ressources embarquées via `importlib.resources` (aide F1, logo à propos, icône app).

### Corrigé / nettoyé

- `package-data` setuptools : `resources/**` inclus dans le wheel.
- Suppression des chemins absolus utilisateur et des chemins `src/etacomp/...` en dur.
- Suppression de `fidelity_gap.py` (onglet orphelin) et de `apply_session_to_ui` (no-op).
