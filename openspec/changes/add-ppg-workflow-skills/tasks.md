## 1. 建立 ppg-explore skill

- [x] 1.1 建立 `.claude/skills/ppg-explore/` 目錄與 `SKILL.md`
- [x] 1.2 將 `pdf-parser-explore` 的環境檢查、PDF 分類、低假設萃取、Normalize、Review Markdown 產出邏輯移入 `ppg-explore/SKILL.md`
- [x] 1.3 將互動式問答邏輯（Step 5-6）移入 skill，確認不寫檔案
- [x] 1.4 在 skill 結尾加上「探索完成，執行 `/ppg:propose` 匯出規格」的提示
- [x] 1.5 將 `pdf-parser-explore/references/` 目錄移至 `ppg-explore/references/`，更新 SKILL.md 內的參照路徑

## 2. 建立 ppg-propose skill

- [x] 2.1 建立 `.claude/skills/ppg-propose/` 目錄與 `SKILL.md`
- [x] 2.2 實作從 conversation context 讀取欄位狀態的邏輯
- [x] 2.3 定義 `pdf_field_spec.md` 的輸出模板（固定 Markdown 章節結構）
- [x] 2.4 實作寫入 `pdf-parser-generator/{pdf檔名}/pdf_field_spec.md` 的邏輯（自動建立目錄）
- [x] 2.5 加入 conversation 無欄位狀態時的提示（引導執行 `/ppg:explore`）
- [x] 2.6 加入匯出後等待 user 確認的提示

## 3. 建立 ppg-apply skill

- [x] 3.1 建立 `.claude/skills/ppg-apply/` 目錄與 `SKILL.md`
- [x] 3.2 實作讀取 `pdf_field_spec.md` 的邏輯（spec 不存在時提示執行 `/ppg:propose`）
- [x] 3.3 實作根據 spec 欄位產生 `parser.py` 的邏輯
- [x] 3.4 實作根據 spec 預期值產生 `test_parser.py` 的邏輯（每欄位至少一個 assert）
- [x] 3.5 實作執行 test_parser.py 並解析 pass/fail 結果的邏輯
- [x] 3.6 實作回報結果：成功列出萃取值，失敗列出實際值 vs 預期值並提示選項

## 4. 移除舊 skill

- [x] 4.1 確認 `ppg-explore/references/` 已包含所有必要的 references 檔案
- [x] 4.2 刪除 `.claude/skills/pdf-parser-explore/` 整個目錄
- [x] 4.3 確認沒有其他地方參照 `pdf-parser-explore` skill 名稱
