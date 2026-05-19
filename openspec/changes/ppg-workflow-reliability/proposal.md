## Why

PPG workflow（ppg-explore → ppg-propose → ppg-apply）在實際使用中暴露出四個可靠性缺口：跨 session 時 explore 決策會遺失、condition 字串構造方式未定義導致 primary key 不穩定、warning 出現後不知道能否入庫、以及 section 偵測啟發式衝突時行為不確定。這些問題讓 apply 產出的 parser 在邊界情況下不可預測，需要在 skill 層補齊規格。

## What Changes

- **跨 session 斷點修補**：ppg-explore 完成時寫入 `explore_decisions.md`，ppg-propose 前置條件檢查新增 fallback 讀取此檔
- **Condition 解析規格化**：ppg-apply Step 2 新增 condition 正規化步驟序列、footnote marker 分離規則、空值處理路徑，並提供 `normalize_condition()` 輔助函式
- **Warning 終態語意**：ppg-apply Step 5 回報格式拆為「全部通過無 warning」/ 「通過但有 warning」/ 「部分失敗」三種狀態，新增 warning 入庫建議對照表
- **Section 偵測衝突解決**：ppg-apply Step 2 四條啟發式標注優先層級，定義高優先判定後低優先不得推翻的衝突規則

## Capabilities

### New Capabilities

- `ppg-cross-session-checkpoint`：explore 結束時持久化決策到 `explore_decisions.md`，propose 支援從此檔讀取作為 fallback
- `ppg-condition-parsing`：condition 欄位的正規化、footnote 分離、空值處理的完整實作規格
- `ppg-warning-semantics`：parser 執行結果的 warning 分類與入庫可行性判斷規則

### Modified Capabilities

（無現有 spec 層行為改變，以上皆為新增規格範圍）

## Impact

- 影響檔案：`.claude/skills/ppg-explore/SKILL.md`、`.claude/skills/ppg-propose/SKILL.md`、`.claude/skills/ppg-apply/SKILL.md`
- 不影響 parser.py 的外部介面（輸出 schema 不變）
- `normalize_condition()` 為新增輔助函式，不破壞現有 parser 結構
- explore_decisions.md 為新增 artifact，不與 pdf_field_spec.md 衝突
