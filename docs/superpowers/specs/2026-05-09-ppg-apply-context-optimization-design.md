---
title: ppg-apply Context 使用優化設計
date: 2026-05-09
status: approved
---

# ppg-apply Context 使用優化

## 背景與問題

ppg-apply 是 PDF Parser Generator 三段式流程的第三段，負責讀取欄位規格、實作 parser、執行驗證測試。

處理複雜 PDF（欄位數多）時，context 在單次執行中累積：

| 步驟 | Context 來源 | 估計大小 |
|------|-------------|---------|
| Step 1 | pdf_field_spec.md | 15–25 KB |
| Step 2 | parser.py 實作內容 | 10–20 KB |
| Step 3 | test_parser.py 內容 | 5–10 KB |
| Step 4 | pytest 全欄位輸出 | 20–50 KB（失控點）|
| 修復迴圈 | 重帶整份 spec | +15–25 KB（重複）|

最大問題在 Step 4 的 pytest 輸出（全欄位含通過的）以及修復迴圈中隱含重帶整份 spec，兩者合計可達 35–75 KB 不必要的 context。

## 目標

在不拆分 subagent 的前提下，透過調整 pytest 指令與修復迴圈的 context 攜帶策略，將 Step 4 之後的 context 壓力降低 60–70%。

## 不在本次範圍內

- Step 2 / Step 3 的 code 產生方式（無明顯優化空間）
- 拆分 subagent 架構（已分析，協調開銷超過收益）
- 修改 pdf_field_spec.md 格式

---

## 設計

### 優化 1：Step 4 改為 fail-only 輸出

**現行行為：**

```bash
cd pdf-parser-generator/{pdf} && python -m pytest test_parser.py -v
```

輸出包含所有欄位（通過 + 失敗），結果表格列出全欄位。

**修改後：**

```bash
cd pdf-parser-generator/{pdf} && python -m pytest test_parser.py --tb=short -q
```

結果回報格式改為：

```
## Parser 驗證結果：{pdf_filename}

{n} 個欄位通過，{m} 個欄位失敗

| 欄位 | 萃取值 | 預期值 | 狀態 |
|------|--------|--------|------|
| total_amount | None | 1234.56 | ✗ |
| date | 2024-13-01 | 2024-01-13 | ✗ |
```

通過的欄位不進入結果表格，只在摘要行計數。

**預期效果：** 測試輸出 context 減少 60–70%（失敗率低時效益更大）。

---

### 優化 2：修復迴圈改用 targeted spec excerpt

**現行行為：** 測試失敗後，agent 隱含帶著整份 spec 判斷如何修復。

**修改後：**

1. 從 pytest 失敗輸出提取 failing field names（每個失敗的 `test_{field_name}` 函式名稱）
2. 從 `pdf_field_spec.md` 只取出這些欄位的定義段落，包含：
   - field_name、required、缺失處理、strict_extraction
   - 驗證規則
   - 預期值（sample）
   - 來源證據
3. 帶著這份 targeted excerpt（而非整份 spec）修正 `parser.py` 中對應欄位的萃取邏輯
4. 重跑測試

**Targeted excerpt 結構（傳入修復推理的內容）：**

```
修復目標：{failing_field_names}

以下為這些欄位在 spec 中的定義：

### {field_name_1}
- required: {yes/no}
- strict_extraction: {yes/no}
- 驗證規則: {rule}
- 預期值（sample）: {value}
- 來源證據: {page, position, label}

### {field_name_2}
...
```

其他欄位的 spec 定義不進入此 context。

---

### 優化 3：修復迴圈上限與退出條件

- 最多執行 **2 次** 自動修復迴圈
- 每次修復只修改失敗欄位對應的 parser 段落，不重寫整個 parser.py
- 2 次後仍有失敗，展示選項給 user：
  1. 繼續由 agent 修正（再給一次機會）
  2. 更新 pdf_field_spec.md 的預期值後重跑
  3. 標記為已知問題暫時跳過

---

## SKILL.md 修改範圍

| 段落 | 修改內容 |
|------|---------|
| Step 4：執行測試並回報 | pytest 指令加 `--tb=short -q`；報告格式改為 fail-only |
| 新增 Step 4.5：自動修復迴圈 | 描述 targeted excerpt 邏輯、最多 2 次重試、退出條件 |
| 結果回報格式（全部通過） | 不變 |
| 結果回報格式（部分失敗） | 移除全欄位表格，改為 fail-only 表格 + 修復迴圈說明 |

---

## 預期效果

| 場景 | 優化前 context（Step 4 後） | 優化後 |
|------|---------------------------|--------|
| 30 欄、無失敗 | ~60 KB | ~30 KB（省 50%） |
| 30 欄、5 欄失敗 | ~80 KB（含修復 spec） | ~35 KB（省 56%） |
| 60 欄、10 欄失敗 | ~120 KB | ~50 KB（省 58%） |
