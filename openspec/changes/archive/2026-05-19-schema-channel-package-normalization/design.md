## Context

目前 `parts` 表以 `part_id TEXT` 為唯一鍵，所有子表也以相同 TEXT 欄位關聯。此設計在遇到 N/P 雙 channel 同料號（如 LJ4525 互補對 MOSFET）時無法區分，且 `package` 為自由文字欄位，無法保證白名單約束或未來擴充 metadata。專案尚未上線，可直接修改 schema 而無需 online migration。

## Goals / Non-Goals

**Goals:**
- `parts` 表以 surrogate `id SERIAL` 為 PK，`UNIQUE(part_number, channel)` 保證自然鍵唯一性
- 新增 `package_types` 查找表，預留 metadata 欄位
- 所有子表 `part_id` 改為 INTEGER FK，PK 結構不變
- parser 能從 header 文字抽取 channel；normalizer 提供 package 白名單 hard error
- query API 支援 channel 過濾

**Non-Goals:**
- 雙 channel PDF 的新 parser（LJ4525 型，獨立 change）
- Online migration 腳本（專案未上線，直接重建 schema）
- Embedding 邏輯異動（RAG 準度不受此 change 影響）

## Decisions

### 1. Surrogate key 而非複合自然鍵

**決定**：`parts.id SERIAL` 為 PK，子表 `part_id INTEGER FK → parts.id`。

**為何不用複合自然鍵 `(part_number, channel)`**：子表若每張都帶 `channel` 欄位，未來再新增維度（電壓等級、溫度規格）會需要修改所有子表。Surrogate key 讓 N/P 唯一性只需在 `parts` 一張表維護。

### 2. channel 拆分為 topology + polarity 兩個 ENUM 欄位

**決定**：`CREATE TYPE channel_topology AS ENUM ('Single','Dual','Comp','Comp2','Asymmetric')`；`CREATE TYPE channel_polarity AS ENUM ('N','P')`。`parts` 表有兩個獨立欄位：`topology channel_topology NOT NULL` 和 `polarity channel_polarity NOT NULL`。`UNIQUE(part_number, topology, polarity)`。

**為何拆分而非單一 ENUM 或 sys_config**：已知 channel 值有 9 種（Single N/P、Dual N/P、Comp N/P、Comp2 N/P、Asymmetric N），拆分後 `WHERE polarity='N'` 可直接過濾極性，`WHERE topology='Dual'` 可直接過濾拓樸，不需 LIKE pattern。V(BR)DSS fallback 天然對應 polarity 欄位。sys_config 為 EAV anti-pattern，每次查詢需多次 JOIN。

### 3. package 用獨立 package_types 表

**決定**：`package_types(id SERIAL PK, value TEXT UNIQUE, pin_count, width_mm, ...)`，`parts.package_id INTEGER FK`。

**為何不用 ENUM**：package 未來可能需要存封裝尺寸、針腳數等 metadata；ENUM 無法附加屬性。獨立表讓 `ALTER TABLE package_types ADD COLUMN` 即可擴充，不需要改 parts 表。

### 4. 兩步 upsert 流程

**決定**：`import_pipeline.py` 先 `upsert_parts RETURNING id`，再以 numeric id 寫入子表。

**理由**：子表需要 numeric `part_id`，而該值只有在 parts upsert 完成後才存在。Skip check 改為查 `(part_number, channel)` 在 parts 表是否已存在。

### 5. Channel 抽取策略

**決定**：Parser 優先從頁面 header regex 抽取（`N[- ]?[Cc]hannel` / `P[- ]?[Cc]hannel`）；若所有頁面都找不到，從 `max_ratings` 的 `V(BR)DSS` 或 `VDSS` 值正負號判斷（>0 → N，<0 → P）；兩者都失敗則 `normalize_channel` 回傳 hard error。

### 6. Normalizer 的 package 白名單時機

**決定**：`normalizer.py` 在 import 前做 hard error（早期失敗，不進 embed/upsert）；DB FK 是最後防線。兩層守門確保錯誤可在 app 層給出清晰訊息。

## Risks / Trade-offs

- **[Risk] 查詢需要 JOIN parts**：`query.py` 每個 `_TABLE_QUERIES` 都要加 `JOIN parts`，稍微增加複雜度 → 用統一的 helper 函式套入 JOIN，降低重複。
- **[Risk] re_embed.py 的 pk tuple 型別不對**：目前 pk 用 TEXT `part_id` 查詢，改為 INTEGER 後若未更新，UPDATE WHERE 會全部失敗 → tasks 中列為獨立驗證步驟。
- **[Trade-off] package_types 需預填資料**：Schema 建立後需 seed `package_types` 表，才能 import 任何 PDF → `schema.sql` 直接包含 INSERT seed data。

## Migration Plan

1. 重建 DB（`psql ... < db/schema.sql`）
2. `package_types` seed data 已包含在 `schema.sql` 的 INSERT 語句中
3. 重跑 `python db/inserter.py` 匯入所有 PDF

## Open Questions

- 無（所有設計決策已在 explore 階段確認）
