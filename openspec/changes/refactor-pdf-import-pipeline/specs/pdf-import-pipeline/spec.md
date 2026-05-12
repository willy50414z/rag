## ADDED Requirements

### Requirement: 提供 `import_pdf` 作為 PDF → datasheet DB 的程式化入口

系統 SHALL 提供 `import_pipeline.import_pdf(pdf_path, parser)` function，接受一個 PDF 路徑與一個 parser module 物件作為輸入，完成「解析 → embedding → MinIO 上傳 → PostgreSQL upsert」的完整流程。`parser` 參數 MUST 為 Python module 物件，且必須提供 `parse(pdf_path: str) -> dict` 與 `parse_typical_charts(pdf_path: str, part_id: str) -> list[dict]` 兩個 callable。

#### Scenario: 成功匯入一個 PDF
- **WHEN** 呼叫者傳入有效的 PDF 路徑與符合介面的 parser module
- **THEN** 系統解析 PDF，產生對應的 6 張表資料與 footnote dict
- **AND** 系統為 max_ratings、thermal_characteristics、electrical_characteristics、typical_charts、footnotes 中的每筆紀錄產生 embedding
- **AND** 系統將所有 chart 圖片上傳至 MinIO bucket
- **AND** 系統在單一 PostgreSQL transaction 內完成 6 張表的 upsert
- **AND** function 回傳 None（或 import 結果摘要 dict），呼叫者可繼續其他工作

#### Scenario: parser 不符合介面
- **WHEN** 呼叫者傳入的 parser module 缺少 `parse` 或 `parse_typical_charts` 屬性
- **THEN** 系統 SHALL 在實際呼叫前以清楚的 `AttributeError` 或 `TypeError` 失敗
- **AND** 系統 MUST NOT 嘗試任何 DB 連線或 MinIO 連線

### Requirement: pipeline 不得內含 parser discovery 邏輯

系統 SHALL 將「決定要用哪個 parser」的責任完全交給呼叫者。`import_pdf` MUST NOT 依 PDF 檔名、檔案內容、或任何外部 registry 自行載入 parser module。

#### Scenario: pipeline 不讀檔案系統找 parser
- **WHEN** `import_pdf` 被呼叫
- **THEN** 系統 MUST NOT 對 `pdf-parser-generator/`、`datasheet_parser/`、或任何其他位置執行檔案搜尋
- **AND** 系統 MUST 直接使用呼叫者傳入的 `parser` 物件

### Requirement: pipeline 各 layer 之間以資料結構解耦

系統 SHALL 確保 parser、embedding generator、MinIO uploader、DB writer 之間透過明確的資料結構（dict 或 dataclass）傳遞資料，不直接共享狀態。embedding 結果 MUST 以與 parsed records 對應、長度一致的結構傳給 DB writer。

#### Scenario: embedding 與 record 長度不一致時失敗
- **WHEN** 任一張表的 embedding list 長度與對應 records list 長度不同
- **THEN** 系統 SHALL 在進入 DB upsert 前以 `AssertionError` 或同等級的明確錯誤失敗
- **AND** 不執行任何 DB 寫入

### Requirement: MinIO 上傳必須在 DB upsert 之前完成

系統 SHALL 先完成所有 chart 圖片到 MinIO 的上傳，再開始 PostgreSQL transaction。若 MinIO 上傳失敗，系統 MUST 中止流程，且 MUST NOT 對 PostgreSQL 進行任何寫入。

#### Scenario: MinIO 上傳失敗中止整個流程
- **WHEN** MinIO 上傳過程中任一張 chart 失敗
- **THEN** 系統 SHALL 拋出例外
- **AND** 系統 MUST NOT 開啟 PostgreSQL transaction
- **AND** 已成功上傳的 chart 可留在 MinIO（不在本次 scope 內處理 cleanup）

### Requirement: CLI wrapper 提供反向相容的呼叫方式

系統 SHALL 保留 `python db/inserter.py <pdf_path>` 的 CLI 行為。CLI 層 MUST 自行決定要用哪個 vendor parser，然後委派給 `import_pdf`。CLI 層 MUST NOT 包含任何 PDF parsing、embedding、MinIO、DB upsert 邏輯。

#### Scenario: CLI 接收 PDF 路徑並推測 vendor
- **WHEN** 使用者執行 `python db/inserter.py pdfs/VSP007N06MS-G.pdf`
- **THEN** CLI 根據檔名或 part_id prefix 推測 vendor（VSP* → vdsemi）
- **AND** CLI 載入對應的 parser module
- **AND** CLI 呼叫 `import_pdf(pdf_path, parser)` 並印出進度訊息

#### Scenario: CLI 找不到對應 vendor parser
- **WHEN** 使用者傳入的 PDF 無法對應到任何已註冊的 vendor parser
- **THEN** CLI SHALL 以清楚的錯誤訊息結束（exit code 非 0）
- **AND** 訊息中 SHALL 列出目前可用的 vendor 清單
