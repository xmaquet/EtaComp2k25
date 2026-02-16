## EtaComp2K25 — Rétro‑ingénierie de l’architecture actuelle

Version: 0.1.1

### Sommaire
- [1. Contexte et objectifs](#1-contexte-et-objectifs)
- [2. Vue d’ensemble de l’architecture](#2-vue-densemble-de-larchitecture)
- [3. Modules et responsabilités](#3-modules-et-responsabilités)
- [4. Démarrage et flux logique](#4-démarrage-et-flux-logique)
- [5. Dépendances et environnements](#5-dépendances-et-environnements)
- [6. Conventions et patterns](#6-conventions-et-patterns)
- [7. Forces et faiblesses](#7-forces-et-faiblesses)
- [8. Diagramme d’architecture (Mermaid)](#8-diagramme-darchitecture-mermaid)
- [9. Annexes et ADR](#9-annexes-et-adr)

## 1. Contexte et objectifs

- Application de métrologie pour l’étalonnage de comparateurs (UI PySide6).
- Objectifs:
  - Gérer des sessions de mesure (métadonnées, acquisition série).
  - Construire un tableau de campagnes (cycles montants/descendants, moyennes).
  - Éditer une bibliothèque de comparateurs validée strictement.
  - Définir/valider des règles de tolérances (UI dédiée).
  - Préparer calculs d’erreurs et rapport (onglet Finalisation).

## 2. Vue d’ensemble de l’architecture

- Architecture en couches informelles:
  - UI (PySide6) multi-onglets gère orchestration et une partie de la logique (campagne de mesures).
  - Modèles Pydantic pour comparateurs/sessions.
  - Moteur de règles encapsulé et bien testé.
  - I/O série (pyserial) via un manager Qt + thread lecteur.
  - Persistance JSON sous `~/.EtaComp2K25`.
- Singletons notables: `serial_manager`, `session_store`.

## 3. Modules et responsabilités

- Entrée: `etacomp.app:run` (création `QApplication`, thème, `MainWindow`).
- UI:
  - `main_window.py`: onglets, thèmes, Aide.
  - Onglets: `session.py`, `measures.py`, `library.py`, `finalization.py`, `fidelity_gap.py` (placeholder), `calibration_curve.py` (placeholder), `settings.py` (incl. `settings_rules.py`), `help_dialog.py`.
- Domaine/Modèles: `models/comparator.py` (validation stricte, 11 cibles), `models/session.py`.
- Règles: `rules/tolerances.py` (dataclass + moteur + validation + match + import/export).
- Calculs: `calculations/errors.py` (API prévue; non alignée au modèle de session actuel).
- I/O & état: `io/serialio.py`, `io/serial_manager.py`, `io/storage.py`, `state/session_store.py`.
- Outils: scripts de migration et sonde série.

## 4. Démarrage et flux logique

- Démarrage: CLI `etacomp` → `app.run()` → UI thème → `MainWindow`.
- Flux utilisateur:
  1) `Session`: métadonnées, choix comparateur, connexion COM.
  2) `Mesures`: lancer campagne (consommation série, écriture tableau, moyennes).
  3) Sauvegarder la session.
  4) `Bibliothèque`: gérer comparateurs.
  5) `Paramètres ▸ Règles`: configurer tolérances.
  6) `Finalisation`: calcul/affichage (placeholder partiel), export à implémenter.

## 5. Dépendances et environnements

- Python ≥ 3.10.
- PySide6, pydantic v2, pyserial; déclarés aussi: numpy, matplotlib (placeholders UI prévus).
- Données runtime dans `~/.EtaComp2K25` (comparators, sessions, rules, config).

## 6. Conventions et patterns

- Nommage FR, classes CamelCase, fonctions snake_case.
- Pydantic v2 pour validations fortes (comparateurs).
- JSON non versionnés (sessions/règles), scripts de migration existants.
- UI “pilotante” (logique de campagne située dans `MeasuresTab`).

## 7. Forces et faiblesses

- Forces:
  - Moteur de règles robuste et testé, validations strictes des profils.
  - UI modulaire, thèmes QSS clairs, outils de migration.
  - I/O série paramétrable (regex, décimale, EOL, modes).
- Faiblesses:
  - Couplage logique UI (campagne) ↔ composants PySide6.
  - Décalage `calculations/errors.py` ↔ modèle de session (API non branchée).
  - Ressources référencées par chemins source (non packagées).
  - JSON non versionnés, gestion d’exceptions parfois silencieuse.
  - Placeholders non implémentés (fidelity/calibration/export).

## 8. Diagramme d’architecture (Mermaid)

```mermaid
flowchart TD
  subgraph UI [UI (PySide6)]
    MW[MainWindow]
    TSession[Tab Session]
    TMeasures[Tab Mesures]
    TLib[Tab Bibliothèque]
    TFinal[Tab Finalisation]
    TRules[Tab Règles (Paramètres)]
    THelp[HelpDialog]
  end

  subgraph Domain [Domaine / Modèles]
    MComp[ComparatorProfile / RangeType]
    MSession[Session / MeasureSeries]
    Errors[ErrorCalculator / ErrorResults]
    Rules[ToleranceRuleEngine / ToleranceRule]
  end

  subgraph IO
    SerialMgr[SerialManager]
    SerialIO[SerialConnection/ReaderThread]
    Storage[storage.py (JSON)]
  end

  subgraph State
    Store[SessionStore]
  end

  MW --> TSession
  MW --> TMeasures
  MW --> TLib
  MW --> TFinal
  MW --> TRules
  MW --> THelp

  TSession --> Store
  TSession --> SerialMgr
  TSession --> Storage

  TMeasures --> Store
  TMeasures --> SerialMgr
  TMeasures --> Storage
  Store --> Storage

  TLib --> Storage
  TRules --> Rules
  TFinal --> Store
  TFinal --> Rules
  TFinal --> Errors

  SerialMgr --> SerialIO
  Storage --> MComp
  Storage --> MSession
```

## 9. Annexes et ADR

- ADR‑001: L’UI pilote la campagne de mesures (simplicité court‑terme). Impact: couplage avec PySide6; testabilité réduite.
- ADR‑002: Persistance JSON dans `~/.EtaComp2K25` (portabilité, human‑readable). Impact: nécessité de migrations et versionnage.
- ADR‑003: Moteur de règles dédié et validé (fiabilité métier). Impact: UI peut rester plus simple; bonne séparabilité.
- ADR‑004: PySide6 pour l’UI (écosystème Qt, QSS). Impact: binaire lourd en standalone; exige packaging des plugins Qt.




