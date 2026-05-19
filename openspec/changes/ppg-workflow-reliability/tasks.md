## 1. ppg-explore：跨 session checkpoint

- [x] 1.1 在 ppg-explore SKILL.md 的「完成提示」區塊前新增 Step 6.5，定義 explore_decisions.md 的寫入時機與格式
- [x] 1.2 確認 explore_decisions.md 格式包含所有 propose 需要的章節（row key、DB schema、anchors、RAG 設計、未解決項目）

## 2. ppg-propose：前置條件 fallback

- [x] 2.1 在 ppg-propose SKILL.md 的「前置條件檢查」區塊加入 fallback 邏輯：conversation 無決策時讀取 explore_decisions.md
- [x] 2.2 加入「未解決項目非空時先回報再繼續」的處理規則
- [x] 2.3 確認 propose 的 artifact 責任分工移除 parser_spec.json，改為 parser.py / test_parser.py / output.json

## 3. ppg-apply：Condition 解析實作規格

- [x] 3.1 在 ppg-apply SKILL.md Step 2「實作規則」中新增 Condition 解析段落
- [x] 3.2 定義五步正規化序列（strip、換行合併、等號空白、特殊字元、不改順序）
- [x] 3.3 定義 footnote marker 分離規則（先提取、再正規化）
- [x] 3.4 定義空值三路徑處理（forward-fill / warning 不可入庫 / 空字串）
- [x] 3.5 在 parser shape 中加入 normalize_condition() 輔助函式定義

## 4. ppg-apply：Section 偵測衝突解決

- [x] 4.1 為 Section 偵測的四條啟發式標注優先層級（最高 / 高 / 中 / 低）
- [x] 4.2 加入衝突規則：格式線索不可單獨推翻高優先啟發式判定
- [x] 4.3 加入灰色地帶處理：有疑慮時加 warning 並當資料列

## 5. ppg-apply：Warning 終態語意

- [x] 5.1 將 Step 5 結果回報格式拆為三種狀態（無 warning / 有 warning / 部分失敗）
- [x] 5.2 加入 Warning 入庫建議對照表（四類 warning 對應入庫建議）
- [x] 5.3 確認 required 欄位 null 是唯一硬封鎖（不可入庫）

## 6. 驗證

- [x] 6.1 確認 ppg-explore SKILL.md 的 References 仍指向現存的四個 reference 檔案
- [x] 6.2 確認 ppg-propose 的 artifact 責任分工與 ppg-apply 的輸出目錄一致
- [x] 6.3 確認三個 skill 的 workflow 說明文字互相一致（explore → propose → apply）
