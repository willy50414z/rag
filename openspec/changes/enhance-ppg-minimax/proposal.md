## Why

目前 ppg workflow (ppg-explore/ppg-propose/ppg-apply) 只覆蓋了 Phase 3 的一部分核心目標，缺少對 OCR pipeline、table extraction、座標應用（label-value 配對）和 chunking 前期思考的系統性支援。這導致學習者只能完成「欄位萃取」，而非完整的 Phase 3 文件解析流程。

## What Changes

- 在 `ppg-explore` 中增加 OCR 明確指引（當文件分類為 scanned/hybrid 時）
- 增加「table extraction as separate task」的獨立處理邏輯
- 增加利用 bbox 做 label-value 配對的 example
- 增加 chunking 前置考量指引（輸出如何影響後續 chunk）
- 選擇性產出 Markdown/JSON 中間格式，呼應 Phase 3 最小練習

## Capabilities

### New Capabilities
- `ppg-ocr-support`: 補齊 scanned PDF 的 OCR pipeline 指引，包括環境檢查、backend 選擇、降級策略
- `ppg-table-extraction`: 將表格當作獨立 parsing 任務處理，而非僅作為萃取的欄位之一
- `ppg-coordinate-application`: 展示如何利用 bbox/座標資訊做欄位對應（label-value pairing）
- `ppg-chunking-consideration`: 在 workflow 中增加「萃取結果如何影響 chunk」的指引
- `ppg-intermediate-format`: 選擇性產出 Markdown 或 JSON 中間結果

### Modified Capabilities
- `ppg-explore`: 現有 skill 需要擴充以支援上述新能力
- `ppg-apply`: 可能需要調整以支援新的萃取格式

## Impact

- 修改 `.claude/skills/ppg-explore/SKILL.md`
- 可能需修改 `.claude/skills/ppg-apply/SKILL.md`
- 預期新增 `references/` 下的 OCR/table extraction 指引文件