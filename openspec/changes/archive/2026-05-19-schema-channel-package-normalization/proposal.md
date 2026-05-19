## Why

目前 `parts` 表以 `part_id TEXT` 為唯一鍵，無法支援同一料號存在 N/P 雙 channel 的情況（例如 LJ4525 互補對 MOSFET），且 `package` 欄位為自由文字，缺乏白名單約束與未來擴充 metadata 的能力。需要在保持 RAG 查詢準度的前提下，完成 schema 正規化。

## What Changes

- **BREAKING** `parts` 表新增 surrogate PK `id SERIAL`，自然鍵由 `part_id TEXT` 改為 `part_number TEXT`，新增 `channel channel_type NOT NULL`（PostgreSQL ENUM `'N'|'P'`），`UNIQUE(part_number, channel)`
- **BREAKING** 新增 `package_types` 表（`id SERIAL PK`, `value TEXT UNIQUE`, 預留 `pin_count`, `width_mm` 等 metadata 欄位），`parts.package` 改為 `package_id INTEGER FK → package_types.id`
- **BREAKING** 所有子表（`max_ratings`, `thermal_characteristics`, `electrical_characteristics`, `typical_charts`, `footnotes`）的 `part_id TEXT` 改為 `part_id INTEGER FK → parts.id`；各表 PK 結構不變，無需加 `channel` 欄位
- `normalizer.py` 新增 `PACKAGE_WHITELIST` hard error（import 前早期驗證）及 `normalize_channel()` 函式
- `vdsemi_parser.py` 新增從頁面 header 文字抽取 channel（`N-Channel`/`P-Channel` regex），fallback 為 `V(BR)DSS` 正負號判斷；parts record 輸出欄位名稱由 `part_id` 改為 `part_number`
- `import_pipeline.py` 改為兩步 upsert：先 upsert parts `RETURNING id`，再以 numeric id 寫入子表；skip check 改用 `(part_number, channel)` 查詢
- `query.py` search API 新增 `channel` 參數，SQL 改為 JOIN parts 取得 `part_number` + `channel`；`format_context` 輸出改用 `part_number`
- `re_embed.py` pk tuple 中 `part_id` 型別由 TEXT 改為 INTEGER（值不變，邏輯不變）
- `validator.py` 新增 `channel` 欄位格式驗證（必須為 `'N'` 或 `'P'`）

## Capabilities

### New Capabilities

- `channel-aware-parts`：parts 表支援 N/P channel 區分，surrogate key 讓子表維持簡單結構；含 parser 端的 channel 抽取邏輯
- `package-normalization`：新增 `package_types` 查找表，package 白名單由 DB FK 約束守門，normalizer 提供 import 前的 hard error 早期驗證

### Modified Capabilities

無現有 spec 檔案（openspec/specs/ 目前為空）

## Impact

- **DB schema**：破壞性變更，所有現有資料需要 migration 或 rebuild
- **db/schema.sql**：新增 `channel_type` ENUM、`package_types` 表；`parts` 改 PK；子表 `part_id` 型別改 INTEGER
- **db/upserts.py**：upsert_parts 改為 `RETURNING id`；所有子表 upsert 接收 `int part_id` 參數
- **db/re_embed.py**：pk tuple 型別對應更新
- **db/query.py**：search 函式簽章變更（新增 `channel` 參數）；SQL 加 JOIN；`format_context` 欄位名稱更新
- **db/validator.py**：validate_parts 加 channel 驗證
- **import_pipeline.py**：upsert 流程由單步改為兩步
- **datasheet_parser/normalizer.py**：新增 package 白名單與 channel 正規化
- **datasheet_parser/vdsemi_parser.py**：新增 channel 抽取；parts record 格式調整
- **不影響**：`db/embeddings.py`、`db/text_representations.py`、`db/minio_client.py`（RAG embedding 邏輯完全不受此變更影響）
- **不在此 change 範圍**：雙 channel PDF（LJ4525 型）的新 parser 實作
