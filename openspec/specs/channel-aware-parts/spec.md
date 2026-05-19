## Purpose

定義 `parts` 表及相關子表、pipeline、parser、query 與 validator 如何支援 N/P channel 區分，使同一料號的 N-Channel 與 P-Channel 元件可各自獨立入庫與查詢。

## Requirements

### Requirement: parts 表以 surrogate key 支援 N/P channel

`parts` 表 SHALL 使用 `id SERIAL` 為 primary key，並以 `UNIQUE(part_number, channel)` 保證自然鍵唯一性。`channel` 欄位 SHALL 為 PostgreSQL ENUM `channel_type`，只允許值 `'N'` 或 `'P'`。

#### Scenario: 同料號不同 channel 可各自入庫

- **WHEN** 以 `part_number='LJ4525', channel='N'` 和 `part_number='LJ4525', channel='P'` 分別 upsert
- **THEN** `parts` 表應有兩筆 row，各自有獨立的 `id`，不互相覆蓋

#### Scenario: 同料號同 channel 重複 upsert 為 idempotent

- **WHEN** 以相同 `(part_number, channel)` 執行兩次 upsert
- **THEN** `parts` 表仍只有一筆 row，第二次更新 package_id / marking 等欄位

### Requirement: 子表以 INTEGER FK 關聯 parts

所有子表（`max_ratings`, `thermal_characteristics`, `electrical_characteristics`, `typical_charts`, `footnotes`）的 `part_id` 欄位 SHALL 為 `INTEGER`，參照 `parts.id`。子表 PK 結構 SHALL 保持不變（只改型別）。子表 SHALL NOT 包含 `channel` 欄位。

#### Scenario: 子表 part_id 為合法 parts.id

- **WHEN** 插入子表 row 時 `part_id` 值不存在於 `parts.id`
- **THEN** DB 拒絕插入（FK 約束違反）

#### Scenario: 查詢子表可取得 part_number 與 channel

- **WHEN** 查詢 `electrical_characteristics JOIN parts ON parts.id = electrical_characteristics.part_id`
- **THEN** 結果集包含 `part_number` 與 `channel` 欄位

### Requirement: import_pipeline 以兩步 upsert 流程寫入

`import_pipeline.import_pdf` SHALL 先執行 `upsert_parts` 並取得回傳的 `id`，再以該 numeric id 作為 `part_id` 寫入所有子表。Skip check SHALL 使用 `(part_number, channel)` 查詢 `parts` 表。

#### Scenario: 已存在的 (part_number, channel) 跳過 import

- **WHEN** `parts` 表已有 `(part_number='VSP007N06MS-G', channel='N')`
- **THEN** `import_pdf` 印出 skip 訊息並提前返回，不重新 embed 或 upsert 子表

#### Scenario: 新的 (part_number, channel) 完整走完 import 流程

- **WHEN** `parts` 表不存在對應 `(part_number, channel)` 記錄
- **THEN** pipeline 依序完成 parse → normalize → embed → upsert parts → upsert 子表

### Requirement: Parser 從 header 抽取 channel

`vdsemi_parser.parse()` SHALL 掃描每頁 header 文字，以 regex 識別 `N-Channel`/`P-Channel`（大小寫不敏感），並將結果放入 `parts` record 的 `channel` 欄位。若 header 找不到，SHALL 從 `max_ratings` 的 `V(BR)DSS` 或 `VDSS` 值正負號判斷（>0 → `'N'`，<0 → `'P'`）。若兩種方法均失敗，SHALL 回傳 hard error。

#### Scenario: Header 含 N-Channel 文字

- **WHEN** PDF 任一頁 header 含 "N-Channel Advanced Power MOSFET"
- **THEN** `parts[0]['channel']` 為 `'N'`

#### Scenario: Header 含 P-Channel 文字

- **WHEN** PDF 任一頁 header 含 "P-Channel Enhancement Mode MOSFET"
- **THEN** `parts[0]['channel']` 為 `'P'`

#### Scenario: Fallback 使用 V(BR)DSS 正負號

- **WHEN** 頁面 header 未含 N/P 文字，但 `max_ratings` 有 `VDSS` row 且值為 `40`（正數）
- **THEN** `parts[0]['channel']` 為 `'N'`

### Requirement: query.py search 支援 channel 過濾

`query.search()` SHALL 接受 `channel: str | None` 參數（`None` 表示不限）。當 `channel` 指定時，SQL WHERE 條件 SHALL 過濾 `parts.channel = channel`。查詢結果 SHALL 包含 `part_number` 與 `channel` 欄位（從 JOIN 帶回）。

#### Scenario: 指定 channel='N' 過濾查詢

- **WHEN** `search("RDS(ON)", part_number="LJ4525", channel="N")`
- **THEN** 結果只包含 `channel='N'` 的記錄

#### Scenario: channel=None 返回所有 channel 結果

- **WHEN** `search("drain current", channel=None)`
- **THEN** 結果可包含 N 和 P channel 的記錄

### Requirement: validator 驗證 channel 欄位

`validate_parsed` SHALL 驗證 `parts` 每筆 row 的 `channel` 欄位為 `'N'` 或 `'P'`。

#### Scenario: 合法 channel 值通過驗證

- **WHEN** `parts[0]['channel']` 為 `'N'`
- **THEN** validator 不產生 error

#### Scenario: 非法 channel 值產生 error

- **WHEN** `parts[0]['channel']` 為 `'X'` 或空字串
- **THEN** validator 回傳包含 channel 欄位的 Layer 1 error
