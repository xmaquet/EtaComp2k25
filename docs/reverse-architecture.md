## EtaComp2K25 — Rétro‑ingénierie de l’architecture actuelle

Version: 0.2.0 — Dernière mise à jour : 18 février 2026

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
  - `main_window.py`: onglets, thèmes, Aide, signaux rafraîchissement (détenteur/comparateur créés).
  - Onglets: `session.py`, `measures.py`, `library.py`, `fidelity_deviations.py`, `calibration_curve.py`, `finalization.py`, `settings.py` (sous-onglets Général, Règles, Détenteurs, Bancs étalon, Exports, TESA ASCII), `help_dialog.py`.
- Domaine/Modèles: `models/comparator.py` (11 cibles, periodicite_controle_mois), `models/session.py` (holder_ref, banc_ref, fidelity), `models/detenteur.py`, `models/banc_etalon.py`.
- Règles: `rules/tolerances.py` (UI), `rules/tolerance_engine.py` (verdict), `rules/verdict.py` (évaluation tolérances).
- Calculs: `core/calculation_engine.py` (SessionV2 → CalculatedResults), `core/session_adapter.py` (Session runtime → SessionV2), `calculations/errors.py` (pont compatibilité).
- Résultats: `ui/results_provider.py` (agrège SessionV2, calculs, verdict).
- I/O & état: `io/serialio.py`, `io/tesa_reader.py`, `io/serial_manager.py`, `io/storage.py` (comparateurs, détenteurs, bancs étalon, sessions, export_config), `state/session_store.py`.
- Config: `config/export_config.py`, `config/tesa.py`, `config/prefs.py`.
- Outils: scripts de migration et sonde série.

## 4. Démarrage et flux logique

- Démarrage: CLI `etacomp` → `app.run()` → UI thème → `MainWindow`.
- Flux utilisateur:
  1) `Session`: métadonnées, comparateur, détenteur, banc étalon, connexion COM ; enregistrer session.
  2) `Mesures`: lancer campagne (flux série, tableau, moyennes) ; bouton sauvegarde déplacé vers Session.
  3) `Écarts de fidélité`: capture série 5 au point critique.
  4) `Courbe d’étalonnage`: graphe erreurs/mesures, seuils Emt.
  5) `Finalisation`: calcul erreurs (CalculationEngine), verdict tolérances, export PDF/HTML (placeholders).
  6) `Bibliothèque`: gérer comparateurs (11 cibles, périodicité).
  7) `Paramètres`: Règles, Détenteurs, Bancs étalon, Exports, TESA ASCII.

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
  - Ressources référencées par chemins source (non packagées).
  - JSON non versionnés (sessions), gestion d’exceptions parfois silencieuse.
  - Export PDF/HTML non implémenté (placeholders).

## 8. Diagramme d’architecture (Mermaid)

```mermaid
flowchart TD
  subgraph UI [UI (PySide6)]
    MW[MainWindow]
    TSession[Tab Session]
    TMeasures[Tab Mesures]
    TFidelity[Tab Écarts fidélité]
    TCalib[Tab Courbe étalonnage]
    TLib[Tab Bibliothèque]
    TFinal[Tab Finalisation]
    TSettings[Tab Paramètres]
    THelp[HelpDialog]
  end

  subgraph Domain [Domaine / Modèles]
    MComp[ComparatorProfile / RangeType]
    MSession[Session / MeasureSeries / FidelitySeries]
    MDet[Detenteur]
    MBanc[BancEtalon]
    SessionV2[SessionV2 / CalculationEngine]
    Rules[ToleranceRuleEngine / verdict]
  end

  subgraph IO
    SerialMgr[SerialManager]
    TesaReader[TesaSerialReader]
    Storage[storage.py (JSON)]
  end

  subgraph State
    Store[SessionStore]
  end

  MW --> TSession
  MW --> TMeasures
  MW --> TFidelity
  MW --> TCalib
  MW --> TLib
  MW --> TFinal
  MW --> TSettings
  MW --> THelp

  TSession --> Store
  TSession --> SerialMgr
  TSession --> Storage
  TSession --> MDet
  TSession --> MBanc

  TMeasures --> Store
  TMeasures --> SerialMgr
  TMeasures --> Storage
  Store --> Storage

  TFidelity --> Store
  TFidelity --> SerialMgr
  TFidelity --> SessionV2
  TCalib --> SessionV2
  TFinal --> Store
  TFinal --> SessionV2
  TFinal --> Rules
  TLib --> Storage
  TSettings --> Storage
  TSettings --> Rules

  SerialMgr --> TesaReader
  Storage --> MComp
  Storage --> MSession
  Storage --> MDet
  Storage --> MBanc
```

## 9. Annexes et ADR

- ADR‑001: L’UI pilote la campagne de mesures (simplicité court‑terme). Impact: couplage avec PySide6; testabilité réduite.
- ADR‑002: Persistance JSON dans `~/.EtaComp2K25` (portabilité, human‑readable). Impact: nécessité de migrations et versionnage.
- ADR‑003: Moteur de règles dédié et validé (fiabilité métier). Impact: UI peut rester plus simple; bonne séparabilité.
- ADR‑004: PySide6 pour l’UI (écosystème Qt, QSS). Impact: binaire lourd en standalone; exige packaging des plugins Qt.




