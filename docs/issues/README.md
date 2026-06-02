# Issues de stabilisation v1.0.1

Corps d'issues prêts pour GitHub, dérivés de la review EtaComp2K25 v1.0.0.

## Création en une commande

```powershell
gh auth login
cd <racine-du-repo>
.\scripts\create_stabilisation_issues.ps1
```

## Fichiers

- `manifest.json` — ordre, titres, labels, lien vers les corps
- `ISSUE-*.md` — description, tâches, critères d'acceptation, tests

## Ordre recommandé

005 → 001 → 002 → 004 → 011 → 013 → 003 → 008 → 007 → 006 → 009, 010, 014 → 012
