## Context

PPG workflow 是一個三段式 skill chain（explore → propose → apply），用於將 text PDF 解析成 DB-ready 的 flat record。目前 skill 定義缺少四個關鍵規格：explore 決策的持久化機制、condition 欄位的構造規則、warning 的入庫語意、以及 section 偵測啟發式的衝突解決。這些缺口導致 agent 在邊界情況下行為不確定，需要在 skill 層補齊而非留給 agent 即興判斷。

所有修改僅在 skill 文件層（.claude/skills/ppg-*/SKILL.md），不涉及 parser.py 的外部介面。

## Goals / Non-Goals

**Goals:**
- 定義 explore_decisions.md 的格式與寫入時機，讓 propose 在跨 session 情況下仍能讀到決策
- 定義 condition 字串的正規化步驟序列與 footnote 分離規則，消除 primary key 不穩定性
- 定義 warning 三種終態的入庫建議對照，讓 apply 結果有明確的可行性判斷
- 定義 section 偵測四條啟發式的優先順序與衝突解決規則

**Non-Goals:**
- 不改變 parser.py 的輸出 schema
- 不引入新的中間 artifact（explore_decisions.md 是 checkpoint，不是中間格式）
- 不處理 scanned PDF 或 OCR 路線（仍由 ppgm-explore 負責）
- 不修改 ppg-propose 的 spec 模板結構

## Decisions

### D1：explore_decisions.md 使用結構化 Markdown，不使用 YAML/JSON

**選擇**：Markdown 格式，與 pdf_field_spec.md 一致。  
**理由**：YAML/JSON 需要 agent 額外解析，且與「不產出 YAML 中間層」原則矛盾；Markdown 可由人工直接閱讀與修改，也能被 propose 直接讀取。  
**替代方案**：YAML checkpoint（被排除，與既有原則矛盾）。

### D2：condition 正規化採保守策略，不拆解參數順序

**選擇**：只做空白正規化與 footnote 分離，不改變逗號分隔的參數順序。  
**理由**：PDF 內 condition 字串的參數順序在同系列文件中通常穩定，強制排序反而引入轉換錯誤；保留原始順序對 RAG 語意查詢更友好。  
**替代方案**：正規化為 sorted key-value dict（被排除，過度設計且破壞原始資訊）。

### D3：section 偵測衝突採高優先覆蓋，格式線索不獨立判定

**選擇**：四條啟發式有明確優先順序，格式線索（第 4 條）需搭配第 2 或第 3 條才能觸發判定。  
**理由**：全大寫欄位標題（如 `VGS`）在資料列中很常見，格式線索獨立判定會產生大量誤判；高優先啟發式（pattern 比對、欄位數異常）更具客觀性。

### D4：warning 分四類，required 欄位 null 是唯一硬封鎖

**選擇**：nullable 欄位 null → 可入庫；section 模糊 / 特殊字元未匹配 → 建議 review 後入庫；required 欄位 null → 不可入庫。  
**理由**：nullable 欄位 null 是 spec 允許的正常狀態，不應阻止入庫；required 欄位 null 代表 spec 或 parser 有錯誤，必須回到修復迴圈。

## Risks / Trade-offs

- **explore_decisions.md 與 conversation 決策可能不同步**：若 user 在 explore 結束後於同 session 修改決策，但未重新寫入 explore_decisions.md，propose fallback 讀到的是舊版。→ 緩解：propose 發現 conversation 有決策時優先使用 conversation，不依賴檔案。
- **condition 正規化不完整**：若 PDF 使用非標準空白字元（NBSP、全形空格），正規化步驟可能漏掉。→ 緩解：normalize_condition() 的正規化步驟序列可在 spec 中擴充，不影響函式介面。
- **section 偵測仍有灰色地帶**：啟發式規則仍無法覆蓋所有 PDF 排版，灰色地帶 row 加 warning 並當資料列處理，不阻止 output。→ 可接受，warning 機制已能回溯定位問題位置。

## Open Questions

- 無。所有決策已在 explore 對話中確認。
