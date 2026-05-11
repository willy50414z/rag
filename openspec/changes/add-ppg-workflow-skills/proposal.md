## Why

現有的 `pdf-parser-explore` skill 是一個涵蓋探索到規格草稿的單一 monolithic workflow，無法讓 user 在各階段獨立介入。將其拆分為 `/ppg:explore`、`/ppg:propose`、`/ppg:apply` 三個獨立 skill，讓每個階段都有明確的進入點與產出物，並刪除舊的 `pdf-parser-explore` skill。

## What Changes

- 新增 `ppg:explore` skill：在 conversation 內互動式探索 PDF 欄位，不寫檔案
- 新增 `ppg:propose` skill：從 conversation 狀態匯出欄位規格，寫入 `pdf-parser-generator/{pdf檔名}/pdf_field_spec.md`（純 Markdown）
- 新增 `ppg:apply` skill：讀取 spec md，實作 `parser.py` 與 `test_parser.py`，對 sample PDF 執行測試並回報 pass/fail
- 刪除 `pdf-parser-explore` skill 及其所有 references 檔案

## Capabilities

### New Capabilities

- `ppg-explore`: 互動式 PDF 欄位探索 skill，分類 PDF、萃取結構、問 user 問題、確認欄位政策，全程在 conversation 內進行
- `ppg-propose`: 從 conversation 狀態匯出純 Markdown 欄位規格檔，路徑為 `pdf-parser-generator/{pdf檔名}/pdf_field_spec.md`
- `ppg-apply`: 讀 spec md、實作 parser、產生測試、對 sample PDF 執行驗證並回報結果

### Modified Capabilities

## Impact

- `.claude/skills/pdf-parser-explore/` 整個目錄將被刪除
- 新增 `.claude/skills/ppg-explore/SKILL.md`
- 新增 `.claude/skills/ppg-propose/SKILL.md`
- 新增 `.claude/skills/ppg-apply/SKILL.md`
- 新增輸出目錄規範：`pdf-parser-generator/{pdf檔名}/`（parser.py、test_parser.py、pdf_field_spec.md）
