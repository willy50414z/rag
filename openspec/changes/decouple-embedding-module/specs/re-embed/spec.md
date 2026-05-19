## ADDED Requirements

### Requirement: re-embed 工具腳本可獨立執行
`db/re_embed.py` SHALL 可作為 CLI 腳本直接執行（`python db/re_embed.py`），從 DB 讀出現有記錄，用目前的 `to_embed_text()` 與 `embed()` 重新計算向量，並批量更新對應 table 的 embedding 欄位。

#### Scenario: 全量 re-embed
- **WHEN** 執行 `python db/re_embed.py` 不帶任何參數
- **THEN** 對所有支援 embedding 的 table（max_ratings、thermal_characteristics、electrical_characteristics、typical_charts、footnotes）的全部記錄重新計算並更新 embedding

#### Scenario: 指定 table re-embed
- **WHEN** 執行 `python db/re_embed.py --table electrical_characteristics`
- **THEN** 只更新 `electrical_characteristics` 的 embedding 欄位，其他 table 不受影響

#### Scenario: dry-run 模式
- **WHEN** 執行 `python db/re_embed.py --dry-run`
- **THEN** 印出每個 table 預計更新的記錄筆數，不實際寫入 DB

### Requirement: 批次處理避免 OOM
re_embed.py SHALL 支援 `--batch-size N` 參數（預設 256），以分批方式讀取與更新記錄，避免一次將全部 DB 資料載入記憶體。

#### Scenario: 大量記錄批次處理
- **WHEN** DB 中有超過 batch-size 筆記錄
- **THEN** 分多次查詢與更新，每批次不超過 batch-size 筆，全部完成後印出總更新筆數

#### Scenario: 批次中斷後可重跑
- **WHEN** re_embed.py 在中途被中斷（Ctrl+C 或錯誤）後再次執行
- **THEN** 所有記錄（包含已更新與未更新的）均被重新計算並更新，結果與完整執行一致

### Requirement: 讀取 DATABASE_URL 環境變數
re_embed.py SHALL 從環境變數 `DATABASE_URL` 讀取連線字串（與 import_pipeline 一致），不硬編碼連線資訊。

#### Scenario: 缺少環境變數
- **WHEN** 執行時 `DATABASE_URL` 未設定
- **THEN** 印出明確錯誤訊息並以非零 exit code 退出，不拋出 unhandled exception
