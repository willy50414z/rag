# Parser Spec: VSP007N06MS-G

## 文件資訊

- 來源檔案：`pdfs/VSP007N06MS-G.pdf`
- 分類：digital-text
- 探索日期：2026-05-11
- 目標用途：RAG + DB 入庫（兩者）
- 文件家族：多份同系列（同廠商 Vergiga Semiconductor 不同型號，需跨文件比較）
- 預期 parser runtime：pdfplumber
- **資料萃取範圍：Page 1–2 only**（Page 3–6 跳過）

---

## 文件結構摘要

- 總頁數：6 頁（僅萃取 P1–P2）
- **萃取 Table 清單**：

| Table ID | 頁碼 | 內容 | pdfplumber index |
|----------|------|------|-----------------|
| P1-T1 | P1 | Part Identification（零件識別） | page[0].tables[1] |
| P1-T2 | P1 | Maximum Ratings（額定值） | page[0].tables[2] |
| P1-T3 | P1 | Thermal Characteristics（熱阻） | page[0].tables[3] |
| P2-T0 | P2 | Electrical Characteristics（電氣特性） | page[1].tables[0] |

- 跨頁 table：無
- Footnote 模式：動態圓圈數字（`①②③④`，U+2460–U+2463），數量因文件而異，P2 尾端有 4 條 NOTE
- 特殊字元：
  - `℃`（U+2103 Celsius Sign）→ 正規化為 `°C`
  - `Ω`（U+2126 Ohm Sign）→ 保留
  - ``（PUA）→ 映射為 `θ`（出現於 Thermal 表 symbol）
  - ``（PUA U+F06D）→ 映射為 `④`（出現於 RDS(ON) parameter 欄末尾，為圓圈數字的 font-specific 編碼）
  - subscript/superscript：pdfplumber 以 `\n` 分隔，例如 `R\nDS(ON)` → normalize 為 `RDS(ON)`

---

## DB Schema

### Table: parts

- **Primary Key**：`(part_id)`
- **設計理由**：零件識別是所有其他 table 的 join key；Part ID 在文件家族中唯一

| 欄位 | 型別 | Nullable | 說明 |
|------|------|----------|------|
| part_id | TEXT | NO | e.g. `VSP007N06MS-G`，從 P1 標題列萃取 |
| package | TEXT | NO | e.g. `PDFN5x6` |
| marking | TEXT | NO | e.g. `007N06M` |
| packing | TEXT | YES | e.g. `3000PCS/Reel`，部分型號可能無此欄位 |
| source_page | INT | NO | = 1（evidence trace） |
| table_ref | TEXT | NO | = `P1-T1` |

---

### Table: max_ratings

- **Primary Key**：`(part_id, symbol, condition_normalized)`
- **設計理由**：同一 symbol（如 `ID`）在不同溫度條件（TC=25°C / TC=100°C）為不同額定值，需以 condition_normalized 區分

| 欄位 | 型別 | Nullable | 說明 |
|------|------|----------|------|
| part_id | TEXT | NO | 跨文件 join key |
| symbol | TEXT | NO | e.g. `V(BR)DSS`、`ID`、`EAS`（PUA normalize 後） |
| parameter | TEXT | NO | 去除 footnote ref 後的參數說明文字 |
| condition_raw | TEXT | YES | 原始條件字串，e.g. `TC=25°C` |
| condition_normalized | TEXT | YES | 排序後 canonical string，e.g. `TC=25°C`；無條件時為空字串 |
| value_raw | TEXT | NO | 原始值字串，e.g. `±20`、`-55to150`、`75`、`--` |
| value_num | REAL | YES | 可直接解析為單一數字時的浮點值；`±20`、`--` 等情形為 NULL |
| value_min | REAL | YES | 範圍下限，e.g. `-55to150` → `-55`；`±20` → `-20` |
| value_max_num | REAL | YES | 範圍上限，e.g. `-55to150` → `150`；`±20` → `20` |
| unit | TEXT | NO | e.g. `V`、`A`、`mJ`、`°C` |
| footnote_ref | TEXT | YES | e.g. `①`、`②`，從 parameter 欄末尾萃取 |
| source_page | INT | NO | = 1 |
| table_ref | TEXT | NO | = `P1-T2` |

---

### Table: thermal_characteristics

- **Primary Key**：`(part_id, symbol)`
- **設計理由**：Thermal 表每個 symbol 只有一列（無 condition），結構與 electrical_characteristics 不同，獨立成表避免大量 NULL 欄位

| 欄位 | 型別 | Nullable | 說明 |
|------|------|----------|------|
| part_id | TEXT | NO | 跨文件 join key |
| symbol | TEXT | NO | e.g. `RθJC`、`RθJA`（PUA `` → `θ` 後） |
| parameter | TEXT | NO | e.g. `Thermal Resistance, Junction-to-Case` |
| typ | REAL | NO | 此表只有 Typical 欄位，無 Min/Max |
| unit | TEXT | NO | e.g. `°C/W` |
| source_page | INT | NO | = 1 |
| table_ref | TEXT | NO | = `P1-T3` |

---

### Table: electrical_characteristics

- **Primary Key**：`(part_id, symbol, condition_normalized)`
- **設計理由**：同一 symbol（如 `RDS(ON)`）在不同 VGS / Tj 條件下為不同量測列，condition_normalized 作為 row 唯一識別的第三鍵；`(part_id, symbol, condition_normalized)` 在本文件驗證為唯一

| 欄位 | 型別 | Nullable | 說明 |
|------|------|----------|------|
| part_id | TEXT | NO | 跨文件 join key |
| symbol | TEXT | NO | e.g. `RDS(ON)`、`Ciss`、`trr`（normalize 後） |
| parameter | TEXT | NO | 去除 footnote ref 後的參數說明文字 |
| section | TEXT | NO | `Static`、`Dynamic`、`Switching`、`DiodeCharacteristics` 四個值之一 |
| condition_raw | TEXT | YES | 合併後的條件原文，e.g. `VGS=10V, ID=40A, Tj=100°C` |
| condition_kv | TEXT | YES | JSON 字串，e.g. `{"ID":"40A","Tj":"100°C","VGS":"10V"}` |
| condition_normalized | TEXT | YES | key 排序後 canonical string，e.g. `ID=40A,Tj=100°C,VGS=10V`；無條件時為空字串 |
| min | REAL | YES | `--` 或缺失時為 NULL |
| typ | REAL | YES | `--` 或缺失時為 NULL |
| max | REAL | YES | `--` 或缺失時為 NULL |
| value_raw | TEXT | YES | 非標準數字原文，e.g. `±100`（IGSS max）；一般數值列為 NULL |
| unit | TEXT | NO | e.g. `mΩ`、`pF`、`nC`、`ns`、`V` |
| footnote_ref | TEXT | YES | 圓圈數字，從 parameter 欄末尾萃取 |
| source_page | INT | NO | = 2 |
| table_ref | TEXT | NO | = `P2-T0` |

---

## Parser 定位策略

**原則**：所有 table 以 header row 文字內容定位，禁止 hardcode page index 或 table 出現順序。

### P1-T1：Part Identification

- **定位方式**：在 P1 搜尋 header row 包含 `["PartID", "PackageType", "Marking", "Packing"]` 的 table
- **搜尋範圍**：Page 1
- **Fallback**：若找不到，嘗試從頁面文字直接以 regex 萃取（`VSP\w+` + `PDFN\w+` pattern）
- **萃取模式**：固定 1 data row（不需 forward-fill）

### P1-T2：Maximum Ratings

- **定位方式**：在 P1 搜尋 header row 包含 `["Symbol", "Parameter", "Rating", "Unit"]`（含 None 佔位欄）的 table
- **搜尋範圍**：Page 1
- **Fallback**：若找不到，log warning，回傳空 list（不 raise）
- **Section 分段**：此表無 section header，所有列均屬 Maximum Ratings

### P1-T3：Thermal Characteristics

- **定位方式**：在 P1 搜尋 header row 包含 `["Symbol", "Parameter", "Typical", "Unit"]` 的 table
- **搜尋範圍**：Page 1
- **Fallback**：同上，log warning + 空 list
- **萃取模式**：固定 2 data rows（RθJC、RθJA）

### P2-T0：Electrical Characteristics

- **定位方式**：在 P2 搜尋 header row 包含 `["Symbol", "Parameter", "Condition", "Min.", "Typ.", "Max.", "Unit"]`（含 None 佔位欄，共 8 欄）的 table
- **搜尋範圍**：Page 2
- **Fallback**：log warning + 空 list
- **Section 分段依據**：列中 col[0] 符合 regex `(Static|Dynamic|Switching|Source-Drain)\s+\w*\s*Characteristics`，且 col[1]–col[6] 均為 None 或空字串 → 視為 section header row，不存為資料，更新 section 狀態機

  | Section header 文字（含） | section 欄位值 |
  |--------------------------|---------------|
  | `Static Electrical Characteristics` | `Static` |
  | `Dynamic Electrical Characteristics` | `Dynamic` |
  | `Switching Characteristics` | `Switching` |
  | `Source-Drain Diode Characteristics` | `DiodeCharacteristics` |

---

## 欄位處理規則

### symbol（所有 table 共用）

- **業務意義**：參數的標準縮寫，跨文件比較的語意鍵
- **正規化規則**：
  1. pdfplumber subscript 換行展平：`R\nDS(ON)` → `RDS(ON)`，`V\n(BR)DSS` → `V(BR)DSS`
  2. PUA Unicode 替換：`` → `θ`（symbol 欄）；`` → `④`（parameter 欄，後續由 footnote_ref 偵測邏輯處理）
  3. **Qg(xV) 特例**：pdfplumber 將 `Q (10V)\ng` / `Q (4.5V)\ng` 展平後，括號內電壓（`10V`、`4.5V`）是 VGS 條件，不是 symbol 名稱的一部分。
     - 正規化後 symbol 統一為 `Qg`
     - 括號內電壓提取為 `VGS` condition override（見 condition_raw forward-fill 規則）
     - 識別 regex：`Qg\s*\((\d+\.?\d*V)\)` → symbol=`Qg`，VGS=captured group
  4. 結果 strip 空白
- **Sample 值**：`RDS(ON)`、`V(BR)DSS`、`RθJC`、`ID`、`VGS(TH)`、`Qg`（來自 `Qg(10V)` 或 `Qg(4.5V)`）

---

### condition_raw（max_ratings / electrical_characteristics）

- **業務意義**：量測時的測試條件，是 row key 的一部分
- **資料來源**：
  - max_ratings：P1-T2 的 condition 欄（col[2]）
  - electrical_characteristics：P2-T0 的 col[2]（primary）+ col[3]（secondary temperature override）
- **Forward-fill 規則**（electrical_characteristics）：
  - 當 col[0]（symbol）為 None → 繼承上列的 symbol、parameter、condition_raw（primary）
  - 當 col[3]（secondary condition）不為 None → 將 col[3] 解析的溫度條件附加到繼承的 condition_raw 後
  - **RDS(ON) 特例**：col[2] 含 `\n` → 僅取 `\n` 前的第一行作為 primary condition（`\n` 後的溫度行屬於 col[3] 範圍，由 continuation row 的 col[3] 處理）
  - **Qg(xV) 特例**：當 symbol 欄符合 `Qg(xV)` 模式時，從 symbol 中提取 VGS 值，覆蓋繼承 condition 中的 VGS 欄位。
    - `Qg(10V)` 行（有完整 condition `VDS=30V, ID=40A, VGS=10V`）：直接使用 col[2] condition
    - `Qg(4.5V)` 行（col[2]=None，繼承上列 condition）：繼承後將 VGS 覆蓋為 `4.5V`
    - 最終：`Qg(10V)` → condition=`VDS=30V, ID=40A, VGS=10V`；`Qg(4.5V)` → condition=`VDS=30V, ID=40A, VGS=4.5V`
    - `Qgs`、`Qgd` 仍正常繼承 `Qg(10V)` 的 condition（`VGS=10V`），不受此規則影響
- **溫度符號正規化**：`T=100℃\nj` → `Tj=100°C`（`\nj` = subscript j，`℃` → `°C`）
- **Sample 值**：`VGS=10V, ID=40A`、`VGS=10V, ID=40A, Tj=100°C`、`Tj=25°C, Isd=40A, VGS=0V, di/dt=100A/μs`

---

### condition_kv（electrical_characteristics 專用）

- **業務意義**：結構化條件，支援欄位級別查詢（e.g. 只查 Tj=100°C 的資料）
- **解析規則**：
  1. 輸入：condition_raw 正規化後字串
  2. Split on `,` → 各 token
  3. 每個 token split on `=` → `{key: value}`
  4. 無法解析的 token（如含空格的自然語言片段）→ 存入 `_raw` key
- **型別**：JSON 字串，存入 DB 時使用 TEXT 欄位
- **condition_normalized**：將 condition_kv 的 key 排序後，`join("key=value", ",")`
- **無條件情形**：condition_raw 為 NULL 時，condition_kv = NULL，condition_normalized = `""`（空字串，仍可作為 PK component）
- **Sample 值**：
  - 輸入：`VGS=10V, ID=40A, Tj=100°C`
  - 輸出：`{"ID":"40A","Tj":"100°C","VGS":"10V"}`
  - normalized：`ID=40A,Tj=100°C,VGS=10V`

---

### value_raw / value_num / value_min / value_max_num（max_ratings 專用）

- **業務意義**：額定值，部分為範圍或雙極性，需保留原文並拆解數值
- **解析規則**：

  | 輸入 | value_raw | value_num | value_min | value_max_num |
  |------|-----------|-----------|-----------|---------------|
  | `65` | `"65"` | 65.0 | NULL | NULL |
  | `75` | `"75"` | 75.0 | NULL | NULL |
  | `±20` | `"±20"` | NULL | -20.0 | 20.0 |
  | `±100` | `"±100"` | NULL | -100.0 | 100.0 |
  | `-55to150` | `"-55to150"` | NULL | -55.0 | 150.0 |
  | `--` | `"--"` | NULL | NULL | NULL |

- **`--` 處理**：此值代表「未規範」，所有數值欄位設 NULL，value_raw 仍存 `"--"`

---

### min / typ / max（electrical_characteristics 專用）

- **業務意義**：Min / Typical / Max 量測值
- **解析規則**：
  - `--` → NULL（float 欄位）
  - 純數字字串 → float
  - `±100`（出現於 IGSS max 欄）→ max 欄存 NULL，同時在 value_raw 存原文
- **IGSS 特例**：`max = "±100"` → `max = NULL`，`value_raw = "±100"`

---

### footnote_ref（所有 table）

- **業務意義**：標注哪一筆資料受頁尾 NOTE 約束
- **萃取規則**：
  1. **PUA 前置映射**：將 parameter 字串中的 `` 替換為 `④`（其他 PUA 圈數字若出現亦同理轉換）
  2. 再以 regex 偵測圓圈數字：`[①②③④⑤⑥⑦⑧⑨]`（U+2460–U+2468）
  3. 萃取後 strip 出 parameter 主文；footnote 符號存入 footnote_ref
  4. 不 hardcode 圓圈數字數量（動態偵測）
- **Sample 值**：`①`（IDM pulse rating）、`②`（EAS 測試條件）、`③`（PDSM ambient rating）、`④`（RDS(ON) pulse width ≤380μs 限制）

---

### section（electrical_characteristics 專用）

- **業務意義**：電氣特性分類，供 RAG chunk 邊界使用
- **狀態機**：parser 維護 `current_section` 變數，遇 section header row 更新，後續資料列繼承
- **允許值**：`Static`、`Dynamic`、`Switching`、`DiodeCharacteristics`
- **初始值**：`Static`（第一個 header 出現前的資料列若有，預設為 Static）

---

## 跨文件穩定性備註

文件家族：Vergiga Semiconductor VSP 系列 N-Channel MOSFET

| 結構元素 | 穩定性評估 | Parser 策略 |
|---------|-----------|------------|
| 欄位標題文字（Symbol/Parameter/Min./Typ./Max./Unit） | **高** | 作為 anchor，不 hardcode index |
| Section header 文字（Static/Dynamic/Switching/Source-Drain Diode） | **高** | 用 regex 偵測 |
| Part ID 格式（VSP + 電流代碼 + N06MS-G） | **高** | 從標題文字 regex 萃取 |
| 圓圈 footnote 數量 | **低** | 動態偵測，不 hardcode 上限 |
| RDS(ON) 測試條件種類（VGS=10V / 4.5V） | **中** | 兩組條件均為 nullable；部分型號可能只有 VGS=10V 一組 |
| EAS（Avalanche energy） | **中低** | nullable；部分型號可能無此 symbol |
| IDSM（ambient 電流額定） | **中低** | nullable |
| 個別 switching time 數值（td(on), tr 等） | **中** | nullable（部分型號可能省略 Min/Max） |
| Thermal 表欄位（只有 Typical，無 Min/Max） | **高** | 固定結構 |

**跨文件必定存在的 symbol（required across family）**：
`V(BR)DSS`、`VGS`、`ID`、`VGS(TH)`、`RDS(ON)`（至少 VGS=10V 條件）、`Ciss`、`Coss`、`Crss`、`VSD`、`RθJC`、`RθJA`

**可能在某型號缺失的 symbol（optional / nullable）**：
`EAS`、`IDSM`、`IGSS`、`Rg`、`Qg`（VGS=4.5V 條件）、`trr`、`Qrr`

---

## RAG 設計

- **進向量庫的欄位**：`parameter`（完整參數名稱）+ `condition_raw`（條件文字）+ 數值摘要（`typ` 或 `max`）
  - 組合方式：`"{parameter}, Condition: {condition_raw}, Typ: {typ} {unit}, Max: {max} {unit}"`
- **Structured query 欄位**：`part_id`、`symbol`、`section`、`condition_kv`（JSON filter）、`min`、`typ`、`max`、`unit`
- **Condition 正規化策略**：雙欄並存 — `condition_raw`（原文保留）+ `condition_kv`（JSON KV）+ `condition_normalized`（排序後 canonical string 作 PK component）
- **跨文件比較需求**：有 — `part_id` 作為所有 table 的 join key，`symbol + condition_normalized` 作為跨文件比較的語意鍵

---

## Chunking Considerations

- **不拆碎原則**：同一 symbol 的多個條件列必須在同一 chunk
  - e.g. `RDS(ON)` 三列（VGS=10V/Tj=25°C、VGS=10V/Tj=100°C、VGS=4.5V/Tj=25°C）→ 同一 chunk
  - e.g. `ID` 兩列（TC=25°C、TC=100°C）→ 同一 chunk
- **Chunk 邊界**：以 section 為邊界（Static / Dynamic / Switching / DiodeCharacteristics）
- **Footnote 附加層**：掛在 section chunk 層級，不是單列層級
- **Chunk metadata**（供 retrieval filter）：
  - `part_id`：零件識別
  - `section`：電氣特性分類
  - `page_ref`：來源頁碼
  - `symbol_list`：當前 chunk 包含的 symbol 清單（支援 symbol 層級的 pre-filter）

---

## 未解決的模糊項目

無。所有 Q1–Q4 設計決策已於 explore 階段由 user 確認。
