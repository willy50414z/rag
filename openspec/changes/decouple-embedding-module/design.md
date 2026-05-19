## Context

目前 `db/embeddings.py` 做了兩件在概念上獨立的事：

1. **文字表示格式**：每個 table 的 record 要怎麼被「轉成一段文字」，例如 `f"{symbol} {parameter}: {value_raw} {unit}"` 是 max_ratings 的格式
2. **向量化**：用 `SentenceTransformer("all-MiniLM-L6-v2")` 把文字轉成 384 維向量

`import_pipeline.py` 呼叫 `EmbeddingGenerator.encode_bundle(parsed)` 一次完成這兩步，並且 `encode_bundle()` 直接吃整個 `parsed` dict（PDF parsing 輸出格式）。

結果：任何想要產生 embedding 的路徑，都必須構造出跟 PDF parser 輸出一模一樣的 dict 結構，或重新複製這兩段邏輯。

`query.py` 也有自己的 `SentenceTransformer` 實例（同一個模型名稱），目前是重複 load。

## Goals / Non-Goals

**Goals:**
- 將「文字表示格式」邏輯抽成獨立的純函式模組，任何資料來源皆可呼叫
- 讓 `embeddings.py` 只負責「文字 → 向量」，不知道 table schema
- 提供 `re_embed.py` 工具腳本，可在換模型或修正格式後對既有 DB 資料全量重算
- `import_pipeline.py` 行為不變，只是改呼叫分離後的模組

**Non-Goals:**
- 不做成 HTTP / gRPC 微服務
- 不支援多模型並行或 A/B 測試
- 不變更 DB schema
- 不改變 `upsert_all()` 的介面

## Decisions

### 決策 1：`text_representations.py` 使用純函式，不用 class

```python
# db/text_representations.py
def to_embed_text(record: dict, table: str) -> str: ...
```

**為什麼**：文字表示邏輯是 pure function（無狀態、無副作用），不需要 class 的封裝。呼叫方只需 `from db.text_representations import to_embed_text`，簡單直接。

**替代方案考慮**：用 `dict[str, Callable]` mapping 也可，但可讀性較差；用 class 沒有好處。

---

### 決策 2：`embeddings.py` 保留 lazy-load singleton，`query.py` 共用

```python
# db/embeddings.py
_generator: EmbeddingGenerator | None = None

def get_generator() -> EmbeddingGenerator: ...
def embed(texts: list[str]) -> list[list[float]]: ...
```

**為什麼**：`all-MiniLM-L6-v2` 載入需要約 1-2 秒，import pipeline 和 query 都用同一個 singleton 避免重複 load。現在 `query.py` 是另建一個 `SentenceTransformer` 實例，這是浪費。

---

### 決策 3：`re_embed.py` 是 CLI 腳本，不是 library

```bash
python db/re_embed.py [--table TABLE] [--batch-size N] [--dry-run]
```

**為什麼**：re-embedding 是維運操作，不是業務邏輯的一部分。做成 CLI 腳本：可獨立執行、可 dry-run 確認、不會被其他模組意外呼叫。

**替代方案考慮**：做成函式讓 pipeline 也能呼叫，但這樣就需要處理「什麼時候該 re-embed」的判斷邏輯，反而複雜化。

---

### 決策 4：`encode_bundle()` 從 `embeddings.py` 移除，改為 pipeline 內組合呼叫

`import_pipeline.py` 改為：

```python
texts_per_table = {
    "max_ratings":               [to_embed_text(r, "max_ratings") for r in records],
    "thermal_characteristics":   [...],
    ...
}
embeddings_per_table = {
    table: embed(texts)
    for table, texts in texts_per_table.items()
}
```

**為什麼**：`encode_bundle()` 的存在是因為格式耦合；拆分後自然消失，不需要替代品。

## Risks / Trade-offs

| 風險 | 緩解 |
|------|------|
| `to_embed_text()` 與 DB 實際欄位格式不同步（新 vendor parser 新增欄位但沒更新格式）| 在 `to_embed_text()` 加上對未知 table 的 `ValueError`，強迫呼叫方明確處理 |
| `re_embed.py` 執行期間主服務仍在查詢，可能讀到舊 embedding | re-embed 逐筆更新（非 truncate-reload），pgvector 欄位更新是原子操作，單筆記錄不會出現半舊半新 |
| `query.py` 與 `embeddings.py` 共用 singleton 但 `query.py` 不在 import pipeline 流程裡 | `get_generator()` 做 lazy init，兩邊第一次呼叫時各自初始化，行為跟現在相同 |

## Migration Plan

1. 新增 `db/text_representations.py`，複製現有格式邏輯
2. 重構 `db/embeddings.py`，移除 `encode_bundle()`，加 `embed()` 公開函式
3. 更新 `import_pipeline.py` 呼叫新介面，執行現有 test 確認行為不變
4. 新增 `db/re_embed.py`
5. 更新 `db/query.py` 改用 `get_generator()`（可選，為了消除重複 load）

無需 DB migration，無需部署協調。

## Open Questions

- `re_embed.py` 是否需要 `--part-id` 參數，支援只對單一零件重算？（目前預設全量，可後續加）
- `query.py` 的 singleton 共用是否在本次範圍內處理，還是單獨做？
