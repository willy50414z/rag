# -*- coding: utf-8 -*-
"""
Datasheet PDF → PostgreSQL import pipeline.

Layer composition:
    parser (datasheet_parser/<vendor>_parser.py)  → records + chart images
    datasheet_parser.normalizer (normalize_parsed) → symbol/package/channel normalization
    db.validator   (validate_parsed)               → abort on errors before any I/O
    db.text_representations (to_embed_text)        → per-record text
    db.embeddings  (embed, EmbeddingsBundle)       → vector bundle
    db.minio_client                               → chart upload
    db.upserts     (upsert_parts, upsert_all)     → 2-step write

`import_pdf(pdf_path, parser)` is the only public entry point.

Execution order:
  1. Parse + normalize
  2. Validate — abort on errors before touching MinIO or the DB
  3. DB: check duplicate + upsert parts → RETURNING id  (single connection)
  4. Inject numeric part_id into all child records
  5. Extract chart images
  6. Upload charts to MinIO
  7. Generate embeddings
  8. DB: upsert child tables in one transaction

NOTE: MinIO orphan cleanup (chart uploaded then DB write fails) is intentionally
out of scope for this module.
"""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from datasheet_parser.normalizer import normalize_parsed
from db.embeddings import EmbeddingsBundle, embed
from db.minio_client import build_minio_client, upload_charts
from db.text_representations import to_embed_text
from db.upserts import upsert_all, upsert_parts
from db.validator import validate_parsed

_DB_ENV = Path(__file__).parent / "db" / ".env"


def _env(key: str, default: str | None = None) -> str:
    val = os.environ.get(key, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def _part_exists(conn, part_number: str, topology: str, polarity: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM parts WHERE part_number = %s AND topology = %s::channel_topology"
            " AND polarity = %s::channel_polarity LIMIT 1",
            (part_number, topology, polarity),
        )
        return cur.fetchone() is not None


def import_pdf(pdf_path: Path, parser) -> None:
    """
    Parse a datasheet PDF, embed its records, upload chart images to MinIO,
    then upsert all datasheet tables in a single PostgreSQL transaction.

    Args:
        pdf_path: path to the input PDF.
        parser:   a Python module exposing:
                    parse(pdf_path: str) -> dict
                    parse_typical_charts(pdf_path: str, part_id: str) -> list[dict]
    """
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

    # -- Parse + normalize
    print(f"Parsing {pdf_path.name} ...")
    parsed     = normalize_parsed(parser.parse(str(pdf_path)))
    tables     = parsed["tables"]
    parts      = tables["parts"]

    if not parts:
        raise ValueError("parse() returned no parts records — cannot determine part identity")

    part_number = parts[0]["part_number"]
    topology    = parts[0]["topology"]
    polarity    = parts[0]["polarity"]
    print(f"  part_number: {part_number}")
    print(f"  channel    : {topology} {polarity}")
    print(f"  max_rat    : {len(tables['max_ratings'])} rows")
    print(f"  thermal    : {len(tables['thermal_characteristics'])} rows")
    print(f"  elec       : {len(tables['electrical_characteristics'])} rows")
    print(f"  charts     : {len(tables['typical_charts'])} rows")
    print(f"  footnotes  : {len(parsed['footnotes'])} entries")

    # -- Validate before any I/O (MinIO / DB writes)
    # Hard errors abort the import; low confidence emits a warning and continues.
    print("Validating parsed data ...")
    vresult = validate_parsed(parsed)
    if vresult.errors:
        raise ValueError(
            f"Validation failed for '{pdf_path.name}' — "
            f"{len(vresult.errors)} error(s). Import aborted.\n"
            + vresult.summary()
        )
    if vresult.review_required:
        print(f"  WARNING: confidence={vresult.confidence:.2f} — low confidence, "
              f"proceeding with {len(vresult.warnings)} warning(s).")
        for w in vresult.warnings:
            print(f"    {w}")
    else:
        print(f"  Validation OK (confidence={vresult.confidence:.2f}, "
              f"warnings={len(vresult.warnings)})")

    # -- Step 1: duplicate check + upsert parts (single connection)
    conn = psycopg2.connect(db_url)
    try:
        if _part_exists(conn, part_number, topology, polarity):
            print(f"  '{part_number} {topology} {polarity}' already exists — skipping.")
            return
        with conn:
            with conn.cursor() as cur:
                numeric_part_id = upsert_parts(cur, parts)
    finally:
        conn.close()

    # -- Inject numeric part_id into all child table records
    for tname in ("max_ratings", "thermal_characteristics",
                  "electrical_characteristics", "typical_charts"):
        for row in tables[tname]:
            row["part_id"] = numeric_part_id

    # -- Chart images (with bytes, for MinIO)
    print("Extracting chart images ...")
    charts_full = parser.parse_typical_charts(str(pdf_path), part_number)
    for row in charts_full:
        row["part_id"] = numeric_part_id

    # -- MinIO upload
    print("Uploading charts to MinIO ...")
    minio_client = build_minio_client(minio_raw, minio_ak, minio_sk)
    upload_charts(minio_client, minio_bucket, charts_full)

    # -- Embeddings
    print("Generating embeddings ...")
    footnotes_dict = parsed["footnotes"]
    embeddings = EmbeddingsBundle(
        max_ratings=embed([to_embed_text(r, "max_ratings")                for r in tables["max_ratings"]]),
        thermal    =embed([to_embed_text(r, "thermal_characteristics")    for r in tables["thermal_characteristics"]]),
        electrical =embed([to_embed_text(r, "electrical_characteristics") for r in tables["electrical_characteristics"]]),
        charts     =embed([to_embed_text(r, "typical_charts")             for r in tables["typical_charts"]]),
        footnotes  =embed([to_embed_text({"marker": m, "text": t}, "footnotes") for m, t in footnotes_dict.items()]),
    )
    total = sum([len(embeddings.max_ratings), len(embeddings.thermal), len(embeddings.electrical),
                 len(embeddings.charts), len(embeddings.footnotes)])
    print(f"  Generated {total} embedding(s)")

    # -- Step 2: upsert child tables (single transaction)
    print("Upserting to PostgreSQL ...")
    conn = psycopg2.connect(db_url)
    try:
        upsert_all(conn, parsed, embeddings, numeric_part_id)
    finally:
        conn.close()

    print(f"\nDone — {part_number} {topology} {polarity} inserted successfully.")
