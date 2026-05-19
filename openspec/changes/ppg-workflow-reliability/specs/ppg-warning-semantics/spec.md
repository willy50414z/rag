## ADDED Requirements

### Requirement: Apply 結果回報區分三種狀態

ppg-apply Step 5 SHALL 依測試結果與 warning 數量，將驗證結果分為三種回報狀態：全部通過無 warning、全部通過但有 warning、部分失敗。每種狀態 SHALL 明確顯示入庫建議。

#### Scenario: 測試全通過且無 warning

- **WHEN** 所有 pytest 測試通過且 parser 輸出的 warnings 清單為空
- **THEN** agent 回報「可直接入庫」

#### Scenario: 測試全通過但有 warning

- **WHEN** 所有 pytest 測試通過但 parser 輸出的 warnings 清單非空
- **THEN** agent 列出每條 warning 並依 warning 類別給出對應入庫建議

#### Scenario: 有測試失敗

- **WHEN** 至少一個 pytest 測試失敗
- **THEN** agent 回報失敗清單與對應 spec 章節，不給入庫建議

### Requirement: Warning 依四類決定入庫可行性

ppg-apply SHALL 依以下對照表判斷每條 warning 的入庫建議：
- `nullable 欄位為 null`（nullable: true 欄位確實無值）→ 可直接入庫
- `section 偵測模糊`（低優先啟發式衝突，保留為資料列）→ 建議人工 review output.json 確認 section 值後入庫
- `特殊字元未匹配`（PDF 出現 spec 未涵蓋字元，原樣保留）→ 建議確認欄位值後入庫
- `required 欄位為 null`（nullable: false 欄位缺值）→ **不可入庫**，回到 `/ppg:propose` 修正

#### Scenario: Required 欄位出現 null warning

- **WHEN** parser 輸出 warnings 包含 `nullable: false` 欄位為 null 的條目
- **THEN** agent 回報「不可入庫」，並指示回到 `/ppg:propose` 修正對應欄位的 nullable 設定或 forward-fill 規則

#### Scenario: 僅有 nullable 欄位 null 的 warning

- **WHEN** parser 輸出 warnings 全部屬於 nullable: true 欄位為 null
- **THEN** agent 回報「可直接入庫」，列出 warning 供參考
