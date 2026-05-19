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

- `pdf_field_spec.md`：human-reviewed semantic contract，**read-only**（parser 直接讀此檔，不另生中間格式）
- `parser.py`：實際 parser code（覆寫）
- `test_parser.py`：測試碼（覆寫）
- `output.json`：執行 parser 的結果，DB 入庫前的 review 用（覆寫）

apply 不修改 `pdf_field_spec.md`。

---

## Step 1：讀取 spec

讀取 `pdf_field_spec.md`，從中直接萃取以下資訊（保留在 conversation 中，不另生中間檔案）：

- 文件資訊（PDF 路徑、目標用途、文件家族）
- DB Schema（每張 table 的 primary key、欄位、nullable）
- Parser 定位策略（每張 table 的 anchor 與 fallback）
- 欄位處理規則（型別、正規化、forward-fill、特殊處理）
- 跨文件穩定性備註

若 spec 缺少 anchor 或 row key：

- 指出缺少的章節，不腦補
- 要求 user 回到 `/ppg:propose` 補上

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
- **Condition 解析**：condition 欄位影響 primary key 唯一性，需遵守以下規則：
  - **Condition 是單一字串，不拆解成多筆 record**：`VGS=10V, Tj=25°C, ID=8A` 整體是一個測試條件，描述同一次量測的環境，不應拆成多列；多個不同條件出現在 table 的不同 row 才是多筆 record
  - **正規化（Normalization）**：每個 condition 字串在存入前執行以下清理，確保同一條件在不同文件中產生相同 key：
    1. strip 首尾空白
    2. 合併 cell 內換行（`\n` → 空格）
    3. 等號兩側空白移除（`VGS = 10V` → `VGS=10V`）
    4. 依 spec 的特殊字元規則正規化（℃→°C 等）
    5. **不**移除逗號、不改變參數順序
  - **Footnote marker 分離**：condition cell 內的 footnote 符號（①②③ 等）移至 `footnote_ref`，不留在 condition 字串中，避免污染 primary key
  - **空值處理**：condition 為 null 時，若 spec 標記 `forward_fill: true` 則繼承上列；若無 forward-fill 且 spec 標記 `nullable: false`，加入 warning（不可入庫）；若 spec 標記 `nullable: true` 且業務語意允許（如 max_ratings 無 condition 欄），存為 `""` 空字串而非 `null`，以確保 primary key 可組合

  parser shape 中加入對應的輔助函式：

  ```python
  def normalize_condition(raw: str | None, footnote_pattern: re.Pattern) -> tuple[str, str]:
      """
      Returns (condition_normalized, footnote_ref_extracted).
      footnote_ref is empty string if none found.
      """
      if not raw:
          return "", ""
      text = raw.replace("\n", " ").strip()
      # extract footnote markers before other normalization
      markers = footnote_pattern.findall(text)
      text = footnote_pattern.sub("", text).strip()
      # normalize spacing around = signs
      text = re.sub(r"\s*=\s*", "=", text)
      text = re.sub(r"\s{2,}", " ", text)
      return text, "".join(markers)
  ```

- **Section 偵測**：用以下啟發式判斷某 row 是否為 section header（非資料列），依優先順序評估，高優先結果覆蓋低優先結果：
  1. **Pattern 比對（最高優先）**：row 文字匹配 `section_split.patterns` 中任一 pattern → 判定為 section header，不再評估後續啟發式
  2. **欄位數異常（高優先）**：row 的有效 cell 數明顯少於 table 的標準欄位數（通常是 merged 全寬 cell）→ 判定為 section header
  3. **前後空白（中優先）**：row 前後有空白列，且 row 本身只有一個文字 cell → 判定為 section header
  4. **格式線索（低優先）**：cell 文字為全大寫、含粗體標記、或字體顯著大於資料列 → 單獨成立時不足以判定，需搭配第 2 或第 3 條才判定為 section header
  - 衝突規則：若高優先啟發式判定為資料列（不匹配任何 pattern 且欄位數正常），低優先啟發式（格式線索）不得單獨推翻；若低優先啟發式有疑慮，加入 warning 並繼續當作資料列處理
  - Section header row 不應被當作資料 record 輸出；它只影響後續 row 的 `section` 欄位值
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

### 領域規則驗證（可選）

若 spec 對應的 PDF 屬於有已知領域規則的類別（如 MOSFET datasheet），從 spec 的 domain reference 中萃取值域驗證規則，加入測試：

- **數值範圍**：min ≤ typ ≤ max（同一 condition 組內）
- **跨欄位關係**：例如 MOSFET 的 crss < coss < ciss、qgd < qgs < qg
- **正負號規則**：channel=N 時電流類欄位 > 0，channel=P 時 < 0
- **enum 值域**：channel 只能是 N 或 P、package 匹配已知封裝格式

範例：

```python
def test_value_ordering(result):
    """min <= typ <= max for all rows that have all three stats."""
    for r in result["tables"]["electrical_characteristics"]:
        if r["min"] is not None and r["typ"] is not None and r["max"] is not None:
            assert r["min"] <= r["typ"] <= r["max"], \
                f"{r['symbol']} @ {r['condition']}: min={r['min']} typ={r['typ']} max={r['max']}"


def test_capacitance_ordering(result):
    """crss < coss < ciss for all rows with capacitance data."""
    rows = result["tables"]["electrical_characteristics"]
    ciss = next((r for r in rows if r["symbol"] == "Ciss"), None)
    coss = next((r for r in rows if r["symbol"] == "Coss"), None)
    crss = next((r for r in rows if r["symbol"] == "Crss"), None)
    if all([ciss, coss, crss]):
        assert crss["typ"] < coss["typ"] < ciss["typ"], \
            f"Expected Crss({crss['typ']}) < Coss({coss['typ']}) < Ciss({ciss['typ']})"
```

這些測試接在結構測試之後，補足語意正確性的驗證。若 spec 未包含領域知識 reference，可跳過此節。

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

**全部通過，無 warning：**

```text
## Parser 驗證結果：{pdf_filename}

所有測試通過，無 warning。輸出已寫入 output.json。

| Table | Row count | Primary key 唯一 | Required 完整 | 狀態 |
|---|---|---|---|---|
| electrical_characteristics | 32 | ✓ | ✓ | pass |
| max_ratings | 8 | ✓ | ✓ | pass |

入庫建議：可直接入庫。
```

**全部通過，但有 warning：**

```text
## Parser 驗證結果：{pdf_filename}

所有測試通過，但有 {n} 個 warning。輸出已寫入 output.json。

| Table | Row count | Primary key 唯一 | Required 完整 | 狀態 |
|---|---|---|---|---|
| electrical_characteristics | 32 | ✓ | ✓ | pass（2 warnings）|
| max_ratings | 8 | ✓ | ✓ | pass |

Warnings：
- [electrical_characteristics] row 14：typ 為 null（nullable: true，允許）
- [electrical_characteristics] row 22：section 偵測模糊，已標記為資料列（低優先啟發式衝突）

入庫建議：{依 warning 類別決定，見下表}
```

**Warning 入庫建議對照表：**

| Warning 類別 | 來源 | 入庫建議 |
|---|---|---|
| nullable 欄位為 null | `nullable: true` 欄位確實無值 | 可直接入庫 |
| section 偵測模糊 | 低優先啟發式衝突，已保留為資料列 | 建議人工 review output.json 確認 section 值後入庫 |
| 特殊字元未匹配 | PDF 出現 spec 未涵蓋的字元，已原樣保留 | 建議確認欄位值後入庫 |
| required 欄位為 null | `nullable: false` 欄位缺值 | **不可入庫**，回到 `/ppg:propose` 修正 nullable 設定或 forward-fill 規則 |

**部分失敗：**

```text
## Parser 驗證結果：{pdf_filename}

{n} 通過 / {m} 失敗

| 測試 | 失敗原因 | 應修改 spec 章節 |
|---|---|---|
| test_primary_key_unique | RDS(ON) 重複 row key | DB Schema → Primary Key 設計 |
| test_anchors_resolved | max_ratings 找不到 | Parser 定位策略 → anchor headers |
| test_required_fields_present | symbol 為 null | 欄位處理規則 → forward-fill 設定 |
```

失敗原因與應修改的 spec 章節對照：

| 失敗類別 | 對應 spec 章節 | 常見修正方式 |
|---|---|---|
| Primary key 重複 | `## DB Schema` → Primary Key | 加入更多欄位（通常漏了 condition） |
| Anchor 找不到 | `## Parser 定位策略` → anchor headers | 調整 expected_headers 或 search_pages |
| Forward-fill 邏輯錯 | `## 欄位處理規則` → 特定欄位 | 確認 forward-fill 標記正確 |
| Special char 未正規化 | `## 欄位處理規則` → 正規化規則 | 補上遺漏的字元對應 |
| Required field null | `## DB Schema` → Nullable 欄 | 確認 nullable 設定符合實際 PDF |
| Row count 不符 | `## DB Schema` → 整體或 `## Parser 定位策略` | 可能漏抓跨頁 table 或被 section header 截斷 |

---

## Step 5.5：自動修復迴圈

若 Step 5 有失敗，最多執行 2 次修復。

每次修復先分類失敗原因，並告知對應的 spec 章節：

| 失敗類別 | 對應 spec 章節 | 處理 |
|---|---|---|
| Anchor 找不到 | `## Parser 定位策略` | 檢查 spec 的 expected_headers 是否與實際 PDF 一致；若需修改 spec，停止並要求 user 更新 |
| Primary key 重複 | `## DB Schema` → Primary Key | 檢查 row key 設計是否需要加入更多欄位；若需修改 spec，停止並要求 user 更新 |
| Forward-fill 邏輯錯 | `## 欄位處理規則` | 修 parser 的繼承邏輯，不改 spec |
| 特殊字元未處理 | `## 欄位處理規則` | 加入 spec 中已列出的正規化規則 |
| Spec 規則缺失 | 視缺失項目而定 | 停止修復，指出需修改的 spec 章節，要求 user 回到 `/ppg:propose` |

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
    parser.py             <- apply 產出（覆寫）
    test_parser.py        <- apply 產出（覆寫）
    output.json           <- apply 執行結果，DB 入庫前 review（覆寫）
```

不再產出 `raw_extraction.json`、`normalized.json` 或 `parser_spec.json`（已棄用）。

---

## 失敗處理

- `pdf_field_spec.md` 不存在：提示先執行 `/ppg:propose`
- 原始 PDF 找不到：提示確認 spec 中的「來源檔案」路徑
- spec 章節不完整（DB schema / Parser 定位策略 / 欄位處理規則）：指出缺少的章節，要求回到 `/ppg:propose` 補上
- Anchor 找不到對應 table：先嘗試放寬 search_pages，再回報是 spec 問題還是 PDF 結構問題
- 測試失敗但 evidence 無法回溯：優先懷疑 spec 或 anchor 設計，不硬猜
- user 要求從單一 sample 保證跨文件泛化：明確拒絕，建議用第二份 PDF 驗證
