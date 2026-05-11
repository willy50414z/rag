---
name: ppg-apply
description: 讀取 /ppg:propose 產出的 pdf_field_spec.md，實作 pdfplumber-based parser.py（直接讀 PDF，使用 semantic anchor 定位 table）、產生 test_parser.py，並驗證輸出為 DB-ready 的 flat record。當使用者要把 text PDF 的 human-reviewed 規格落成可執行 parser、或要修正 anchor 與 row key 對齊問題時，使用此 skill。
---

# PDF Parser Generator — Apply

讀取欄位規格、實作直接讀 PDF 的 parser、執行驗證、產出 DB-ready 資料。

```text
/ppg:explore  -> 直接讀 PDF，產出分析決策
/ppg:propose  -> 產出 pdf_field_spec.md
/ppg:apply    -> 實作 parser（讀 PDF），驗證輸出
```

本 skill 不重新探索原始 PDF；只把已確認的 spec 落成可重複執行的 parser。

---

## Input

- `pdf-parser-generator/{pdf檔名}/pdf_field_spec.md`
- 原始 PDF 檔案（路徑由 spec 中的「來源檔案」指定）

若 spec 不存在：

> 找不到 apply 所需輸入。請先完成 `/ppg:explore` 與 `/ppg:propose`，產出 `pdf_field_spec.md` 後再執行 apply。

---

## Artifact 責任分工

- `pdf_field_spec.md`：human-reviewed semantic contract，**read-only**
- `parser_spec.json`：可選的機器可讀 spec compile 結果（覆寫）
- `parser.py`：實際 parser code（覆寫）
- `test_parser.py`：測試碼（覆寫）
- `output.json`：執行 parser 的結果，DB 入庫前的 review 用（覆寫）

apply 不修改 `pdf_field_spec.md`。

---

## Step 1：讀取並 compile spec

讀取 `pdf_field_spec.md`，萃取：

- 文件資訊（PDF 路徑、目標用途、文件家族）
- DB Schema（每張 table 的 primary key、欄位、nullable）
- Parser 定位策略（每張 table 的 anchor 與 fallback）
- 欄位處理規則（型別、正規化、forward-fill、特殊處理）
- 跨文件穩定性備註

寫入：

```text
pdf-parser-generator/{pdf檔名}/parser_spec.json
```

格式建議：

```json
{
  "pdf_path": "...",
  "target": "RAG | DB | both",
  "tables": [
    {
      "name": "electrical_characteristics",
      "primary_key": ["part_id", "symbol", "condition"],
      "anchor": {
        "type": "header_text",
        "headers": ["Symbol", "Parameter", "Min", "Typ", "Max", "Unit"],
        "search_pages": [1, 2, 3],
        "fallback": "raise"
      },
      "section_split": {
        "patterns": ["Static Electrical", "Dynamic Electrical", "Switching", "Source-Drain Diode"]
      },
      "fields": [
        {"name": "symbol", "type": "TEXT", "nullable": false, "forward_fill": true},
        ...
      ]
    }
  ]
}
```

若 spec 缺少 anchor 或 row key：

- 在 compile 結果中標記 `unresolved`
- 不腦補；要求 user 回到 `/ppg:propose` 補上

---

## Step 2：實作 parser.py

在 `pdf-parser-generator/{pdf檔名}/parser.py` 產生 parser。

### 核心設計原則

1. **直接讀 PDF**：使用 `pdfplumber.open(pdf_path)`，不依賴中間 JSON
2. **Semantic anchor 定位 table**：用 header row 文字搜尋，不 hardcode `tables[2]`
3. **動態 footnote 抓取**：從頁面文字掃描，不 hardcode footnote dict
4. **輸出 flat record**：DB-ready，每筆對應一個 DB row
5. **Evidence trace**：每筆資料附 `source_page` 與 `table_ref`

### Parser shape

```python
"""
Parser for {pdf_filename}
Generated from: pdf_field_spec.md
"""
import pdfplumber
import re
from pathlib import Path

PDF_PATH = "..."  # from spec


def find_table_by_header(pdf, expected_headers, search_pages=None):
    """Locate a table whose first row matches expected_headers (substring match)."""
    pages = pdf.pages if search_pages is None else [pdf.pages[i-1] for i in search_pages]
    for page in pages:
        for ti, table in enumerate(page.extract_tables()):
            if not table:
                continue
            header_row = [(c or "").strip() for c in table[0]]
            if all(any(h in cell for cell in header_row) for h in expected_headers):
                return page.page_number, ti, table
    return None, None, None


def extract_footnotes_dynamic(pdf):
    """Scan all pages for NOTE: section, build {marker: definition} dict."""
    ...


def parse(pdf_path: str = PDF_PATH) -> dict:
    """
    Returns:
        {
            "tables": {
                "electrical_characteristics": [
                    {"part_id": ..., "symbol": ..., "condition": ...,
                     "min": ..., "typ": ..., "max": ..., "unit": ...,
                     "section": ..., "footnote_ref": ...,
                     "source_page": ..., "table_ref": ...},
                    ...
                ],
                ...
            },
            "footnotes": {"①": "...", ...},
            "warnings": [...]
        }
    """
    ...
```

### 實作規則

- **Anchor first**：每張 table 用 anchor 找，不靠 index
- **Forward-fill**：spec 標記為 `forward_fill: true` 的欄位，當 cell 為 null 時繼承上列
- **Section 偵測**：用 `section_split.patterns` 比對 row 文字判斷是否為 section header
- **Footnote 動態抓取**：必須包含掃描頁面文字的 `extract_footnotes_dynamic`
- **特殊字元正規化**：依 spec 規則（℃→°C、Ohm→Ω 等）
- **Evidence trace**：每筆 record 附 `source_page` 與 `table_ref`（如 `P2-T0`）
- 不從 spec 中遺漏的欄位產生輸出
- `nullable: false` 且缺值時，加入 warnings，不靜默通過

---

## Step 3：產生 test_parser.py

在 `pdf-parser-generator/{pdf檔名}/test_parser.py` 產生測試。

### 測試重點

不只驗 `value == expected_value`，還要驗：

- **Row count**：每張 table 的列數符合預期
- **Primary key 唯一**：no duplicate row key
- **Required 欄位非 null**：spec 標記 `nullable: false` 的欄位確實有值
- **Anchor 找得到**：assertEqual `find_table_by_header` 回傳非 None
- **Footnote 動態抓取正確**：偵測到的 footnote 數量與 spec 一致
- **Evidence trace 存在**：每筆 record 都有 `source_page` 與 `table_ref`
- **抽樣值正確**：spec 中的 sample value 在輸出中能找到對應的 record

### 測試 shape

```python
import pytest
from parser import parse

@pytest.fixture(scope="module")
def result():
    return parse()


def test_anchors_resolved(result):
    """每張 table 都被找到（沒有 fallback 到 raise）"""
    assert result["tables"]["electrical_characteristics"]
    assert result["tables"]["max_ratings"]


def test_primary_key_unique(result):
    rows = result["tables"]["electrical_characteristics"]
    keys = [(r["part_id"], r["symbol"], r["condition"]) for r in rows]
    assert len(keys) == len(set(keys)), "Duplicate primary keys"


def test_required_fields_present(result):
    for r in result["tables"]["electrical_characteristics"]:
        assert r["symbol"] is not None
        assert r["unit"] is not None
        assert r["source_page"] is not None


def test_sample_value(result):
    rows = result["tables"]["electrical_characteristics"]
    rds_on_25 = next((r for r in rows
                      if r["symbol"] == "RDS(ON)"
                      and "Tj=25" in (r["condition"] or "")), None)
    assert rds_on_25 is not None
    assert rds_on_25["max"] == 4.8
```

---

## Step 4：執行 parser，產出 output.json

執行 parser 並寫入：

```text
pdf-parser-generator/{pdf檔名}/output.json
```

這份 JSON 是 DB 入庫前的 review 用，結構等於 `parse()` 回傳的 dict。

---

## Step 5：執行測試並回報

```bash
cd pdf-parser-generator/{pdf檔名} && python -m pytest test_parser.py --tb=short -q
```

### 結果回報格式

**全部通過：**

```text
## Parser 驗證結果：{pdf_filename}

所有測試通過。輸出已寫入 output.json。

| Table | Row count | Primary key 唯一 | Required 完整 | 狀態 |
|---|---|---|---|---|
| electrical_characteristics | 32 | ✓ | ✓ | pass |
| max_ratings | 8 | ✓ | ✓ | pass |
```

**部分失敗：**

```text
## Parser 驗證結果：{pdf_filename}

{n} 通過 / {m} 失敗

| 測試 | 失敗原因 | 建議檢查 |
|---|---|---|
| test_primary_key_unique | RDS(ON) 重複 row key | condition 正規化是否漏掉某個溫度 |
| test_anchors_resolved | max_ratings 找不到 | 確認 spec 的 expected_headers |
```

---

## Step 5.5：自動修復迴圈

若 Step 5 有失敗，最多執行 2 次修復。

每次修復先分類失敗原因：

| 失敗類別 | 處理 |
|---|---|
| Anchor 找不到 | 檢查 spec 的 expected_headers 是否與實際 PDF 一致 |
| Primary key 重複 | 檢查 row key 設計是否需要加入更多欄位（例如 condition）|
| Forward-fill 邏輯錯 | 修 parser 的繼承邏輯，不改 spec |
| 特殊字元未處理 | 加入 spec 中已列出的正規化規則 |
| Spec 規則缺失 | 停止修復，要求 user 回到 `/ppg:propose` |

不自行修改 `pdf_field_spec.md`。

---

## Step 6：跨文件驗證提示（多份同系列文件時）

若 spec 中標示「多份同系列文件」：

完成單一文件驗證後提示：

```text
此 parser 已通過 {pdf_filename} 的測試。

由於 spec 標示為「N 份同系列文件」，建議：
1. 取另一份同系列 PDF 執行 parser，檢查 anchor 是否仍能定位
2. 確認 nullable 欄位在不同版本是否確實可能消失
3. 若失敗，回到 /ppg:explore 補充跨文件穩定性備註
```

---

## 輸出目錄

```text
pdf-parser-generator/
  {pdf_filename}/
    pdf_field_spec.md     <- propose 產出，唯一人工可修改檔
    parser_spec.json      <- apply compile 產出（覆寫，可選）
    parser.py             <- apply 產出（覆寫）
    test_parser.py        <- apply 產出（覆寫）
    output.json           <- apply 執行結果，DB 入庫前 review（覆寫）
```

不再產出 `raw_extraction.json` 或 `normalized.json`（已棄用）。

---

## 失敗處理

- `pdf_field_spec.md` 不存在：提示先執行 `/ppg:propose`
- 原始 PDF 找不到：提示確認 spec 中的「來源檔案」路徑
- compile spec 失敗：指出哪個章節不完整（DB schema / Parser 定位策略 / 欄位處理規則）
- Anchor 找不到對應 table：先嘗試放寬 search_pages，再回報是 spec 問題還是 PDF 結構問題
- 測試失敗但 evidence 無法回溯：優先懷疑 spec 或 anchor 設計，不硬猜
- user 要求從單一 sample 保證跨文件泛化：明確拒絕，建議用第二份 PDF 驗證
