# EtaComp2K25

Application de métrologie pour la vérification des comparateurs mécaniques ou numériques à tige rentrante, avec interface PySide6.

## Fonctionnalités

- **Bibliothèques** : comparateurs (11 cibles, graduation, course, famille, périodicité), détenteurs (code ES + libellé), bancs étalon (référence, capteur, validité)
- **Session** : opérateur, conditions ambiantes, comparateur, détenteur, banc étalon, connexion série TESA
- **Mesures** : campagne 4 séries (2 cycles montée/descente), acquisition automatique ou manuelle, série 5 (fidélité au point critique)
- **Calculs** : erreur totale, locale, fidélité, hystérésis
- **Évaluation** : règles de tolérances par famille/graduation/course, verdict (apte / inapte / indéterminé)
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

- `docs/SPECIFICATION_FONCTIONNELLE_EtaComp2K25.md` : cahier des charges fonctionnel complet
- `docs/SYNTHESE_IMPLEMENTATIONS_18-02-2026.md` : synthèse des implémentations (détenteurs, bancs, exports, feedback, etc.)
- `docs/reverse-architecture.md` : architecture actuelle
- `docs/code-map.md` : carte du code
- Aide intégrée : menu Aide ou F1

## Dépendances

Python ≥ 3.10, PySide6, pydantic, pyserial, matplotlib.
