## Context

目前 `pdf-parser-explore` 是一個 7 步驟的 monolithic skill，從 PDF 探索一路到 parser-spec 草稿。User 無法在中間階段獨立介入，也無法重跑單一階段。拆分成三個獨立 skill 能讓每個階段有清晰的邊界、進入點和產出物。

三個 skill 位於 `.claude/skills/` 下的專案級目錄：
- `ppg-explore/SKILL.md`
- `ppg-propose/SKILL.md`
- `ppg-apply/SKILL.md`

## Goals / Non-Goals

**Goals:**
- `ppg:explore` 在 conversation 內完成 PDF 分類、欄位萃取、user 互動，不寫任何檔案
- `ppg:propose` 將 conversation 狀態匯出為純 Markdown spec 檔，路徑為 `pdf-parser-generator/{pdf檔名}/pdf_field_spec.md`
- `ppg:apply` 讀 spec md，實作 parser，產生測試，執行驗證，回報 pass/fail
- 刪除舊的 `pdf-parser-explore` skill

**Non-Goals:**
- 不建立狀態持久化機制（不寫 session 檔案）；狀態透過 conversation context 傳遞
- 不支援多 PDF 同時處理
- 不實作通用 parser；parser 針對單一 PDF 格式

## Decisions

### 1. 狀態傳遞：conversation context，不寫 session 檔案

`explore` 結束時欄位狀態活在對話上下文裡，`propose` 從 conversation 讀取。

**理由**：寫 session 檔案需要定義 schema、維護讀寫邏輯、處理版本問題。Conversation context 已足夠，且符合 openspec-explore 的既有模式。

**代替方案考慮**：session YAML 檔案 → 增加複雜度，且 `propose` 直接從 conversation 可以完全解決需求。

### 2. spec 格式：純 Markdown，不加 YAML frontmatter

`pdf_field_spec.md` 使用結構化 Markdown（固定章節標題和清單格式），不加 YAML frontmatter。

**理由**：`apply` 的消費者是 agent（LLM），不是 script。Agent 讀結構化 Markdown 完全可靠。加 frontmatter 引入兩套表示（frontmatter + body）需要同步，增加複雜度而沒有對等收益。

**代替方案考慮**：YAML frontmatter + Markdown body → 若 user 只改 body，frontmatter 可能過時；若 user 只改 frontmatter，body 可能過時，同步問題難以避免。

### 3. 輸出目錄：`pdf-parser-generator/{pdf檔名}/`

```
pdf-parser-generator/
  {pdf_filename}/
    pdf_field_spec.md   ← propose 產出
    parser.py           ← apply 產出
    test_parser.py      ← apply 產出
```

**理由**：每個 PDF 文件的所有相關產出物集中在同一目錄，易於管理。`pdf-parser-generator/` 作為 workspace，與 `lib/` 分離（lib 放穩定可重用的 library code）。

### 4. references 共用

`ppg-explore` 繼承 `pdf-parser-explore` 的 references 目錄（workflow-artifacts.md、review-template.md、field-policy-template.md、parser-spec-template.yaml），避免重複維護。

## Risks / Trade-offs

- **Conversation context 遺失**：若 user 離開對話又重新開始，`propose` 無法重建 explore 的狀態。緩解：`propose` 開頭說明需要先執行 `/ppg:explore`，若 conversation 中沒有欄位狀態則提示重跑。
- **Markdown 格式漂移**：若 user 大幅修改 `pdf_field_spec.md` 的結構，`apply` 可能誤讀。緩解：spec 模板在 `ppg-propose` skill 內固定，`apply` skill 說明預期的 section 標題。
- **Parser 實作不夠通用**：針對 sample PDF 的 parser 可能無法處理同格式的其他 PDF。緩解：這是設計邊界，不在 first-version scope 內。
