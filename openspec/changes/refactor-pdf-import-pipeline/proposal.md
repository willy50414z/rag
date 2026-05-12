## Why

目前 `db/inserter.py:run()` 把 parser discovery、PDF 解析、embedding 計算、MinIO 上傳、PostgreSQL upsert 全部黏在同一個 function 裡，難以重用、測試與替換。同時 parser 已經從「按 PDF stem 動態載入」（`pdf-parser-generator/<stem>/parser.py`）改成「按 vendor 分檔」（`datasheet_parser/<vendor>_parser.py`），原本的 stem-based discovery 已經與檔案配置脫節。

## What Changes

- **新增** `import_pipeline.py`（位於 repo root），提供 `import_pdf(pdf_path, parser)` 作為主要 entry point，parser 以 module 物件方式傳入。
- **新增** `db/upserts.py`，把 `db/inserter.py` 中的六個 `upsert_*` function 與 transaction lifecycle 抽出，成為純 DB 寫入層；不依賴 embedding model、MinIO client、parser。
- **新增** `db/embeddings.py`，獨立 embedding 產生層，封裝 SentenceTransformer 載入與 batched encode。
- **新增** `db/minio_client.py`，獨立 MinIO upload 層。
- **BREAKING** 移除 `db/inserter.py` 中以 PDF stem 動態 import parser 的行為（不再讀 `pdf-parser-generator/<stem>/parser.py`）。
- **BREAKING** `db/inserter.py:run()` 重構為薄薄一層 CLI wrapper：解析 argv、依 vendor 名稱對應 parser module、呼叫 `import_pdf(pdf_path, parser)`。
- 維持現有 6 張表的 upsert 行為與 idempotency 不變；資料庫 schema 不變。

## Capabilities

### New Capabilities
- `pdf-import-pipeline`：以 (pdf_path, parser_module) 為輸入，協調 parse → embed → MinIO upload → DB upsert 的完整 PDF 匯入流程。
- `datasheet-db-writes`：對 datasheet 相關 6 張表（parts、max_ratings、thermal_characteristics、electrical_characteristics、typical_charts、footnotes）的純 SQL 寫入層，提供 transaction-scoped 的 idempotent upsert。

### Modified Capabilities
（無，目前 `openspec/specs/` 為空）

## Impact

- **影響的程式檔案**：
  - `db/inserter.py`（重構為薄 CLI wrapper）
  - 新增 `import_pipeline.py`、`db/upserts.py`、`db/embeddings.py`、`db/minio_client.py`
- **影響的 API / 入口**：
  - CLI `python db/inserter.py <pdf_path>` 行為保持，但內部改為呼叫 `import_pipeline.import_pdf`。
  - 新增可程式呼叫的 entry point：`from import_pipeline import import_pdf`。
- **依賴**：無新增第三方套件；現有 `psycopg2`、`minio`、`sentence-transformers`、`pdfplumber` 不變。
- **資料**：PostgreSQL schema 不變；MinIO bucket / key 命名規則不變。
- **未受影響**：`datasheet_parser/vdsemi_parser.py` 與其他 parser 內部實作；`db/query.py`；`db/schema.sql`。
