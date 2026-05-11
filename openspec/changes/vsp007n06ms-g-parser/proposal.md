## Why

資料庫中需要能夠自動萃取 MOSFET 資料表的電氣特性數值，以取代人工查閱與手動輸入。VSP007N06MS-G（Vergiga 65V/75A N-Channel MOSFET）是第一個目標元件，以此建立可複用的 parser 模式。

## What Changes

- 新增 VSP007N06MS-G 資料表 PDF parser，可從前 2 頁萃取結構化電氣參數
- 每個萃取欄位附帶 `condition`、`unit`、`footnote_ref` 等中繼資料
- 輸出格式為有序 list（JSON/YAML），每筆記錄包含 `symbol`、`stat`、`value`、`unit`、`condition`、`footnote_ref`
- 附帶 footnote 對照表（①②③④）
- 附帶萃取驗證測試，對已知值做斷言

## Capabilities

### New Capabilities

- `pdf-field-extraction`：從 VSP007N06MS-G.pdf 前 2 頁萃取結構化欄位，涵蓋元件識別、最大額定值、熱阻、靜態／動態／切換／體二極體電氣特性，共約 55 筆記錄
- `field-spec-schema`：定義每筆記錄的結構（symbol, stat, value, unit, condition, footnote_ref, required, on_missing, strict），作為 parser 輸出與測試的共同合約

### Modified Capabilities

## Impact

- 新增 Python parser 模組（`lib/` 或 `parsers/` 下）
- 依賴 `pdfplumber`（已安裝）
- 輸入：`VSP007N06MS-G.pdf`（已存在於 `E:\code\rag\`）
- 輸出：JSON 或 YAML 結構化資料
- 無破壞性變更，無外部 API 依賴
