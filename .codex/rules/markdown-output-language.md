# Markdown Output Language Rule

## Rule

當代理產出新的 Markdown 文件（`.md`）或改寫既有 Markdown 文件內容時，預設使用中文撰寫。

## Scope

此規則適用於：

- `README.md`
- `spec.md`
- `analysis-summary.md`
- `iteration-plan.md`
- `review`、`report`、`notes`、`hypothesis-log` 等 Markdown 文件
- 其他以 Markdown 為主要內容格式的知識庫、策略文件、研究文件、會話文件

## Required Behavior

- 文件標題、段落說明、分析文字、結論、建議、註解，預設使用中文。
- 若文件內需要保留固定英文識別字，允許保留英文，例如：
  - 檔名
  - 程式碼
  - CLI 指令
  - API 名稱
  - schema 欄位名
  - 明確要求不可翻譯的專有名詞
- 若既有工作流或下游程式明確依賴固定英文欄位，應保留該英文欄位名，並僅將說明文字改為中文。

## Exceptions

只有在下列情況下可以不使用中文：

- 使用者明確要求英文或其他語言
- 下游 parser、schema、測試或工具明確要求固定英文內容
- 引用原始英文文本且翻譯會改變其法律、技術或評估意義

## Priority

若沒有更高優先級的使用者要求或工具格式限制，Markdown 文件一律以中文為預設輸出語言。
