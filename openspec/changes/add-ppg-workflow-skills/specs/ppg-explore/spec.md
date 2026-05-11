## ADDED Requirements

### Requirement: 環境檢查

Skill SHALL 在分析 PDF 前先確認可用的 PDF 萃取工具（pypdf、pdfplumber、pymupdf、pytesseract 等），若缺少必要工具應說明缺什麼、影響什麼，並請 user 安裝最小必要依賴集。

#### Scenario: 工具缺失

- **WHEN** user 提供 PDF 路徑但環境缺少 PDF 萃取工具
- **THEN** skill 說明缺少哪些工具、影響什麼功能，並建議安裝指令，不繼續執行萃取

#### Scenario: 工具可用

- **WHEN** 環境已有足夠的 PDF 萃取工具
- **THEN** skill 回報選用的 backend 路徑並繼續流程

### Requirement: PDF 分類

Skill SHALL 判斷 PDF 屬於 `digital-text`、`scanned`、`hybrid` 或 `uncertain`，並說明判斷依據。

#### Scenario: 數位文字 PDF

- **WHEN** PDF 含有可直接萃取的文字層
- **THEN** skill 分類為 `digital-text` 並選用輕量文字萃取路徑

#### Scenario: 掃描 PDF

- **WHEN** PDF 頁面主要為圖像，無文字層
- **THEN** skill 分類為 `scanned` 並說明需要 OCR 路徑

### Requirement: 低假設萃取

Skill SHALL 萃取結構化中間資料，保留 page_number、block_type、text、bbox（可用時）、reading_order、source_type，不進行激進的語意推測。

#### Scenario: 成功萃取

- **WHEN** PDF 萃取後產出 blocks 資料
- **THEN** skill 保留所有可用欄位，缺失欄位標記 null 而非省略

### Requirement: 互動式欄位確認

Skill SHALL 產出 review Markdown 摘要，提出針對性問題（候選值選擇、required/missing 政策、strict extraction），並根據 user 回答更新欄位政策，可多輪互動。

#### Scenario: 問題有界且可回答

- **WHEN** 有欄位候選值需 user 確認
- **THEN** skill 提出具體問題（「候選 A 還是候選 B 是正確的發票號碼？」），不問開放式問題

#### Scenario: User 回答後更新狀態

- **WHEN** user 回答欄位相關問題
- **THEN** skill 更新該欄位的 policy_status 為 `user_confirmed` 或 `user_modified`

### Requirement: 不寫檔案

Skill SHALL 不在 explore 階段寫入任何檔案，所有狀態保留在 conversation context。

#### Scenario: Explore 結束

- **WHEN** 欄位探索完成或 user 準備進入下一階段
- **THEN** skill 提示執行 `/ppg:propose` 匯出規格，不自動寫檔

### Requirement: References 沿用

Skill SHALL 使用 `pdf-parser-explore` skill 既有的 references（workflow-artifacts.md、review-template.md、field-policy-template.md）作為內部指引。

#### Scenario: 需要參考 artifact 格式

- **WHEN** skill 需要產出 review Markdown 或確認 artifact 結構
- **THEN** skill 參照 references 目錄內的模板，不自行定義新格式
