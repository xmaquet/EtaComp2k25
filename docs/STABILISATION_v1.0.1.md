# Stabilisation v1.0.1 — Inventaire tests (issue #1)

Date : 2025-06-02  
Branche : `stabilisation/v1.0.1`

## État actuel

| Métrique | Avant | Après correctifs tests |
|----------|-------|------------------------|
| Tests passants | 39/50 | **92/92** |
| CI | absente | `.github/workflows/ci.yml` |

Commande locale :

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

## Inventaire des 11 échecs initiaux

| Test | Cause | Action (issue #1) | Issue liée |
|------|-------|-------------------|------------|
| `test_engine_full_session` | S5 fidélité sur cible 2.0 alors que le point critique Emt est à 1.0 montée | Données de test alignées sur le moteur actuel | #4 (comportement UI à unifier) |
| `test_validation_exactly_11_targets` | Pydantic v2 lève `ValidationError` avant le `ValueError` métier | `pytest.raises(PROFILE_ERRORS)` + motif `11` | — |
| `test_validation_targets_in_range` (négatif) | `min(targets)` déclenche « première cible » avant « hors plage » | Attente message « première cible » | — |
| `test_validation_graduation_positive` | Contrainte `Field(gt=0)` Pydantic | Motif `greater than 0` | — |
| `test_validation_course_positive` | Idem | Motif `greater than 0` | — |
| `test_save_invalid_profile` | Profil invalide rejeté à la construction | Test sur `ValidationError` à la création | — |
| `test_match_normale_with_course` (course=10) | Intervalles **inclusifs** `[min,max]` : double match | Attendre `ConfigurationOverlapError` | #2 |
| `test_overlap_detection` | `validate()` ne signale plus les chevauchements | Test via `match()` en zone overlap | #2 |
| `test_evaluate_conforme` | `course=5` avec cibles jusqu'à 10 mm | Cibles ≤ course (11 points sur [0,5]) | — |
| `test_evaluate_non_conforme` | Idem | Idem | — |
| `test_evaluate_indetermine_no_rule` | Idem | Idem | — |

## Moteurs de tolérances

- **Runtime UI / verdict** : `rules/tolerance_engine.py` (intervalles semi-ouverts) — couvert par `test_tolerance_engine.py`.
- **Legacy** : `rules/tolerances.py` (inclusif) — couvert par `test_tolerances_engine.py` ; unification prévue en **#2**.

## Fixtures

Répertoire `tests/fixtures/sessions/` :

- `session_conforme_minimal.json` — session partielle (S1/S2) pour smoke import.
- `README.md` — description des jeux de données.

## Issue #11 (2025-06-02)

- `ComparatorEditDialog` : OK désactivé si ≠ 11 cibles ; `ValidationError` → `QMessageBox` (plus de crash).
- Helpers testables : `parse_targets_field`, `format_validation_error`.
- Tests : `tests/test_library_targets.py`.

## Issue #14 (2025-06-02)

- `package-data` : `resources/**` (aide, logos).
- Module `package_resources.py` (`importlib.resources`) — plus de chemins `C:\Users\...` ni `src/etacomp/...`.
- Autosave minimal : timer + `save_autosave_session` → `autosave/autosave_session.json`.
- Code mort supprimé : `fidelity_gap.py`, `apply_session_to_ui`.
- `CHANGELOG.md` ; tests `test_package_resources.py`, `test_autosave.py`.

## Issue #13 (2025-06-02)

- `Session.comparator_snapshot` persisté à l'enregistrement et au changement de comparateur.
- `resolve_comparator_snapshot` : snapshot session prioritaire sur la bibliothèque live ; warning si absent.
- Tests : `tests/test_session_snapshot.py`.

## Issue #10 (2025-06-02)

- `atomic_write` (`.tmp` + `os.replace`) pour sessions, comparateurs, détenteurs, bancs.
- `sanitize_filename` pour références comparateur / session / export PDF.
- Fichiers corrompus : `logger.warning` / `logger.error` au lieu de `except: pass` silencieux ; `load_session_file` lève une erreur explicite (UI existante).
- Tests : `tests/test_storage_atomic.py`.

## Issue #9 (2025-06-02)

- `MainWindow.closeEvent` → `serial_manager.close()` (port COM + thread TESA).
- `SerialManager.close()` : signal d'arrêt, fermeture du port puis `join` du thread (déblocage lecture bloquante).
- Tests : `tests/test_serial_shutdown.py`.

## Issue #12 (2025-06-02)

- Bloc D « TODO » remplacé par la section **Résultats métrologiques** (tableau Critère | Mesuré | Limite | Dépassement | Statut).
- Données issues de `verdict.measured`, `verdict.limits`, `verdict.exceed` ; Ef absente → « Indisponible ».
- Courbe d'étalonnage conservée (bloc C).
- Tests : `tests/test_pdf_export.py` (extraction texte via `pypdf` en dev).

## Issue #8 (2025-06-02)

- Suppression de `ResultsProvider._last_fidelity` et `remember_fidelity()`.
- `compute_all` s'appuie uniquement sur `Session.fidelity` (via `session_adapter`).
- `new_session()` remet `fidelity` à `None` ; capture S5 → `session_store.set_fidelity` uniquement.
- Test : `test_fidelity_not_leaked_across_sessions_same_comparator`.

## Issue #7 (2025-06-02)

- `Session.date` : `Field(default_factory=datetime.now)` (plus de date figée à l'import).
- Module `datetime_utils.py` : `datetime.now(timezone.utc)` à la place de `utcnow()`.
- `SessionV2.created_at_iso` dérivé de la date runtime de la session.
- Plus de `DeprecationWarning utcnow` dans pytest (66 tests).

## Issue #6 (2025-06-02)

- Suppression de `abs()` à l'enregistrement série (Mesures, fidélité S5).
- Détection du zéro initial : toujours `abs(value) <= tol` (comparaison seule).
- Tests : `test_tesa_reader.py` (trame `-0.015`, erreur mesuré − cible).

## Issue #5 (2025-06-02)

- Limite explicite **2 cycles** (`campaign_cycles.py`, séries S1–S4).
- UI Session : spin 1–2, libellé et tooltip ; défaut prefs = 2.
- Chargement session avec `series_count > 2` : avertissement + clamp.
- Adapter : logs WARNING si mesures ignorées.
- Tests : `test_session_adapter.py`.

## Issue #3 (2025-06-02)

- `ToleranceRule.Eml` optionnelle (`None` = non applicable) dans `tolerance_engine.py`.
- `RuleEditDialog` : case « Eml non applicable » pour faible/limitée, pas de `setValue(None)`.
- Verdict : `Eml` évaluée seulement si présente sur la règle (`0.0` ≠ `None`).
- Tests : `test_tolerance_eml_optional.py`.

## Issues #2 et #4 (2025-06-02)

- **#2** : module `rules/interval_match.py` partagé ; `tolerances.py` aligné sur intervalles semi-ouverts + détection chevauchements à la validation.
- **#4** : module `core/critical_point.py` ; moteur, onglet Mesures et `session_store.set_fidelity` utilisent la même logique de tie-break.

## Prochaines étapes (roadmap)

Roadmap v1.0.1 **complète** (14/14 issues). Tag release et fermeture du milestone GitHub recommandés.
