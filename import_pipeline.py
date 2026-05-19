# -*- coding: utf-8 -*-
"""
Datasheet PDF → PostgreSQL import pipeline.

Layer composition:
    parser (datasheet_parser/<vendor>_parser.py)  → records + chart images
    datasheet_parser.normalizer (normalize_parsed) → cross-parser symbol/condition normalization
    db.text_representations (to_embed_text)        → per-record text
    db.embeddings  (embed, EmbeddingsBundle)       → vector bundle
    db.minio_client                               → chart upload
    db.upserts     (upsert_all)                   → 6-table single-transaction write

`import_pdf(pdf_path, parser)` is the only public entry point. The parser is
passed in by the caller (e.g. db/inserter.py CLI); this module performs no
filesystem search to discover parsers.

NOTE: MinIO orphan cleanup (chart uploaded then DB write fails) is intentionally
out of scope for this module. Callers needing transactional guarantees across
both stores should layer that on top.
"""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from datasheet_parser.normalizer import normalize_parsed
from db.embeddings import EmbeddingsBundle, embed
from db.minio_client import build_minio_client, upload_charts
from db.text_representations import to_embed_text
from db.upserts import upsert_all
from db.validator import validate_parsed

_DB_ENV = Path(__file__).parent / "db" / ".env"


def _env(key: str, default: str | None = None) -> str:
    val = os.environ.get(key, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def _part_exists(conn, part_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM parts WHERE part_id = %s LIMIT 1", (part_id,))
        return cur.fetchone() is not None


def import_pdf(pdf_path: Path, parser) -> None:
    """
    Parse a datasheet PDF, embed its records, upload chart images to MinIO,
    then upsert all 6 datasheet tables in a single PostgreSQL transaction.

    Args:
        pdf_path: path to the input PDF.
        parser:   a Python module exposing two callables:
                    parse(pdf_path: str) -> dict
                    parse_typical_charts(pdf_path: str, part_id: str) -> list[dict]
    """
    # Duck-type check before any IO
    if not hasattr(parser, "parse") or not callable(parser.parse):
        raise TypeError(f"parser {parser!r} must expose a callable parse(pdf_path)")
    if not hasattr(parser, "parse_typical_charts") or not callable(parser.parse_typical_charts):
        raise TypeError(
            f"parser {parser!r} must expose a callable parse_typical_charts(pdf_path, part_id)"
        )

    load_dotenv(_DB_ENV)

    db_url       = _env("DATABASE_URL")
    minio_raw    = _env("MINIO_ENDPOINT",   "localhost:9000")
    minio_ak     = _env("MINIO_ACCESS_KEY", "minioadmin")
    minio_sk     = _env("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket = _env("MINIO_BUCKET",     "ds-typical-characteristics")

    # -- Parse PDF
    print(f"Parsing {pdf_path.name} ...")
    parsed     = normalize_parsed(parser.parse(str(pdf_path)))
    tables     = parsed["tables"]
    parts      = tables["parts"]
    part_id    = parts[0]["part_id"] if parts else pdf_path.stem
    print(f"  part_id  : {part_id}")
    print(f"  max_rat  : {len(tables['max_ratings'])} rows")
    print(f"  thermal  : {len(tables['thermal_characteristics'])} rows")
    print(f"  elec     : {len(tables['electrical_characteristics'])} rows")
    print(f"  charts   : {len(tables['typical_charts'])} rows")
    print(f"  footnotes: {len(parsed['footnotes'])} entries")

    # -- Skip if part already imported
    conn = psycopg2.connect(db_url)
    try:
        if _part_exists(conn, part_id):
            print(f"  part_id '{part_id}' already exists — skipping.")
            return
    finally:
        conn.close()

    # -- Chart images (with bytes, for MinIO)
    print("Extracting chart images ...")
    charts_full = parser.parse_typical_charts(str(pdf_path), part_id)

    # -- MinIO upload (must complete before DB transaction opens)
    print("Uploading charts to MinIO ...")
    minio_client = build_minio_client(minio_raw, minio_ak, minio_sk)
    upload_charts(minio_client, minio_bucket, charts_full)

    # -- Embeddings
    print("Generating embeddings ...")
    footnotes_dict = parsed["footnotes"]
    embeddings = EmbeddingsBundle(
        max_ratings=embed([to_embed_text(r, "max_ratings")               for r in tables["max_ratings"]]),
        thermal    =embed([to_embed_text(r, "thermal_characteristics")   for r in tables["thermal_characteristics"]]),
        electrical =embed([to_embed_text(r, "electrical_characteristics") for r in tables["electrical_characteristics"]]),
        charts     =embed([to_embed_text(r, "typical_charts")            for r in tables["typical_charts"]]),
        footnotes  =embed([to_embed_text({"marker": m, "text": t}, "footnotes") for m, t in footnotes_dict.items()]),
    )
    total = sum([len(embeddings.max_ratings), len(embeddings.thermal), len(embeddings.electrical),
                 len(embeddings.charts), len(embeddings.footnotes)])
    print(f"  Generated {total} embedding(s)")

    # validator
    validate_parsed(parsed)

    # -- DB upserts (single transaction)
    print("Upserting to PostgreSQL ...")
    conn = psycopg2.connect(db_url)
    try:
        upsert_all(conn, parsed, embeddings)
    finally:
        conn.close()

    print(f"\nDone — {part_id} inserted successfully.")
