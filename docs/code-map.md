## EtaComp2K25 — Carte du code (fichiers, rôles, liaisons)

### Sommaire
- [1. Points d’entrée et bootstrap](#1-points-dentrée-et-bootstrap)
- [2. UI (onglets, widgets, thèmes)](#2-ui-onglets-widgets-thèmes)
- [3. Domaine et calculs](#3-domaine-et-calculs)
- [4. Règles et évaluation](#4-règles-et-évaluation)
- [5. I/O série, stockage et état](#5-io-série-stockage-et-état)
- [6. Outils et tests](#6-outils-et-tests)
- [7. Flux exécutable principal](#7-flux-exécutable-principal)
- [8. Diagramme de dépendances (Mermaid)](#8-diagramme-de-dépendances-mermaid)
- [9. ADR](#9-adr)

## 1. Points d’entrée et bootstrap

- `pyproject.toml`: `etacomp = etacomp.app:run`
- `src/etacomp/__main__.py`: exécute `run()`
- `src/etacomp/app.py`:
  - Crée `QApplication`.
  - Charge préférences (`config/prefs.py`) et QSS (`ui/themes`).
  - Ouvre `ui/main_window.MainWindow` (maximisée).

## 2. UI (onglets, widgets, thèmes)

- `ui/main_window.py`:
  - Onglets:
    - `tabs/session.py`: métadonnées + connexion COM.
    - `tabs/measures.py`: campagne, tableau, log série, sauvegarde session.
    - `tabs/library.py`: CRUD comparateurs.
    - `tabs/fidelity_gap.py`: placeholder.
    - `tabs/calibration_curve.py`: placeholder (Matplotlib prévu).
    - `tabs/finalization.py`: résultats d’erreurs + verdict (placeholders calculs, export TODO).
    - `ui/settings.py` (incl. `ui/tabs/settings_rules.py`): préférences et règles.
  - Menu Aide: `ui/help_dialog.py`.

- `ui/tabs/session.py`:
  - Champs: opérateur/date/temp/humi/comparateur/itérations/mesures/obs.
  - Connexion série: ports/baud/connect/disconnect (via `serial_manager`).
  - Métadonnées ↔ `session_store`.

- `ui/tabs/measures.py`:
  - Tableau: colonnes=cibles, lignes=cycles ↑/moyenne ↑/cycles ↓/moyenne ↓ + ligne indices.
  - Avancement: `current_cycle`, `current_phase_up`, `current_col`, `waiting_zero`.
  - Réception série: `line_received(raw, value)` → écriture cellule → avance → renvoi commande si “À la demande”.
  - Sauvegarde session.

- `ui/tabs/library.py`:
  - Table 6 colonnes, dialogue d’édition `ComparatorEditDialog`.
  - Appels `io/storage` pour persister.

- `ui/tabs/finalization.py`:
  - Charge moteur de règles (défaut ou fichier).
  - “Calculer les erreurs”: résultats neutres et messages; tables d’affichage; export PDF/HTML TODO.

- `ui/settings.py`:
  - Thème (light/dark), valeurs par défaut session, autosave, langue, data dir, onglet Règles.
  - Signal `themeChanged` + application QSS.

- `ui/tabs/settings_rules.py`:
  - Éditeur CRUD des règles par famille; import/export/restauration; validation live.

- `ui/help_dialog.py`:
  - Viewer Markdown (ToC, recherche/surlignage, export PDF, reload).
  - Fichier par défaut: `resources/help/aid.md`.

- `ui/themes/__init__.py`:
  - Génération QSS avec placeholders; `apply_theme`, `load_theme_qss`.

- `ui/widgets/section_header.py`:
  - Petit widget d’en-tête stylé.

## 3. Domaine et calculs

- `models/comparator.py`:
  - `RangeType` (enum + `display_name`).
  - `ComparatorProfile` (pydantic):
    - 11 cibles strictes; première 0.0; 0 ≤ t ≤ course; ordre non-décroissant; >0 pour graduation/course.
    - `load_profile`/`save_profile`.
    - Alias `Comparator`.
- `models/session.py`:
  - `Session` (métadonnées + `series: List[MeasureSeries]`).
  - `MeasureSeries(target, readings: List[float])`.
- `calculations/errors.py`:
  - `ErrorResults`, `ErrorCalculator` (API attend `measurements` + `direction` → décalage avec modèle actuel).
  - Non branché à la campagne réelle pour l’instant.

## 4. Règles et évaluation

- `rules/tolerances.py`:
  - `ToleranceRule` (dataclass, validation bornes/tolérances).
  - `ToleranceRuleEngine`: `load/save/validate/match/evaluate`.
  - Règles par famille: `normale`, `grande`, `faible`, `limitee`.
  - `Verdict`: statut “apte/inapte/indetermine”, dépassements, messages.
  - Chemin par défaut: `~/.EtaComp2K25/rules/tolerances.json`.

## 5. I/O série, stockage et état

- `io/serialio.py`:
  - `SerialConnection` (open/read/write robustes).
  - `SerialReaderThread`: assemble lignes (CR/LF/CRLF), parse via regex + décimale (virgule/point).
  - `list_serial_ports()`.
- `io/serial_manager.py`:
  - `SerialManager` (QObject singleton):
    - Config ASCII (regex, décimale).
    - Config envoi (mode, trigger, EOL).
    - `open/close`, `send_text`, signaux `line_received/debug/error`.
- `io/storage.py`:
  - Persistance JSON (comparators/sessions) sous `~/.EtaComp2K25`.
  - Tolère erreurs sur fichiers comparateurs (ignore silencieux).
- `state/session_store.py`:
  - `SessionStore` (QObject singleton):
    - `current`, `update_metadata`, `set_series`, `save`, `load_from_file`.
    - Signaux: `session_changed`, `measures_updated`, `saved`.

## 6. Outils et tests

- Outils: `tools/migrate_comparators.py`, `tools/migrate_tolerances.py`, `tools/serial_probe.py`.
- Tests:
  - `tests/test_tolerances_engine.py`: couverture large (match, validate, evaluate, save/load).
  - `tests/test_comparator_profile.py`: validations + I/O profil.
  - `tests/test_smoke.py`: version.

## 7. Flux exécutable principal

- `etacomp` → `app.run()` → UI → `MainWindow`:
  - Onglet `Session`: prépare contexte + COM.
  - `Mesures`: lance campagne (consomme série) → `session_store` → `storage`.
  - `Finalisation`: (placeholder calculs) + affichage + exports (TODO).
  - `Paramètres ▸ Règles`: admin règles avec validation live.

## 8. Diagramme de dépendances (Mermaid)

```mermaid
graph TD
  A[app.run] --> B[MainWindow]
  B --> C[Tab Session]
  B --> D[Tab Mesures]
  B --> E[Tab Bibliothèque]
  B --> F[Tab Finalisation]
  B --> G[Paramètres/Règles]
  B --> H[HelpDialog]

  C --> S[SessionStore]
  C --> M[SerialManager]
  C --> J[Storage]

  D --> S
  D --> M
  D --> J

  E --> J
  F --> S
  F --> R[ToleranceRuleEngine]
  F --> X[ErrorCalculator]

  M --> T[SerialReaderThread]
  J --> P[ComparatorProfile/Session]

  R --> P
```

## 9. ADR

- ADR‑010: Le tableau de campagne est construit côté UI (simplicité d’implémentation).
- ADR‑011: Les fichiers utilisateur sont stockés dans `~/.EtaComp2K25` (portabilité).
- ADR‑012: Les règles sont éditables via UI et validées à la volée (UX priorisé).
- ADR‑013: Scripts de migration distribués pour accompagner l’évolution des formats JSON.




