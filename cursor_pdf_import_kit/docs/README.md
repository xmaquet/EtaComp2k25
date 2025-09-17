# Kit d'import PDF pour Cursor (Python)

Ce kit te permet de convertir rapidement des PDF en **Markdown** (ou **TXT**)
afin de pouvoir les **@-référencer** dans Cursor (Chat/Agent).

## Installation rapide

1. Crée un venv et installe les dépendances :
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Place tes PDF dans `docs/` (ou indique un chemin spécifique).

## Conversion

- Tout le dossier `docs/` → Markdown, **1 fichier par page** :
  ```bash
  make convert
  ```
  Les sorties sont écrites dans `docs/_converted/`.

- Un seul fichier :
  ```bash
  make convert-one FILE=docs/mon_doc.pdf
  ```

- Sans Makefile, usage direct :
  ```bash
  python tools/pdf_to_md.py --input docs/mon_doc.pdf --out-dir docs/_converted --format md --split page
  ```

## Options utiles

- `--format md|txt` : format de sortie (Markdown recommandé).
- `--split none|page|chunks` : sortie en un fichier unique, un fichier par page, ou par blocs de `--pages-per-file`.
- `--pages-per-file N` : utilisé avec `--split chunks` (par défaut 10).
- `--force` : écrase les fichiers existants.

> Remarque : les PDF **scannés** nécessitent un OCR en amont (ex. tesseract/ocrmypdf), le script n'effectue pas d'OCR.

## Utilisation dans Cursor

1. Ouvre le projet dans Cursor et assure-toi que le venv est sélectionné.
2. Dans le chat, tape `@Files & Folders` et choisis les fichiers sous `docs/_converted/`.
3. Pose tes questions, par exemple :
   - « @docs/_converted/mon_doc_p01.md Résume cette page et donne les 5 points clés. »
   - « Compare @docs/_converted/mon_doc_p01.md et @docs/_converted/mon_doc_p02.md sur la section Sécurité. »
   - « À partir de @docs/_converted/mon_doc_p03.md, génère une checklist opérationnelle. »

## Limitations et conseils

- La **mise en page** PDF complexe est simplifiée lors de l'extraction.
- Découpe les gros PDF en sections si besoin.
- Tu peux committer `docs/_converted/` si tu veux de l'historique de doc, sinon laisse-le ignorer via `.gitignore`.
