## Lot
**Lot 2** — Reproductibilité

## Constats liés
C8

## Description
Sauvegarde = runtime `Session` sans snapshot figé. `build_session_from_runtime` reconstruit le comparateur via `list_comparators()` au moment du calcul → résultats changent si le profil est modifié après coup.

## Risque métier
Perte d'auditabilité et contestation des constats.

## Périmètre
- `src/etacomp/models/session.py`
- `src/etacomp/io/storage.py`
- `src/etacomp/state/session_store.py`
- `src/etacomp/core/session_adapter.py`

## Tâches
- [ ] Ajouter `comparator_snapshot: Optional[dict]` sur `Session`
- [ ] Remplir à la sauvegarde et au changement de comparateur
- [ ] Adapter : priorité snapshot session > bibliothèque live
- [ ] Fallback sessions anciennes + warning

## Critères d'acceptation
- [ ] Modifier comparateur en bibliothèque après session → recalcul identique
- [ ] `test_comparator_modified_after_session_does_not_change_results` passe

## Tests
- `test_storage_roundtrip_session_with_fidelity`
- `test_loaded_session_recomputes_same_results`

## Dépendances
- **ISSUE-003**, **ISSUE-005**

## Estimation
**M**
