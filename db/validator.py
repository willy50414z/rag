# -*- coding: utf-8 -*-
"""
Phase 6 Validation System: datasheet import pipeline 的資料驗證層。

驗證分三層：
  Layer 1 - 格式驗證：欄位存在、型別正確、值非空、字元異常偵測
  Layer 2 - 業務邏輯：跨欄位一致性、condition round-trip、batch 內重複 key
  Layer 3 - 信心評估：依完整度算出 confidence score，低於閾值進 review queue

公開 API：
    validate_parsed(parsed)  -> ValidationResult
    ValidationResult         -- 含 valid, errors, warnings, confidence, review_required
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

# ---- 常數 ----------------------------------------------------------------

REVIEW_THRESHOLD = 0.70
REQUIRED_SECTIONS = {"Static", "Dynamic", "Switching", "DiodeCharacteristics"}

# PUA block U+E000 to U+F8FF：用 chr() 構建，避免 source file 的 Unicode 編碼問題
# parser._PUA_MAP 只映射 2 個字符，其餘 PUA 字符會直接穿透進欄位值
_PUA_RE = re.compile("[" + chr(0xE000) + "-" + chr(0xF8FF) + "]")

# 非列印控制字符（不含 \t \n \r，這些在 condition 原始文字中可能合法出現）
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# symbol 和 unit 不應含有換行或 tab（parser 應已清除但可能漏網）
_NEWLINE_RE = re.compile(r"[\n\r\t]")


# ---- 資料結構 ------------------------------------------------------------

@dataclass
class ValidationIssue:
    layer: int           # 1=格式  2=業務邏輯  3=信心
    table: str
    row_index: int | None
    field: str
    message: str

    def __str__(self) -> str:
        loc = (f"{self.table}[{self.row_index}].{self.field}"
               if self.row_index is not None
               else f"{self.table}.{self.field}")
        return f"[Layer{self.layer}] {loc}: {self.message}"


@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    confidence: float = 1.0
    review_required: bool = False

    def summary(self) -> str:
        lines = [
            f"valid={self.valid}  confidence={self.confidence:.2f}  "
            f"review_required={self.review_required}",
            f"errors={len(self.errors)}  warnings={len(self.warnings)}",
        ]
        for e in self.errors:
            lines.append(f"  ERROR   {e}")
        for w in self.warnings:
            lines.append(f"  WARNING {w}")
        return "\n".join(lines)


# ---- 內部輔助 ------------------------------------------------------------

def _require_str(val: Any, table: str, idx: int | None, fname: str,
                 errors: list) -> bool:
    if not isinstance(val, str) or not val.strip():
        errors.append(ValidationIssue(1, table, idx, fname,
                                      "必填字串欄位為空或非字串"))
        return False
    return True


def _require_int_or_str_int(val: Any, table: str, idx: int | None, fname: str,
                             errors: list) -> bool:
    if val is None:
        errors.append(ValidationIssue(1, table, idx, fname, "必填欄位為 None"))
        return False
    try:
        int(val)
    except (TypeError, ValueError):
        errors.append(ValidationIssue(1, table, idx, fname,
                                      f"預期可轉為 int，實際值：{val!r}"))
        return False
    return True


def _valid_json_str(val: str | None) -> bool:
    if val is None:
        return True
    try:
        json.loads(val)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def _check_anomalous_chars(val: str, table: str, idx: int | None, fname: str,
                            warnings: list, strict_newline: bool = False) -> None:
    """
    掃描欄位值是否含有：
      - PUA 字符（U+E000-U+F8FF）：代表 _PUA_MAP 未映射的 parser artifact
      - 非列印控制字符
      - 換行 / tab（對 symbol / unit 欄位開啟 strict_newline=True）
    """
    pua = _PUA_RE.findall(val)
    if pua:
        uniq = list(dict.fromkeys(pua))
        codes = [hex(ord(c)) for c in uniq]
        warnings.append(ValidationIssue(1, table, idx, fname,
                                         f"含有未映射 PUA 字符 {codes}，"
                                         f"可能是 parser._PUA_MAP 遺漏項目"))

    ctrl = _CTRL_RE.findall(val)
    if ctrl:
        codes = [hex(ord(c)) for c in ctrl]
        warnings.append(ValidationIssue(1, table, idx, fname,
                                         f"含有非列印控制字符 {codes}"))

    if strict_newline and _NEWLINE_RE.search(val):
        warnings.append(ValidationIssue(1, table, idx, fname,
                                         "含有未清除的換行 / tab（parser 應已 strip）"))


# ---- Layer 1：格式驗證 ---------------------------------------------------

def _validate_parts(rows: list[dict], errors: list, warnings: list) -> int:
    score = 0
    for i, r in enumerate(rows):
        ok = True
        ok &= _require_str(r.get("part_id"), "parts", i, "part_id", errors)
        ok &= _require_str(r.get("package"), "parts", i, "package", errors)
        ok &= _require_int_or_str_int(r.get("source_page"), "parts", i,
                                      "source_page", errors)
        if r.get("marking") is not None and not isinstance(r["marking"], str):
            warnings.append(ValidationIssue(1, "parts", i, "marking",
                                            "marking 應為字串或 None"))
        pid = r.get("part_id", "")
        if pid == "UNKNOWN":
            warnings.append(ValidationIssue(1, "parts", i, "part_id",
                                            "part_id 為 'UNKNOWN'：parser 未能從頁面標題抽取，"
                                            "請確認 PDF 第一頁格式"))
        if isinstance(pid, str):
            _check_anomalous_chars(pid, "parts", i, "part_id", warnings)
        score += 1 if ok else 0
    return score


def _validate_max_ratings(rows: list[dict], errors: list, warnings: list) -> int:
    score = 0
    for i, r in enumerate(rows):
        ok = True
        ok &= _require_str(r.get("part_id"),   "max_ratings", i, "part_id", errors)
        ok &= _require_str(r.get("symbol"),    "max_ratings", i, "symbol", errors)
        ok &= _require_str(r.get("parameter"), "max_ratings", i, "parameter", errors)
        ok &= _require_str(r.get("value_raw"), "max_ratings", i, "value_raw", errors)
        ok &= _require_str(r.get("unit"),      "max_ratings", i, "unit", errors)
        ok &= _require_int_or_str_int(r.get("source_page"), "max_ratings", i,
                                      "source_page", errors)

        if not _valid_json_str(r.get("condition_kv")):
            errors.append(ValidationIssue(1, "max_ratings", i, "condition_kv",
                                          "condition_kv 不是合法 JSON 字串"))
            ok = False

        for fname in ("symbol", "unit"):
            v = r.get(fname)
            if isinstance(v, str):
                _check_anomalous_chars(v, "max_ratings", i, fname, warnings,
                                       strict_newline=True)
        for fname in ("parameter", "condition_raw"):
            v = r.get(fname)
            if isinstance(v, str):
                _check_anomalous_chars(v, "max_ratings", i, fname, warnings)

        score += 1 if ok else 0
    return score


def _validate_thermal(rows: list[dict], errors: list, warnings: list) -> int:
    score = 0
    for i, r in enumerate(rows):
        ok = True
        ok &= _require_str(r.get("part_id"),   "thermal_characteristics", i, "part_id", errors)
        ok &= _require_str(r.get("symbol"),    "thermal_characteristics", i, "symbol", errors)
        ok &= _require_str(r.get("parameter"), "thermal_characteristics", i, "parameter", errors)
        ok &= _require_str(r.get("unit"),      "thermal_characteristics", i, "unit", errors)

        typ = r.get("typ")
        if typ is None:
            warnings.append(ValidationIssue(1, "thermal_characteristics", i, "typ",
                                            "typ 為 None，可能抽取失敗"))
        elif not isinstance(typ, (int, float)):
            warnings.append(ValidationIssue(1, "thermal_characteristics", i, "typ",
                                            f"typ 應為數字，實際型別：{type(typ).__name__}，值：{typ!r}"))

        for fname in ("symbol", "unit"):
            v = r.get(fname)
            if isinstance(v, str):
                _check_anomalous_chars(v, "thermal_characteristics", i, fname, warnings,
                                       strict_newline=True)

        score += 1 if ok else 0
    return score


def _validate_electrical(rows: list[dict], errors: list, warnings: list) -> int:
    score = 0
    for i, r in enumerate(rows):
        ok = True
        ok &= _require_str(r.get("part_id"),   "electrical_characteristics", i, "part_id", errors)
        ok &= _require_str(r.get("symbol"),    "electrical_characteristics", i, "symbol", errors)
        ok &= _require_str(r.get("parameter"), "electrical_characteristics", i, "parameter", errors)
        ok &= _require_str(r.get("unit"),      "electrical_characteristics", i, "unit", errors)

        section = r.get("section")
        if not isinstance(section, str) or not section.strip():
            errors.append(ValidationIssue(1, "electrical_characteristics", i, "section",
                                          "section 為空或非字串"))
            ok = False

        if r.get("min") is None and r.get("typ") is None and r.get("max") is None:
            warnings.append(ValidationIssue(1, "electrical_characteristics", i,
                                            "min/typ/max", "min/typ/max 全為 None"))

        if not _valid_json_str(r.get("condition_kv")):
            errors.append(ValidationIssue(1, "electrical_characteristics", i,
                                          "condition_kv",
                                          "condition_kv 不是合法 JSON 字串"))
            ok = False

        for fname in ("symbol", "unit"):
            v = r.get(fname)
            if isinstance(v, str):
                _check_anomalous_chars(v, "electrical_characteristics", i, fname, warnings,
                                       strict_newline=True)
        for fname in ("parameter", "condition_raw"):
            v = r.get(fname)
            if isinstance(v, str):
                _check_anomalous_chars(v, "electrical_characteristics", i, fname, warnings)

        score += 1 if ok else 0
    return score


def _validate_charts(rows: list[dict], errors: list, warnings: list) -> int:
    score = 0
    for i, r in enumerate(rows):
        ok = True
        ok &= _require_str(r.get("part_id"),   "typical_charts", i, "part_id", errors)
        ok &= _require_str(r.get("caption"),   "typical_charts", i, "caption", errors)
        ok &= _require_str(r.get("minio_key"), "typical_charts", i, "minio_key", errors)
        ok &= _require_int_or_str_int(r.get("source_page"), "typical_charts", i,
                                      "source_page", errors)
        score += 1 if ok else 0
    return score


def _validate_footnotes(footnotes: dict, errors: list, warnings: list) -> int:
    score = 0
    for marker, text in footnotes.items():
        ok = True
        if not isinstance(marker, str) or not marker.strip():
            errors.append(ValidationIssue(1, "footnotes", None, "marker",
                                          f"marker 非字串或空：{marker!r}"))
            ok = False
        if not isinstance(text, str) or not text.strip():
            errors.append(ValidationIssue(1, "footnotes", None, "text",
                                          f"marker={marker!r} 的 text 為空"))
            ok = False
        score += 1 if ok else 0
    return score


# ---- Layer 2：業務邏輯驗證 ----------------------------------------------

def _cross_validate_max_ratings(rows: list[dict], errors: list,
                                 warnings: list) -> None:
    for i, r in enumerate(rows):
        mn  = r.get("value_min")
        num = r.get("value_num")
        mx  = r.get("value_max_num")
        if mn is not None and num is not None:
            try:
                if float(mn) > float(num):
                    warnings.append(ValidationIssue(2, "max_ratings", i,
                                                    "value_min/value_num",
                                                    f"value_min({mn}) > value_num({num})"))
            except (TypeError, ValueError):
                pass
        if mn is not None and mx is not None:
            try:
                if float(mn) > float(mx):
                    errors.append(ValidationIssue(2, "max_ratings", i,
                                                  "value_min/value_max_num",
                                                  f"value_min({mn}) > value_max_num({mx})"))
            except (TypeError, ValueError):
                pass


def _cross_validate_electrical(rows: list[dict], errors: list,
                                warnings: list) -> None:
    for i, r in enumerate(rows):
        mn  = r.get("min")
        mx  = r.get("max")
        section = r.get("section", "")

        if mn is not None and mx is not None:
            try:
                if float(mn) > float(mx):
                    errors.append(ValidationIssue(2, "electrical_characteristics", i,
                                                  "min/max",
                                                  f"min({mn}) > max({mx})"))
            except (TypeError, ValueError):
                pass

        if section and section not in REQUIRED_SECTIONS:
            warnings.append(ValidationIssue(2, "electrical_characteristics", i,
                                            "section",
                                            f"未知 section：{section!r}，"
                                            f"已知：{sorted(REQUIRED_SECTIONS)}"))


def _cross_validate_parts_consistency(tables: dict, errors: list,
                                      warnings: list) -> None:
    """各子表的 part_id 應與 parts[0].part_id 一致。"""
    parts = tables.get("parts", [])
    if not parts:
        return
    expected_id = parts[0].get("part_id", "")
    for tname in ("max_ratings", "thermal_characteristics",
                  "electrical_characteristics", "typical_charts"):
        for i, r in enumerate(tables.get(tname, [])):
            if r.get("part_id") != expected_id:
                errors.append(ValidationIssue(2, tname, i, "part_id",
                                              f"part_id={r.get('part_id')!r} "
                                              f"與 parts[0].part_id={expected_id!r} 不符"))


def _check_condition_consistency(rows: list[dict], table_name: str,
                                  warnings: list) -> None:
    """
    驗證 condition_kv (JSON 字串) 與 condition_normalized 的一致性。

    upserts.py 以 condition_normalized 當 conflict key。若兩者不一致，
    代表 parser 在計算 normalized 時路徑有分歧，可能導致重複入庫或 key collision。
    """
    for i, r in enumerate(rows):
        kv_str = r.get("condition_kv")
        stored_norm = r.get("condition_normalized") or ""

        if kv_str is None:
            if stored_norm:
                warnings.append(ValidationIssue(2, table_name, i,
                                                "condition_normalized",
                                                f"condition_kv 為 None 但 "
                                                f"condition_normalized={stored_norm!r}（預期為空）"))
            continue

        try:
            kv = json.loads(kv_str)
        except json.JSONDecodeError:
            continue  # 已由 Layer 1 捕捉

        expected_norm = ",".join(
            f"{k}={v}" for k, v in sorted(kv.items()) if k != "_raw"
        )
        if expected_norm != stored_norm:
            warnings.append(ValidationIssue(2, table_name, i,
                                            "condition_normalized",
                                            f"stored={stored_norm!r} 但從 condition_kv "
                                            f"重新計算得 {expected_norm!r}；"
                                            f"upserts 以此欄位為 conflict key"))


def _check_duplicate_keys(rows: list[dict], table_name: str,
                           warnings: list) -> None:
    """
    偵測同一 batch 內 (part_id, symbol, condition_normalized) 重複的 row。

    upserts.py 會靜默去重（last-writer-wins），呼叫端無法得知哪些 row 被覆蓋。
    此處提前警告，讓操作者確認 parser 是否產生非預期的重複 row。
    """
    seen: dict[tuple, int] = {}
    for i, r in enumerate(rows):
        key = (
            r.get("part_id", ""),
            r.get("symbol", ""),
            r.get("condition_normalized") or "",
        )
        if key in seen:
            warnings.append(ValidationIssue(2, table_name, i,
                                            "symbol/condition_normalized",
                                            f"與 row[{seen[key]}] 重複 key={key}；"
                                            f"upsert 時 row[{seen[key]}] 將被此 row 覆蓋"))
        seen[key] = i


# ---- Layer 3：Confidence Scoring ----------------------------------------

def _calc_confidence(parsed: dict, warnings: list[ValidationIssue]) -> float:
    """
    依資料完整度計算 0.0 ~ 1.0 的信心分數。

    規則：
      - parts 有資料：+0.15
      - max_ratings 有資料：+0.20
      - thermal 有資料：+0.15
      - electrical 有資料：+0.25
      - typical_charts 有資料：+0.15
      - footnotes 有資料：+0.10
      每個 warning 扣 0.03（上限 -0.30）
    """
    tables = parsed.get("tables", {})
    score = 0.0
    weights = {
        "parts":                      0.15,
        "max_ratings":                0.20,
        "thermal_characteristics":    0.15,
        "electrical_characteristics": 0.25,
        "typical_charts":             0.15,
    }
    for tname, w in weights.items():
        if tables.get(tname):
            score += w
    if parsed.get("footnotes"):
        score += 0.10

    penalty = min(len(warnings) * 0.03, 0.30)
    return max(0.0, round(score - penalty, 4))


# ---- 公開入口 ------------------------------------------------------------

def validate_parsed(parsed: dict) -> ValidationResult:
    """
    驗證 parser.parse() 的輸出。

    三層檢查順序：
      Layer 1 (格式) 全部跑完 → Layer 2 (業務邏輯，含字元 / condition 一致性 / 重複 key)
      → Layer 3 (confidence scoring)

    Layer 2 不因 Layer 1 有 error 而跳過；condition 一致性與 dup-key 屬於
    獨立的資料品質檢查，即使 Layer 1 發現格式問題也要執行。

    Args:
        parsed: {"tables": {...}, "footnotes": {...}}

    Returns:
        ValidationResult — 含 valid, errors, warnings, confidence, review_required
    """
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    tables    = parsed.get("tables", {})
    footnotes = parsed.get("footnotes", {})

    # -- 頂層結構
    if not isinstance(tables, dict):
        errors.append(ValidationIssue(1, "parsed", None, "tables",
                                      "parsed['tables'] 不是 dict"))
        return ValidationResult(valid=False, errors=errors)

    if not tables.get("parts"):
        errors.append(ValidationIssue(1, "parts", None, "parts",
                                      "parts 表為空，無法確認 part_id"))

    # -- 空表警告（max_ratings / electrical 為核心表，空資料通常代表 parser 錨點失敗）
    for tname in ("max_ratings", "electrical_characteristics"):
        if not tables.get(tname):
            warnings.append(ValidationIssue(1, tname, None, "(table)",
                                            f"{tname} 為空，可能是 parser 未找到對應表格錨點"))

    # ---- Layer 1
    _validate_parts(tables.get("parts", []), errors, warnings)
    _validate_max_ratings(tables.get("max_ratings", []), errors, warnings)
    _validate_thermal(tables.get("thermal_characteristics", []), errors, warnings)
    _validate_electrical(tables.get("electrical_characteristics", []), errors, warnings)
    _validate_charts(tables.get("typical_charts", []), errors, warnings)
    _validate_footnotes(footnotes, errors, warnings)

    # ---- Layer 2（包含 min/max 一致性、condition round-trip、重複 key、part_id 一致性）
    _cross_validate_max_ratings(tables.get("max_ratings", []), errors, warnings)
    _cross_validate_electrical(tables.get("electrical_characteristics", []),
                               errors, warnings)
    _cross_validate_parts_consistency(tables, errors, warnings)

    for tname in ("max_ratings", "electrical_characteristics"):
        _check_condition_consistency(tables.get(tname, []), tname, warnings)
        _check_duplicate_keys(tables.get(tname, []), tname, warnings)

    # ---- Layer 3
    confidence      = _calc_confidence(parsed, warnings)
    review_required = confidence < REVIEW_THRESHOLD or bool(errors)

    return ValidationResult(
        valid=not bool(errors),
        errors=errors,
        warnings=warnings,
        confidence=confidence,
        review_required=review_required,
    )
