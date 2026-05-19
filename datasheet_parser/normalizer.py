# -*- coding: utf-8 -*-
"""
Cross-parser symbol & condition normalization layer.

責任切分：
  - parser (vdsemi_parser 等)：忠實讀取 PDF，輸出原始 parsed dict
  - THIS MODULE：跨 vendor 統一的 symbol / condition / package / channel 正規化
  - db/upserts：純寫入，不做語意轉換

主要對外 API：
    normalize_parsed(parsed: dict) -> dict
        在 parser.parse() 之後、import_pipeline 入庫之前呼叫。
        回傳新的 dict，不修改原始輸入。

新增 symbol 對應規則：在 SYMBOL_CANON 或 SYMBOL_PATTERN_RULES 增加一條。
新增 package：在 PACKAGE_WHITELIST 增加一條，並同步更新 db/schema.sql seed data。
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Symbol 白名單（exact match → canonical）
# ---------------------------------------------------------------------------

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

SYMBOL_PATTERN_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"TSTG", re.IGNORECASE), "TSTG,TJ"),
]

# ---------------------------------------------------------------------------
# Package 白名單與 alias mapping
# ---------------------------------------------------------------------------
# PACKAGE_WHITELIST：必須與 db/schema.sql 的 package_types seed data 保持一致。
# PACKAGE_ALIAS：PDF 原始值 → 白名單 canonical value 的 mapping。
#   新增 PDF 出現的變體時只需在 PACKAGE_ALIAS 加一條，不需動白名單或 DB。

PACKAGE_WHITELIST: frozenset[str] = frozenset([
    "TO-252",
    "TO-263",
    "TO-263-6L",
    "PDFN5*6",
    "TO-220",
    "TO-220F",
    "TOLT",
    "TOLL",
    "TO-220AB",
    "PDFN3*3",
])

PACKAGE_ALIAS: dict[str, str] = {
    "PDFN5060X": "PDFN5*6",
    "PDFN5x6": "PDFN5*6",
    "PDFN3333": "PDFN3*3",
}

# ---------------------------------------------------------------------------
# Channel topology / polarity 正規化
# ---------------------------------------------------------------------------

_TOPOLOGY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bComp2\b",        re.IGNORECASE), "Comp2"),
    (re.compile(r"\bComplementary\b",re.IGNORECASE), "Comp"),
    (re.compile(r"\bComp\b",         re.IGNORECASE), "Comp"),
    (re.compile(r"\bAsymmetric\b",   re.IGNORECASE), "Asymmetric"),
    (re.compile(r"\bDual\b",         re.IGNORECASE), "Dual"),
]

_POLARITY_RE = re.compile(r"\b([NP])[- ]?(?:Channel|CH|Type|ch)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# 核心正規化函式
# ---------------------------------------------------------------------------

def normalize_symbol(symbol: str) -> str:
    canon = SYMBOL_CANON.get(symbol)
    if canon is not None:
        return canon
    for pattern, replacement in SYMBOL_PATTERN_RULES:
        if pattern.search(symbol):
            return replacement
    return symbol


def normalize_package(package: str) -> str:
    """將 PDF 原始 package 值 alias mapping 後驗證在白名單內，回傳 canonical value。"""
    canonical = PACKAGE_ALIAS.get(package, package)
    if canonical not in PACKAGE_WHITELIST:
        raise ValueError(
            f"Package {package!r} 不在白名單內，也無對應 alias。"
            f"已知 package：{sorted(PACKAGE_WHITELIST)}"
        )
    return canonical


def normalize_channel(raw: str) -> tuple[str, str]:
    """
    將原始 channel 字串（來自 PDF header 或 V(BR)DSS fallback）
    映射為 (topology, polarity)。

    topology ∈ {'Single','Dual','Comp','Comp2','Asymmetric'}
    polarity ∈ {'N','P'}

    無法識別時拋出 ValueError。
    """
    # Polarity
    m = _POLARITY_RE.search(raw)
    if m is None:
        # 允許僅有 "N" 或 "P" 的極簡格式（來自 V(BR)DSS fallback）
        stripped = raw.strip().upper()
        if stripped in ("N", "P"):
            polarity = stripped
        else:
            raise ValueError(
                f"無法從 {raw!r} 識別 channel polarity (N/P)。"
                "請確認 PDF header 含有 'N-Channel' 或 'P-Channel' 字樣。"
            )
    else:
        polarity = m.group(1).upper()

    # Topology（找不到則預設 Single）
    topology = "Single"
    for pattern, topo_value in _TOPOLOGY_PATTERNS:
        if pattern.search(raw):
            topology = topo_value
            break

    return topology, polarity


# ---------------------------------------------------------------------------
# 內部正規化邏輯
# ---------------------------------------------------------------------------

def _norm_rows(rows: list[dict]) -> list[dict]:
    result = []
    for r in rows:
        if "symbol" in r and isinstance(r["symbol"], str):
            normalized = normalize_symbol(r["symbol"])
            if normalized != r["symbol"]:
                r = dict(r)
                r["symbol"] = normalized
        result.append(r)
    return result


def _norm_parts(rows: list[dict]) -> list[dict]:
    """驗證並正規化 parts 的 package 和 channel 欄位。"""
    result = []
    for r in rows:
        r = dict(r)
        # package alias mapping + 白名單驗證
        pkg = r.get("package", "")
        r["package"] = normalize_package(pkg)

        # channel 正規化：parser 輸出 raw_channel，轉為 topology + polarity
        raw_ch = r.pop("raw_channel", None)
        if raw_ch is not None and "topology" not in r:
            r["topology"], r["polarity"] = normalize_channel(raw_ch)

        # 驗證 topology / polarity 已存在且合法
        topology = r.get("topology", "")
        polarity = r.get("polarity", "")
        valid_topologies = {"Single", "Dual", "Comp", "Comp2", "Asymmetric"}
        if topology not in valid_topologies:
            raise ValueError(
                f"非法 topology {topology!r}。已知：{sorted(valid_topologies)}"
            )
        if polarity not in ("N", "P"):
            raise ValueError(
                f"非法 polarity {polarity!r}。必須為 'N' 或 'P'。"
            )
        result.append(r)
    return result


def normalize_parsed(parsed: dict) -> dict:
    """
    對 parser.parse() 的輸出套用跨 parser 正規化規則。

    執行：
      - parts 的 package 白名單驗證（hard error）
      - parts 的 channel → topology + polarity 正規化
      - 所有表的 symbol 欄位套用 normalize_symbol()

    回傳新的 dict（淺複製 tables layer，不修改原始輸入）。
    """
    tables = parsed.get("tables", {})
    new_tables = {}
    for tname, rows in tables.items():
        if not isinstance(rows, list):
            new_tables[tname] = rows
            continue
        if tname == "parts":
            new_tables[tname] = _norm_parts(rows)
        else:
            new_tables[tname] = _norm_rows(rows)
    return {**parsed, "tables": new_tables}
