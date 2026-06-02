## Lot
**Lot 4** — Robustesse runtime

## Constats liés
C10

## Description
Pas de `closeEvent` sur `MainWindow` → port COM et thread `TesaSerialReader` peuvent rester actifs après fermeture.

## Périmètre
- `src/etacomp/ui/main_window.py`
- `src/etacomp/io/serial_manager.py`

## Tâches
- [ ] `closeEvent` → `serial_manager.close()`
- [ ] Vérifier arrêt thread (`join`) et libération port
- [ ] Test manuel : fermer app avec port connecté

## Critères d'acceptation
- [ ] Pas de port COM bloqué après fermeture application

## Estimation
**S**
