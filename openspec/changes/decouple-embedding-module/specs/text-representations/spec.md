## ADDED Requirements

### Requirement: 文字表示邏輯獨立為純函式模組
`db/text_representations.py` 模組 SHALL 提供 `to_embed_text(record: dict, table: str) -> str` 函式，接收單筆 record dict 與 table 名稱，回傳用於 embedding 的文字字串。此函式 SHALL 為 pure function（無副作用、無狀態）。

#### Scenario: max_ratings 記錄的文字表示
- **WHEN** 呼叫 `to_embed_text(record, "max_ratings")` 且 record 包含 symbol、parameter、value_raw、unit 欄位
- **THEN** 回傳格式為 `"{symbol} {parameter}: {value_raw} {unit}"` 的字串（若有 condition_raw 則附加 `", {condition_raw}"`）

#### Scenario: thermal_characteristics 記錄的文字表示
- **WHEN** 呼叫 `to_embed_text(record, "thermal_characteristics")`
- **THEN** 回傳格式為 `"{symbol} {parameter}: {typ} {unit}"` 的字串

#### Scenario: electrical_characteristics 記錄的文字表示
- **WHEN** 呼叫 `to_embed_text(record, "electrical_characteristics")`
- **THEN** 回傳格式為 `"[{section}] {symbol} {parameter}: {min}/{typ}/{max} {unit}"` 的字串（若有 condition_raw 則附加）

#### Scenario: typical_charts 記錄的文字表示
- **WHEN** 呼叫 `to_embed_text(record, "typical_charts")`
- **THEN** 回傳 record 的 `caption` 欄位值

#### Scenario: footnotes 記錄的文字表示
- **WHEN** 呼叫 `to_embed_text(record, "footnotes")`
- **THEN** 回傳格式為 `"Note {marker}: {text}"` 的字串

#### Scenario: 未知 table 名稱
- **WHEN** 呼叫 `to_embed_text(record, "unknown_table")`
- **THEN** 拋出 `ValueError` 並說明不支援的 table 名稱

### Requirement: embeddings.py 只負責向量化
重構後的 `db/embeddings.py` SHALL 提供 `embed(texts: list[str]) -> list[list[float]]` 公開函式，只負責文字到向量的轉換，不包含任何 table schema 或文字格式邏輯。

#### Scenario: 批量向量化
- **WHEN** 呼叫 `embed(["text1", "text2", "text3"])`
- **THEN** 回傳長度相同的 list，每個元素為 384 維 float list

#### Scenario: 空列表輸入
- **WHEN** 呼叫 `embed([])`
- **THEN** 回傳空 list，不拋出例外

### Requirement: import_pipeline 行為與原本一致
重構後的 `import_pipeline.py` SHALL 透過呼叫 `to_embed_text()` + `embed()` 組合產生 embedding，外部可觀察行為（寫入 DB 的向量值、資料完整性）SHALL 與重構前相同。

#### Scenario: 整批 PDF 匯入後 embedding 正確性
- **WHEN** 對同一份 PDF 分別用舊版與新版 pipeline 匯入
- **THEN** 寫入 DB 的 embedding 向量值 SHALL 相同（相同輸入文字、相同模型）
