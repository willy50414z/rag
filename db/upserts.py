# -*- coding: utf-8 -*-
"""
Pure PostgreSQL write layer for the datasheet schema.

This module MUST NOT import sentence_transformers, minio, pdfplumber, or any
PDF/ML dependency. Callers prepare records + embeddings elsewhere and pass
them in.

Public API:
    upsert_all(conn, parsed, embeddings, numeric_part_id)  — single-transaction upsert
    upsert_parts(cur, rows) -> int                         — returns parts.id
    upsert_max_ratings, upsert_thermal, …                  — per-table primitives
"""

import json

import psycopg2
import psycopg2.extras


# ---------------------------------------------------------------------------
# Per-table upserts
# ---------------------------------------------------------------------------

def upsert_parts(cur, rows: list[dict]) -> int:
    """
    Upsert parts and return the numeric parts.id.

    Looks up package_id from package_types by the 'package' text value.
    ON CONFLICT (part_number, topology, polarity) updates metadata fields.
    Returns the integer primary key of the upserted row.
    """
    if not rows:
        raise ValueError("upsert_parts requires at least one row")
    r = rows[0]

    # Resolve package text → package_id
    cur.execute(
        "SELECT id FROM package_types WHERE value = %s",
        (r["package"],),
    )
    pkg_row = cur.fetchone()
    if pkg_row is None:
        raise ValueError(
            f"package {r['package']!r} not found in package_types. "
            "Add it to the table or update PACKAGE_WHITELIST."
        )
    package_id = pkg_row[0]

    sql = """
    INSERT INTO parts (part_number, topology, polarity, package_id, marking, packing, source_page, table_ref)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (part_number, topology, polarity) DO UPDATE SET
        package_id  = EXCLUDED.package_id,
        marking     = EXCLUDED.marking,
        packing     = EXCLUDED.packing,
        source_page = EXCLUDED.source_page,
        table_ref   = EXCLUDED.table_ref
    RETURNING id
    """
    cur.execute(sql, (
        r["part_number"], r["topology"], r["polarity"],
        package_id, r["marking"], r.get("packing"),
        r["source_page"], r["table_ref"],
    ))
    row = cur.fetchone()
    numeric_id = row[0]
    print(f"  Upserted parts → id={numeric_id} ({r['part_number']} {r['topology']} {r['polarity']})")
    return numeric_id


def upsert_max_ratings(cur, rows: list[dict], embeddings: list) -> None:
    sql = """
    INSERT INTO max_ratings (
        part_id, symbol, parameter,
        condition_raw, condition_kv, condition_normalized,
        value_raw, value_num, value_min, value_max_num,
        unit, footnote_ref, source_page, table_ref, embedding
    ) VALUES %s
    ON CONFLICT (part_id, symbol, condition_normalized) DO UPDATE SET
        parameter            = EXCLUDED.parameter,
        condition_raw        = EXCLUDED.condition_raw,
        condition_kv         = EXCLUDED.condition_kv,
        value_raw            = EXCLUDED.value_raw,
        value_num            = EXCLUDED.value_num,
        value_min            = EXCLUDED.value_min,
        value_max_num        = EXCLUDED.value_max_num,
        unit                 = EXCLUDED.unit,
        footnote_ref         = EXCLUDED.footnote_ref,
        embedding            = EXCLUDED.embedding
    """
    seen: dict[tuple, int] = {}
    pairs = list(zip(rows, embeddings))
    for idx, (r, _) in enumerate(pairs):
        key = (r["part_id"], r["symbol"], r.get("condition_normalized") or "")
        seen[key] = idx
    deduped = [pairs[i] for i in sorted(seen.values())]
    if len(deduped) < len(rows):
        print(f"  Deduplicated {len(rows) - len(deduped)} max_ratings row(s) before upsert")

    data = [
        (
            r["part_id"], r["symbol"], r["parameter"],
            r.get("condition_raw"),
            psycopg2.extras.Json(json.loads(r["condition_kv"])) if r.get("condition_kv") else None,
            r.get("condition_normalized") or "",
            r["value_raw"], r.get("value_num"), r.get("value_min"), r.get("value_max_num"),
            r["unit"], r.get("footnote_ref"), r["source_page"], r["table_ref"],
            emb,
        )
        for r, emb in deduped
    ]
    psycopg2.extras.execute_values(cur, sql, data)
    print(f"  Upserted {len(data)} row(s) → max_ratings")


def upsert_thermal(cur, rows: list[dict], embeddings: list) -> None:
    sql = """
    INSERT INTO thermal_characteristics (
        part_id, symbol, parameter, typ, unit, source_page, table_ref, embedding
    ) VALUES %s
    ON CONFLICT (part_id, symbol) DO UPDATE SET
        parameter = EXCLUDED.parameter,
        typ       = EXCLUDED.typ,
        unit      = EXCLUDED.unit,
        embedding = EXCLUDED.embedding
    """
    data = [
        (r["part_id"], r["symbol"], r["parameter"], r["typ"],
         r["unit"], r["source_page"], r["table_ref"], emb)
        for r, emb in zip(rows, embeddings)
    ]
    psycopg2.extras.execute_values(cur, sql, data)
    print(f"  Upserted {len(data)} row(s) → thermal_characteristics")


def upsert_electrical(cur, rows: list[dict], embeddings: list) -> None:
    sql = """
    INSERT INTO electrical_characteristics (
        part_id, symbol, parameter, section,
        condition_raw, condition_kv, condition_normalized,
        min, typ, max, value_raw,
        unit, footnote_ref, source_page, table_ref, embedding
    ) VALUES %s
    ON CONFLICT (part_id, symbol, condition_normalized) DO UPDATE SET
        parameter            = EXCLUDED.parameter,
        section              = EXCLUDED.section,
        condition_raw        = EXCLUDED.condition_raw,
        condition_kv         = EXCLUDED.condition_kv,
        min                  = EXCLUDED.min,
        typ                  = EXCLUDED.typ,
        max                  = EXCLUDED.max,
        value_raw            = EXCLUDED.value_raw,
        unit                 = EXCLUDED.unit,
        footnote_ref         = EXCLUDED.footnote_ref,
        embedding            = EXCLUDED.embedding
    """
    seen: dict[tuple, int] = {}
    pairs = list(zip(rows, embeddings))
    for idx, (r, _) in enumerate(pairs):
        key = (r["part_id"], r["symbol"], r.get("condition_normalized") or "")
        seen[key] = idx
    deduped = [pairs[i] for i in sorted(seen.values())]
    if len(deduped) < len(rows):
        print(f"  Deduplicated {len(rows) - len(deduped)} electrical row(s) before upsert")

    data = [
        (
            r["part_id"], r["symbol"], r["parameter"], r["section"],
            r.get("condition_raw"),
            psycopg2.extras.Json(json.loads(r["condition_kv"])) if r.get("condition_kv") else None,
            r.get("condition_normalized") or "",
            r.get("min"), r.get("typ"), r.get("max"), r.get("value_raw"),
            r["unit"], r.get("footnote_ref"), r["source_page"], r["table_ref"],
            emb,
        )
        for r, emb in deduped
    ]
    psycopg2.extras.execute_values(cur, sql, data)
    print(f"  Upserted {len(data)} row(s) → electrical_characteristics")


def upsert_charts(cur, rows: list[dict], embeddings: list) -> None:
    sql = """
    INSERT INTO typical_charts (
        part_id, caption, source_page, minio_key, table_ref, embedding
    ) VALUES %s
    ON CONFLICT (part_id, minio_key) DO UPDATE SET
        caption     = EXCLUDED.caption,
        source_page = EXCLUDED.source_page,
        embedding   = EXCLUDED.embedding
    """
    data = [
        (r["part_id"], r["caption"], r["source_page"],
         r["minio_key"], r["table_ref"], emb)
        for r, emb in zip(rows, embeddings)
    ]
    psycopg2.extras.execute_values(cur, sql, data)
    print(f"  Upserted {len(data)} row(s) → typical_charts")


def upsert_footnotes(cur, part_id: int, footnotes: dict, embeddings: list) -> None:
    sql = """
    INSERT INTO footnotes (part_id, marker, text, embedding)
    VALUES %s
    ON CONFLICT (part_id, marker) DO UPDATE SET
        text      = EXCLUDED.text,
        embedding = EXCLUDED.embedding
    """
    items = list(footnotes.items())
    data  = [
        (part_id, marker, text, emb)
        for (marker, text), emb in zip(items, embeddings)
    ]
    psycopg2.extras.execute_values(cur, sql, data)
    print(f"  Upserted {len(data)} row(s) → footnotes")


# ---------------------------------------------------------------------------
# Coarse-grained orchestration: 6 tables, single transaction
# ---------------------------------------------------------------------------

def upsert_all(conn, parsed: dict, embeddings, numeric_part_id: int) -> None:
    """
    Upsert all 5 child datasheet tables for a single PDF in one transaction.

    Args:
        conn:            psycopg2 connection
        parsed:          dict from parser.parse() after normalize_parsed()
                         Child table records must already have part_id = numeric_part_id (int).
        embeddings:      EmbeddingsBundle with five list[list[float]] fields
        numeric_part_id: integer parts.id (from upsert_parts RETURNING id)
    """
    tables    = parsed["tables"]
    max_rat   = tables["max_ratings"]
    thermal   = tables["thermal_characteristics"]
    electrical= tables["electrical_characteristics"]
    charts    = tables["typical_charts"]
    footnotes = parsed["footnotes"]

    if len(max_rat) != len(embeddings.max_ratings):
        raise AssertionError(
            f"max_ratings length mismatch: records={len(max_rat)}, "
            f"embeddings={len(embeddings.max_ratings)}"
        )
    if len(thermal) != len(embeddings.thermal):
        raise AssertionError(
            f"thermal_characteristics length mismatch: records={len(thermal)}, "
            f"embeddings={len(embeddings.thermal)}"
        )
    if len(electrical) != len(embeddings.electrical):
        raise AssertionError(
            f"electrical_characteristics length mismatch: records={len(electrical)}, "
            f"embeddings={len(embeddings.electrical)}"
        )
    if len(charts) != len(embeddings.charts):
        raise AssertionError(
            f"typical_charts length mismatch: records={len(charts)}, "
            f"embeddings={len(embeddings.charts)}"
        )
    if len(footnotes) != len(embeddings.footnotes):
        raise AssertionError(
            f"footnotes length mismatch: records={len(footnotes)}, "
            f"embeddings={len(embeddings.footnotes)}"
        )

    with conn:
        with conn.cursor() as cur:
            upsert_max_ratings(cur, max_rat,    embeddings.max_ratings)
            upsert_thermal(    cur, thermal,    embeddings.thermal)
            upsert_electrical( cur, electrical, embeddings.electrical)
            upsert_charts(     cur, charts,     embeddings.charts)
            upsert_footnotes(  cur, numeric_part_id, footnotes, embeddings.footnotes)
