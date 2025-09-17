#!/usr/bin/env python
"""
Convert PDFs to Markdown or plain text for use in Cursor.

Usage examples:
  python tools/pdf_to_md.py --input docs/my.pdf --out-dir docs/_converted --format md --split page
  python tools/pdf_to_md.py --input docs --out-dir docs/_converted --format md --split chunks --pages-per-file 8
"""
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Iterable, List

# pdfminer.six
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LAParams


def iter_pdf_pages_text(pdf_path: Path) -> Iterable[str]:
    laparams = LAParams()  # default layout analysis
    for page_layout in extract_pages(pdf_path, laparams=laparams):
        chunks: List[str] = []
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                chunks.append(element.get_text())
        yield normalize_text("".join(chunks))


def normalize_text(text: str) -> str:
    # Basic cleanup: strip trailing spaces, normalize blank lines
    lines = [ln.rstrip() for ln in text.splitlines()]
    txt = "\n".join(lines)
    # Collapse 3+ blank lines to 2
    while "\n\n\n" in txt:
        txt = txt.replace("\n\n\n", "\n\n")
    return txt.strip()


def to_markdown(pages: List[str], title: str | None, heading_level: int = 2) -> str:
    parts: List[str] = []
    if title:
        parts.append(f"# {title}\n")
    for i, p in enumerate(pages, 1):
        parts.append(f"\n{'#'*heading_level} Page {i}\n")
        parts.append(p if p else "_(page vide)_")
    return "\n".join(parts).strip() + "\n"


def write_output_md(pages: List[str], out_path: Path, title: str):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(to_markdown(pages, title), encoding="utf-8")


def write_output_txt(pages: List[str], out_path: Path, title: str):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = f"{title}\n{'='*len(title)}\n\n" if title else ""
    body = "\n\n".join(pages) + "\n"
    out_path.write_text(header + body, encoding="utf-8")


def chunk_pages(pages: List[str], size: int):
    for i in range(0, len(pages), size):
        yield pages[i:i + size]


def sanitize_stem(stem: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in stem)


def convert_file(pdf: Path, out_dir: Path, fmt: str, split: str, pages_per_file: int, force: bool):
    pages = list(iter_pdf_pages_text(pdf))
    if not pages:
        pages = [""]  # ensure we create at least something

    stem = sanitize_stem(pdf.stem)
    written: List[Path] = []

    if split == "none":
        out_path = out_dir / f"{stem}.{fmt}"
        if out_path.exists() and not force:
            raise FileExistsError(f"{out_path} exists. Use --force to overwrite.")
        if fmt == "md":
            write_output_md(pages, out_path, title=pdf.name)
        else:
            write_output_txt(pages, out_path, title=pdf.name)
        written.append(out_path)

    elif split == "page":
        for i, page in enumerate(pages, 1):
            out_path = out_dir / f"{stem}_p{i:02d}.{fmt}"
            if out_path.exists() and not force:
                # skip silently to keep batch runs smooth
                continue
            if fmt == "md":
                write_output_md([page], out_path, title=f"{pdf.name}")
            else:
                write_output_txt([page], out_path, title=f"{pdf.name} - Page {i}")
            written.append(out_path)

    elif split == "chunks":
        for idx, chunk in enumerate(chunk_pages(pages, pages_per_file), 1):
            out_path = out_dir / f"{stem}_chunk{idx:02d}.{fmt}"
            if out_path.exists() and not force:
                continue
            if fmt == "md":
                start = (idx - 1) * pages_per_file + 1
                end = min(idx * pages_per_file, len(pages))
                write_output_md(chunk, out_path, title=f"{pdf.name} (pages {start}–{end})")
            else:
                write_output_txt(chunk, out_path, title=f"{pdf.name} (chunk {idx})")
            written.append(out_path)
    else:
        raise ValueError("--split must be one of: none, page, chunks")

    return written


def find_pdfs(input_path: Path):
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        return [input_path]
    elif input_path.is_dir():
        return sorted(p for p in input_path.rglob("*.pdf"))
    else:
        raise FileNotFoundError(f"No PDF found at {input_path}")


def main(argv=None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Convert PDFs to Markdown/TXT for Cursor usage.")
    parser.add_argument("--input", required=True, help="PDF file or directory containing PDFs")
    parser.add_argument("--out-dir", default="docs/_converted", help="Output directory (will be created)")
    parser.add_argument("--format", dest="fmt", choices=["md", "txt"], default="md", help="Output format")
    parser.add_argument("--split", choices=["none", "page", "chunks"], default="page",
                        help="One output file, one per page, or chunks of N pages")
    parser.add_argument("--pages-per-file", type=int, default=10, help="Used when --split chunks")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args(argv)

    in_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pdfs = find_pdfs(in_path)
    if not pdfs:
        print("No PDFs found.", file=sys.stderr)
        return 1

    total_written = 0
    for pdf in pdfs:
        try:
            written = convert_file(pdf, out_dir, args.fmt, args.split, args.pages_per_file, args.force)
            total_written += len(written)
            print(f"Converted {pdf} → {len(written)} file(s).")
        except Exception as e:
            print(f"[WARN] {pdf}: {e}", file=sys.stderr)

    print(f"Done. Wrote {total_written} file(s) in: {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
