PY ?= python
IN ?= docs
OUT ?= docs/_converted

.PHONY: convert convert-one clean

# Convert all PDFs found under docs/ into Markdown, one file per page
convert:
	$(PY) tools/pdf_to_md.py --input $(IN) --out-dir $(OUT) --format md --split page

# Convert a single file: make convert-one FILE=docs/myfile.pdf
convert-one:
	@if [ -z "$(FILE)" ]; then echo "Usage: make convert-one FILE=path/to/file.pdf"; exit 1; fi
	$(PY) tools/pdf_to_md.py --input $(FILE) --out-dir $(OUT) --format md --split page

clean:
	rm -rf $(OUT)/*
