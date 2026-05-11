# Phase 2：LLM 與 Prompt Engineering

## 這一階段在學什麼

Phase 2 的核心不是「學會和 AI 聊天」，而是理解：

- LLM 到底怎麼接收輸入、產生輸出
- 哪些參數會影響結果
- 怎麼讓模型輸出更穩定、可控、可被程式使用
- 怎麼把自然語言請求轉成結構化結果

如果 Phase 1 是讓你能寫程式，那 Phase 2 就是讓你知道怎麼正確使用模型。

---

## 這一階段完成後，你應該會什麼

- 看得懂 LLM API 的基本參數
- 知道 `temperature`、`top_p`、`token` 在做什麼
- 能分辨 prompt 寫不好，還是任務本身不適合交給 LLM
- 能設計出穩定輸出 JSON 的 prompt
- 知道什麼時候該用 schema validation、retry、tool calling

---

## 一、LLM 是什麼

LLM 是 Large Language Model，大型語言模型。

你可以先把它理解成：

- 它不是資料庫
- 它不是搜尋引擎
- 它不是絕對正確的推理機器
- 它本質上是在「根據上下文，預測下一段最可能的文字」

這件事很重要，因為它代表：

- 它很會生成文字
- 它可以模仿格式
- 它可以做一定程度的分類、整理、摘要、抽取
- 但它也可能自信地胡說

這就是後面會提到的 hallucination。

---

## 二、Phase 2 常見名詞解釋

## 1. token

### 是什麼

token 是模型計算文字的基本單位，不一定等於一個字，也不一定等於一個單字。

例如：

- 一句中文可能被切成多個 token
- 一個英文長字也可能被切成多個 token

### 為什麼重要

- API 計價通常跟 token 有關
- 模型一次能處理多少內容，取決於 context window
- prompt 太長，會浪費成本，也可能擠掉重要資訊

### 你應該先知道什麼

- 輸入會吃 token
- 輸出也會吃 token
- 範例越多，token 成本越高

---

## 2. context window

### 是什麼

context window 是模型一次可以看到的總內容上限。

這個總內容包含：

- system prompt
- user prompt
- 對話歷史
- tool results
- 模型輸出

### 為什麼重要

如果你塞太多內容進去：

- 成本會上升
- 回應速度可能變慢
- 真正重要的資訊可能被淹沒
- 超過限制時，請求可能失敗或被截斷

### 實務理解

不是 context 越大越好，重點是放「最有用的資訊」。

---

## 3. hallucination

### 是什麼

hallucination 指模型生成了看起來合理、但其實不正確的內容。

例如：

- 編造不存在的文件內容
- 補出你沒提供的欄位
- 自己猜測日期、金額、來源

### 為什麼會發生

因為模型的目標是生成「合理的文字」，不是保證「真實的答案」。

### 怎麼降低

- 提供更清楚的上下文
- 限制輸出格式
- 要求「找不到就明確說找不到」
- 對結果做 schema validation
- 對高風險資料加 rule-based 檢查

---

## 4. temperature

### 是什麼

temperature 是控制輸出隨機性的參數。

### 可以怎麼理解

- 低 `temperature`：比較保守、穩定、接近固定答案
- 高 `temperature`：比較發散、有創意、變化較大

### 什麼時候用低

像你這種做 RAG、抽取、分類、JSON 輸出，通常偏向低一點比較合理，因為你要的是穩定，不是創作。

### 常見誤解

`temperature = 0` 不等於永遠 100% 一模一樣，但通常會更穩。

---

## 5. top_p

### 是什麼

`top_p` 也是控制取樣範圍的參數。

它的概念是：

- 模型不是從所有可能字詞中亂選
- 而是從累積機率最高的一小群候選中選

### 你先怎麼記

初學時可以先把它理解成另一種控制輸出發散程度的方法。

### 實務建議

初期不用同時大調 `temperature` 和 `top_p`。通常先固定一個，避免變因太多。

---

## 三、Prompt Engineering 是什麼

Prompt Engineering 不是寫漂亮句子，而是設計「讓模型更容易做對事」的輸入方式。

你可以把 prompt 想成任務規格書。

一個好的 prompt 應該至少說清楚：

- 你要模型做什麼
- 輸入是什麼
- 輸出格式是什麼
- 哪些不能亂猜
- 找不到時該怎麼辦

---

## 四、Prompt Engineering 常見名詞

## 1. system prompt

### 是什麼

system prompt 是給模型的最高層行為指令，通常用來定義：

- 角色
- 任務邊界
- 輸出原則
- 禁止事項

### 例子

```text
你是一個資訊抽取助手。只能根據使用者提供的內容抽取欄位。
如果資料不存在，請輸出 null，不要自行猜測。
輸出必須符合指定 JSON 格式。
```

### 作用

它不是保證，但通常能明顯改善模型的穩定性。

---

## 2. role prompting

### 是什麼

role prompting 是先定義模型扮演什麼角色，再要求它做任務。

例如：

- 你是一位法律文件分析員
- 你是一位發票欄位抽取器
- 你是一位只輸出 JSON 的 API

### 為什麼有效

角色會影響模型偏好的回答風格與注意重點。

### 注意

role prompting 只是輔助，不是魔法。真正決定品質的，還是任務描述是否清楚。

---

## 3. few-shot

### 是什麼

few-shot 是在 prompt 裡放幾個範例，讓模型照著學格式與邏輯。

### 例子

你可以給模型：

- 一段輸入文本
- 對應的正確 JSON 輸出

然後再給它新的文本，要求它比照處理。

### 為什麼有效

比起抽象規則，模型常常更容易從範例理解：

- 你要哪些欄位
- 什麼算空值
- 格式要長什麼樣子

### 缺點

- 會增加 token 成本
- 範例如果寫不好，模型會學歪

---

## 4. structured output

### 是什麼

structured output 是要求模型輸出固定格式，例如：

- JSON
- 指定欄位的物件
- schema 限定的資料結構

### 為什麼重要

因為程式最好處理的是結構化資料，不是自由文字。

### 例子

不要只說：

```text
請幫我整理這份發票內容
```

而是說：

```text
請輸出 JSON，欄位包含：
invoice_no, invoice_date, vendor_name, total_amount
若找不到欄位，填 null。
不要輸出多餘文字。
```

---

## 五、JSON Extraction 相關名詞

## 1. schema output

### 是什麼

schema output 是先定義好輸出結構，再要求模型符合。

例如你先定義：

- `invoice_no` 是字串
- `total_amount` 是數字
- `invoice_date` 是日期字串

### 好處

- 減少格式漂移
- 程式比較好驗證
- 比較容易串後端

---

## 2. JSON validation

### 是什麼

模型說它輸出的是 JSON，不代表真的合法。

JSON validation 就是在程式端檢查：

- 格式是不是合法 JSON
- 欄位有沒有缺
- 型別對不對
- 值是否合理

### 為什麼重要

這是很多人剛開始會漏掉的地方。

prompt 只能提高成功率，validation 才能真正控風險。

---

## 3. function calling / tool calling

### 是什麼

這是一種讓模型不要直接輸出自由文字，而是輸出「要呼叫哪個工具、帶什麼參數」的方式。

### 你可以怎麼理解

不是叫模型自己去做所有事，而是讓它負責：

- 判斷下一步要做什麼
- 組出結構化參數
- 再由程式真的去執行

### 例子

如果使用者說：

```text
幫我查詢 2024 年 5 月的發票
```

模型可能不直接回答，而是輸出類似：

```json
{
  "tool": "search_invoice",
  "arguments": {
    "year": 2024,
    "month": 5
  }
}
```

### 好處

- 結構清楚
- 容易跟系統整合
- 比純自由文字更穩

---

## 六、OpenAI / LLM API 相關名詞

## 1. chat completion

### 是什麼

這是最常見的互動方式：你送一串 messages 給模型，模型回一段結果。

常見 message 類型：

- system
- user
- assistant

### 你需要理解的重點

- 模型不是只看最後一句話
- 它會一起看整段對話上下文

---

## 2. streaming

### 是什麼

streaming 是讓模型一邊生成、一邊回傳，不用等整段生成完才看到內容。

### 好處

- 使用者體感比較快
- 長回答時比較自然

### 注意

如果你要做嚴格 JSON parsing，streaming 會讓處理稍微麻煩一些，因為你收到的是一段一段的內容。

---

## 3. retry

### 是什麼

retry 是請求失敗時重新送出一次。

### 常見失敗原因

- timeout
- rate limit
- 暫時性伺服器錯誤
- 模型輸出格式不合法

### 注意

retry 不是無腦重送，要設上限，也要知道失敗類型。

---

## 4. batching

### 是什麼

batching 是把多個任務打包處理，以提升吞吐量或降低成本。

### 例子

例如你有 100 筆短文字分類任務，可以考慮分批送，而不是 100 次單獨呼叫。

### 注意

batching 不一定永遠比較好，因為：

- prompt 會變長
- 單次失敗成本更高
- 結果切分與對應會更麻煩

---

## 5. cost control

### 是什麼

cost control 是控制模型成本的能力。

### 常見方法

- 縮短 prompt
- 減少不必要的對話歷史
- 減少 few-shot 範例
- 只取必要 chunk
- 小任務用較便宜模型
- 把 deterministic 的部分交給程式處理

### 核心觀念

最貴的不是 token，本質上是「把不該給 LLM 做的事也丟給 LLM」。

---

## 七、你在 RAG 專案裡，這一階段真正要學會什麼

如果你是為了後面的 RAG、抽取、文件理解做準備，Phase 2 真正的重點可以濃縮成下面五件事：

1. 知道模型不可靠，所以要設計約束
2. 知道 prompt 要明確定義任務與輸出格式
3. 知道輸出 JSON 後，還要做 validation
4. 知道不是所有工作都該交給 LLM
5. 知道成本、延遲、穩定性是工程問題，不只是模型問題

---

## 八、初學者最常見的誤區

## 1. 以為 prompt 寫越長越好

錯。太長常常只是在堆廢話，還增加成本。

## 2. 以為模型懂你的業務背景

錯。你沒講清楚，它就會自己猜。

## 3. 以為模型說是 JSON，就一定能 parse

錯。一定要做 validation。

## 4. 以為回答看起來合理，就代表正確

錯。這是 hallucination 最危險的地方。

## 5. 以為 prompt engineering 可以解決所有問題

錯。很多問題其實要靠：

- better data
- better retrieval
- better schema
- better validation
- better workflow

---

## 九、建議你怎麼學 Phase 2

不要一口氣追很多理論，建議用這個順序：

1. 先理解 token、context window、hallucination、temperature
2. 學會寫基本的 system prompt
3. 練習要求模型輸出固定 JSON
4. 在程式端做 JSON validation
5. 練習 few-shot 與 retry
6. 最後再碰 function calling / tool calling

---

## 十、Phase 2 的最小實作練習

你可以做一個最小專案：

### 題目

輸入一段文字，請模型抽出固定欄位並輸出 JSON。

### 欄位範例

- `company_name`
- `invoice_date`
- `invoice_no`
- `total_amount`

### 你要練到的能力

- 寫 system prompt
- 寫 user prompt
- 控制輸出只回 JSON
- parse JSON
- 驗證欄位
- 失敗時 retry

---

## 十一、你可以用這個標準判斷自己有沒有學會

如果你已經能做到下面幾件事，就代表 Phase 2 基本過關：

- 你能用自己的話解釋 token、context window、hallucination
- 你知道為什麼抽取任務通常不適合高 temperature
- 你能設計一個要求固定 JSON 輸出的 prompt
- 你知道為什麼要做 schema validation
- 你知道 function calling 的目的不是炫技，而是讓系統更穩

---

## 十二、給你的簡化結論

Phase 2 可以濃縮成一句話：

> 學會把「叫 AI 幫你做事」這件事，變成一個可控、可驗證、可程式化的流程。

這一階段不是背名詞，而是建立正確心智模型。

只要你把下面這條主線抓住，後面做 RAG 會順很多：

- LLM 很強，但不可靠
- prompt 要清楚
- 輸出要結構化
- 結果要驗證
- 失敗要能重試或 fallback

---

## 十三、下一步建議

你現在最適合做的不是繼續看更多名詞，而是立刻做一個小練習：

1. 寫一個簡單 prompt，要求模型抽取固定欄位
2. 讓模型輸出 JSON
3. 用 Python 驗證 JSON 是否合法
4. 試幾組故意模糊或不完整的輸入
5. 觀察模型在哪些地方開始亂猜

做完這個練習，你對 Phase 2 的理解會比單看術語快很多。
