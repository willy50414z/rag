## ADDED Requirements

### Requirement: Explore 完成時寫入決策 checkpoint

ppg-explore SHALL 在所有 Step 完成後，將 conversation 中已確認的 explore 決策寫入 `pdf-parser-generator/{pdf檔名}/explore_decisions.md`，格式包含：目標用途、文件家族、每張 table 的 row key、DB schema 草案、semantic anchors、跨文件穩定性備註、RAG 設計、chunking 注意事項、未解決項目。

#### Scenario: 正常完成 explore 後寫入 checkpoint

- **WHEN** ppg-explore 完成 Step 1–6 且所有必要決策已確認
- **THEN** agent 寫入 `pdf-parser-generator/{pdf檔名}/explore_decisions.md`，包含上述所有決策章節

#### Scenario: 有未解決項目時仍寫入但標記

- **WHEN** Step 5 有未確認項目（例如 row key 尚有歧義）
- **THEN** agent 仍寫入 explore_decisions.md，並在 `## 未解決項目` 章節列出待確認事項，不阻止寫入

### Requirement: Propose 支援從 checkpoint 讀取決策

ppg-propose 前置條件檢查 SHALL 在 conversation 缺少 explore 決策時，嘗試讀取 `pdf-parser-generator/{pdf檔名}/explore_decisions.md` 作為 fallback 來源。

#### Scenario: 跨 session 執行 propose 且 checkpoint 存在

- **WHEN** propose 在新 session 執行，conversation 無 explore 決策，但 explore_decisions.md 存在且完整
- **THEN** agent 從 explore_decisions.md 萃取決策並繼續執行 propose，不要求重跑 explore

#### Scenario: Checkpoint 有未解決項目

- **WHEN** propose 讀到 explore_decisions.md 且 `## 未解決項目` 非「無」
- **THEN** agent 先回報未解決項目並要求 user 確認，確認後才繼續 propose

#### Scenario: Conversation 與 checkpoint 都沒有決策

- **WHEN** propose 在新 session 執行，且 explore_decisions.md 不存在
- **THEN** agent 回報找不到 exploration 決策，要求先執行 `/ppg:explore`
