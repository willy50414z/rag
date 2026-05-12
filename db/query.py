# -*- coding: utf-8 -*-
"""
Datasheet RAG query functions.

Usage:
    from db.query import search, format_context

    results = search("RDS(ON) at high temperature", part_id="VSP007N06MS-G")
    print(format_context(results))

Reads credentials from db/.env (or environment variables directly).
"""

import os
from functools import lru_cache
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv(Path(__file__).parent / ".env")

EMBED_MODEL = "all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(EMBED_MODEL)


def _conn():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


# ---------------------------------------------------------------------------
# Per-table search queries
# ---------------------------------------------------------------------------

_TABLE_QUERIES = {
    "electrical_characteristics": """
        SELECT
            'electrical_characteristics'  AS _table,
            1 - (embedding <=> %(vec)s::vector)   AS _score,
            part_id, symbol, parameter, section,
            condition_raw, condition_normalized,
            min, typ, max, value_raw, unit, footnote_ref, source_page
        FROM electrical_characteristics
        {where}
        ORDER BY embedding <=> %(vec)s::vector
        LIMIT %(k)s
    """,
    "max_ratings": """
        SELECT
            'max_ratings'                 AS _table,
            1 - (embedding <=> %(vec)s::vector)   AS _score,
            part_id, symbol, parameter,
            condition_raw, condition_normalized,
            value_raw, value_num, value_min, value_max_num,
            unit, footnote_ref, source_page
        FROM max_ratings
        {where}
        ORDER BY embedding <=> %(vec)s::vector
        LIMIT %(k)s
    """,
    "thermal_characteristics": """
        SELECT
            'thermal_characteristics'     AS _table,
            1 - (embedding <=> %(vec)s::vector)   AS _score,
            part_id, symbol, parameter, typ, unit, source_page
        FROM thermal_characteristics
        {where}
        ORDER BY embedding <=> %(vec)s::vector
        LIMIT %(k)s
    """,
    "typical_charts": """
        SELECT
            'typical_charts'              AS _table,
            1 - (embedding <=> %(vec)s::vector)   AS _score,
            part_id, caption, minio_key, source_page
        FROM typical_charts
        {where}
        ORDER BY embedding <=> %(vec)s::vector
        LIMIT %(k)s
    """,
    "footnotes": """
        SELECT
            'footnotes'                   AS _table,
            1 - (embedding <=> %(vec)s::vector)   AS _score,
            part_id, marker, text
        FROM footnotes
        {where}
        ORDER BY embedding <=> %(vec)s::vector
        LIMIT %(k)s
    """,
}


# ---------------------------------------------------------------------------
# Core search
# ---------------------------------------------------------------------------

def search(
    question: str,
    part_id: str | None = None,
    tables: list[str] | None = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Semantic search across datasheet tables.

    Args:
        question: Natural language query.
        part_id:  Filter to a specific part (e.g. "VSP007N06MS-G").
                  None = search all parts.
        tables:   Subset of tables to search. None = all tables.
        top_k:    Number of results to return (after merging all tables).

    Returns:
        List of result dicts sorted by similarity score (highest first).
        Each dict has '_table' and '_score' plus all columns of that table.
    """
    target_tables = tables or list(_TABLE_QUERIES.keys())

    vec_list = _model().encode(question).tolist()
    vec_str  = "[" + ",".join(str(x) for x in vec_list) + "]"

    where_clause = "WHERE part_id = %(pid)s" if part_id else ""
    params = {"vec": vec_str, "k": top_k, "pid": part_id}

    rows: list[dict] = []
    conn = _conn()
    try:
        with conn.cursor() as cur:
            for tbl in target_tables:
                if tbl not in _TABLE_QUERIES:
                    continue
                sql = _TABLE_QUERIES[tbl].format(where=where_clause)
                cur.execute(sql, params)
                rows.extend(dict(r) for r in cur.fetchall())
    finally:
        conn.close()

    rows.sort(key=lambda r: r["_score"], reverse=True)
    return rows[:top_k]


# ---------------------------------------------------------------------------
# Context formatter for LLM
# ---------------------------------------------------------------------------

def format_context(results: list[dict]) -> str:
    """Format search results as plain text context for an LLM prompt."""
    if not results:
        return "(no relevant records found)"

    lines = []
    for r in results:
        tbl   = r["_table"]
        score = r["_score"]
        pid   = r.get("part_id", "")

        if tbl == "electrical_characteristics":
            cond = f", {r['condition_raw']}" if r.get("condition_raw") else ""
            nums = []
            if r.get("min") is not None: nums.append(f"min={r['min']}")
            if r.get("typ") is not None: nums.append(f"typ={r['typ']}")
            if r.get("max") is not None: nums.append(f"max={r['max']}")
            if r.get("value_raw"):        nums.append(r["value_raw"])
            lines.append(
                f"[{score:.2f}] {pid} | {r['section']} | "
                f"{r['symbol']} {r['parameter']}{cond}: "
                f"{' '.join(nums)} {r['unit']}"
            )

        elif tbl == "max_ratings":
            cond = f", {r['condition_raw']}" if r.get("condition_raw") else ""
            lines.append(
                f"[{score:.2f}] {pid} | max_rating | "
                f"{r['symbol']} {r['parameter']}{cond}: "
                f"{r['value_raw']} {r['unit']}"
            )

        elif tbl == "thermal_characteristics":
            lines.append(
                f"[{score:.2f}] {pid} | thermal | "
                f"{r['symbol']} {r['parameter']}: {r['typ']} {r['unit']}"
            )

        elif tbl == "typical_charts":
            lines.append(
                f"[{score:.2f}] {pid} | chart | "
                f"{r['caption']} → {r['minio_key']}"
            )

        elif tbl == "footnotes":
            lines.append(
                f"[{score:.2f}] {pid} | note {r['marker']} | {r['text']}"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sample usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    PART = "VSP007N06MS-G"

    samples = [
        # (description, kwargs)
        (
            "語意搜尋（跨所有 table，top 5）",
            {"question": "RDS(ON) at high temperature", "part_id": PART, "top_k": 5},
        ),
        (
            "只搜 max_ratings + electrical",
            {
                "question": "maximum drain current",
                "part_id": PART,
                "tables": ["max_ratings", "electrical_characteristics"],
                "top_k": 3,
            },
        ),
        (
            "圖表搜尋",
            {"question": "gate charge curve", "part_id": PART,
             "tables": ["typical_charts"], "top_k": 3},
        ),
        (
            "不指定 part_id（搜全庫）",
            {"question": "thermal resistance junction to ambient", "top_k": 3},
        ),
    ]

    for title, kwargs in samples:
        q = kwargs["question"]
        print(f"{'─' * 60}")
        print(f"範例：{title}")
        print(f"問題：{q}")
        print()
        results = search(**kwargs)
        print(format_context(results))
        print()

    # --- 取原始 dict 做進一步處理 ---
    print("─" * 60)
    print("取原始 dict（直接存取欄位）")
    results = search("breakdown voltage", part_id=PART,
                     tables=["max_ratings"], top_k=2)
    for r in results:
        print(f"  symbol={r['symbol']}, value={r['value_raw']} {r['unit']}, "
              f"score={r['_score']:.3f}")
