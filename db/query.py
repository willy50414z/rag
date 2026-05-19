# -*- coding: utf-8 -*-
"""
Datasheet RAG query functions.

Usage:
    from db.query import search, format_context

    results = search("RDS(ON) at high temperature", part_number="VSP007N06MS-G")
    results = search("drain current", part_number="LJ4525", polarity="N")
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
# All queries JOIN parts to surface part_number, topology, polarity.
# WHERE filters use p.part_number / p.topology / p.polarity.
# ---------------------------------------------------------------------------

_TABLE_QUERIES = {
    "electrical_characteristics": """
        SELECT
            'electrical_characteristics'  AS _table,
            1 - (e.embedding <=> %(vec)s::vector)   AS _score,
            p.part_number, p.topology, p.polarity,
            e.symbol, e.parameter, e.section,
            e.condition_raw, e.condition_normalized,
            e.min, e.typ, e.max, e.value_raw, e.unit,
            e.footnote_ref, e.source_page
        FROM electrical_characteristics e
        JOIN parts p ON p.id = e.part_id
        {where}
        ORDER BY e.embedding <=> %(vec)s::vector
        LIMIT %(k)s
    """,
    "max_ratings": """
        SELECT
            'max_ratings'                 AS _table,
            1 - (m.embedding <=> %(vec)s::vector)   AS _score,
            p.part_number, p.topology, p.polarity,
            m.symbol, m.parameter,
            m.condition_raw, m.condition_normalized,
            m.value_raw, m.value_num, m.value_min, m.value_max_num,
            m.unit, m.footnote_ref, m.source_page
        FROM max_ratings m
        JOIN parts p ON p.id = m.part_id
        {where}
        ORDER BY m.embedding <=> %(vec)s::vector
        LIMIT %(k)s
    """,
    "thermal_characteristics": """
        SELECT
            'thermal_characteristics'     AS _table,
            1 - (t.embedding <=> %(vec)s::vector)   AS _score,
            p.part_number, p.topology, p.polarity,
            t.symbol, t.parameter, t.typ, t.unit, t.source_page
        FROM thermal_characteristics t
        JOIN parts p ON p.id = t.part_id
        {where}
        ORDER BY t.embedding <=> %(vec)s::vector
        LIMIT %(k)s
    """,
    "typical_charts": """
        SELECT
            'typical_charts'              AS _table,
            1 - (c.embedding <=> %(vec)s::vector)   AS _score,
            p.part_number, p.topology, p.polarity,
            c.caption, c.minio_key, c.source_page
        FROM typical_charts c
        JOIN parts p ON p.id = c.part_id
        {where}
        ORDER BY c.embedding <=> %(vec)s::vector
        LIMIT %(k)s
    """,
    "footnotes": """
        SELECT
            'footnotes'                   AS _table,
            1 - (f.embedding <=> %(vec)s::vector)   AS _score,
            p.part_number, p.topology, p.polarity,
            f.marker, f.text
        FROM footnotes f
        JOIN parts p ON p.id = f.part_id
        {where}
        ORDER BY f.embedding <=> %(vec)s::vector
        LIMIT %(k)s
    """,
}


# ---------------------------------------------------------------------------
# Core search
# ---------------------------------------------------------------------------

def search(
    question: str,
    part_number: str | None = None,
    topology: str | None = None,
    polarity: str | None = None,
    tables: list[str] | None = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Semantic search across datasheet tables.

    Args:
        question:    Natural language query.
        part_number: Filter to a specific part number (e.g. "VSP007N06MS-G").
                     None = search all parts.
        topology:    Filter to channel topology ('Single','Dual','Comp','Comp2','Asymmetric').
                     None = no filter.
        polarity:    Filter to channel polarity ('N' or 'P').
                     None = no filter.
        tables:      Subset of tables to search. None = all tables.
        top_k:       Number of results to return (after merging all tables).

    Returns:
        List of result dicts sorted by similarity score (highest first).
        Each dict has '_table', '_score', 'part_number', 'topology', 'polarity'
        plus all columns of that table.
    """
    target_tables = tables or list(_TABLE_QUERIES.keys())

    vec_list = _model().encode(question).tolist()
    vec_str  = "[" + ",".join(str(x) for x in vec_list) + "]"

    # Build WHERE clause
    conditions = []
    if part_number:
        conditions.append("p.part_number = %(part_number)s")
    if topology:
        conditions.append("p.topology = %(topology)s::channel_topology")
    if polarity:
        conditions.append("p.polarity = %(polarity)s::channel_polarity")
    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    params = {
        "vec":         vec_str,
        "k":           top_k,
        "part_number": part_number,
        "topology":    topology,
        "polarity":    polarity,
    }

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
        tbl      = r["_table"]
        score    = r["_score"]
        pnum     = r.get("part_number", "")
        channel  = f"{r.get('topology','')} {r.get('polarity','')}".strip()
        part_str = f"{pnum} [{channel}]" if channel else pnum

        if tbl == "electrical_characteristics":
            cond = f", {r['condition_raw']}" if r.get("condition_raw") else ""
            nums = []
            if r.get("min") is not None: nums.append(f"min={r['min']}")
            if r.get("typ") is not None: nums.append(f"typ={r['typ']}")
            if r.get("max") is not None: nums.append(f"max={r['max']}")
            if r.get("value_raw"):        nums.append(r["value_raw"])
            lines.append(
                f"[{score:.2f}] {part_str} | {r['section']} | "
                f"{r['symbol']} {r['parameter']}{cond}: "
                f"{' '.join(nums)} {r['unit']}"
            )

        elif tbl == "max_ratings":
            cond = f", {r['condition_raw']}" if r.get("condition_raw") else ""
            lines.append(
                f"[{score:.2f}] {part_str} | max_rating | "
                f"{r['symbol']} {r['parameter']}{cond}: "
                f"{r['value_raw']} {r['unit']}"
            )

        elif tbl == "thermal_characteristics":
            lines.append(
                f"[{score:.2f}] {part_str} | thermal | "
                f"{r['symbol']} {r['parameter']}: {r['typ']} {r['unit']}"
            )

        elif tbl == "typical_charts":
            lines.append(
                f"[{score:.2f}] {part_str} | chart | "
                f"{r['caption']} → {r['minio_key']}"
            )

        elif tbl == "footnotes":
            lines.append(
                f"[{score:.2f}] {part_str} | note {r['marker']} | {r['text']}"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sample usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    PART = "VSP007N06MS-G"

    samples = [
        # (
        #     "語意搜尋（跨所有 table，top 5）",
        #     {"question": "RDS(ON) at high temperature", "part_number": PART, "top_k": 5},
        # ),
        # (
        #     "只搜 max_ratings + electrical",
        #     {
        #         "question": "maximum drain current",
        #         "part_number": PART,
        #         "tables": ["max_ratings", "electrical_characteristics"],
        #         "top_k": 3,
        #     },
        # ),
        # (
        #     "圖表搜尋",
        #     {"question": "gate charge curve", "part_number": PART,
        #      "tables": ["typical_charts"], "top_k": 3},
        # ),
        # (
        #     "不指定 part_number（搜全庫）",
        #     {"question": "thermal resistance junction to ambient", "top_k": 3},
        # ),
        # (
        #     "只搜 N-channel 零件",
        #     {"question": "breakdown voltage", "polarity": "N", "top_k": 3},
        # ),
        (
            "搜 N-channel 零件的替代料號",
            {"question": "bvdss>=30 & VGS是+-20 & Id約等於40的料號", "polarity": "N", "top_k": 3},
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
