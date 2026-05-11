## Context

現有 ppg workflow (ppg-explore/ppg-propose/ppg-apply) 是針對「欄位萃取」的專案實作流程，主要處理 digital-text PDF，缺少：
- OCR pipeline 指引（scanned PDF 處理）
- Table extraction 獨立處理邏輯
- 座標應用（label-value 配對）
- Chunking 前置考量
- 中間格式（Markdown/JSON）產出

目標讀者是正在學習 Phase 3 的 RAG 學員，需要完整的文件解析流程指引。

## Goals / Non-Goals

**Goals:**
- 在 ppg-explore 中補齊 OCR 指引，使能處理 scanned/hybrid PDF
- 增加 table extraction 作為獨立的 parsing 任務
- 提供座標應用的實際 example（label-value pairing）
- 增加 chunking 前置考量指引
- 選擇性產出 Markdown/JSON 中間結果

**Non-Goals:**
- 不實作完整的 OCR engine，而是指引使用者選擇合適的工具
- 不改變既有的欄位萃取邏輯結構
- 不處理 Phase 4 以後的 chunking 實作

## Decisions

1. **OCR 處理策略：降級式 pipeline**
   - 選擇：環境檢查 → 分類 → 路由 → 降級
   - 理由：OCR 品質受多因素影響，需要明確的降級策略而非單一方案

2. **Table extraction 作為獨立任務**
   - 選擇：在 artifact 結構中增加 `table_blocks` 區塊，與 `text_blocks` 分開
   - 理由：Phase 3 強調「表格需要單獨處理」，萃取時應保留表格結構

3. **座標應用方式：label-value 配對**
   - 選擇：利用 bbox 資訊，找出左右/上下對應的 label 和 value
   - 理由：Phase 3 強調「欄位名稱與欄位值可能左右對應」

4. **中間格式：Markdown + JSON 雙軌**
   - 選擇：輸出時可選擇產生 Markdown（人可讀）或 JSON（機器處理）
   - 理由：Phase 3 說「Markdown 和 JSON 都值得保留」

## Risks / Trade-offs

- [Risk] OCR 指引可能過於 general → [Mitigation] 聚焦在工具選擇策略，而非細部調參
- [Risk] label-value pairing 演算法可能有 false positive → [Mitigation] 在 review 階段標記為候選，需 user 確認
- [Risk] 增加中間格式產出會增加 workflow 複雜度 → [Mitigation] 設為 optional，不強制要求