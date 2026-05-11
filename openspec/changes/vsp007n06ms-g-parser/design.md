## Context

目前無自動化方式從 MOSFET PDF 資料表萃取電氣參數。VSP007N06MS-G（Vergiga 65V/75A N-Channel MOSFET，PDFN5x6）的 PDF 已確認為 digital-text 格式，前 2 頁包含所有需要的電氣特性表格。本次以 pdfplumber 為萃取 backend，採用確定性（deterministic）table 解析，不依賴 LLM 逐次萃取。

## Goals / Non-Goals

**Goals:**
- 以 pdfplumber 解析 VSP007N06MS-G.pdf 前 2 頁的 4 個表格（p1_t2、p1_t3、p1_t4、p2_t1）
- 每筆記錄輸出 `symbol`、`stat`、`value`、`unit`、`condition`、`footnote_ref`、`required`、`on_missing`、`strict` 欄位
- 輸出結構為有序 list（JSON），可供後續比對或入庫使用
- 附帶 footnote 對照表（①②③④）
- 提供針對已知值的驗證測試

**Non-Goals:**
- 不支援第 3 頁以後（曲線圖、封裝尺寸、Marking 資訊）
- 不實作 OCR（此 PDF 為純數位文字）
- 不實作跨廠商通用 parser（本次僅針對 VSP007N06MS-G 格式）
- 不實作資料庫寫入或 API 介面

## Decisions

**D1：以 pdfplumber `extract_tables()` 為主要萃取方式**
- 此 PDF 表格邊框清晰，pdfplumber table detection 可穩定運作
- 備選：`extract_words()` 搭配位置推算 → 複雜度高，僅在 table 解析失敗時使用
- 結論：採用 `extract_tables()`，對已知欄位 index 做確定性對應

**D2：condition 與 symbol 分離儲存**
- 不將 condition 嵌入 key 名稱（如 `rds_on_vgs_10v_id_40a_typ`），改為每筆記錄的獨立 `condition` 字串欄位
- 理由：同一 symbol 在不同條件下有多筆量測值（如 rds_on 有 3 組條件），嵌入 key 會導致 key 爆炸且難以比對
- 輸出格式：有序 list，每筆為獨立物件

**D3：footnote 以 `footnote_ref` 字串欄位記錄，另附 `footnotes` dict**
- footnote 文字不重複寫入每筆記錄，僅記錄符號（`"①"`），footnote 對照表作為輸出 JSON 的頂層 `footnotes` key
- 理由：避免冗餘，保留原始文字的可查閱性

**D4：來自 parameter 文字的 inline condition 合併至 condition 欄位**
- 如 ID/IDSM 的 parameter 欄含 `@VGS=10V`，此資訊納入 `condition` 字串，不另建欄位
- 理由：condition 欄位已為自由文字，合併最簡單且完整

## Risks / Trade-offs

- **PDF 版本漂移**：若廠商更新 PDF 導致表格 row/col 偏移，hardcoded index 會靜默產出錯值 → 驗證測試可偵測；建議對 part_id 做前置斷言
- **多行 cell 合併問題**：部分 condition 欄含換行（如 `VGS=10V,ID=40A\nT=100℃`），parser 需正規化換行為空格 → 已在欄位政策中標記，測試覆蓋此情境
- **pdfplumber 版本依賴**：table detection 行為可能隨版本改變 → 鎖定 requirements 版本

## Open Questions

- ④ footnote 在 p1_t3 原始 PDF 中的確切 symbol 標記位置尚未以程式確認（已由 user 口頭確認對應 rds_on）
