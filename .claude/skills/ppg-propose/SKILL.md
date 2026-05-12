---
name: ppg-propose
description: 讀取 /ppg:explore 在 conversation 中已確認的決策（row key、欄位語意、DB schema 草案、跨文件穩定性、RAG 設計），產生唯一可人工修改的 pdf_field_spec.md。當使用者要把 text PDF exploration 結果正式化成 DB-ready 的欄位規格、保留 semantic anchor 與 chunking 注意事項、並為後續 parser 實作做準備時，使用此 skill。
---

# PDF Parser Generator — Propose

將 text PDF exploration 結果正式化為人可編輯的欄位與 DB schema 規格。

```text
/ppg:explore  -> 直接讀 PDF，產出分析決策（row key / DB schema / RAG 設計）
/ppg:propose  -> 將決策匯出為 pdf_field_spec.md（唯一人工可修改檔）
/ppg:apply    -> 讀 spec，實作 parser 並驗證
```

---

## 前置條件檢查

確認 conversation 中已有來自 `/ppg:explore` 的以下決策：

- 目標（RAG / DB / 兩者）與文件家族規模
- 每張 table 的 row key
- 每個欄位的語意分類（識別鍵 / 測量值 / 條件 / metadata）
- DB schema 草案（含 nullable、型別）
- Semantic anchor（取代 hardcode page/table index 的文字定位點）
- 跨文件穩定性評估（若是多份同系列文件）
- RAG 設計（哪些欄位進向量庫、condition 是否正規化）
- Chunking 前置考量

若缺少其中任一項：

> 找不到完整的 exploration 決策。請先執行 `/ppg:explore <pdf路徑>`，確認 row key、DB schema 與 anchor 設計後再執行 propose。

不從 PDF 重新探索；只把 conversation 中的決策正式化。

---

## Artifact 責任分工

- `pdf_field_spec.md`：human-reviewed semantic contract，唯一可由 user 直接編輯
- `parser.py` / `parser_spec.json`：由 `/ppg:apply` 產生，不手改
- 不產生 `normalized.json` 或 `raw_extraction.json`（已棄用）

---

## Step 1：確認輸出路徑

```text
pdf-parser-generator/{pdf檔名（不含副檔名）}/pdf_field_spec.md
```

若目錄不存在，自動建立。

---

## Step 2：彙整 conversation 中的決策

從 conversation 萃取：

- Step 0 答案（目標、文件家族、查詢類型）
- Step 3 每張 table 的 checklist 結果（A/B/C/D）
- Step 4 DB schema 草案
- Step 5 user 對 row key、nullable、condition 拆解的確認

若 conversation 中決策矛盾或缺失：

- 先回報矛盾，不自行解決
- 在 spec 中保留 `unresolved` 標記
- 不從 PDF 重新推論

---

## Step 3：匯出 pdf_field_spec.md

依以下結構匯出（中文）：

```markdown
# Parser Spec: {pdf_filename}

## 文件資訊

- 來源檔案：{pdf路徑}
- 分類：digital-text
- 探索日期：{YYYY-MM-DD}
- 目標用途：{RAG / DB / 兩者}
- 文件家族：{單份 / N 份同系列廠商}
- 預期 parser runtime：pdfplumber

## 文件結構摘要

- 總頁數與主要 section：{摘要}
- Table 清單：{tables_p1[0]: 識別 / tables_p1[2]: max ratings / tables_p2[0]: electrical...}
- 跨頁 table：{有無，描述}
- Footnote 模式：{動態圓圈數字 / 固定符號 / 無}
- 特殊字元：{℃、上下標、PUA Unicode 等}

## DB Schema

### Table: {table_name}

- **Primary Key**：`(欄位1, 欄位2, ...)`
- **設計理由**：{為什麼這組欄位是 row key}

| 欄位 | 型別 | Nullable | 說明 |
|---|---|---|---|
| part_id | TEXT | NO | 跨文件 join key |
| symbol | TEXT | NO | e.g. RDS(ON) |
| condition | TEXT | NO | e.g. VGS=10V, Tj=25°C |
| min | REAL | YES | |
| typ | REAL | YES | |
| max | REAL | YES | |
| unit | TEXT | NO | |
| section | TEXT | YES | Static / Dynamic / Switching |
| footnote_ref | TEXT | YES | |
| source_page | INT | NO | evidence trace |
| table_ref | TEXT | NO | e.g. P2-T0 |

（每張 table 一節，依此格式重複）

## Parser 定位策略

每張 table 的定位 anchor（取代 hardcode index）：

### {table_name}

- **定位方式**：搜尋 header row 包含 `["Symbol", "Parameter", "Min", "Typ", "Max", "Unit"]` 的 table
- **搜尋範圍**：第 1-3 頁
- **Fallback**：若找不到，{錯誤策略：raise / log warning + 用第 N 頁第 M 個 table}
- **Section 分段依據**：欄位文字符合 `Static Electrical|Dynamic Electrical|Switching|Source-Drain Diode`

## 欄位處理規則

### {field_name}

- 業務意義：{欄位語意}
- 資料來源：{table_name}.{column_name}
- 型別：{string | number | enum}
- 正規化規則：{e.g. 將 ℃ 轉為 °C，將 Ohm 轉為 Ω}
- 缺失處理：error | null | needs_review
- Forward-fill：{是否從上列繼承，何時繼承}
- 特殊處理：{e.g. RDS(ON) 在 Tj=100°C 列要附加 ④ 註腳}
- Sample 值：`{sample value}`

## 跨文件穩定性備註

僅在多份同系列文件目標下記錄：

- 哪些欄位是所有版本都有（required across family）
- 哪些欄位可能在某版本消失（optional across family）
- 哪些 anchor 文字在版本間穩定
- 哪些值類型可能變動（例如某版本新增 enum 值）

## RAG 設計

- 進向量庫的欄位：{e.g. parameter, condition}
- Structured query 欄位：{e.g. part_id, symbol, min, typ, max}
- Condition 正規化策略：{保留原始字串 / 拆解為 KV / 雙欄並存}
- 跨文件比較需求：{有 / 無，影響 join key 設計}

## Chunking Considerations

- 同一 symbol 的多個條件列保持在同一 chunk
- Section header 作為 chunk 邊界
- Footnote 附加在 table 層級
- Metadata 欄位（part_id, section, symbol）放進 retrieval filter

## 未解決的模糊項目

- **{欄位名}**：{模糊描述} -> 需要：{user 需釐清事項}
```

---

## Step 4：匯出規則

- 每張 table 在 `## DB Schema` 各一小節
- 每個 field 在 `## 欄位處理規則` 各一小節
- `## Parser 定位策略`必須有 anchor 設計，不允許空
- `## 跨文件穩定性備註`：單份文件可省略，但要明確標示「單份文件，不評估跨文件穩定性」
- 樣本值必須來自實際 evidence，不可臆測
- 若 user 確認所有項目，省略 `## 未解決的模糊項目`
- 不加 YAML frontmatter

---

## Step 5：等待 user 確認

寫入後顯示：

```text
pdf_field_spec.md 已匯出至：pdf-parser-generator/{pdf檔名}/pdf_field_spec.md

這份檔案是唯一需要人工修改的規格檔。
請確認以下項目正確：
1. DB schema 的 primary key 與 nullable 設計
2. Parser 定位策略的 anchor 文字
3. 跨文件穩定性備註（若是多份同系列）
4. RAG 設計的欄位分類

確認後執行 `/ppg:apply` 實作 parser。
```

不自動觸發 `/ppg:apply`。

---

## 失敗處理

- conversation 缺少 row key 決策：要求先確認
- conversation 缺少 DB schema 草案：要求先確認
- 缺少 anchor 設計：要求 explore 補上
- PDF 檔名無法確定：詢問 user 確認輸出目錄名稱
- 部分欄位 unresolved：照常匯出，在模糊項目章節列出，不阻止匯出
