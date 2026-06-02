## Lot
**Lot 4** — Robustesse runtime

## Constats liés
C13, C14, C15

## Description
- Écriture JSON directe (non atomique)
- Noms de fichiers : seulement `replace(" ", "_")`
- `except: pass` sur fichiers corrompus → silence

## Périmètre
- `src/etacomp/io/storage.py`
- Utilitaire `safe_filename` (nouveau, suggéré)

## Tâches
- [ ] `atomic_write(path, content)` : `.tmp` + `os.replace`
- [ ] `sanitize_filename(ref)` pour comparateurs/sessions/exports
- [ ] Logger + message utilisateur au lieu de `pass`
- [ ] Test atomique

## Critères d'acceptation
- [ ] Référence avec caractères interdits Windows ne casse pas le chemin
- [ ] Coupure pendant save ne corrompt pas le fichier cible

## Tests
- `test_storage_atomic_write`
- `test_sanitize_filename_special_chars`

## Estimation
**M**
