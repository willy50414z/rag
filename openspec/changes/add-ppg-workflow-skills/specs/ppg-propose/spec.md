## ADDED Requirements

### Requirement: 從 conversation 匯出欄位規格

Skill SHALL 從當前 conversation context 讀取欄位狀態，匯出為純 Markdown 規格檔，路徑為 `pdf-parser-generator/{pdf檔名}/pdf_field_spec.md`。

#### Scenario: Conversation 有欄位狀態

- **WHEN** user 執行 `/ppg:propose` 且 conversation 中已有 explore 的欄位狀態
- **THEN** skill 匯出 `pdf_field_spec.md`，包含所有欄位定義、預期值、驗證規則

#### Scenario: Conversation 無欄位狀態

- **WHEN** user 執行 `/ppg:propose` 但 conversation 中沒有 explore 的欄位狀態
- **THEN** skill 提示需要先執行 `/ppg:explore`，不繼續

### Requirement: pdf_field_spec.md 格式

`pdf_field_spec.md` SHALL 使用純 Markdown，包含固定章節結構，供 user 審閱與 apply 讀取。格式如下：

```markdown
# Parser Spec: {pdf_filename}

## 文件資訊
- 來源檔案：{path}
- 分類：{digital-text|scanned|hybrid}
- Backend：{backend}

## 欄位定義

### {field_name}
- 說明：{description}
- Required：yes | no
- 缺失處理：error | null | needs_review
- Strict extraction：yes | no
- 驗證規則：{natural language}
- 預期值（sample）：`{expected_value}`
- 來源證據：{page, block reference}

## 未解決的模糊項目

- {issue}: {action_needed}
```

#### Scenario: 有未解決模糊項目

- **WHEN** 部分欄位 policy_status 為 `unresolved`
- **THEN** skill 在 `## 未解決的模糊項目` 章節列出，不強行解析為 confirmed 值

#### Scenario: 所有欄位已確認

- **WHEN** 所有欄位 policy_status 為 `user_confirmed` 或 `user_modified`
- **THEN** 未解決模糊項目章節省略或標記為空

### Requirement: 等待 User 確認

Skill SHALL 匯出 spec 後提示 user 審閱，並告知確認後可執行 `/ppg:apply`，不自動觸發 apply。

#### Scenario: 匯出後提示

- **WHEN** `pdf_field_spec.md` 寫入完成
- **THEN** skill 顯示檔案路徑，提示 user 確認或修改，說明確認後執行 `/ppg:apply`
