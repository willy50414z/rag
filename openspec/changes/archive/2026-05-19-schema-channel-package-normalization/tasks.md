## 1. Schema (db/schema.sql)

- [x] 1.1 新增 `channel_type` ENUM (`'N'`, `'P'`)
- [x] 1.2 新增 `package_types` 表（`id SERIAL PK`, `value TEXT UNIQUE`, `pin_count INTEGER`, `width_mm REAL`, `height_mm REAL`）
- [x] 1.3 INSERT seed data：將 9 個白名單 package 值預填入 `package_types`
- [x] 1.4 改寫 `parts` 表：加 `id SERIAL PK`、`part_number TEXT`、`channel channel_type NOT NULL`、`package_id INTEGER FK → package_types`、`UNIQUE(part_number, channel)`；移除原 `PRIMARY KEY(part_id)` 和 `package TEXT`
- [x] 1.5 所有子表（`max_ratings`, `thermal_characteristics`, `electrical_characteristics`, `typical_charts`, `footnotes`）：`part_id` 欄位型別改為 `INTEGER`，加 `REFERENCES parts(id)`

## 2. normalizer.py (datasheet_parser/normalizer.py)

- [x] 2.1 新增 `PACKAGE_WHITELIST` 常數（與 schema seed data 一致的 9 個值）
- [x] 2.2 實作 `normalize_package(package: str) -> str`：不在白名單則拋出 `ValueError`
- [x] 2.3 實作 `normalize_channel(raw: str) -> str`：將 `N-Channel`/`N-CH`/`N channel` 等映射為 `'N'`，P 系列映射為 `'P'`，無法識別拋出 `ValueError`
- [x] 2.4 在 `normalize_parsed()` 中對 `parts` 每筆 row 呼叫 `normalize_package` 和 `normalize_channel`

## 3. vdsemi_parser.py (datasheet_parser/vdsemi_parser.py)

- [x] 3.1 新增 `_extract_channel(pdf) -> str`：掃描所有頁面 header，regex 識別 `N[- ]?[Cc]hannel` / `P[- ]?[Cc]hannel`
- [x] 3.2 實作 fallback：若 header 未找到 channel，從 parsed max_ratings 中找 `V(BR)DSS` 或 `VDSS` 值，正數 → `'N'`，負數 → `'P'`
- [x] 3.3 `parse()` 輸出的 `parts` record 欄位名稱由 `part_id` 改為 `part_number`，並加入 `channel` 欄位
- [x] 3.4 確認 `parse_typical_charts` 也改用 `part_number` 欄位（若有用到）

## 4. db/upserts.py

- [x] 4.1 `upsert_parts`：改為 `INSERT ... RETURNING id`；在寫入前查詢 `package_types` 取得 `package_id`；ON CONFLICT 改為 `(part_number, channel)`；回傳 `int` (numeric id)
- [x] 4.2 其餘子表 upsert 函式（`upsert_max_ratings`, `upsert_thermal`, `upsert_electrical`, `upsert_charts`, `upsert_footnotes`）：`part_id` 參數型別改為 `int`，SQL 中 `part_id` 欄位值直接使用傳入的 integer
- [x] 4.3 `upsert_all`：改為先呼叫 `upsert_parts` 取得 `numeric_id`，再傳入各子表 upsert

## 5. import_pipeline.py

- [x] 5.1 skip check 改為查詢 `(part_number, channel)` 是否存在於 `parts`，需在 `parse()` 之後執行
- [x] 5.2 `part_id` 變數重命名為 `part_number`，避免與 numeric id 混淆
- [x] 5.3 確認 `upsert_all` 呼叫簽章與新版 `upserts.py` 一致

## 6. db/re_embed.py

- [x] 6.1 `_TABLES` 中各表的 `pk` tuple 更新：`part_id` 欄位在 UPDATE WHERE 子句中改以 integer 比對（SQL 型別自動推斷，邏輯不變，確認 `IS NOT DISTINCT FROM` 仍適用）
- [x] 6.2 dry-run 測試確認 re_embed 能正確讀取所有表的 row count

## 7. db/validator.py

- [x] 7.1 `_validate_parts`：新增 `channel` 欄位驗證（必填，值必須為 `'N'` 或 `'P'`）
- [x] 7.2 `_validate_parts`：`part_id` 相關檢查改為 `part_number` 欄位
- [x] 7.3 `_cross_validate_parts_consistency`：改用 `part_number` 欄位做跨表 part 一致性檢查（子表仍只有 int `part_id`，此驗證邏輯可能簡化）

## 8. db/query.py

- [x] 8.1 所有 `_TABLE_QUERIES` SQL 加入 `JOIN parts p ON p.id = <table>.part_id`，SELECT 帶回 `p.part_number`, `p.channel`
- [x] 8.2 `search()` 函式簽章：`part_id: str | None` 改為 `part_number: str | None`，新增 `channel: str | None = None` 參數
- [x] 8.3 WHERE 條件改為 `p.part_number = %(part_number)s AND (%(channel)s IS NULL OR p.channel = %(channel)s)`
- [x] 8.4 `format_context`：`r.get("part_id")` 改為 `r.get("part_number")`，視需要顯示 channel

## 9. 驗證

- [x] 9.1 重建 DB schema（`psql ... < db/schema.sql`）確認無錯誤
- [x] 9.2 執行 `python db/inserter.py <single_pdf>` 確認單一 PDF import 成功
- [x] 9.3 執行 `python db/re_embed.py --dry-run` 確認所有表 row count 正確
- [x] 9.4 執行 `python db/query.py` sample queries 確認 search 結果包含 `part_number` 與 `channel`
- [x] 9.5 確認 `_test_normalizer.py` / `_test_validator.py` 通過（或更新測試以反映新欄位）
