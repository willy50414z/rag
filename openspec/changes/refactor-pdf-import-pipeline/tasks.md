## 1. 抽取 DB 寫入層 (`db/upserts.py`)

- [x] 1.1 建立 `db/upserts.py`，將 `db/inserter.py` 中六個 `upsert_*` function（`upsert_parts`、`upsert_max_ratings`、`upsert_thermal`、`upsert_electrical`、`upsert_charts`、`upsert_footnotes`）原樣搬入；保留 SQL、ON CONFLICT 規則、`psycopg2.extras.execute_values` 與 print 訊息不變。
- [x] 1.2 在 `db/upserts.py` 新增 `upsert_all(conn, parsed: dict, embeddings) -> None`；內部以 `with conn:` + `with conn.cursor() as cur:` 包住 6 個 `upsert_*` 呼叫，順序與現行 `run()` 一致（parts → max_ratings → thermal → electrical → charts → footnotes）。
- [x] 1.3 在 `upsert_all` 入口處加上 length-mismatch assertion：對 max_ratings、thermal、electrical、charts、footnotes 各自確認 `len(records) == len(embeddings.<field>)`；不符則 raise `AssertionError` 並訊息中標明哪一張表。
- [x] 1.4 確認 `db/upserts.py` 只 import `json`、`psycopg2`、`psycopg2.extras`，不 import `sentence_transformers`、`minio`、`pdfplumber`、`importlib`、`os` 等與 SQL 寫入無關的 dependency。

## 2. 抽取 embedding layer (`db/embeddings.py`)

- [x] 2.1 建立 `db/embeddings.py`，將 `_text_max_rating`、`_text_thermal`、`_text_electrical`、`_text_chart`、`_text_footnote`、`embed_texts` 與 `EMBED_MODEL` / `EMBED_DIM` 常數從 `db/inserter.py` 搬入。
- [x] 2.2 定義 `EmbeddingsBundle` dataclass，欄位為 `max_ratings`、`thermal`、`electrical`、`charts`、`footnotes`（皆為 `list[list[float]]`）。
- [x] 2.3 實作 `EmbeddingGenerator` class：constructor 接受 `model_name: str = EMBED_MODEL`，內部 lazy-load `SentenceTransformer`；提供 `encode_bundle(parsed: dict, footnotes: dict) -> EmbeddingsBundle`，內部一次 batch encode 全部 text 後切片成五個 list，行為等同現有 `run()` 中 `all_texts` → `all_embs` 的切片邏輯。
- [x] 2.4 確認 `db/embeddings.py` 只 import `sentence_transformers`、`dataclasses` 等必要 dependency；不 import `psycopg2`、`minio`、`pdfplumber`。

## 3. 抽取 MinIO layer (`db/minio_client.py`)

- [x] 3.1 建立 `db/minio_client.py`，將 `_minio_endpoint`、`upload_charts` 從 `db/inserter.py` 搬入。
- [x] 3.2 提供 `build_minio_client(endpoint_raw, access_key, secret_key) -> Minio` helper，封裝現有 `_minio_endpoint` 切 scheme 與 `Minio(...)` 建構流程。
- [x] 3.3 確認 `db/minio_client.py` 只 import `io`、`minio`；不 import `psycopg2`、`sentence_transformers`、`pdfplumber`。

## 4. 建立 pipeline orchestrator (`import_pipeline.py`)

- [x] 4.1 在 repo root 建立 `import_pipeline.py`，定義 `import_pdf(pdf_path: Path, parser) -> None`。
- [x] 4.2 在 `import_pdf` 內依序：(a) duck-type 檢查 `parser` 具備 `parse` 與 `parse_typical_charts` 屬性，否則 raise；(b) 呼叫 `parser.parse(str(pdf_path))` 取得 `parsed`；(c) 從 `parsed["tables"]["parts"][0]["part_id"]` 取出 `part_id`，fallback 為 `pdf_path.stem`；(d) 呼叫 `parser.parse_typical_charts(str(pdf_path), part_id)` 取得 `charts_full`（含 `image_bytes`）。
- [x] 4.3 接續：(e) `EmbeddingGenerator().encode_bundle(parsed, footnotes)` 產生 embeddings；(f) 從 env 讀取 MinIO config，呼叫 `build_minio_client` 與 `upload_charts(client, bucket, charts_full)`；(g) 從 env 讀取 `DATABASE_URL`，`psycopg2.connect`，呼叫 `db.upserts.upsert_all(conn, parsed, embeddings)`；(h) `conn.close()` 在 `finally`。
- [x] 4.4 將 `db/inserter.py` 中的 `_env` helper 搬到 `import_pipeline.py`（或抽到一個小的 `db/config.py`，視重複度而定）；確認 import_pdf 不直接依賴 `os.environ` 的 raw key 讀取以外的東西。
- [x] 4.5 確認 `import_pipeline.py` 不執行檔案系統搜尋來找 parser；parser 完全由參數傳入。

## 5. 重構 `db/inserter.py` 為薄 CLI wrapper

- [x] 5.1 移除 `db/inserter.py` 中所有已搬走的 function（`upsert_*`、`_text_*`、`embed_texts`、`upload_charts`、`_minio_endpoint`、`run` 內的 parsing/embedding/upload/upsert 邏輯）。
- [x] 5.2 在 `db/inserter.py` 內新增 `_VENDOR_PARSERS: dict[str, str]` 註冊表，目前只填 `{"vdsemi": "datasheet_parser.vdsemi_parser"}`；保留註解說明新增 vendor 時加新 entry。
- [x] 5.3 實作 `_resolve_parser(pdf_path: Path) -> tuple[str, ModuleType]`：根據 PDF stem prefix 判斷 vendor（VSP* / VS* → vdsemi），用 `importlib.import_module` 載入對應 module，回傳 `(vendor_name, module)`；找不到 mapping raise `ValueError` 並列出可用 vendor 清單。
- [x] 5.4 重寫 `run(pdf_path: Path) -> None` 為三行：解析 vendor + parser、印出 vendor/parser 訊息、呼叫 `import_pipeline.import_pdf(pdf_path, parser)`。
- [x] 5.5 維持 `if __name__ == "__main__":` 行為：argv 解析與錯誤訊息與現行一致。

## 6. 端對端驗證

- [ ] 6.1 對 `pdfs/VSP007N06MS-G.pdf` 跑一次完整 `python db/inserter.py pdfs/VSP007N06MS-G.pdf`，確認流程不報錯且印出進度訊息與重構前對齊（parts / max_rat / thermal / elec / charts / footnotes 計數一致）。
      **部分驗證**：parser → MinIO upload → embedding 全部成功（counts 與重構前一致：parts 1, max_rat 12, thermal 2, elec 23, charts 11, footnotes 4；52 embeddings）。DB upsert 因 `rag` database 不存在而 fail（`psycopg2.OperationalError: database "rag" does not exist`）— 環境問題，非程式碼問題。
- [ ] 6.2 在 PostgreSQL 內 `SELECT COUNT(*) FROM parts WHERE part_id = 'VSP007N06MS-G'` 等 6 張表，確認 row 數與重構前一致。
      **阻塞於 6.1**。
- [ ] 6.3 連續跑兩次同一 PDF 的 import，確認 6 張表 row count 不變（idempotent）。
      **阻塞於 6.1**。
- [ ] 6.4 對 `pdfs/VS11240GTH.pdf` 與 `pdfs/VS1602GTH.pdf` 嘗試執行 CLI，預期：若 vendor inference rule 涵蓋 VS* prefix，能成功 import；若 parser 內部對該 PDF 失敗，錯誤訊息應出現在 parser 層而非 pipeline 層。
      **阻塞於 6.1**（同樣會 hit DB error；vendor lookup 已驗證對 VS*/VSP* 前綴正確路由）。
- [x] 6.5 確認 `db/upserts.py`、`db/embeddings.py`、`db/minio_client.py` 三個 module 各自可單獨 `python -c "import db.upserts"` / etc. 而不觸發其他 layer 的 dependency 載入。

## 7. 清理與文件更新

- [x] 7.1 移除 `db/inserter.py` 中已不使用的 import（`importlib.util`、`io`、`json`、`sentence_transformers`、`minio`、`Minio`、`SentenceTransformer` 等）。
- [x] 7.2 更新 `db/inserter.py` 開頭 docstring，反映「薄 CLI wrapper」的新角色，並指出實際邏輯在 `import_pipeline.import_pdf`。
- [x] 7.3 在 `import_pipeline.py` 開頭 docstring 簡述 layer 分工（parser / embedding / minio / db.upserts），並註記「MinIO orphan cleanup 不在本 module scope」。
- [x] 7.4 若 repo 內有 `README.md` 提到 `python db/inserter.py` 或匯入流程，同步更新；無則略過。
      **無 project README**（僅有第三方套件 README）→ skipped per task condition.
