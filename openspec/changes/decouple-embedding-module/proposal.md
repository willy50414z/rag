## Why

目前 `db/embeddings.py` 將「每個 table 的文字表示格式」與「向量化模型」耦合在同一個模組，import pipeline 是唯一能觸發 embedding 的路徑。當需要對已存在的記錄進行修改、從非 PDF 來源（手動輸入、API、Excel）新增資料，或更換 embedding 模型時，都必須繞過現有結構或重寫 embedding 邏輯。

## What Changes

- **新增** `db/text_representations.py`：將每個 table 的文字表示邏輯（`to_embed_text(record, table_name) → str`）獨立成模組，任何資料來源皆可使用
- **重構** `db/embeddings.py`：只保留 `SentenceTransformer` 包裝層（`embed(texts) → vectors`），移除對 parsed dict 格式的直接依賴
- **新增** `db/re_embed.py`：獨立的 re-embedding 工具腳本，從 DB 讀出現有記錄、重新計算文字表示、批量更新 embedding 欄位
- **更新** `import_pipeline.py`：改呼叫新分離的 `to_embed_text()` + `embed()`，行為不變

## Capabilities

### New Capabilities

- `text-representations`：每個 table（max_ratings、thermal_characteristics、electrical_characteristics、typical_charts、footnotes）的文字表示格式邏輯，作為獨立可呼叫的模組
- `re-embed`：從 DB 讀出現有資料並批量更新 embedding 的工具腳本，支援換模型或修正文字表示格式後的全量重算

### Modified Capabilities

（無 spec 層級的行為變更，僅為實作重構）

## Impact

- `db/embeddings.py`：大幅精簡，移除 `encode_bundle()` 與文字表示邏輯
- `db/text_representations.py`：新增檔案
- `db/re_embed.py`：新增檔案
- `import_pipeline.py`：呼叫介面調整，外部行為不變
- 無 DB schema 變更
- 無 `upsert_all()` 介面破壞性變更
