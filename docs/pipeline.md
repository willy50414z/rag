# Datasheet Import Pipeline 說明文件

## 概覽

這份文件說明從 PDF 到 PostgreSQL 的完整資料入庫流程，包含各模組的職責、資料流、設定方式，以及如何新增新的 vendor parser。

---

## 架構圖

```
PDF 檔案
   │
   ▼
db/inserter.py          ← CLI 入口：解析 vendor、委派給 import_pipeline
   │
   ▼
import_pipeline.py      ← 流程協調層：呼叫 parser、embeddings、MinIO、DB
   │
   ├──► datasheet_parser/<vendor>_parser.py   ← 解析 PDF，輸出 parsed dict
   │
   ├──► db/embeddings.py (EmbeddingGenerator) ← 文字 → 向量
   │
   ├──► db/minio_client.py                   ← 圖片上傳 MinIO
   │
   └──► db/upserts.py (upsert_all)           ← 6 張表寫入 PostgreSQL
```

---

## 模組職責

### `db/inserter.py`

**角色：** CLI 入口 / vendor router

- 從 PDF 檔名前綴判斷 vendor（例如 `VS*` → `vdsemi`）
- 查找 `_VENDOR_PARSERS` 對應的 parser module
- 呼叫 `import_pipeline.import_pdf(pdf_path, parser)`

**新增 vendor 的方式：**

```python
# db/inserter.py
_VENDOR_PARSERS: dict[str, str] = {
    "vdsemi": "datasheet_parser.vdsemi_parser",
    "newvendor": "datasheet_parser.newvendor_parser",  # 新增這行
}
```

並在 `_resolve_parser()` 內加入對應的前綴判斷邏輯。

**執行方式：**

```bash
# 單一 PDF
python db/inserter.py E:/code/rag/pdfs/VSP007N06MS-G.pdf

# 批次（直接執行 __main__，掃描 E:/tmp/datasheet/ 下所有子目錄）
python db/inserter.py
```

---

### `import_pipeline.py`

**角色：** 流程協調層（唯一公開入口：`import_pdf`）

執行順序：

1. **Duck-type check** — 確認 parser 有 `parse` 與 `parse_typical_charts` 兩個 callable
2. **環境變數載入** — 從 `db/.env` 載入 DB / MinIO 設定
3. **PDF 解析** — 呼叫 `parser.parse(pdf_path)`
4. **重複檢查** — 若 `parts` 表已有此 `part_id`，直接跳過
5. **圖片抽取** — 呼叫 `parser.parse_typical_charts(pdf_path, part_id)`
6. **MinIO 上傳** — 上傳 chart PNG，**必須在 DB transaction 前完成**
7. **Embedding 生成** — 批次產生所有表的向量
8. **DB 寫入** — 呼叫 `upsert_all`，單一 transaction 覆蓋 6 張表

> **注意：** MinIO orphan 問題（chart 已上傳但 DB 寫入失敗）在此模組外處理。
> 需要跨 store 事務保證的呼叫端應自行實作補償機制。

---

### `datasheet_parser/<vendor>_parser.py`

**角色：** PDF → 結構化 dict

每個 parser 必須暴露以下兩個 callable：

```python
def parse(pdf_path: str) -> dict:
    """
    回傳格式：
    {
        "tables": {
            "parts": [{"part_id", "package", "marking", "packing", "source_page", "table_ref"}],
            "max_ratings": [...],
            "thermal_characteristics": [...],
            "electrical_characteristics": [...],
            "typical_charts": [...],
        },
        "footnotes": {"①": "text", ...}
    }
    """

def parse_typical_charts(pdf_path: str, part_id: str) -> list[dict]:
    """
    回傳格式（含 image_bytes，供 MinIO 上傳用）：
    [{"part_id", "caption", "source_page", "minio_key", "image_bytes", "table_ref"}]
    """
```

---

### `db/embeddings.py`

**角色：** 文字 → 向量（不碰 DB、MinIO、PDF）

- 預設模型：`all-MiniLM-L6-v2`（dim=384）
- 以 `EmbeddingsBundle` dataclass 回傳 5 個表的向量 list
- 文字組成規則：

| 表 | 文字格式範例 |
|---|---|
| max_ratings | `VDSS Drain-Source Voltage: 60 V` |
| thermal | `RθJC Junction-to-Case: 1.5 °C/W` |
| electrical | `[Static] RDS(on) On Resistance, VGS=10V: typ=7 max=10 mΩ` |
| typical_charts | `圖表 caption 原文` |
| footnotes | `Note ①: 說明文字` |

---

### `db/minio_client.py`

**角色：** chart PNG 上傳 MinIO

- `build_minio_client(endpoint_raw, access_key, secret_key)` — 支援帶 scheme（`http://`）或純 host:port 格式
- `upload_charts(client, bucket, charts)` — 若 bucket 不存在會自動建立

---

### `db/upserts.py`

**角色：** 純 PostgreSQL write layer

- 對 6 張表分別提供 per-table upsert function
- `upsert_all(conn, parsed, embeddings)` — 單一 transaction 寫入全部
- **重複資料處理：** `max_ratings` 與 `electrical_characteristics` 在 batch 內做去重（last-writer-wins），避免 ON CONFLICT 在同一 statement 中衝突
- **長度一致性檢查：** 在開啟 transaction 前驗證 records 與 embeddings 數量是否對齊

---

## 資料庫 Schema 摘要

| 表 | 主鍵 / Unique |
|---|---|
| `parts` | `part_id` |
| `max_ratings` | `(part_id, symbol, condition_normalized)` |
| `thermal_characteristics` | `(part_id, symbol)` |
| `electrical_characteristics` | `(part_id, symbol, condition_normalized)` |
| `typical_charts` | `(part_id, minio_key)` |
| `footnotes` | `(part_id, marker)` |

---

## 環境設定

設定檔路徑：`db/.env`

```env
DATABASE_URL=postgresql://user:password@localhost:5432/ragdb
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=ds-typical-characteristics
```

---

## 驗證層

`db/validator.py` 提供入庫前的資料驗證，見 [Phase 6 Validation System](../Phase 6：Validation System.md) 說明。

用法：

```python
from db.validator import validate_parsed

result = validate_parsed(parsed)
if not result.valid:
    for err in result.errors:
        print(f"[ERROR] {err}")
    # 決定是否停止入庫
```

詳細說明見 `db/validator.py` 模組文件。
