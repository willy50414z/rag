# -*- coding: utf-8 -*-
"""
Per-record text representation logic for embedding generation.

Defines how each table's record is converted to a string before encoding.
Pure functions — no model dependency, no side effects.

Public API:
    to_embed_text(record: dict, table: str) -> str
"""


def to_embed_text(record: dict, table: str) -> str:
    """Return the text used to embed a single record from *table*."""
    fn = _TABLE_FUNCS.get(table)
    if fn is None:
        raise ValueError(
            f"No text representation defined for table {table!r}. "
            f"Supported tables: {sorted(_TABLE_FUNCS)}"
        )
    return fn(record)


def _max_ratings(r: dict) -> str:
    cond = f", {r['condition_raw']}" if r["condition_raw"] else ""
    return f"{r['symbol']} {r['parameter']}: {r['value_raw']} {r['unit']}{cond}"


def _thermal_characteristics(r: dict) -> str:
    return f"{r['symbol']} {r['parameter']}: {r['typ']} {r['unit']}"


def _electrical_characteristics(r: dict) -> str:
    nums = []
    if r["typ"] is not None:
        nums.append(f"typ={r['typ']}")
    if r["max"] is not None:
        nums.append(f"max={r['max']}")
    if r["min"] is not None:
        nums.append(f"min={r['min']}")
    cond = f", {r['condition_raw']}" if r["condition_raw"] else ""
    return (
        f"[{r['section']}] {r['symbol']} {r['parameter']}{cond}: "
        f"{' '.join(nums)} {r['unit']}"
    )


def _typical_charts(r: dict) -> str:
    return r["caption"]


def _footnotes(r: dict) -> str:
    return f"Note {r['marker']}: {r['text']}"


_TABLE_FUNCS: dict = {
    "max_ratings":                _max_ratings,
    "thermal_characteristics":    _thermal_characteristics,
    "electrical_characteristics": _electrical_characteristics,
    "typical_charts":             _typical_charts,
    "footnotes":                  _footnotes,
}
