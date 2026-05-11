## ADDED Requirements

### Requirement: 解析前 2 頁的 4 個表格
Parser SHALL 僅解析 VSP007N06MS-G.pdf 的第 1、2 頁（0-indexed: page 0、page 1），涵蓋以下 4 個表格：
- p1_t2：元件識別（Part ID、Package）
- p1_t3：絕對最大額定值（13 筆）
- p1_t4：熱阻（2 筆）
- p2_t1：電氣特性（靜態、動態、切換、體二極體，共 40 筆）

#### Scenario: 頁面範圍限制
- **WHEN** parser 執行
- **THEN** 第 3 頁以後的內容 SHALL NOT 被解析或出現在輸出中

#### Scenario: 輸出筆數
- **WHEN** parser 解析完整 PDF
- **THEN** 輸出有序 list SHALL 包含至少 50 筆記錄

### Requirement: 元件識別欄位（p1_t2）
Parser SHALL 萃取以下欄位：

| symbol | stat | 預期值 | condition |
|---|---|---|---|
| `part_id` | rating | VSP007N06MS-G | — |
| `package` | rating | PDFN5x6 | — |

#### Scenario: part_id 驗證
- **WHEN** parser 解析 p1_t2
- **THEN** `part_id` 的 `value` SHALL 等於 `"VSP007N06MS-G"`

### Requirement: 絕對最大額定值（p1_t3）
Parser SHALL 萃取以下 13 筆記錄（stat 均為 `rating`）：

| symbol | value | unit | condition |
|---|---|---|---|
| `v_br_dss` | 65 | V | — |
| `vgs` | ±20 | V | — |
| `is` | 75 | A | TC=25°C |
| `id` | 75 | A | VGS=10V, TC=25°C |
| `id` | 48 | A | VGS=10V, TC=100°C |
| `idm` | 300 | A | TC=25°C |
| `idsm` | 23 | A | VGS=10V, TA=25°C |
| `idsm` | 18 | A | VGS=10V, TA=70°C |
| `eas` | 25 | mJ | — |
| `pd` | 45 | W | TC=25°C |
| `pdsm` | 4.2 | W | TA=25°C |
| `t_stg_tj` | -55 | °C（min）| — |
| `t_stg_tj` | 150 | °C（max）| — |

Footnote 對應：`idm`→①、`eas`→②、`pdsm`→③、`rds_on`→④。

#### Scenario: t_stg_tj 拆分
- **WHEN** parser 解析 p1_t3 的溫度範圍欄位
- **THEN** SHALL 輸出兩筆記錄：`stat="min"` value=-55 與 `stat="max"` value=150，而非單一字串 `"-55 to 150"`

#### Scenario: inline condition 納入 condition 欄位
- **WHEN** parameter 文字包含 `@VGS=10V`（如 ID、IDSM）
- **THEN** `condition` 欄位 SHALL 包含 `VGS=10V` 字串

### Requirement: 熱阻（p1_t4）
Parser SHALL 萃取 2 筆熱阻記錄：

| symbol | stat | value | unit |
|---|---|---|---|
| `rthjc` | typ | 2.8 | °C/W |
| `rthja` | typ | 30 | °C/W |

#### Scenario: rthjc 數值驗證
- **WHEN** parser 解析 p1_t4
- **THEN** `symbol="rthjc"` 的 `value` SHALL 等於 `2.8`

### Requirement: 靜態電氣特性（p2_t1 static section）
Parser SHALL 萃取以下記錄：

| symbol | stat | value | unit | condition |
|---|---|---|---|---|
| `v_br_dss` | min | 65 | V | VGS=0V, ID=250µA |
| `idss` | max | 1 | µA | VDS=60V, VGS=0V |
| `idss` | max | 100 | µA | VDS=60V, VGS=0V, Tj=125°C |
| `igss` | max | ±100 | nA | VGS=±20V, VDS=0V |
| `vgs_th` | min | 1.3 | V | VDS=VGS, ID=250µA |
| `vgs_th` | typ | 1.8 | V | VDS=VGS, ID=250µA |
| `vgs_th` | max | 2.5 | V | VDS=VGS, ID=250µA |
| `rds_on` | typ | 4.5 | mΩ | VGS=10V, ID=40A, Tj=25°C |
| `rds_on` | max | 6 | mΩ | VGS=10V, ID=40A, Tj=25°C |
| `rds_on` | typ | 5.5 | mΩ | VGS=10V, ID=40A, Tj=100°C |
| `rds_on` | typ | 7.0 | mΩ | VGS=4.5V, ID=20A, Tj=25°C |
| `rds_on` | max | 10 | mΩ | VGS=4.5V, ID=20A, Tj=25°C |

#### Scenario: rds_on footnote ④ 標記
- **WHEN** parser 萃取所有 rds_on 記錄
- **THEN** 每筆 rds_on 記錄的 `footnote_ref` SHALL 等於 `"④"`

#### Scenario: vgs_th 三值完整
- **WHEN** parser 解析 VGS(TH) 欄位
- **THEN** SHALL 輸出 3 筆記錄（min=1.3、typ=1.8、max=2.5），共用相同 condition

### Requirement: 動態電氣特性（p2_t1 dynamic section）
Parser SHALL 萃取 Ciss/Coss/Crss（各 min/typ/max）、Rg（typ）、Qg@10V（typ）、Qg@4.5V（typ）、Qgs（typ）、Qgd（typ），共 14 筆。

#### Scenario: 電容三值
- **WHEN** parser 解析 Ciss
- **THEN** SHALL 輸出 min=1660、typ=1950、max=2240 三筆，unit 均為 `pF`，condition 均為 `"VDS=30V, VGS=0V, f=1MHz"`

#### Scenario: Qg 雙 VGS 版本
- **WHEN** parser 解析 Qg
- **THEN** SHALL 輸出兩筆：condition=`"VDS=30V, ID=40A, VGS=10V"` value=30 與 condition=`"VDS=30V, ID=40A, VGS=4.5V"` value=14

### Requirement: 切換特性（p2_t1 switching section）
Parser SHALL 萃取 td(on)、tr、td(off)、tf 的 typ 值，共 4 筆，condition 均為 `"VDD=30V, ID=40A, RG=3Ω, VGS=10V"`。

#### Scenario: 切換時間數值
- **WHEN** parser 解析切換特性
- **THEN** `tr_typ` 的 value SHALL 等於 `55`，unit 為 `ns`

### Requirement: 體二極體特性（p2_t1 diode section）
Parser SHALL 萃取 Vsd（typ/max）、trr（typ）、Qrr（typ），共 4 筆。

#### Scenario: trr condition 完整
- **WHEN** parser 解析 trr
- **THEN** condition SHALL 包含 `di/dt=100A/µs` 字串

### Requirement: Footnote 對照表輸出
Parser SHALL 在輸出 JSON 的頂層附加 `footnotes` dict，包含 ①②③④ 的完整文字。

#### Scenario: footnotes 存在
- **WHEN** parser 產出 JSON
- **THEN** `footnotes["①"]` SHALL 等於 `"Repetitive rating; pulse width limited by max junction temperature."`

#### Scenario: footnotes 四條完整
- **WHEN** parser 產出 JSON
- **THEN** `footnotes` dict SHALL 包含 `①`、`②`、`③`、`④` 四個 key
