## 1. 專案結構

- [ ] 1.1 建立 parser 模組目錄（如 `lib/parsers/vsp007n06ms_g/`），加入 `__init__.py`
- [ ] 1.2 確認 `pdfplumber` 版本並鎖定至 requirements 檔案

## 2. Field Spec Schema

- [ ] 2.1 定義 `FieldRecord` dataclass 或 TypedDict，包含 symbol、stat、value、unit、condition、footnote_ref、required、on_missing、strict
- [ ] 2.2 定義輸出結構：`{"fields": [...], "footnotes": {...}}`

## 3. Footnote 表

- [ ] 3.1 硬編碼 footnote 對照 dict（①②③④）至 parser 模組

## 4. 表格萃取 — Page 1

- [ ] 4.1 實作 `parse_p1_t2()`：萃取 part_id、package（元件識別）
- [ ] 4.2 實作 `parse_p1_t3()`：萃取 13 筆最大額定值，處理 t_stg_tj 拆分為 min/max，處理 id/idsm 的 inline condition（@VGS=10V），附加 footnote_ref（idm→①、eas→②、pdsm→③）
- [ ] 4.3 實作 `parse_p1_t4()`：萃取 rthjc、rthja 熱阻 2 筆

## 5. 表格萃取 — Page 2

- [ ] 5.1 實作 `parse_p2_static()`：萃取靜態電氣特性 12 筆，處理 rds_on 多行條件合併（含 Tj=100°C 繼承列）、附加 rds_on footnote_ref=④
- [ ] 5.2 實作 `parse_p2_dynamic()`：萃取動態特性 14 筆，處理 Coss/Crss condition 繼承自 Ciss、Qg 雙 VGS 條件、Qgs/Qgd condition 繼承
- [ ] 5.3 實作 `parse_p2_switching()`：萃取切換特性 4 筆，共用 condition 字串
- [ ] 5.4 實作 `parse_p2_diode()`：萃取體二極體特性 4 筆

## 6. 主要 Parser 入口

- [ ] 6.1 實作 `parse(pdf_path: str) -> dict`，依序呼叫所有子 parser，合併為統一輸出結構
- [ ] 6.2 在入口加入 part_id 前置斷言（驗證為 VSP007N06MS-G，防止對錯誤 PDF 靜默執行）

## 7. 驗證測試

- [ ] 7.1 建立測試檔，對 `parse()` 輸出驗證 part_id、rthjc、rds_on footnote、t_stg_tj 拆分、Ciss 三值、tr 切換時間、trr condition 字串、footnotes dict 四條等關鍵 scenario
- [ ] 7.2 執行測試，確認全數通過

## 8. 輸出驗證

- [ ] 8.1 手動執行 parser 對 `VSP007N06MS-G.pdf`，確認輸出 JSON 筆數 ≥ 50
- [ ] 8.2 比對輸出 JSON 與本次 explore 的欄位政策草稿，確認無遺漏欄位
