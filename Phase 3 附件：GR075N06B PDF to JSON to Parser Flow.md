# Phase 3 附件：GR075N06B PDF to JSON to Parser Flow

## 這份附件的目的

這份文件不是在講抽象概念，而是要讓你拿 `GR075N06B.pdf` 直接練習一套完整流程：

1. 先把 PDF 解析成低假設的原始資料
2. 再整理成可讀的 JSON
3. 由你人工檢查與定義欄位語意
4. 再讓 agent 根據你的說明收斂成 parser 規格
5. 最後把 parser 做成可重複執行的程式

這套流程的重點不是一開始就要求 agent 「直接理解整份 PDF」，而是：

> 先讓 AI 把資料攤開，再由你校正語意，最後再收斂成規則。

這通常比憑空描述版面規則更快，也更穩。

---

## 一、這套流程要解決什麼問題

你前面提到一個很實際的困難：

- 如果只能靠相對位置描述文件，很容易說不清楚
- 一開始憑空描述欄位規則，常常講不準
- 文件裡哪些資訊重要，通常是看到資料後才更容易說明

所以更合理的做法不是直接寫 parser，而是走這條路：

1. `PDF -> raw extraction`
2. `raw extraction -> normalized JSON`
3. `human review -> field semantics`
4. `field semantics -> parser spec`
5. `parser spec -> executable parser`

---

## 二、你這次練習的目標

拿 `GR075N06B.pdf` 做完這次練習後，你應該至少要學會：

- 怎麼把 PDF 轉成中間表示
- 怎麼要求 agent 保留 metadata
- 怎麼人工標記欄位語意
- 怎麼把「這個看起來像我要的欄位」變成明確規則
- 怎麼要求 agent 把規則收斂成 parser

---

## 三、整體工作流

```text
GR075N06B.pdf
  ->
Step 1. 判斷文件類型
  ->
Step 2. 抽出 raw blocks / tables / metadata
  ->
Step 3. 整理成 normalized JSON
  ->
Step 4. 人工檢查樣本並標記欄位意義
  ->
Step 5. 產生 parser spec
  ->
Step 6. 實作 parser
  ->
Step 7. 驗證 parser 輸出
```

---

## 四、Step 1：先判斷文件類型

### 你要判斷什麼

先判斷 `GR075N06B.pdf` 比較接近哪一種：

- `text PDF`
- `scanned PDF`
- `hybrid PDF`

### 你可以怎麼看

人工先檢查：

- 能不能反白選字
- 複製出的文字是不是正常
- 每頁看起來像文字文件還是掃描影像
- 表格是不是清楚

### 你可以要求 agent 做的事

讓 agent 先幫你做「初步判斷」，但不要直接相信它。

#### Prompt 範例

```text
我要練習 PDF parsing。

請先不要做欄位抽取，只做文件型態判斷。

目標檔案：GR075N06B.pdf

請設計一個 Python 小工具，輸出以下資訊：
1. PDF 頁數
2. 每頁能否抽出文字
3. 每頁抽出的文字長度
4. 是否疑似 scanned PDF / text PDF / hybrid PDF
5. 若判斷依據不充分，請明確標註 uncertain

請先輸出實作方案，再提供程式碼。
```

### 人工操作範例

你實際檢查時，可以在筆記裡先寫：

```text
GR075N06B.pdf 初步觀察
- 頁數：
- 能否選字：
- 首頁是否有正常文字層：
- 是否有表格：
- 是否每頁格式一致：
- 初步判定：text / scanned / hybrid
```

---

## 五、Step 2：先做 low-assumption raw extraction

這一步最重要的原則是：

> 先多保留資料，不要太早做強假設。

不要一開始就要求 agent 直接抽出最終欄位。先讓它把資料攤開。

### 你要保留的最低欄位

raw extraction 至少應該保留：

- `page_number`
- `block_id`
- `block_type`
- `text`
- `bbox`
- `reading_order`
- `table_id` 或 `section_hint`

如果工具能提供更多，也可以加：

- `font_size`
- `font_name`
- `is_bold`
- `ocr_confidence`
- `source_type`

### 推薦 raw block JSON 結構

```json
{
  "document_id": "GR075N06B",
  "pages": [
    {
      "page_number": 1,
      "blocks": [
        {
          "block_id": "p1_b1",
          "block_type": "text",
          "text": "...",
          "bbox": [x1, y1, x2, y2],
          "reading_order": 1
        }
      ],
      "tables": []
    }
  ]
}
```

### 這一步要交代 agent 的關鍵要求

- 不要先做欄位推論
- 不要先做語意分類
- 先完整保留文本與位置
- 如果偵測到表格，要單獨列出
- 如果無法確定 `block_type`，要標記 `unknown`

#### Prompt 範例

```text
請為 GR075N06B.pdf 實作第一版 raw extraction。

要求：
1. 不要直接做欄位抽取
2. 先以低假設方式輸出 JSON
3. 每頁要保留 blocks
4. 每個 block 至少保留：
   - page_number
   - block_id
   - block_type
   - text
   - bbox
   - reading_order
5. 若有表格，請另外輸出 tables 區塊
6. 若 PDF 是掃描型，請把 OCR 流程納入，但也要明確標記來源
7. 請優先讓結果可供人工檢查，不要先追求最終抽取正確率

請先提出資料結構設計，再產生程式碼。
```

---

## 六、Step 3：把 raw extraction 整理成 normalized JSON

raw extraction 常常會太原始，不利於你閱讀與校正，所以第二步通常要做一層整理。

### normalized JSON 的目的

- 讓人比較容易看
- 讓 agent 比較容易做後續推理
- 降低原始 parser 的雜訊
- 保留 traceability

### 你可以要求整理的內容

- 合併明顯屬於同一段的 block
- 清掉重複頁首頁尾
- 標記疑似標題 / 段落 / 表格 / label-value
- 保留原 block reference

### 建議 normalized 結構

```json
{
  "document_id": "GR075N06B",
  "sections": [
    {
      "section_id": "s1",
      "page_number": 1,
      "section_type": "header",
      "text": "...",
      "source_blocks": ["p1_b1", "p1_b2"]
    }
  ],
  "tables": [],
  "metadata": {
    "source_file": "GR075N06B.pdf"
  }
}
```

### 這一步的重要觀念

normalized JSON 不是最終答案，它是讓你更容易做人工語意校正的中間層。

#### Prompt 範例

```text
我已經有 GR075N06B.pdf 的 raw extraction JSON。

請幫我再做一層 normalized JSON，目標不是抽出最終欄位，而是讓人更容易檢查。

要求：
1. 儘量保留 source_blocks 對應
2. 可合併明顯同段內容
3. 可標記粗略 section_type，例如：
   - header
   - paragraph
   - table
   - footer
   - label_value_candidate
4. 不要憑空補值
5. 若判斷不確定，保留 uncertain 標記

請先說明你的 normalization 規則，再提供程式調整方案。
```

---

## 七、Step 4：人工檢查與欄位語意校正

這一步是整個流程最關鍵的地方。

因為你不是在看最終答案對不對，而是在定義：

- 哪些資料才是你真正想抽的
- 同一欄位在文件裡可能長什麼樣
- 哪些位置線索有用
- 哪些區塊其實是噪音

### 你人工檢查時要看什麼

至少看這些：

- 哪些 section / block 是正文
- 哪些是頁首頁尾
- 哪些是表格
- 哪些像欄位 label
- 哪些像欄位 value
- 同一欄位是否有多個候選值
- 哪些資料絕對不能猜

### 你不要只說「這個是我要的」

你要進一步說成規格。

錯的說法：

- 這個是金額

比較好的說法：

- 當文字區塊出現 `Total`、`Total Amount`、`Grand Total` 這類 label 時，右側或下方最近的金額候選可視為 `total_amount`
- 若同頁有多個總額候選，優先採摘要區塊或表格底部合計列
- 若沒有明確 label，不要猜

### 人工標註範例模板

你可以直接照這個格式寫：

```text
文件：GR075N06B.pdf

欄位：document_number
- 可能出現位置：首頁上半部 / 標題區附近
- 常見 label：
- 值的型態：字串
- 候選判斷方式：
- 若有多個候選，優先規則：
- 不可接受情況：

欄位：document_date
- 可能出現位置：
- 常見 label：
- 值的型態：日期
- 候選判斷方式：
- 若找不到：

欄位：total_amount
- 可能出現位置：
- 常見 label：
- 值的型態：數字
- 候選判斷方式：
- 與其他欄位關係：
- 若無明確 label：
```

---

## 八、Step 5：把人工說明收斂成 parser spec

當你已經看過 `GR075N06B.pdf` 的資料後，就不要再用口語反覆修。要開始把規則寫成 parser spec。

### parser spec 應包含什麼

- 欄位名稱
- 欄位定義
- 欄位型別
- 來源區塊規則
- 位置規則
- 語意規則
- evidence 規則
- fallback 規則
- 不可猜測規則

### parser spec 範例

```yaml
fields:
  - name: total_amount
    type: number
    required: false
    labels:
      - Total
      - Total Amount
      - Grand Total
    candidate_rules:
      - prefer_same_block
      - otherwise_prefer_right_nearest_numeric
      - otherwise_prefer_below_nearest_numeric
    rejection_rules:
      - reject_if_no_numeric_pattern
      - reject_if_multiple_candidates_and_no_label_alignment
    evidence_required: true
    if_not_found: null
    do_not_guess: true
```

### 你可以怎麼請 agent 做這一步

#### Prompt 範例

```text
以下是我對 GR075N06B.pdf 的人工校正說明。

請不要直接改寫成程式，先幫我整理成 parser spec。

要求：
1. 把每個欄位整理成明確規則
2. 區分 label 規則、位置規則、值型別規則、fallback 規則
3. 把不能猜的欄位標清楚
4. 如果我描述還不夠明確，請列出 ambiguity，不要自行補假設
5. 請輸出 YAML 或 JSON 格式的 parser spec

這是人工校正內容：
[貼上你的欄位說明]
```

---

## 九、Step 6：從 parser spec 產生 executable parser

這一步才是讓 agent 寫程式的時候。

前面你做了這麼多，不是因為麻煩，而是因為這樣 agent 寫出的 parser 會穩很多。

### 這一步應該要求什麼

- 程式讀取 normalized JSON
- 依照 parser spec 抽出欄位
- 每個欄位都保留 evidence
- 抽不到就 `null`
- 不符合規則時要輸出原因

### 輸出建議

最終輸出不要只有值，應該長得像：

```json
{
  "document_number": {
    "value": "ABC123",
    "evidence": "Document No. ABC123",
    "page_number": 1,
    "source_blocks": ["p1_b4"],
    "confidence": 0.91
  }
}
```

### Prompt 範例

```text
請根據 parser spec，為 GR075N06B.pdf 的 normalized JSON 實作 parser。

要求：
1. 讀取 normalized JSON
2. 依 spec 抽取欄位
3. 每個欄位輸出：
   - value
   - evidence
   - page_number
   - source_blocks
   - confidence
4. 若找不到，輸出 null，不可猜
5. 若規則衝突，保留 warning 或 reason
6. 程式結構要可擴充，不要把規則全部硬寫死在單一函式

請先說明程式設計，再提供實作。
```

---

## 十、Step 7：驗證 parser，不是只看有沒有值

很多人做到這裡就停了，但你真正要驗證的是：

- 值是不是對的
- evidence 對不對
- 規則是不是可重複
- 同類型文件能不能沿用

### 驗證檢查清單

- 欄位值正確嗎
- evidence 真的支持該值嗎
- source block 對得上嗎
- 多候選值時有沒有選對
- 表格欄位有沒有被誤抓成正文
- 沒有值時是否有亂猜

### 你應該要求 agent 做的事

- 列出每個欄位的抽取路徑
- 對低信心欄位標 warning
- 對 ambiguous candidate 提供 debug 資訊

#### Prompt 範例

```text
請針對目前的 parser 輸出，幫我做 extraction review。

要求：
1. 不只看值，還要看 evidence 是否支持
2. 列出每個欄位的抽取理由
3. 標出低信心欄位
4. 標出可能誤抓的欄位
5. 若規則不穩定，請指出應回頭修改 raw extraction、normalization 還是 parser spec
```

---

## 十一、建議你的實際練習順序

你拿 `GR075N06B.pdf` 可以照下面順序練：

1. 先人工看 PDF
2. 請 agent 寫文件型態判斷工具
3. 請 agent 產 raw extraction JSON
4. 你看 raw extraction 是否夠用
5. 請 agent 整理成 normalized JSON
6. 你開始定義欄位意義
7. 請 agent 幫你整理成 parser spec
8. 請 agent 根據 spec 產 parser
9. 你根據輸出結果回頭修規則

這條路線比一開始就說：

- 幫我把這份 PDF 所有重要欄位抽出來

要穩很多。

---

## 十二、你跟 agent 對話時最重要的原則

## 1. 先要求「攤開資料」，不要先要求「總結答案」

因為一旦直接要答案，agent 很容易偷偷補假設。

## 2. 每一步只提高一點假設強度

順序應該是：

- raw
- normalized
- semantic
- parser
- final extraction

不要跳步。

## 3. 你給的回饋要規格化

不要只說：

- 這裡不對

要說：

- 這個欄位不應從 footer 區塊取值
- 同頁多個金額候選時，優先選表格總計列
- 沒有 label 時不能猜

## 4. 要求 evidence

只要最終欄位沒有 evidence，後面一定很難 debug。

---

## 十三、人工操作範例

下面是一個你之後可以直接照著做的人工 review 範例格式。

```text
文件：GR075N06B.pdf
版本：raw extraction v1

觀察：
- 首頁上半部有文件標頭
- 中段疑似正文區塊
- 下半部疑似表格或摘要
- 頁首頁尾有重複資訊

我要抽的欄位：
1. document_number
2. document_date
3. issuer_name
4. recipient_name
5. total_amount

修正意見：
- p1_b1 ~ p1_b3 應視為 header，不要當正文
- 疑似 total_amount 的候選值有 3 個，優先選摘要區塊中的最大金額候選
- footer 中的日期不是 document_date
- 若欄位沒有明確 label，先不要抽
- 表格列中的數值不要直接當 total_amount

下一步需求：
- 請根據以上修正整理成 parser spec
- spec 要列出 ambiguity
- 不可直接寫死單一 block id
```

---

## 十四、你最終要學會的不是某段程式，而是這個能力

你真正要練起來的能力是：

> 把一份你也還沒完全搞清楚的 PDF，逐步轉成一套 agent 可執行、可驗證、可重複的 extraction workflow。

這比直接學某個 PDF library 更重要，因為未來你遇到的文件格式一定會變。

---

## 十五、最後的簡化結論

對 `GR075N06B.pdf` 這次練習，最快的方式不是一開始憑空描述版面規則，而是：

1. 先把資料完整攤開
2. 保留 metadata
3. 你人工定義欄位語意
4. 讓 agent 把你的說明收斂成 parser spec
5. 再由 agent 實作 parser

這是從：

- 憑空描述

轉成：

- 先看資料，再修正與規格化

對文件解析來說，這通常是更快也更實際的路線。
