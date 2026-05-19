## ADDED Requirements

### Requirement: Condition 字串為單一正規化字串，不拆解為多筆 record

parser.py 中的 condition 欄位 SHALL 將 PDF 表格 condition cell 的完整內容視為單一測試條件字串，不因逗號分隔而拆分為多筆 record。多個不同條件對應 table 的不同 row，不對應同一 cell 的分割。

#### Scenario: Condition cell 含多個參數

- **WHEN** PDF condition cell 內容為 `VGS=10V, Tj=25°C, ID=8A`
- **THEN** parser 輸出一筆 record，condition 欄位為正規化後的整體字串，不拆分為三筆

### Requirement: Condition 字串執行五步正規化後存入

parser.py SHALL 對每個 condition 字串依序執行以下五步正規化，再存入 record：
1. strip 首尾空白
2. 合併 cell 內換行（`\n` → 空格）
3. 等號兩側空白移除（`VGS = 10V` → `VGS=10V`）
4. 依 spec 特殊字元規則正規化（℃→°C 等）
5. 不移除逗號、不改變參數順序

#### Scenario: Condition 含等號兩側空白

- **WHEN** PDF condition cell 為 `VGS = 10V, Tj = 25°C`
- **THEN** parser 輸出 condition 為 `VGS=10V, Tj=25°C`

#### Scenario: Condition 含 cell 內換行

- **WHEN** pdfplumber 解析出的 condition cell 含 `\n`
- **THEN** parser 將 `\n` 替換為空格後正規化輸出

### Requirement: Footnote marker 在 condition 正規化前分離

parser.py SHALL 在執行 condition 正規化之前，先從 condition cell 提取 footnote marker（如 ①②③），將其存入 `footnote_ref` 欄位，再對剩餘字串執行正規化，確保 footnote marker 不污染 primary key。

#### Scenario: Condition cell 含 footnote marker

- **WHEN** PDF condition cell 為 `VGS=10V, Tj=25°C ①`
- **THEN** parser 輸出 condition 為 `VGS=10V, Tj=25°C`，footnote_ref 為 `①`

### Requirement: Condition 空值依 spec 設定處理

parser.py SHALL 對 condition 為 null 的 row 依以下路徑處理：
- 若 spec 標記 `forward_fill: true`：繼承上列 condition
- 若 spec 標記 `nullable: false` 且無 forward-fill：加入 warning，不可入庫
- 若 spec 標記 `nullable: true`（業務允許無 condition）：存為空字串 `""`，確保 primary key 可組合

#### Scenario: Condition nullable 且業務允許

- **WHEN** table 的 condition 欄 spec 標記 `nullable: true`（如 max_ratings）
- **THEN** parser 輸出 condition 為 `""`，不輸出 null，primary key 仍可組合
