# -*- coding: utf-8 -*-
"""
CLI wrapper: resolve a vendor parser by PDF filename, then delegate to
`import_pipeline.import_pdf` for the full parse/embed/upload/upsert flow.

All real work lives in:
    import_pipeline.import_pdf
    db.upserts, db.embeddings, db.minio_client

Usage:
    python db/inserter.py <pdf_path>
    python db/inserter.py E:/code/rag/pdfs/VSP007N06MS-G.pdf
"""

import importlib
import sys
from pathlib import Path
from types import ModuleType

# Allow running as `python db/inserter.py …` (no -m) by adding repo root to sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from import_pipeline import import_pdf

# Vendor → parser module path. Add new entries here when onboarding a new vendor.
_VENDOR_PARSERS: dict[str, str] = {
    "vdsemi": "datasheet_parser.vdsemi_parser",
}


def _resolve_parser(pdf_path: Path) -> tuple[str, ModuleType]:
    """Pick a vendor parser based on the PDF stem prefix."""
    stem_upper = pdf_path.stem.upper()
    if stem_upper.startswith("VS"):              # covers VSP*, VS*
        vendor = "vdsemi"
    else:
        vendor = None

    module_path = _VENDOR_PARSERS.get(vendor) if vendor else None
    if not module_path:
        available = ", ".join(sorted(_VENDOR_PARSERS)) or "(none)"
        raise ValueError(
            f"No vendor parser registered for PDF '{pdf_path.name}'. "
            f"Available vendors: {available}. "
            f"Add a new entry to _VENDOR_PARSERS in {Path(__file__).name}."
        )
    return vendor, importlib.import_module(module_path)


def run(pdf_path: Path) -> None:
    vendor, parser = _resolve_parser(pdf_path)
    print(f"Vendor: {vendor}  (parser: {parser.__name__})")
    import_pdf(pdf_path, parser)


if __name__ == "__main__":
    base_dir = Path(r"E:\tmp\datasheet")
    if not base_dir.is_dir():
        print(f"Directory not found: {base_dir}")
        sys.exit(1)

    pdf_files: list[Path] = []
    for subfolder in sorted(base_dir.iterdir()):
        if subfolder.is_dir():
            pdf_files.extend(subfolder.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found under {base_dir}")
        sys.exit(1)

    vendor = "vdsemi"
    parser_module = importlib.import_module(_VENDOR_PARSERS[vendor])
    print(f"Vendor: {vendor}  (parser: {parser_module.__name__})")

    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path}")
        import_pdf(pdf_path, parser_module)
