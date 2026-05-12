# Phase 5：Structured Extraction

## 這個階段在學什麼

Phase 5 的核心是把非結構化或半結構化資料，穩定地轉成一份可驗證、可寫入資料庫、可被後續系統使用的 schema。

如果說：

- Phase 3 在處理「文件怎麼讀」
- Phase 4 在處理「資料怎麼找」

那麼 Phase 5 處理的是：

- 「欄位怎麼定義」
- 「值怎麼抽」
- 「抽出來的值怎麼保證格式一致」

這一階段的重點不是只做一次 extraction 成功，而是讓 extraction 有穩定規則、明確 schema、失敗時可診斷。

---

## 先建立一個心智模型

Structured extraction 可以拆成下面幾層：

1. 定義 output schema。
2. 把原始內容對應到 schema 欄位。
3. 對欄位做 normalization。
4. 處理 missing value、nullable、enum、單位、條件欄位。
5. 在寫入 DB 前做 validation。

以你目前專案來看，雖然真正的 parser 在 `pdf-parser-generator/<part>/parser.py`，但 `db/inserter.py` 很清楚地反映出你預期 parser 應該輸出什麼結構，所以它很適合拿來當 Phase 5 的教材。

---

## 需要認識的名詞

## 1. Information Extraction

Information extraction 是從原始文件中抓出有意義資訊。

在 datasheet 場景，常見 extraction 對象有：

- part number
- absolute maximum ratings
- electrical characteristics
- thermal characteristics
- chart captions
- footnotes

你在 [db/inserter.py](/E:/code/rag/db/inserter.py:297) 之後，直接讀取：

- `tables["parts"]`
- `tables["max_ratings"]`
- `tables["thermal_characteristics"]`
- `tables["electrical_characteristics"]`
- `tables["typical_charts"]`
- `result["footnotes"]`

這些就是 extraction 後的資料形狀。

---

## 2. Field Mapping

Field mapping 是把文件中的語意，對應到你定義的欄位名稱。

例如：

- 文件上的 `Drain-Source Voltage` 映射成 `parameter`
- `V(BR)DSS` 映射成 `symbol`
- `-60` 或 `60` 映射成 `value_raw` / `value_num`
- `TJ=25C` 映射成 `condition_raw`

這一步是 Structured Extraction 的骨架。欄位一旦命名混亂，後面 validation、query、DB 設計都會一起混亂。

---

## 3. Key-Value Extraction

Key-value extraction 是把「欄位名 / 欄位值」配對起來。

在 datasheet 裡不一定都是直觀的 `key: value`。  
很多時候它其實來自表格欄位，例如：

- `symbol`
- `parameter`
- `min`
- `typ`
- `max`
- `unit`
- `condition`

你目前的 schema 已經很明確地把這些拆出來，這是正確方向。

---

## 4. Table Understanding

Table understanding 是知道一個表格中：

- 哪一列是資料列
- 哪一欄是欄位定義
- 哪些欄位屬於條件
- 哪些欄位屬於數值
- 哪些 footnote 是附加條件

對 datasheet 而言，這通常比一般段落抽取更重要。

你目前的 `max_ratings`、`electrical_characteristics`、`thermal_characteristics` 分表設計，本質上就是 table understanding 的結果。

---

## 5. Deterministic Extraction

Deterministic extraction 是用固定規則抽資料，例如：

- regex
- parser
- rule engine
- 座標規則
- 表格欄位對齊規則

這類方法的優點是穩定、可測、可 debug。

對 datasheet 這類格式相對規律的文件，deterministic extraction 通常應該是主體，而不是把一切都丟給 LLM。

---

## 6. Post-processing

Post-processing 是抽取完後再做整理，例如：

- 把字串數字轉成 float
- 清洗單位
- 正規化 condition
- 處理空字串 / null
- 補上 table reference、source page

在 [db/inserter.py](/E:/code/rag/db/inserter.py:164) 到 [db/inserter.py](/E:/code/rag/db/inserter.py:229)，你可以看到很多欄位已經假設 parser 先做好部分 post-processing，例如：

- `condition_normalized`
- `value_num`
- `value_min`
- `value_max_num`
- `min`
- `typ`
- `max`

這代表你的 extraction pipeline 其實已經不只是「抓字串」，而是開始進入可用資料的階段。

---

## 7. Hybrid Extraction

Hybrid extraction 是 deterministic 與 LLM 混用。

常見形式：

- 先用 parser 擷取候選區塊，再用 LLM 補欄位。
- 先用 regex 抽數字，再用 LLM 判斷欄位語意。
- 先用 layout 鎖定表格，再用模型做欄位對映。

你目前展示出來的 `db/inserter.py` 比較像在吃 deterministic parser 的結果，這其實很合理。  
如果未來遇到更多版型差異，再考慮在 parser 前後接 LLM 輔助會比較穩。

---

## 8. Output Schema

Output schema 是你希望 extraction 最後長成什麼樣子。

從 `upsert_*()` 來看，你目前的 schema 已經相當具體。例如 `electrical_characteristics` 需要：

- `part_id`
- `symbol`
- `parameter`
- `section`
- `condition_raw`
- `condition_kv`
- `condition_normalized`
- `min`
- `typ`
- `max`
- `value_raw`
- `unit`
- `footnote_ref`
- `source_page`
- `table_ref`

這就是典型的 output schema thinking：不是只抽到值，而是把值放進固定欄位。

---

## 9. Pydantic / Schema Validation

Pydantic 或 JSON Schema 的作用，是在資料寫入前先檢查：

- 型別對不對
- 必填欄位有沒有缺
- nullable 欄位是否合理
- enum 是否只出現在合法集合裡

你目前的 `db/inserter.py` 還沒有顯式 Pydantic model，表示 schema 主要依賴 parser 輸出正確與資料庫寫入時才暴露問題。

這在 prototype 階段可行，但正式一點的 extraction pipeline，通常應該在 DB 前就做 validation。

---

## 10. Strict Validation

Strict validation 是寧可提早失敗，也不要把髒資料默默寫進去。

例如：

- `condition_kv` 不是合法 JSON
- `value_num` 應為數字卻出現字串
- `unit` 空白但 schema 不允許

你目前在 [db/inserter.py](/E:/code/rag/db/inserter.py:168) 和 [db/inserter.py](/E:/code/rag/db/inserter.py:225) 用 `json.loads()` 處理 `condition_kv`，這其實已經是一種最小版本的 validation。

---

## 11. Nullable / Default / Enum

這三個概念在 extraction 裡非常常見。

### Nullable

不是所有 datasheet 欄位都一定有值，例如：

- 某列可能只有 `max` 沒有 `typ`
- 某列沒有 footnote

所以 `None` 應該是 schema 設計的一部分，不是例外。

### Default

有些欄位可能希望有預設值，例如缺少 `condition_normalized` 時先設空字串。  
你在 [db/inserter.py](/E:/code/rag/db/inserter.py:169) 和 [db/inserter.py](/E:/code/rag/db/inserter.py:226) 就有這種處理。

### Enum

像 table 類型、section 類型、欄位狀態，未來很適合用 enum，避免同義字亂飛。

---

## 12. Normalization

Normalization 是把多種寫法收斂成一致表示。

例如：

- `Tj`, `TJ`, `Junction Temperature` 可能都要歸一到某個標準欄位
- `RDS(on)`、`Rds(on)` 要統一
- 條件字串要拆成可比較的 `condition_kv`

在你的 schema 裡，`condition_raw` 與 `condition_normalized` 並存，是很好的設計，因為：

- `raw` 保留原始證據；
- `normalized` 方便查詢、比對、去重。

---

## 用 `db/inserter.py` 看 Phase 5

`db/inserter.py` 雖然不是 parser 本體，但非常適合用來理解「好的 extraction output 長什麼樣」。

## 1. 它清楚定義了資料庫需要的欄位

每個 `upsert_*()` 其實都在反向定義 extraction schema。

例如 [upsert_max_ratings()](/E:/code/rag/db/inserter.py:144) 說明：

- 這張表不只要 `symbol` 和 `value_raw`
- 還要 `condition_raw`
- 還要 `condition_kv`
- 還要 `condition_normalized`
- 還要 `footnote_ref`

這表示你對 extraction 的要求已經超過「字抓出來就好」，而是考慮到了後續查詢與驗證。

## 2. 它把 raw value 和 normalized value 分開

例如：

- `value_raw`
- `value_num`
- `value_min`
- `value_max_num`

這種設計很重要，因為：

- `raw` 用來保留原文證據；
- `num` 用來做篩選、排序、比較；
- 有些欄位其實是 range，不是單一值。

這正是 Structured Extraction 的核心思維。

## 3. 它保留 traceability

你有保留：

- `source_page`
- `table_ref`
- `footnote_ref`

這表示之後如果抽錯，可以回到原文件定位。  
這在 extraction 專案裡非常重要，否則 debug 會很痛苦。

## 4. 它假設 parser 已經做完 schema 對齊

`run()` 在 [db/inserter.py](/E:/code/rag/db/inserter.py:297) 之後幾乎直接信任 parser 回傳資料。  
這說明目前的設計把「資料正確性責任」大多放在 parser。

這沒有問題，但也代表：

- parser 要有更好的測試；
- 或 DB 前要加一層 validation model。

---

## 用 `db/query.py` 反過來理解 Phase 5

`db/query.py` 不是 extraction code，但它能反向告訴你 extraction schema 是否設計得好。

## 1. 如果 schema 不清楚，query formatting 會很痛苦

在 [db/query.py](/E:/code/rag/db/query.py:170) 到 [db/query.py](/E:/code/rag/db/query.py:205)，你可以很順地格式化不同 table，原因是 schema 已經相對清楚。

例如 electrical table 明確有：

- `section`
- `symbol`
- `parameter`
- `condition_raw`
- `min`
- `typ`
- `max`
- `unit`

這代表你的 extraction schema 足夠支撐後續問答。

## 2. 如果 extraction 缺 `condition_raw`，檢索答案會不完整

像 `RDS(ON)` 這種欄位，如果沒有條件，答案幾乎不能用。  
所以 Structured Extraction 不是只抽「值」，而是要把值成立的條件一起抽出來。

## 3. 如果 extraction 沒做 normalization，query 端會很難擴充

未來若你想做：

- `section` filter
- `symbol` exact match
- 條件式檢索
- range filter

都會仰賴 extraction schema 是否乾淨。

---

## 這個階段要注意的重點

## 1. 先定 schema，再寫 extraction

很多人會先從 parser 開始，但 Structured Extraction 更好的做法是反過來：

1. 先想最後資料表需要什麼欄位。
2. 再想 parser 要怎麼抽到這些欄位。

你現在的 `upsert_*()` 很適合當 schema 設計的出發點。

## 2. raw 與 normalized 要並存

只留 normalized 值，你會失去原文證據。  
只留 raw 值，你後續查詢與驗證很難做。

兩者都保留，是比較穩的做法。

## 3. 條件欄位常常和主值一樣重要

datasheet 裡很多數值只有在特定條件下才成立。  
如果 extraction 只抽 `typ=4.5`，卻沒抽 `VGS=10V`、`ID=20A`，那筆資料其實不完整。

## 4. Footnote 是 schema 的一部分，不是備註而已

很多限制、例外、測試條件都在 footnote。  
從 extraction 視角來看，它應該是正式 evidence，而不是附屬文字。

## 5. validation 最好在 DB 前做

如果等到 insert 時才失敗，你會很難知道問題出在：

- parser
- normalization
- schema mapping
- DB constraint

中間加一層 validation model，診斷成本會低很多。

---

## 目前實作可以改善的地方

## 1. 為 parser output 建立顯式資料模型

建議為每種 table 建 Pydantic model，例如：

- `PartRecord`
- `MaxRatingRecord`
- `ElectricalCharacteristicRecord`
- `ThermalCharacteristicRecord`
- `ChartRecord`

好處：

- 型別與欄位缺失可以提早發現
- `db/inserter.py` 不用完全信任 parser
- schema 會變得更文件化

## 2. 在 insert 前加 validation pipeline

可以在 [db/inserter.py](/E:/code/rag/db/inserter.py:346) 進 DB 前，先做：

- required field check
- numeric parsing check
- condition JSON check
- unit presence check

這會讓 Phase 5 和 Phase 6 的界線更清楚。

## 3. `condition_kv` 建議在 parser 階段就保證為 dict

目前你在 inserter 用 `json.loads()` 轉換，代表上游可能傳字串。  
從 schema 角度來看，`condition_kv` 若本質是結構化欄位，最好 parser 輸出時就是 dict，而不是 JSON string。

這樣有幾個好處：

- 型別更自然
- 減少重複 parse
- validation 更直接

## 4. 對數值欄位統一命名策略

目前有些表用：

- `value_num`
- `value_min`
- `value_max_num`

有些表用：

- `min`
- `typ`
- `max`

這並不一定錯，但文件裡最好明確解釋命名規則，否則後續維護者會疑惑：

- 哪些是量測值
- 哪些是規格欄位
- 哪些是 range 邊界

## 5. 把 extraction failure case 文件化

建議針對 parser 寫一份失敗案例筆記，整理：

- 表頭變形
- 單位缺失
- footnote 黏在 parameter 上
- range 與負號解析問題
- chart caption 缺失

這會讓 Structured Extraction 不只停在 happy path。

## 6. 增加 parser output 測試

最少應該有：

- parser output schema test
- sample row value test
- `condition_normalized` 一致性 test
- numeric conversion test

否則你現在的 inserter 雖然能 upsert，但不代表 extraction 穩定。

---

## 建議你在這個階段完成的練習

## 練習 1：替每張表寫一份 schema 說明

至少說清楚：

- 每個欄位代表什麼
- 哪些是 required
- 哪些可為 null
- 哪些來自原文
- 哪些是 normalization 後產物

## 練習 2：替 parser output 補 Pydantic model

即使先不改 parser，也可以先在 inserter 前做 model 驗證。  
這會很直接地暴露 schema 設計的模糊處。

## 練習 3：列出 10 個最容易抽錯的欄位

例如：

- 條件字串
- range value
- 負號數值
- 單位
- footnote marker

然後思考每一類應該用：

- deterministic rule
- schema validation
- human review

哪一種方式處理。

---

## 這份文件最重要的結論

Phase 5 的重點不是「把資料抽出來」，而是把資料抽成一份可維護、可驗證、可查詢的結構。

你目前的 `db/inserter.py` 已經透露出一個不錯的方向：

- schema 分表清楚
- raw / normalized 並存
- traceability 欄位有保留
- footnote 與 condition 被視為正式資料

但如果要把這一階段做完整，接下來最值得補的是：

- 顯式 schema model
- DB 前 validation
- parser output 測試
- failure case 文件化

做到這一步，Structured Extraction 才會從「抽得到」進到「抽得穩」。
