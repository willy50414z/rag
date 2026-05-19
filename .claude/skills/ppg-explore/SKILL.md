---
name: ppg-explore
description: Text PDF 專用的互動式 PDF exploration skill，目標是為 RAG 與 DB 入庫做準備。當使用者要分析 text PDF 結構、識別欄位語意與 row key、評估跨文件穩定性、或草擬 DB schema 與 RAG 查詢設計時，使用此 skill。Agent 直接讀 PDF，輸出 markdown review；不產出 JSON/YAML 中間層。完成後交給 /ppg:propose 與 /ppg:apply。
---

# PDF Parser Generator — Explore

Text PDF 三段式流程的第一段：

```text
/ppg:explore  -> 直接讀 PDF，分析結構、語意、跨文件穩定性，草擬 DB schema
/ppg:propose  -> 將 explore 決策匯出為 pdf_field_spec.md（唯一可人工修改的規格）
/ppg:apply    -> 讀 spec，實作 parser 並驗證
```

此 skill 不產出 JSON/YAML 中間層，不實作 parser code。輸出為 conversation 內的分析與可選的 `review.md`。

---

## Scope

只處理 `text PDF`（可選字、可直接抽文字層的 PDF）。

若文件判定不是 `digital-text`：
1. 回報分類結果
2. 說明本 skill 只覆蓋 text PDF
3. 停止，建議改走 ppgm-explore（docling/MinerU 路線）或 OCR 路線

---

## Step 0：前置問題（讀 PDF 之前先問 User）

只問影響後續 spec 設計的問題，不問開放式問題。

必問（只問業務層級問題，技術決策留到 Step 5 根據實際 PDF 內容再確認）：

1. **目標**：RAG 查詢 / DB 結構化入庫 / 兩者都要？
2. **文件家族**：這是單份文件，還是同系列多份（例如同一廠商不同型號）？預計幾份？
3. **查詢類型**：使用者典型會問什麼問題？（例如：「這顆料在 Tj=125°C 的 RDS(ON) 最大值是多少？」）

根據回答調整後續分析重點。若是多份同系列文件，Step 3C（跨文件穩定性）要特別仔細。

以下問題移到 Step 5，在分析完 PDF 實際結構後再根據證據提出建議：
- 跨文件比較需求（影響 part_id join key 設計）
- Condition 正規化策略（保留原始字串 vs. 拆解為結構化 key-value）

---

## Step 1：PDF 分類與工具確認

判斷 PDF 類型：

- `digital-text`：有可萃取文字層，繼續主流程
- `scanned` / `hybrid` / `uncertain`：停止，說明原因，建議替代路線

確認可用工具（只在缺少必要工具時說明並請 user 安裝）：
- 表格萃取：`pdfplumber`（優先）、`camelot`、`tabula-py`
- 文字層確認：`pypdf`、`pymupdf`

---

## Step 2：Agent 直接讀 PDF — 整體結構描述

不透過 JSON 中間層，直接閱讀 PDF。

回報：

- 總頁數與主要 section 分布
- 每頁有哪些 table（數量、大致位置）
- 有無跨頁 table
- 有無 footnote（位置、符號類型）
- 有無特殊字元（℃、上下標、PUA Unicode 圓圈數字）
- 文件是否有多種版型（例如 N-channel / P-channel 同一份 PDF）

---

## Step 3：每張 Table 的分析 Checklist

對每張有資料價值的 table，逐一完成以下四個面向。

### A. 結構面

- **定位 anchor**：哪個欄位標題文字可作為可靠定位點？（取代 hardcode page/table index）
  - 好的 anchor：欄位標題文字（`Symbol`、`Parameter`、`Min`、`Typ`、`Max`、`Unit`）
  - 不好的 anchor：page number、table 出現順序
- **Section header**：是獨立列還是 merged cell？用什麼文字分段？
- **Merged cell / Forward-fill**：哪些欄位有跨列合併（symbol 空白繼承上列）？
- **Continuation row**：有沒有條件繼承（同一 symbol 下多個測試條件）？
- **Footnote**：footnote 符號是動態的（圓圈數字數量不固定）還是固定的？位置在 table 下方還是頁尾？

### B. 欄位語意分類

每個欄位分類為以下之一，並說明理由：

| 類型 | 說明 | 對 DB 的影響 |
|---|---|---|
| **識別鍵** | 唯一識別一筆資料的欄位組合 | Primary key 設計 |
| **測量值** | 數值類欄位（min / typ / max / rating）| float 型別，nullable |
| **條件** | 測試條件（VGS=10V, Tj=25°C）| 需不需要拆解成 key-value |
| **單位** | unit | 附屬欄位 |
| **Metadata** | footnote_ref、section | 附屬欄位，不進主比較邏輯 |
| **識別字串** | part_id、package、channel | required，跨文件 join key |

**Row key 識別**（必答）：
- 哪個欄位組合能唯一識別一列資料？
- 注意：同一 symbol 在不同 condition 下是不同列（例如 RDS(ON) @ Tj=25°C vs. Tj=100°C）
- 提出候選 row key，說明是否夠穩定

**值類型**（必答）：
- 數值欄位是否可能出現非數字（`--`、`±20`、`-55 to 150`）？
- 如何處理：直接存字串、拆解為 value_min / value_max、還是 value_raw + value_num 雙欄？

**Nullable**（必答）：
- 哪些欄位是 required？哪些是 nullable？
- 哪些欄位在同系列其他文件可能消失？

### C. 跨文件穩定性評估（單份文件可略過）

僅在 Step 0 回答「多份同系列文件」時執行。

對每個結構元素評估穩定性：

| 結構元素 | 穩定性 | 建議 |
|---|---|---|
| 欄位標題文字 | 通常高 | 用作 anchor |
| Section header 文字 | 通常高 | 用作 section 分段依據 |
| Page number | 低 | 不要 hardcode |
| Table 出現順序 | 低 | 不要 hardcode index |
| Footnote 數量 | 低 | 動態偵測 |
| 特定欄位的存在 | 中 | 標記為 nullable |

提出：哪些欄位是所有版本都有的（required），哪些是某版本才有的（nullable）。

### D. RAG 相關設計

- 這張 table 能回答什麼使用者問題？（具體舉例）
- 哪些欄位應進向量庫做語意搜尋？哪些只需 structured query？
- Condition 欄位：是否需要正規化成 key-value（`VGS=10V, Tj=25°C`）才能支援查詢？
- 是否有欄位需要單位轉換（mΩ vs. Ω）才能跨文件比較？

---

## Step 4：草擬 DB Schema

基於 Step 3 的分析，提出每張 table 對應的 DB schema 草案。

格式：

```
Table: electrical_characteristics
Primary key: (part_id, symbol, condition)
Columns:
  - part_id       TEXT  NOT NULL   # 跨文件 join key
  - symbol        TEXT  NOT NULL   # e.g. RDS(ON)
  - condition     TEXT  NOT NULL   # e.g. VGS=10V, Tj=25°C
  - min           REAL  NULLABLE
  - typ           REAL  NULLABLE
  - max           REAL  NULLABLE
  - unit          TEXT  NOT NULL
  - section       TEXT  NULLABLE   # Static Electrical / Dynamic...
  - footnote_ref  TEXT  NULLABLE
  - source_page   INT   NOT NULL   # evidence trace
  - table_ref     TEXT  NOT NULL   # e.g. P2-T0
```

說明每個設計決策的理由（為什麼是 NULLABLE、為什麼 condition 不拆解等）。

若有多張 table（max_ratings、thermal、electrical），分別提出 schema，並說明是否應合併或分開。

---

## Step 5：問針對性問題

只問會改變後續 spec 與 parser 行為的問題。

優先問：

- Row key 候選是否正確？（最重要）
- Nullable 欄位清單是否正確？
- 跨文件比較：是否需要 part_id 作為 join key？（基於 Step 3C 的分析結果提出建議）
- Condition 正規化策略：保留原始字串、拆解為 key-value、還是雙欄並存？（基於實際 condition 欄位內容提出建議）
- 值類型有非數字時的處理策略？
- 跨文件時哪些欄位是必定存在的？
- 欄位缺失時是 `null`、`error`、還是 `needs_review`？

避免開放式問題。每個問題都要提出建議選項，讓 user 確認或修改。

---

## Step 6：Chunking Prep 提醒（RAG 用）

不做正式 chunking，但提前說明：

- 哪些 table 不應拆碎（同一 symbol 的多個條件列應保持在同一 chunk）
- 哪些 section header 應作為 chunk 邊界
- Footnote 應附加在哪一層（table 層 vs. 單列層）
- 哪些欄位要放進 metadata 供 retrieval filter 使用（part_id、section、symbol）

---

## 完成提示

完成 explore 後，先寫入決策 checkpoint，再提示 user 執行 propose。

### Step 6.5：寫入 explore_decisions.md

在 `pdf-parser-generator/{pdf檔名（不含副檔名）}/explore_decisions.md` 寫入以下結構（中文）：

```markdown
# Explore Decisions: {pdf_filename}

探索日期：{YYYY-MM-DD}
來源檔案：{pdf路徑}

## Step 0 確認

- 目標用途：{RAG / DB / 兩者}
- 文件家族：{單份 / N 份同系列}
- 查詢類型範例：{e.g. 這顆料在 Tj=125°C 的 RDS(ON) 最大值是多少？}

## 每張 Table 的 Row Key

| Table | Row Key 欄位組合 | 理由 |
|---|---|---|
| electrical_characteristics | (part_id, symbol, condition) | 同一 symbol 在不同 condition 下是不同列 |
| max_ratings | (part_id, symbol) | 無 condition 欄 |

## DB Schema 草案

（逐字貼上 Step 4 產出的 schema 文字）

## Semantic Anchors

| Table | expected_headers | 搜尋頁範圍 |
|---|---|---|
| electrical_characteristics | ["Symbol", "Parameter", "Min", "Typ", "Max", "Unit"] | 1-3 |
| max_ratings | ["Symbol", "Rating", "Value", "Unit"] | 1 |

## 跨文件穩定性

（單份文件填「不適用」；多份同系列填 Step 3C 結論）

## RAG 設計

- 進向量庫：{欄位清單}
- Structured query：{欄位清單}
- Condition 正規化策略：{保留原始 / 拆解 KV / 雙欄}
- 跨文件比較需求：{有 / 無}

## Chunking 注意事項

（貼 Step 6 產出的 chunking 前置考量）

## 未解決項目

（若 Step 5 有未確認項目，列於此；若無則填「無」）
```

這份檔案是 `/ppg:propose` 的 fallback 輸入，也可由 user 在 propose 之前手動修改。

完成寫入後說明：

> 已完成 PDF exploration，決策已存入 `explore_decisions.md`。Row key、DB schema 草案、及 RAG 設計已確認。請執行 `/ppg:propose` 產生 `pdf_field_spec.md`，這是唯一可人工修改的規格檔。

---

## 失敗處理

在以下情況暫停並說明：

- 文件不是 `digital-text`
- Row key 無法確定（需要 user 提供業務知識）
- 同一 symbol 出現方式在文件中不一致，無法定義穩定 row key
- Condition 格式混亂（自然語言與結構化混用），需要 user 決定正規化策略
- 跨文件穩定性評估缺乏第二份文件對照

---

## References

- [text-layout-handling.md](./references/text-layout-handling.md)：閱讀順序、多欄、header/footer 判斷細則
- [table-extraction-guidelines.md](./references/table-extraction-guidelines.md)：table 常見失敗模式與 parser 對應設計
- [field-policy-template.md](./references/field-policy-template.md)：欄位政策模板（explore Step 5 使用）
- [mosfet-domain.md](./references/mosfet-domain.md)：MOSFET datasheet 領域知識
