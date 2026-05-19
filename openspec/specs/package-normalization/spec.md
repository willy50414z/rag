## Purpose

定義 package 正規化流程，包含 `package_types` 查找表、`parts` 表的 FK 欄位設計、normalizer 白名單驗證，以及 upsert 流程中的 package value → id 解析，確保所有 package 值在進入 DB 前均通過白名單驗證並對應至合法的 `package_types` 記錄。

## Requirements

### Requirement: package_types 查找表存在且預填白名單

DB SHALL 包含 `package_types` 表，欄位為 `id SERIAL PK`, `value TEXT NOT NULL UNIQUE`，以及預留 metadata 欄位 `pin_count INTEGER`, `width_mm REAL`, `height_mm REAL`。`schema.sql` SHALL 包含 INSERT seed data 將所有已知 package 預填入表中。

#### Scenario: schema 建立後 package_types 有初始資料

- **WHEN** 執行 `psql ... < db/schema.sql`
- **THEN** `SELECT COUNT(*) FROM package_types` 應 >= 9（對應現有白名單長度）

#### Scenario: package_types 有唯一約束

- **WHEN** 嘗試插入已存在的 `value='TO-252'`
- **THEN** DB 回傳 UNIQUE constraint violation

### Requirement: parts.package_id 以 FK 參照 package_types

`parts` 表 SHALL 有 `package_id INTEGER NOT NULL REFERENCES package_types(id)` 欄位，移除原本的 `package TEXT` 欄位。

#### Scenario: 非法 package_id 被 DB 拒絕

- **WHEN** 插入 `parts` row 時 `package_id` 不存在於 `package_types.id`
- **THEN** DB 回傳 FK constraint violation

#### Scenario: 合法 package_id 成功插入

- **WHEN** `package_id` 對應 `package_types` 中的 `id`（例如 TO-252 的 id）
- **THEN** `parts` row 成功寫入

### Requirement: normalizer 在 import 前對 package 執行 hard error

`normalizer.normalize_parsed()` SHALL 在 `parts` 每筆 row 中檢查 `package` 欄位是否在 `PACKAGE_WHITELIST` 內。若不在白名單，SHALL 拋出 `ValueError`，並在錯誤訊息中指出具體的非法 package 值。不在白名單的 package 值 SHALL NOT 進入 embed 或 upsert 流程。

#### Scenario: 合法 package 通過 normalizer

- **WHEN** `parts[0]['package']` 為 `'TO-252'`
- **THEN** `normalize_parsed` 正常返回，不拋出例外

#### Scenario: 非法 package 在 import 前被攔截

- **WHEN** `parts[0]['package']` 為 `'UNKNOWN-PKG'`
- **THEN** `normalize_parsed` 拋出 `ValueError`，訊息包含 `'UNKNOWN-PKG'`

#### Scenario: normalizer 白名單與 DB seed 一致

- **WHEN** 對 `PACKAGE_WHITELIST` 的每個值查詢 `package_types.value`
- **THEN** 每個值都存在於 `package_types` 表中（無孤兒 whitelist 項目）

### Requirement: upsert_parts 透過 package value 查找 package_id

`upsert_parts` SHALL 接受 `package` 文字值，在寫入前查詢 `package_types` 取得對應 `id`，再以 `package_id` 寫入 `parts`。若查詢結果為空（package 不存在於 `package_types`），SHALL 拋出 `ValueError`。

#### Scenario: 已知 package 正確解析為 id

- **WHEN** upsert_parts 收到 `package='TO-252'`，且 `package_types` 有對應 row
- **THEN** `parts` row 的 `package_id` 為 `package_types` 中 TO-252 的 id

#### Scenario: 未知 package 在 upsert 時拋出例外

- **WHEN** upsert_parts 收到 `package='GHOST-PKG'`，`package_types` 無此值
- **THEN** 拋出 `ValueError`，訊息指出找不到 package
