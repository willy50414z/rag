## ADDED Requirements

### Requirement: 讀取 Spec 並實作 Parser

Skill SHALL 讀取 `pdf-parser-generator/{pdf檔名}/pdf_field_spec.md`，根據欄位定義實作 `parser.py`，存於同一目錄。

#### Scenario: Spec 檔案存在

- **WHEN** user 執行 `/ppg:apply` 且 `pdf_field_spec.md` 存在
- **THEN** skill 讀取 spec，實作對應的 Python parser，寫入 `pdf-parser-generator/{pdf檔名}/parser.py`

#### Scenario: Spec 檔案不存在

- **WHEN** user 執行 `/ppg:apply` 但找不到 `pdf_field_spec.md`
- **THEN** skill 提示需先執行 `/ppg:propose`，不繼續

### Requirement: 產生測試檔案

Skill SHALL 根據 spec 的欄位預期值產生 `test_parser.py`，assert 每個欄位的萃取結果符合 spec 中的 `預期值（sample）`。

#### Scenario: 產生測試

- **WHEN** parser.py 實作完成
- **THEN** skill 產生 `test_parser.py`，每個 spec 欄位對應至少一個 assert

### Requirement: 執行測試並回報

Skill SHALL 對 sample PDF 執行 parser，跑 test_parser.py，並回報每個欄位的 pass/fail 結果。

#### Scenario: 所有欄位通過

- **WHEN** test_parser.py 執行後所有 assert 通過
- **THEN** skill 回報「所有欄位通過」，列出每個欄位的萃取值

#### Scenario: 部分欄位失敗

- **WHEN** 部分 assert 失敗
- **THEN** skill 列出失敗欄位、實際萃取值 vs 預期值，提示 user 選擇修正 parser 或更新 spec

### Requirement: 輸出目錄結構

Skill SHALL 將所有產出物統一放在 `pdf-parser-generator/{pdf檔名}/` 目錄下。

#### Scenario: 目錄不存在

- **WHEN** `pdf-parser-generator/{pdf檔名}/` 目錄不存在
- **THEN** skill 自動建立目錄再寫入檔案

#### Scenario: 目錄已存在

- **WHEN** 目錄已存在且有既有檔案
- **THEN** skill 覆寫 parser.py 和 test_parser.py，保留 pdf_field_spec.md 不動
