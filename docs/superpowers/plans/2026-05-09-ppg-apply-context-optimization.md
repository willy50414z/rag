# ppg-apply Context 優化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修改 `.claude/skills/ppg-apply/SKILL.md`，將 Step 4 的 pytest 輸出改為 fail-only 格式，並新增 Step 4.5 自動修復迴圈，降低複雜 PDF 處理時的 context 累積。

**Architecture:** 單一 SKILL.md 檔案修改，分兩段：（1）Step 4 指令與報告格式更新；（2）新增 Step 4.5 自動修復迴圈段落。無新增檔案，無程式碼異動。

**Tech Stack:** Markdown（SKILL.md 編輯）

---

### Task 1：更新 Step 4 — pytest 指令與 fail-only 回報格式

**Files:**
- Modify: `.claude/skills/ppg-apply/SKILL.md`（Step 4 區塊，約 117–156 行）

- [ ] **Step 1：確認目前 Step 4 內容**

  開啟 `.claude/skills/ppg-apply/SKILL.md`，確認 Step 4 的起始行包含：

  ```
  cd pdf-parser-generator/{pdf檔名} && python -m pytest test_parser.py -v
  ```

  且「部分失敗」結果表格包含通過欄位（如 `invoice_number ✓`）與失敗欄位，後接「失敗欄位選項」清單。

- [ ] **Step 2：修改 pytest 指令**

  將 Step 4 的 bash 指令區塊從：

  ````markdown
  ```bash
  cd pdf-parser-generator/{pdf檔名} && python -m pytest test_parser.py -v
  ```
  ````

  改為：

  ````markdown
  ```bash
  cd pdf-parser-generator/{pdf檔名} && python -m pytest test_parser.py --tb=short -q
  ```
  ````

- [ ] **Step 3：改寫「部分失敗」回報格式**

  將現有「部分失敗」區塊：

  ````markdown
  **部分失敗：**

  ```
  ## Parser 驗證結果：{pdf_filename}

  {n} 個欄位通過，{m} 個欄位失敗

  | 欄位 | 萃取值 | 預期值 | 狀態 |
  |------|--------|--------|------|
  | invoice_number | INV-2024-001 | INV-2024-001 | ✓ |
  | total_amount   | None         | 1234.56      | ✗ |

  失敗欄位選項：
  1. 修正 parser.py 的萃取邏輯（agent 繼續實作）
  2. 更新 pdf_field_spec.md 的預期值後重跑
  3. 標記為已知問題暫時跳過
  ```
  ````

  改為：

  ````markdown
  **部分失敗：**

  ```
  ## Parser 驗證結果：{pdf_filename}

  {n} 個欄位通過，{m} 個欄位失敗

  | 欄位 | 萃取值 | 預期值 |
  |------|--------|--------|
  | total_amount | None | 1234.56 |
  ```

  → 進入 Step 4.5 自動修復迴圈
  ````

  **注意：**
  - 表格僅列失敗欄位，移除「狀態」欄（全為失敗，欄位本身即代表失敗）
  - 移除「失敗欄位選項」清單（改由 Step 4.5 統一處理）
  - 通過的欄位不進入表格

- [ ] **Step 4：驗證 Step 4 區塊**

  閱讀修改後的 SKILL.md，確認：
  - pytest 指令含 `--tb=short -q`
  - 「全部通過」格式不變
  - 「部分失敗」表格無通過欄位、無「失敗欄位選項」清單
  - 結尾有「→ 進入 Step 4.5 自動修復迴圈」

---

### Task 2：新增 Step 4.5 — 自動修復迴圈

**Files:**
- Modify: `.claude/skills/ppg-apply/SKILL.md`（在 Step 4 與「輸出目錄」區塊之間插入新段落）

- [ ] **Step 1：確認插入位置**

  確認 `## 輸出目錄` 標題存在，且位於 Step 4 結束後、`## 失敗處理` 之前。新段落插入於 Step 4 末尾與 `## 輸出目錄` 之間。

- [ ] **Step 2：插入 Step 4.5 段落**

  在 Step 4 區塊結束後、`## 輸出目錄` 之前，插入以下完整段落：

  ````markdown
  ## Step 4.5：自動修復迴圈

  若 Step 4 有欄位失敗，執行最多 **2 次**自動修復。

  ### 每次迴圈步驟

  **1. 提取失敗欄位名稱**

  從 pytest 輸出找出 `FAILED test_parser.py::test_{field_name}` 的所有 `{field_name}`。

  **2. 取出 targeted spec excerpt**

  從 `pdf_field_spec.md` 萃取僅含失敗欄位的定義段落，格式如下：

  ```
  修復目標：{failing_field_names}

  ### {field_name}
  - required: {yes/no}
  - strict_extraction: {yes/no}
  - 驗證規則: {rule}
  - 預期值（sample）: {value}
  - 來源證據: {page, position, label}
  ```

  只帶失敗欄位的 spec 段落進入修復推理，其餘欄位定義略過。

  **3. 修正 parser.py**

  依 targeted excerpt，只修改失敗欄位對應的萃取邏輯段落，不重寫整個 parser.py。

  **4. 重跑測試**

  ```bash
  cd pdf-parser-generator/{pdf檔名} && python -m pytest test_parser.py --tb=short -q
  ```

  以 Step 4 格式回報結果。若仍有失敗，進入下一輪（最多 2 次）。

  ### 迴圈退出條件

  - **通過**：所有欄位通過，結束。
  - **達到 2 次上限仍有失敗**：展示選項給 user：
    1. 繼續由 agent 修正（再給一次機會，帶上目前 targeted excerpt）
    2. 更新 `pdf_field_spec.md` 的預期值後重跑
    3. 對失敗欄位的測試加上 `pytest.mark.skip(reason="known issue")`，暫時跳過
  ````

- [ ] **Step 3：驗證 Step 4.5 插入位置與內容**

  閱讀修改後的 SKILL.md，確認：
  - `## Step 4.5：自動修復迴圈` 位於 Step 4 與 `## 輸出目錄` 之間
  - 包含「每次迴圈步驟」四步：提取失敗欄位、targeted excerpt、修正 parser.py、重跑測試
  - targeted excerpt 格式與 Step 1（讀 spec 的欄位格式）一致
  - pytest 指令與 Task 1 中的指令相同（`--tb=short -q`）
  - 「迴圈退出條件」包含通過、2 次上限兩種情境
  - `## 輸出目錄` 和 `## 失敗處理` 區塊不受影響

- [ ] **Step 4：通讀完整 SKILL.md 確認流程連貫**

  從頭到尾閱讀修改後的 SKILL.md，確認：
  - Step 1 → Step 2 → Step 3 → Step 4 → Step 4.5 → 輸出目錄 → 失敗處理 順序正確
  - Step 4 的「部分失敗」結尾指向 Step 4.5
  - Step 4.5 的修復指令（`--tb=short -q`）與 Step 4 一致
  - 無孤立段落或斷裂敘述

- [ ] **Step 5：Commit**

  ```bash
  git add .claude/skills/ppg-apply/SKILL.md
  git commit -m "feat(ppg-apply): reduce context with fail-only output and auto-repair loop"
  ```
