## EtaComp2K25 — Plan de restructuration (sans code)

*Dernière mise à jour : 18 février 2026*

### Sommaire
- [1. Objectifs du refactor](#1-objectifs-du-refactor)
- [2. Architecture cible](#2-architecture-cible)
- [3. Découpage en phases](#3-découpage-en-phases)
- [4. Migrations et compatibilité](#4-migrations-et-compatibilité)
- [5. Tests à introduire](#5-tests-à-introduire)
- [6. Risques et mitigations](#6-risques-et-mitigations)
- [7. Diagramme des phases (Mermaid)](#7-diagramme-des-phases-mermaid)
- [8. ADR](#8-adr)

## 1. Objectifs du refactor

- Découpler la logique métier (campagne, calculs) de l’UI.
- Aligner le modèle de mesures avec les calculs réels.
- Rendre la persistance évolutive (versionnée, migrable).
- Préparer un packaging standalone robuste (ressources packagées, logs).
- Améliorer la testabilité (DI, moins de singletons, erreurs non silencieuses).

## 2. Architecture cible

- Couche Domaine (pure Python):
  - “CampaignService” gère l’avancement (cibles, cycles, zéro initial, “à la demande”).
  - “CalculationService” pour `ErrorCalculator` et agrégations (stats cibles).
- Couche UI:
  - Vue/contrôleurs PySide6 abonnés aux événements du domaine.
  - Affichage/interaction uniquement (pas de règles métier dans les widgets).
- Persistance:
  - Adapte `storage` avec `schema_version`.
  - Migrations au chargement (et scripts CLI conservés).
- Ressources:
  - `importlib.resources` ou `.qrc` Qt pour images/aide.
- Infra:
  - Logger central (fichiers dans `~/.EtaComp2K25/logs`), niveaux configurables.
  - DI légère pour `SerialManager` et `SessionStore`.

## 3. Découpage en phases

1) Alignement modèle ↔ calculs — **réalisé** (session_adapter, CalculationEngine, ResultsProvider)
   - Session runtime (MeasureSeries.readings) → SessionV2 (measurements + direction).
   - Calculs Emt, Eml, Eh, Ef opérationnels.
2) Extraction “CampaignService”
   - Déplacer l’état/avancement de `MeasuresTab` dans le domaine.
   - UI: binding (affichage/commandes).
3) Packaging ressources
   - Remplacer chemins absolus (About/logo, aide Markdown) par ressources packagées.
4) Persistance versionnée
   - Ajouter `schema_version` aux JSON; migrations runtime.
5) Erreurs & logs
   - Logger central, suppression des `except: pass`, messages explicites.
6) Exports rapport
   - Implémenter HTML/PDF (WeasyPrint/Qt print), tests “golden”.
7) DI / Testabilité
   - Interfaces injectables pour série/store; tests d’intégration headless.

## 4. Migrations et compatibilité

- Sessions:
  - Ajouter `schema_version`.
  - Si ajout `direction`, déduire `ascending/descending` via position dans campagne ou créer 2 séries par cible.
- Règles:
  - Ajouter `schema_version` (non bloquant); conservation de `validate()`.
- Comparateurs:
  - Un tag de version pour tracer les futures évolutions de profil.

## 5. Tests à introduire

- Domaine:
  - Avancement campagne (zéro initial, retour descente, cycles).
  - Stratégie “À la demande” (renvoi de trigger).
- Calculs:
  - Données synthétiques → `ErrorResults` attendus.
- Persistance:
  - Round-trip + migrations; erreurs verbeuses sur JSON invalide.
- UI:
  - Tests pytest‑qt de base (signaux, états visibles).
- Exports:
  - Golden tests HTML/PDF stables.

## 6. Risques et mitigations

- Rupture UI ↔ domaine:
  - Introduire adaptateurs progressifs, maintenir API transitoires.
- Taille binaire standalone (Qt):
  - Profil “lite” sans matplotlib si non nécessaire au runtime.
- Drivers COM variés:
  - Timeouts et recovery robustes; journaux d’erreurs détaillés.

## 7. Diagramme des phases (Mermaid)

```mermaid
flowchart LR
  P1[Phase 1: Aligner modèle & calculs] --> P2[Phase 2: Extraire CampaignService]
  P2 --> P3[Phase 3: Packaging ressources]
  P3 --> P4[Phase 4: Persistance versionnée]
  P4 --> P5[Phase 5: Logs & erreurs]
  P5 --> P6[Phase 6: Exports rapport]
  P6 --> P7[Phase 7: DI & tests intég.]
```

## 8. ADR

- ADR‑030: Séparation stricte UI/domaine pour la campagne (maintenabilité, tests).
- ADR‑031: Versionnage des JSON et migrations runtime (évolution sûre).
- ADR‑032: Packaging ressources via `importlib.resources` ou `.qrc` (standalone).
- ADR‑033: Logger central et bannissement des `except: pass` (observabilité).
- ADR‑034: DI minimale pour série/store (tests déterministes, mocks faciles).




