# -*- coding: utf-8 -*-
"""
Cross-parser symbol & condition normalization layer.

責任切分：
  - parser (vdsemi_parser 等)：忠實讀取 PDF，輸出原始 parsed dict
  - THIS MODULE：跨 vendor 統一的 symbol / condition 正規化
  - db/upserts：純寫入，不做語意轉換

主要對外 API：
    normalize_parsed(parsed: dict) -> dict
        在 parser.parse() 之後、import_pipeline 入庫之前呼叫。
        回傳新的 dict，不修改原始輸入。

新增 symbol 對應規則：在 SYMBOL_CANON 或 SYMBOL_PATTERN_RULES 增加一條，
不需要修改任何 parser。
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Symbol 白名單（exact match → canonical）
# ---------------------------------------------------------------------------
# 規則：key = parser 可能產出的原始 symbol，value = 入庫的標準 symbol
# 新增規則時只要在這裡加一行，所有 parser 都自動受益。

SYMBOL_CANON: dict[str, str] = {
    # Switching time symbols（大小寫差異）
    "Td(on)":  "td(on)",
    "Td(off)": "td(off)",
    "Tf":      "tf",
    "Tr":      "tr",
    # Gate threshold（大小寫差異）
    "VGS(TH)": "VGS(th)",
    # Temperature range（順序 / 空白 / subscript 差異）
    "TJ,TSTG":    "TSTG,TJ",
    "T , TSTG J": "TSTG,TJ",
    "T TSTG J":   "TSTG,TJ",
}

# ---------------------------------------------------------------------------
# Symbol Pattern Rules（regex → canonical，無法用 exact match 覆蓋的情況）
# ---------------------------------------------------------------------------
# 每條規則為 (compiled_pattern, canonical_symbol)
# 按順序嘗試，第一條匹配的 wins。

SYMBOL_PATTERN_RULES: list[tuple[re.Pattern, str]] = [
    # 任何仍含 TSTG 的變體（SYMBOL_CANON 未覆蓋到的邊緣情況）
    (re.compile(r"TSTG", re.IGNORECASE), "TSTG,TJ"),
]


# ---------------------------------------------------------------------------
# 核心正規化邏輯
# ---------------------------------------------------------------------------

def normalize_symbol(symbol: str) -> str:
    """
    將單一 symbol 字串映射到標準形式。

    優先順序：
      1. SYMBOL_CANON exact match
      2. SYMBOL_PATTERN_RULES（regex）
      3. 原樣回傳
    """
    canon = SYMBOL_CANON.get(symbol)
    if canon is not None:
        return canon

    for pattern, replacement in SYMBOL_PATTERN_RULES:
        if pattern.search(symbol):
            return replacement

    return symbol


def _norm_rows(rows: list[dict]) -> list[dict]:
    """Apply normalize_symbol to the 'symbol' field of each row."""
    result = []
    for r in rows:
        if "symbol" in r and isinstance(r["symbol"], str):
            normalized = normalize_symbol(r["symbol"])
            if normalized != r["symbol"]:
                r = dict(r)
                r["symbol"] = normalized
        result.append(r)
    return result


def normalize_parsed(parsed: dict) -> dict:
    """
    對 parser.parse() 的輸出套用跨 parser 正規化規則。

    目前執行：
      - 所有表的 symbol 欄位套用 normalize_symbol()

    回傳新的 dict（淺複製 tables layer，不修改原始輸入）。
    """
    tables = parsed.get("tables", {})
    new_tables = {
        tname: _norm_rows(rows) if isinstance(rows, list) else rows
        for tname, rows in tables.items()
    }
    return {**parsed, "tables": new_tables}
