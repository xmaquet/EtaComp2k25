## Lot
**Lot 1 / Lot 4**

## Constats liés
C12, C16

## Description
- `Session.date = datetime.now()` évalué **à l'import** du module
- `datetime.utcnow()` dans `session_adapter`, fidélité (déprécié)
- Défaut 1 cycle (voir aussi ISSUE-004)

## Périmètre
- `src/etacomp/models/session.py`
- `src/etacomp/core/session_adapter.py`
- `src/etacomp/ui/tabs/fidelity_deviations.py`

## Tâches
- [ ] `date: datetime = Field(default_factory=datetime.now)`
- [ ] Remplacer `utcnow()` par `datetime.now(timezone.utc).isoformat()`
- [ ] Aligner avec ISSUE-004 pour `default_series_count=2`

## Critères d'acceptation
- [ ] Nouvelle session : date du jour réelle
- [ ] Plus de DeprecationWarning utcnow dans pytest

## Estimation
**S**
