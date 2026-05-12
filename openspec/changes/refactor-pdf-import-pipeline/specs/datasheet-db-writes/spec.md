## ADDED Requirements

### Requirement: 提供獨立的 DB 寫入 module

系統 SHALL 在 `db/upserts.py` 提供純 PostgreSQL 寫入層。此 module MUST NOT 載入 SentenceTransformer、MinIO client、PDF parser，或任何與 SQL 寫入無關的 dependency。Module 唯一允許的外部 dependency 為 `psycopg2`。

#### Scenario: 載入 module 不觸發 ML / 外部 IO
- **WHEN** 任何 caller 執行 `import db.upserts`
- **THEN** import 過程 MUST NOT 載入 SentenceTransformer 或任何 ML model
- **AND** import 過程 MUST NOT 開啟 MinIO 或 PostgreSQL 連線
- **AND** import 過程 MUST NOT 開啟任何 PDF 檔案

### Requirement: 提供粗顆粒度的 `upsert_all` 入口

系統 SHALL 提供 `db.upserts.upsert_all(conn, parsed, embeddings) -> None`，在單一 PostgreSQL transaction 內完成 6 張表（parts、max_ratings、thermal_characteristics、electrical_characteristics、typical_charts、footnotes）的 upsert。Connection lifecycle（connect / close）MUST 由 caller 管理，但 transaction 邊界 MUST 由 `upsert_all` 內部以 `with conn:` 控制，確保任何一張表失敗時整體 rollback。

#### Scenario: 一張表失敗導致整個 transaction rollback
- **WHEN** `upsert_all` 在執行 `upsert_electrical` 時觸發 SQL 例外
- **THEN** 先前已執行的 `upsert_parts`、`upsert_max_ratings`、`upsert_thermal` 結果 SHALL 全部 rollback
- **AND** PostgreSQL 中該 part 的舊資料保持不變

#### Scenario: 全部成功則一次 commit
- **WHEN** 6 張表的 upsert 全部成功
- **THEN** transaction commit
- **AND** 後續 query 應能讀到所有新寫入的 row

### Requirement: 個別 `upsert_*` function 維持為 module-level public

系統 SHALL 保留 `upsert_parts`、`upsert_max_ratings`、`upsert_thermal`、`upsert_electrical`、`upsert_charts`、`upsert_footnotes` 為 module-level public function，使未來需要 partial re-insert 的 caller 可直接 import 使用。每個 function MUST 接受 cursor + records (+ embeddings) 作為輸入。

#### Scenario: caller 自行管理 transaction 重灌單一表
- **WHEN** 未來的 caller 想單獨重灌某 part 的 max_ratings
- **THEN** 該 caller 可以 `from db.upserts import upsert_max_ratings`
- **AND** 自行開 connection、cursor、transaction，呼叫 `upsert_max_ratings(cur, rows, embeddings)`

### Requirement: upsert 操作 MUST 為 idempotent

系統 SHALL 確保所有 6 個 `upsert_*` function 在重複呼叫同一筆資料時，最終 DB 狀態相同。所有 `INSERT ... ON CONFLICT DO UPDATE` 子句 MUST 與現有 `db/inserter.py` 行為一致：
- `parts` 衝突鍵：`part_id`
- `max_ratings` 衝突鍵：`(part_id, symbol, condition_normalized)`
- `thermal_characteristics` 衝突鍵：`(part_id, symbol)`
- `electrical_characteristics` 衝突鍵：`(part_id, symbol, condition_normalized)`
- `typical_charts` 衝突鍵：`(part_id, minio_key)`
- `footnotes` 衝突鍵：`(part_id, marker)`

#### Scenario: 重複匯入同一 PDF
- **WHEN** 同一個 PDF 被 import 兩次
- **THEN** DB 中該 part 的 row 數量在第二次 import 後與第一次相同
- **AND** 所有欄位反映最新一次 import 的值

### Requirement: DB sink 不負責產生 embedding 文字

系統 SHALL 將「決定要 embed 哪段文字」的責任交給 embedding layer。`db/upserts.py` MUST 接受呼叫者已準備好的 embedding vector list，且 MUST NOT 自行呼叫任何 text formatting function（例如 `_text_max_rating`、`_text_thermal` 等）。

#### Scenario: caller 已準備好 embedding 才呼叫 upsert
- **WHEN** caller 呼叫 `upsert_max_ratings(cur, rows, embeddings)`
- **THEN** function 直接將 embeddings 寫入對應 row
- **AND** function 內部 MUST NOT 為 row 產生任何描述文字
