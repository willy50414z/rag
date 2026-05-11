## Why

目前 ppg workflow 主要針對「欄位萃取」設計，對 text PDF 特有的問題（文字順序、換行、多欄版面）處理不足，且缺少 table extraction 獨立邏輯、layout 分析、chunking 前置考量。限縮在 text PDF 練習範圍內，需要針對這些痛點優化。

## What Changes

- 增加換行/多欄版面處理指引（文字順序修復）
- Table extraction 作為獨立 parsing 任務（不是當成一般欄位）
- Layout 標記（header/footer/paragraph/section 偵測）
- Chunking 前置考量指引（章節邊界建議）
- 選擇性產出 Markdown/JSON 中間格式

## Capabilities

### New Capabilities
- `ppg-text-layout-handling`: 處理 text PDF 的換行、多欄、閱讀順序問題
- `ppg-text-table-extraction`: 將表格當作獨立 parsing 任務，保留 row/column 結構
- `ppg-text-layout-analysis`: 偵測並標記 header/footer/paragraph/section 等 layout 元素
- `ppg-text-chunking-prep`: 提供萃取結果如何影響 chunk 的指引
- `ppg-text-intermediate-format`: 選擇性產出 Markdown 或 JSON 中間格式

### Modified Capabilities
- `ppg-explore`: 限縮在 text PDF 範圍內的 normalize + review 階段加強

## Impact

- 修改 `.claude/skills/ppg-explore/SKILL.md`
- 預期新增 `references/` 下的 layout-handling 和 table-extraction 指引文件