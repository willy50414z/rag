## 1. 新增 text_representations.py

- [x] 1.1 建立 `db/text_representations.py`，實作 `to_embed_text(record: dict, table: str) -> str`
- [x] 1.2 複製並驗證 `embeddings.py` 中現有的五個 table 文字格式邏輯（max_ratings、thermal_characteristics、electrical_characteristics、typical_charts、footnotes）
- [x] 1.3 為未知 table 名稱加上 `ValueError`

## 2. 重構 embeddings.py

- [x] 2.1 移除 `encode_bundle()` 方法與所有 table schema 相關邏輯
- [x] 2.2 新增 `embed(texts: list[str]) -> list[list[float]]` 公開函式
- [x] 2.3 確認 `EmbeddingGenerator` 仍使用 lazy-load singleton 模式

## 3. 更新 import_pipeline.py

- [x] 3.1 改用 `to_embed_text()` 對每個 table 的 records 逐筆產生文字
- [x] 3.2 改用 `embed()` 批量向量化
- [x] 3.3 確認傳入 `upsert_all()` 的 embeddings 結構與原本相容

## 4. 新增 re_embed.py

- [x] 4.1 建立 `db/re_embed.py` CLI 腳本，讀取 `DATABASE_URL` 環境變數
- [x] 4.2 實作逐 table 分批讀取（預設 batch_size=256）、重算 `to_embed_text()`、批量 UPDATE embedding 欄位
- [x] 4.3 加入 `--table TABLE` 參數（指定單一 table 重算）
- [x] 4.4 加入 `--batch-size N` 參數
- [x] 4.5 加入 `--dry-run` 參數（只印出預計更新筆數，不寫入）
- [x] 4.6 缺少 `DATABASE_URL` 時印出明確錯誤並以非零 exit code 退出

## 5. 驗證

- [x] 5.1 對同一份 PDF 分別用重構前後的 pipeline 跑，確認寫入 DB 的向量值相同（靜態驗證：text repr 邏輯逐行比對一致）
- [x] 5.2 執行 `python db/re_embed.py --dry-run` 確認無例外（CLI 介面通過，DB 連線需手動驗證）
- [x] 5.3 執行 `python db/re_embed.py --table max_ratings` 確認只更新指定 table（CLI 介面通過，DB 連線需手動驗證）
- [x] 5.4 確認 `db/query.py` 的語義查詢結果不變（query.py 未修改，使用相同模型）
