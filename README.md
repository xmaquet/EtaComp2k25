# EtaComp2K25

Application de métrologie pour la vérification des comparateurs mécaniques ou numériques à tige rentrante, avec interface PySide6.

## Fonctionnalités

- **Bibliothèques** : comparateurs (11 cibles, graduation, course, famille, périodicité), détenteurs (code ES + libellé), bancs étalon (référence, capteur, validité)
- **Session** : opérateur, conditions ambiantes, comparateur, détenteur, banc étalon, connexion série TESA
- **Mesures** : campagne 4 séries (2 cycles montée/descente), acquisition automatique ou manuelle, série 5 (fidélité au point critique)
- **Calculs** : erreur totale, locale, fidélité, hystérésis
- **Évaluation** : règles de tolérances par famille/graduation/course, verdict (conforme / non conforme / indéterminé)
- **Export** : constat de vérification PDF depuis Finalisation
- **Visualisation** : courbe d’étalonnage, écarts de fidélité
- **Paramètres** : thème, règles, détenteurs, bancs étalon, configuration export (entité, image, titre, normes), TESA ASCII

## Démarrage

```bash
etacomp
# ou
python -m etacomp
```

## Données

Stockage dans `~/.EtaComp2K25/` : comparators, sessions, rules, detenteurs.json, bancs_etalon.json, export_config.json, config.json, tesa_config.json.

## Documentation

- `docs/SYNTHESE_ARCHITECTURE_DETAILLEE.md` : synthèse architecture détaillée (modules, flux, données, UI)
- `docs/SPECIFICATION_FONCTIONNELLE_EtaComp2K25.md` : cahier des charges fonctionnel complet
- `docs/SYNTHESE_IMPLEMENTATIONS.md` : journal des implémentations (fév.–juin 2026)
- `docs/reverse-architecture.md` : architecture actuelle
- `docs/code-map.md` : carte du code
- Aide intégrée : menu Aide ou F1

## Tests

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

La CI GitHub Actions exécute `pytest` sur les branches `main` et `stabilisation/v1.0.1`. Voir `docs/STABILISATION_v1.0.1.md` pour l’inventaire des échecs initiaux (issue #1).

## Dépendances

Python ≥ 3.10, PySide6, pydantic, pyserial, matplotlib, reportlab. Développement : `pip install -e ".[dev]"` (pytest).

## Référentiel normatif

Les calculs et tolérances de cette application sont basés sur :

- **2RMAT-MO-S4-09-B** : Mode opératoire *Vérifier un comparateur* (2e RMAT, 27/04/2017).
- **Normes associées** :
  - NF X07-011 : Métrologie dans l’entreprise.
  - NF E 11-057 : Spécification géométrique des produits (GPS).
  - NF EN ISO 463 : Instruments de mesurage dimensionnel — Comparateurs mécaniques à cadran.
- **Unités** : Toutes les valeurs sont en **millimètres (mm)**.
