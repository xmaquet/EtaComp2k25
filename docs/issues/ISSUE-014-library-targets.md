## Lot
**Lot 4**

## Constats liés
C17

## Description
`ComparatorEditDialog.result_model()` : si `targets` ≠ 11, `ValidationError` Pydantic non capturée → crash.

## Périmètre
- `src/etacomp/ui/tabs/library.py`

## Tâches
- [ ] try/except `ValidationError` → QMessageBox lisible
- [ ] Bloquer OK si compteur cibles ≠ 11 (label déjà présent)

## Critères d'acceptation
- [ ] 10 ou 12 cibles → message, pas de crash

## Estimation
**S**
