# MOSFET Datasheet 領域知識

當 PDF 被識別為 MOSFET 電子零件規格書時，載入此文件作為探索 context。

---

## 文件辨識特徵

以下特徵出現時可判定為 MOSFET datasheet：

- 標題或副標題含 `MOSFET`、`N-Channel`、`P-Channel`、`Power MOSFET`
- 含有 `Absolute Maximum Ratings` 或 `Maximum Ratings` 表格
- 含有 `Electrical Characteristics` 表格，且有 `VGS`、`VDS`、`RDS(on)` 等符號
- 含有 `Gate Charge`、`Switching Characteristics`、`Body Diode` 等區段

---

## 文件標準區段與對應欄位

MOSFET datasheet 通常按此順序排列：

| 區段名稱 | 常見標題變體 | 包含欄位 |
|---|---|---|
| 識別資訊 | （頁首、料號區） | `part_id`、`package`、`channel` |
| 最大額定值 | Absolute Maximum Ratings, Maximum Ratings | `v_br_dss`(rating)、`vgs`、`id`、`idm`、`is`、`idsm`、`eas`、`pd`、`pdsm`、`t_stg_tj` |
| 熱阻 | Thermal Resistance | `rthjc`、`rthja` |
| 靜態電氣特性 | Static Electrical Characteristics, Static Characteristics | `v_br_dss`(電氣)、`idss`、`igss`、`vgs_th`、`rds_on` |
| 動態特性 | Dynamic Characteristics | `ciss`、`coss`、`crss`、`rg`、`qg`、`qgs`、`qgd` |
| 切換特性 | Switching Characteristics, Switching Performance | `td_on`、`tr`、`td_off`、`tf` |
| 體二極體 | Body Diode, Diode Characteristics | `vsd`、`trr`、`qrr` |

---

## 欄位目錄

### 識別欄位（無 stat 概念，直接萃取字串）

| symbol | 說明 | 型別 | 驗證規則 |
|---|---|---|---|
| `part_id` | 元件料號 | string | 非空字串；通常在第一頁頁首或第一個表格 |
| `package` | 封裝型式 | string | 非空字串；例如 `PDFN5x6`、`TO-220`、`SOT-23` |
| `channel` | 通道型式 | enum | 只允許 `N` 或 `P`；從標題「N-Channel」或「P-Channel」萃取 |

### 最大額定值（stat 固定為 `rating`）

| symbol | 說明 | 單位 | 驗證規則 |
|---|---|---|---|
| `v_br_dss` | Drain-Source Breakdown Voltage | V | N-Channel > 0；P-Channel < 0 |
| `vgs` | Gate-Source Voltage | V | 通常為 `±N` 對稱值 |
| `id` | Continuous Drain Current | A | N > 0，P < 0；可能有多筆不同 TC 條件 |
| `idm` | Pulse Drain Current | A | N > 0，P < 0 |
| `is` | Diode Continuous Forward Current | A | N > 0，P < 0 |
| `idsm` | Continuous Drain Current（SMD） | A | N > 0，P < 0；可能有多筆不同 TA 條件 |
| `eas` | Avalanche Energy | mJ | > 0 |
| `pd` | Maximum Power Dissipation（case） | W | > 0 |
| `pdsm` | Maximum Power Dissipation（SMD/ambient） | W | > 0 |
| `t_stg_tj` | Storage and Junction Temperature Range | °C | 拆為 min（負值）與 max（正值）兩筆 |

### 熱阻（stat 為 `typ` 或 `max`）

| symbol | 說明 | 單位 | 驗證規則 |
|---|---|---|---|
| `rthjc` | Thermal Resistance Junction-to-Case | °C/W | > 0 |
| `rthja` | Thermal Resistance Junction-to-Ambient | °C/W | > 0 |

### 靜態電氣特性

| symbol | 說明 | 單位 | try_stats | 驗證規則 |
|---|---|---|---|---|
| `v_br_dss` | Drain-Source Breakdown Voltage（量測） | V | `[min]` | N > 0，P < 0 |
| `idss` | Zero Gate Voltage Drain Current | µA | `[typ, max]` | N > 0，P < 0；可能有高溫（Tj=125°C）條件額外一筆 |
| `igss` | Gate-Body Leakage Current | nA | `[max]` | 通常為 `±N` 對稱值 |
| `vgs_th` | Gate Threshold Voltage | V | `[min, typ, max]` | min < typ < max；N-Channel 通常 1–5 V |
| `rds_on` | Drain-Source On-State Resistance | mΩ | `[typ, max]`（每個 condition 組） | > 0；VGS=10V 組為主要，VGS=4.5V 組為次要 |

### 動態特性

| symbol | 說明 | 單位 | try_stats | 驗證規則 |
|---|---|---|---|---|
| `ciss` | Input Capacitance | pF | `[min, typ, max]` | > 0；min < typ < max |
| `coss` | Output Capacitance | pF | `[min, typ, max]` | > 0；coss < ciss |
| `crss` | Reverse Transfer Capacitance | pF | `[min, typ, max]` | > 0；crss < coss |
| `rg` | Gate Resistance | Ω | `[typ, max]` | > 0 |
| `qg` | Total Gate Charge | nC | `[typ]`（每個 VGS condition） | > 0；VGS=10V 為主要，VGS=4.5V 為次要 |
| `qgs` | Gate-Source Charge | nC | `[typ]` | > 0；qgs < qg |
| `qgd` | Gate-Drain Charge | nC | `[typ]` | > 0；qgd < qg |

### 切換特性（條件通常含 VDD、ID、RG、VGS）

| symbol | 說明 | 單位 | try_stats | 驗證規則 |
|---|---|---|---|---|
| `td_on` | Turn-on Delay Time | ns | `[typ, max]` | > 0 |
| `tr` | Turn-on Rise Time | ns | `[typ, max]` | > 0 |
| `td_off` | Turn-off Delay Time | ns | `[typ, max]` | > 0 |
| `tf` | Turn-off Fall Time | ns | `[typ, max]` | > 0 |

### 體二極體

| symbol | 說明 | 單位 | try_stats | 驗證規則 |
|---|---|---|---|---|
| `vsd` | Source-Drain Diode Forward On Voltage | V | `[typ, max]` | > 0 |
| `trr` | Reverse Recovery Time | ns | `[typ, max]` | > 0；condition 通常含 `di/dt` |
| `qrr` | Reverse Recovery Charge | nC | `[typ, max]` | > 0 |

---

## 跨欄位關係規則

### Channel 決定正負號

- `channel = N`：電流與電壓類欄位（`v_br_dss`、`id`、`idm`、`is`、`idsm`、`idss`）數值 > 0
- `channel = P`：上述欄位數值 < 0
- 雙向欄位（`vgs`、`igss`）無論 channel 型式，值均含 `±`

### min / typ / max 排序

- 任何同一 condition 組內，`min ≤ typ ≤ max`
- `vgs_th` 三值必須滿足此關係
- `ciss`、`coss`、`crss` 三值必須滿足此關係

### 容值大小關係

- `crss < coss < ciss`（reverse transfer < output < input）

### Gate charge 大小關係

- `qgd < qgs < qg`（drain < source < total）

### 溫度範圍

- `t_stg_tj.min` 必須為負值（通常 -40°C 或 -55°C）
- `t_stg_tj.max` 必須為正值（通常 150°C 或 175°C）

---

## 常見萃取陷阱

### 繼承列（Inherited Condition Rows）

表格中「條件欄為空白」的列，其 condition 通常繼承自上方最近一筆有條件的列。
Parser 必須向上查找 condition，不可直接留空。
常見於：`id`（多溫度）、`idss`（高溫）、`rds_on`（多條件）、`coss`/`crss`（同 `ciss` 條件）。

### rds_on 多條件組

通常有：
- `VGS=10V, ID=...` 組（標準驅動，typ+max）
- `VGS=4.5V, ID=...` 組（低電壓驅動，typ+max）
- 有時含 `Tj=100°C` 組

每個 condition 組獨立嘗試，不同組之間不能混用 condition。

### ±符號

`vgs` 的額定值通常格式為 `±20`，`igss` 也類似。
Parser 應保留 `±` 符號，不可只取絕對值。

### Footnote 參照

欄位值旁的 `①②③④` 等上標符號是 footnote ref，須對應至文件末尾的 footnote 表。
`rds_on` 欄位常全組共用同一個 footnote（脈衝測試條件限制）。

### SMD（表面黏著）額外額定值

部分元件同時有 `TC=25°C`（散熱器）與 `TA=25°C`（無散熱器/SMD）兩組額定值，
對應不同的封裝熱路徑，不可混用。

---

## 更新說明

此文件根據實際探索過的 MOSFET datasheet 樣本累積整理。
每次 `/ppg:explore` 發現新欄位或新的萃取規則時，更新此文件。

已驗證樣本：
- VSP007N06MS-G（Vishay，N-Channel，65V/75A，PDFN5x6 封裝）
