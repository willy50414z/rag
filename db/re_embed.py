# -*- coding: utf-8 -*-
"""
Re-embedding utility — recalculate embedding vectors for existing DB records.

Reads DATABASE_URL from the environment. Useful after changing the embedding
model or updating text representation logic in db.text_representations.

Usage:
    python db/re_embed.py [--table TABLE] [--batch-size N] [--dry-run]
"""

import argparse
import os
import sys

import psycopg2
import psycopg2.extras

from db.embeddings import embed
from db.text_representations import to_embed_text

# Per-table: columns to SELECT and primary key columns for UPDATE WHERE clause.
# All listed columns are passed as-is to to_embed_text(), so they must match
# the field names that text_representations expects.
_TABLES: dict[str, dict] = {
    "max_ratings": {
        "pk": ("part_id", "symbol", "condition_normalized"),
        "columns": ("part_id", "symbol", "parameter", "condition_raw",
                    "value_raw", "unit", "condition_normalized"),
    },
    "thermal_characteristics": {
        "pk": ("part_id", "symbol"),
        "columns": ("part_id", "symbol", "parameter", "typ", "unit"),
    },
    "electrical_characteristics": {
        "pk": ("part_id", "symbol", "condition_normalized"),
        "columns": ("part_id", "symbol", "parameter", "section",
                    "condition_raw", "min", "typ", "max", "unit",
                    "condition_normalized"),
    },
    "typical_charts": {
        "pk": ("part_id", "minio_key"),
        "columns": ("part_id", "minio_key", "caption"),
    },
    "footnotes": {
        "pk": ("part_id", "marker"),
        "columns": ("part_id", "marker", "text"),
    },
}


def _reembed_table(conn, table: str, batch_size: int, dry_run: bool) -> int:
    info     = _TABLES[table]
    pk_cols  = info["pk"]
    sel_cols = info["columns"]

    count_sql = f"SELECT COUNT(*) FROM {table}"
    sel_sql   = f"SELECT {', '.join(sel_cols)} FROM {table}"
    # IS NOT DISTINCT FROM handles NULL PK components correctly
    where     = " AND ".join(f"{c} IS NOT DISTINCT FROM %({c})s" for c in pk_cols)
    upd_sql   = f"UPDATE {table} SET embedding = %(embedding)s WHERE {where}"

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(count_sql)
        total = cur.fetchone()["count"]

    if dry_run:
        print(f"  [{table}] {total} row(s) would be updated")
        return total

    updated = 0
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as sel_cur:
        sel_cur.execute(sel_sql)
        while True:
            batch = sel_cur.fetchmany(batch_size)
            if not batch:
                break
            rows  = [dict(r) for r in batch]
            texts = [to_embed_text(r, table) for r in rows]
            embs  = embed(texts)
            with conn.cursor() as upd_cur:
                for row, emb in zip(rows, embs):
                    params = {c: row[c] for c in pk_cols}
                    params["embedding"] = emb
                    upd_cur.execute(upd_sql, params)
            conn.commit()
            updated += len(batch)
            print(f"  [{table}] {updated}/{total} updated ...")

    print(f"  [{table}] done — {updated} row(s) updated")
    return updated


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Re-embed existing datasheet records in PostgreSQL."
    )
    ap.add_argument(
        "--table", choices=list(_TABLES), default=None,
        help="Re-embed only this table (default: all tables)",
    )
    ap.add_argument(
        "--batch-size", type=int, default=256, dest="batch_size",
        help="Rows per processing batch (default: 256)",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Print row counts only; do not write to DB",
    )
    args = ap.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    tables = [args.table] if args.table else list(_TABLES)

    conn = psycopg2.connect(db_url)
    try:
        total = 0
        for t in tables:
            total += _reembed_table(conn, t, args.batch_size, args.dry_run)

        if args.dry_run:
            print(f"\nDry run complete — {total} row(s) would be updated.")
        else:
            print(f"\nRe-embed complete — {total} row(s) updated.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
