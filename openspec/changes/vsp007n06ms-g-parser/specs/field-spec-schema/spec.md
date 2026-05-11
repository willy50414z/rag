## ADDED Requirements

### Requirement: 每筆萃取記錄遵循統一結構
每筆記錄 SHALL 包含以下欄位：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `symbol` | string | 電氣符號，如 `rds_on`、`vgs_th` |
| `stat` | string | 量測統計類型：`typ`、`min`、`max`、`rating` |
| `value` | string \| number | 萃取值；範圍值（如 `-55 to 150`）保留為字串 |
| `unit` | string | 單位，如 `mΩ`、`V`、`nC` |
| `condition` | string \| null | 測試條件完整字串，如 `"VGS=10V, ID=40A, Tj=25°C"` |
| `footnote_ref` | string \| null | footnote 符號，如 `"①"`；無則為 `null` |
| `required` | boolean | 此欄位是否必要 |
| `on_missing` | string | 缺失時行為：`"error"` 或 `"null"` |
| `strict` | boolean | 是否要求嚴格萃取（不猜測） |

#### Scenario: 必要欄位存在
- **WHEN** parser 產出一筆記錄
- **THEN** 記錄 SHALL 包含 `symbol`、`stat`、`value`、`unit` 四個非空欄位

#### Scenario: condition 為獨立欄位
- **WHEN** 量測條件存在（如 VGS=10V）
- **THEN** condition SHALL 儲存於 `condition` 欄位，而非嵌入 `symbol` 或 key 名稱中

#### Scenario: footnote 對照表
- **WHEN** 輸出 JSON 包含有 footnote_ref 的記錄
- **THEN** 頂層 SHALL 包含 `footnotes` dict，key 為符號（`"①"`），value 為完整文字

### Requirement: 同一 symbol 可有多筆不同條件的記錄
輸出格式 SHALL 為有序 list，允許同一 `symbol`+`stat` 組合出現多次（條件不同）。

#### Scenario: rds_on 多條件並存
- **WHEN** parser 解析 RDS(on) 欄位
- **THEN** 輸出 SHALL 包含至少 3 筆 `symbol="rds_on"` 的記錄，各自帶有不同的 `condition` 字串
