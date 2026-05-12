# Phase 4：Embedding 與 RAG

## 這個階段在學什麼

Phase 4 的核心不是「把資料存進向量資料庫」而已，而是理解整個檢索增強生成（RAG）鏈路怎麼成立：

1. 先把原始資料轉成適合檢索的文字表示。
2. 再把文字轉成 embedding 向量。
3. 讓資料庫能用向量相似度找回最相關的片段。
4. 最後把找回來的片段整理成 LLM 可用的 context。

如果前面 PDF parsing、chunking、欄位命名做得不好，這一階段的 retrieval quality 會直接受影響。

---

## 先建立一個心智模型

可以把目前專案拆成下面這條鏈：

`PDF parser -> 結構化欄位 -> 文字化表示 -> embedding -> PostgreSQL/pgvector -> semantic search -> LLM context`

你目前的兩個 class 剛好就落在這條鏈的中後段：

- `db/inserter.py` 負責 ingestion，也就是把 parser 結果轉成可檢索資料。
- `db/query.py` 負責 retrieval，也就是把使用者問題轉成向量，再從資料庫找答案候選。

這代表你其實已經做了不少 Phase 4 的實作，只是學習上還需要把「為什麼這樣做」講清楚。

---

## 需要認識的名詞

## 1. Embedding

Embedding 是把一段文字轉成一組數字向量，讓模型可以用「語意距離」而不是單純字面比對來找資料。

在 [db/inserter.py](/E:/code/rag/db/inserter.py:35) 你用：

```python
EMBED_MODEL = "all-MiniLM-L6-v2"
```

接著在 [db/inserter.py](/E:/code/rag/db/inserter.py:65) 用 `SentenceTransformer` 產生多筆 embeddings。

學習重點：

- embedding 不是原文，它是原文的語意表示。
- 同一個 embedding model 必須同時用在寫入與查詢。
- 如果之後換模型，向量維度和語意空間都會變，舊資料通常要重建。

---

## 2. Vector Embedding

向量嵌入（Vector Embedding）技術說明文件

### 1. 核心概念：從抽象語義到具體數值
Embedding 是一種將現實世界的資訊（如文字、圖片、影音）轉化為電腦可運算的「數字陣列」的技術。
- **Vector（向量）：** 是 Embedding 的實際展現形式。例如一個 384 維的浮點數陣列：`[0.12, -0.55, ..., 0.89]`。
- **運算邏輯：** 電腦並不理解詞彙，但它能計算向量之間的空間距離。在多維空間中，語義相近的詞（如「蘋果」與「香蕉」）距離會較近；語義不同的詞（如「蘋果」與「手機」）距離則較遠。

### 2. 維度（Dimensions）的設計與意義
維度代表了模型描述一個物件時所使用的「特徵數量」。常見的維度如 384、768、1536 等。為什麼是這些數字？
- **硬體效率：** 符合 GPU 運算的 $2^n$ 倍數，能達到最佳的平行運算效率。
- **架構對齊：** 符合 Transformer 模型的「多頭注意力機制」（Multi-Head Attention），便於將總維度平均分配給各個運算單元。
- **越多維度越好嗎？**
    - **優點：** 語義捕捉更細膩，適合複雜領域（法律、醫療）。
    - **缺點：** 增加儲存成本、降低檢索速度、可能產生「維度災難」導致空間過於稀疏。

### 3. 三大主流供應商評析
目前市場上並非由 OpenAI 獨佔，Google 與 Anthropic (透過合作夥伴) 分別在不同維度上展現優勢：

| 供應商 | 推薦模型 | 核心維度 | 技術特點 |
| :--- | :--- | :--- | :--- |
| **OpenAI** | text-embedding-3 | 256 - 3072 | **MRL 技術：** 支援向量截斷，可根據效能需求自由縮減維度而不過度損失精度。 |
| **Google** | gemini-embedding | 128 - 3072 | **多模態整合：** 唯一能將圖、文、影音原生對齊在同一向量空間的模型。 |
| **Voyage AI** | voyage-3 | 1024 - 2048 | **高資訊密度：** 雖然維度較低，但透過領域微調（程式碼、法律），檢索精度常超越高維模型。 |

### 4. 深度解析：為何「低維度」能勝過「高維度」？
以 Voyage AI 為例，其精度領先的原因不在於「箱子大（維度）」，而在於「收納效率（資訊密度）」：
- **檢索對齊優化：** 專門針對 RAG（檢索增強生成）場景訓練，強化模型對「相似但不相同」內容的辨識力。
- **領域專精：** 提供特定的模型（如 voyage-code），使用較少的數字就能精準捕捉特定產業的邏輯。
- **長文本理解：** 支援更大的上下文輸入，讓產出的每一個向量都包含了更完整的脈絡資訊。

### 5. 實務選擇建議
在開發系統（如 RAG 知識庫）時，建議依據以下標準選擇：
- **追求開發速度與生態系：** 選擇 **OpenAI**。其工具鏈最成熟，且縮減維度功能（Matryoshka）非常彈性。
- **需要處理多媒體檢索：** 選擇 **Gemini**。適合需要「以圖找圖」或「影音檢索」的進階應用。
- **追求極致檢索精度與成本比：** 選擇 **Voyage AI**。特別是在處理程式碼、技術文件或法律合約時，低維度能大幅節省向量資料庫的開銷。

---

在 [db/inserter.py](/E:/code/rag/db/inserter.py:35) 你已經註記 `all-MiniLM-L6-v2` 對應 `dim=384`，這是很重要的實務細節，因為資料庫的 `vector(n)` 維度必須對齊模型輸出。

學習重點：

- 向量維度不對，資料就寫不進去或查不出來。
- 模型版本和 schema 必須一起管理。

---

## 3. Semantic Similarity

Semantic similarity 是語意相似度。它回答的不是「字有沒有一樣」，而是「意思像不像」。

例如：

- query: `RDS(ON) at high temperature`
- datasheet 裡可能寫的是 `Drain-Source On-State Resistance`、`TJ=150C`

雖然字面不完全一致，但 embedding 仍可能把它們拉近。

這就是 RAG 能比 keyword search 更有彈性的原因。

---

## 4. Cosine Similarity / Vector Distance

向量搜尋本質上是在比較 query 向量和資料向量之間的距離。常見做法有 cosine similarity、inner product、L2 distance。

在 [db/query.py](/E:/code/rag/db/query.py:51) 你用的是：

```sql
1 - (embedding <=> %(vec)s::vector) AS _score
```

`<=>` 是 pgvector 的距離運算子，你再把距離轉成一個比較像分數的 `_score`。

學習重點：

- 距離越小，通常代表越相近。
- 分數怎麼定義要一致，否則 threshold 很難調。
- 不同距離函數適合的 embedding 模型可能不同。

---

## 5. Vector Database

Vector database 是能儲存向量並支援 similarity search 的資料庫。

你目前不是另外接 Pinecone、Weaviate，而是走 PostgreSQL + pgvector，這也是很常見的實務選擇。

在你現在的設計裡，向量分散存放在多個表：

- `max_ratings`
- `electrical_characteristics`
- `thermal_characteristics`
- `typical_charts`
- `footnotes`

這個做法的好處是欄位結構清楚；缺點是查詢時要跨表 merge 結果。

---

## 6. Indexing

Indexing 是讓向量搜尋不要每次全表掃描。

雖然目前這兩個檔案沒有直接建立 index，但學習上必須知道：

- 沒有 vector index，資料量大時查詢會變慢。
- pgvector 常見會搭配 `ivfflat` 或 `hnsw`。
- index 的效果要建立在固定維度、固定距離函數、足夠資料量之上。

如果未來 datasheet 數量增加，這會從「效能優化」變成「系統是否可用」的問題。

---

## 7. Metadata Filtering

Metadata filtering 是在向量搜尋前或後，加上結構化條件縮小範圍。

在 [db/query.py](/E:/code/rag/db/query.py:135)：

```python
where_clause = "WHERE part_id = %(pid)s" if part_id else ""
```

這就是最基本的 metadata filter。

學習重點：

- metadata filter 可以降低誤召回。
- 在 datasheet 類場景，`part_id`、`section`、`table type` 都很適合當 filter。
- 只有 semantic search、沒有 filter，常會召回跨零件或跨區塊的雜訊。

---

## 8. Retrieval

Retrieval 是把「問題」轉成向量後，從知識庫中找回候選內容。

在 [db/query.py](/E:/code/rag/db/query.py:110) 的 `search()` 就是在做這件事：

1. 把 `question` encode 成向量。
2. 逐表查詢相似內容。
3. 合併結果後依 `_score` 排序。
4. 回傳 top-k。

這已經是標準的 retrieval pipeline。

---

## 9. Top-k

Top-k 是只取分數最高的前 k 筆結果。

在 [db/query.py](/E:/code/rag/db/query.py:114) 你預設 `top_k=5`，而且每張表都先取 `LIMIT %(k)s`，最後再全域排序一次。

學習重點：

- `k` 太小會漏資料。
- `k` 太大會把雜訊一起送進 context。
- 每表先取 k，再全域截斷，和全庫直接取 k，語義上不完全一樣。

你現在的做法比較像「每張表先保留候選，再做全域競爭」。

---

## 10. Score Threshold

Score threshold 是低於某個相似度分數就不要。

你目前在 `search()` 裡還沒有 threshold 機制，這表示只要 top-k 有東西，就算分數很差也可能被帶回去。

學習重點：

- top-k 解決「取多少」，threshold 解決「夠不夠像」。
- 真實系統通常兩者都要。
- 沒有 threshold 時，LLM 很容易拿低品質 context 亂回答。

---

## 11. Context Injection

Context injection 是把 retrieval 找回來的內容整理後塞進 prompt。

在 [db/query.py](/E:/code/rag/db/query.py:159) 的 `format_context()`，你把不同 table 的結果轉成文字，這就是 context injection 前的 context formatting。

這一步非常關鍵，因為：

- retrieval 找回什麼很重要；
- 你怎麼呈現給 LLM 一樣重要。

如果格式不好，LLM 雖然拿到資料，也可能用不好。

---

## 12. Grounding

Grounding 是回答有沒有根據檢索到的證據，而不是模型自己補。

你目前的格式已經保留：

- `part_id`
- table 類型
- `section`
- `source_page`
- chart key

這些都是 grounding 的基礎。它讓後續 prompt 可以要求模型「只能根據以下內容回答」。

---

## 13. Reranking

Reranking 是先粗搜出候選，再用更強的模型或規則重新排序。

你目前還沒有 reranking，但這是 Phase 4 需要知道的概念，因為：

- embedding search 很快，但不一定最準。
- reranker 可以在前 20 筆候選中挑出最像問題的 5 筆。

對 datasheet 問答來說，含有條件式欄位的資料很常受益於 rerank。

---

## 14. Hybrid Search

Hybrid search 是 keyword search + vector search 一起用。

舉例：

- 使用者問 `VGS(th)`，這很像 exact keyword。
- 使用者問 `gate threshold voltage`，這比較像 semantic search。

只用其中一種，通常都會漏掉一部分場景。

---

## 15. Retrieval Evaluation

Retrieval evaluation 是判斷「找回來的內容到底對不對」。

這一階段常見錯誤是只看 LLM 最終回答，卻沒有拆開驗證 retrieval 品質。

建議你分開檢查：

- query 有沒有找到正確表格。
- 找回來的 row 是否真的能回答問題。
- 分數排序是否合理。
- 有沒有常見失敗 query。

---

## 用 `db/inserter.py` 看 Phase 4

`db/inserter.py` 雖然檔名是 inserter，但它其實做了很多 RAG ingestion 準備工作。

### 1. 你先把結構化資料轉成可檢索文字

在這幾個 helper：

- [_text_max_rating()](/E:/code/rag/db/inserter.py:71)
- [_text_thermal()](/E:/code/rag/db/inserter.py:76)
- [_text_electrical()](/E:/code/rag/db/inserter.py:80)
- [_text_chart()](/E:/code/rag/db/inserter.py:92)
- [_text_footnote()](/E:/code/rag/db/inserter.py:96)

你其實是在做一件很重要的事：把 row-level schema 轉成 embedding-friendly text。

這是 Phase 4 很容易被忽略的重點。embedding 品質不只取決於模型，也取決於你餵給模型的文字長什麼樣。

### 2. 你把多種資料都向量化了

在 [db/inserter.py](/E:/code/rag/db/inserter.py:327) 之後，你把：

- max ratings
- thermal characteristics
- electrical characteristics
- chart captions
- footnotes

一起做 embedding。

這代表你的檢索空間不是只有正文，而是把 datasheet 多種證據來源都納入了。

### 3. 你把 embedding 和結構化欄位一起存

各種 `upsert_*` function 都保留了原始欄位與 embedding，例如：

- [upsert_max_ratings()](/E:/code/rag/db/inserter.py:144)
- [upsert_electrical()](/E:/code/rag/db/inserter.py:200)

這是正確方向，因為 RAG 不是只要向量，還需要原始欄位做 grounding 和格式化輸出。

---

## 用 `db/query.py` 看 Phase 4

`db/query.py` 比較直接地呈現了 retrieval 本身。

### 1. Query 也用同一個 embedding model

在 [db/query.py](/E:/code/rag/db/query.py:25) 和 [db/query.py](/E:/code/rag/db/query.py:31) 你用同一個 `all-MiniLM-L6-v2` 來 encode 問題，這是正確的。

如果 inserter 和 query 用不同模型，結果通常會直接失真。

### 2. 逐表檢索再合併

在 [db/query.py](/E:/code/rag/db/query.py:47) 你針對不同 table 定義個別 SQL，然後在 [db/query.py](/E:/code/rag/db/query.py:142) 逐表查詢。

這個設計反映一個實務事實：

- `electrical_characteristics` 和 `footnotes` 的欄位長相不同；
- 但檢索時仍希望它們能一起競爭。

### 3. 你已經開始做 LLM-ready context

在 [db/query.py](/E:/code/rag/db/query.py:159) 的 `format_context()`，你不是直接把 dict 丟進 LLM，而是整理成比較像證據片段的文字，這一步在實務上很重要。

---

## 這個階段要注意的重點

## 1. Retrieval quality 往往取決於 ingestion text，不只是模型

以你現在的設計來說，`_text_electrical()` 的文字內容會直接影響未來是否能搜到對的 row。  
如果文字化表示漏掉關鍵條件，例如 `VGS=10V`、`TJ=150C`，檢索就會變差。

## 2. Row-level embedding 很適合精準查值，但不一定適合複合問題

你現在大多是 row-level embedding，這對問單一欄位很有效。  
但如果問題需要跨表整合，例如同時結合 maximum ratings 和 footnotes，單筆 row 的資訊可能不夠。

## 3. Footnote 不能只當附屬資訊

你已經把 footnotes 向量化，這是對的。datasheet 裡很多限制條件其實都藏在 footnote，若 retrieval 忽略它，LLM 會答得像對但其實不完整。

## 4. Chart caption 的 embedding 能搜到圖，但圖本身還沒被語意化

你目前是用 caption 做 chart 檢索，這對第一版足夠；但如果 caption 很短或太泛，就可能搜不到真正想要的曲線。

## 5. 沒有 evaluation，就無法判斷 RAG 是否真的有效

如果只憑「看起來能查到幾筆」來判斷，很容易高估系統品質。  
Phase 4 一定要開始累積測試 query 和預期答案。

---

## 目前實作可以改善的地方

以下建議我會特別放在「Phase 4 的學習觀點」下看。

## 1. 把 embedding model 設定集中管理

目前 `db/inserter.py` 和 `db/query.py` 都各自寫了 `EMBED_MODEL`，雖然目前一致，但長期容易漂移。

建議：

- 抽成共用設定檔，例如 `db/config.py`
- 連同維度一起集中定義
- 寫明「更換模型時需要 re-embed」

## 2. 在 `search()` 加入 `score_threshold`

目前 [db/query.py](/E:/code/rag/db/query.py:151) 只做排序後取前 `top_k`。  
建議加入可選參數：

- `score_threshold`
- `per_table_k`

這樣你可以分開控制「候選數量」和「最低品質」。

## 3. 明確區分「每表候選 k」和「最後輸出 k」

現在每張表都 `LIMIT top_k`，最後再取全域 `top_k`。  
這不一定錯，但最好在介面上明講，不然使用者會誤以為是全庫直接 top-k。

## 4. 為 retrieval 補上 debug 資訊

可以考慮讓 `search()` 選配回傳：

- query embedding model 名稱
- 命中的 table
- 原始 distance
- 是否通過 threshold

這對失敗案例分析很有幫助。

## 5. 建立固定的 retrieval evaluation 集

例如做一個 `tests/rag_queries.md` 或 JSON 檔，收集：

- query
- 預期 table
- 預期 symbol / parameter
- 可接受的 evidence

這樣你就能真的驗證 Phase 4，而不是只有 demo。

## 6. 規劃 rerank 或 hybrid search

你現在的架構已經可以先跑 baseline。下一步最值得補的是：

- BM25/ILIKE + vector hybrid
- 或 cross-encoder reranker

這兩者都很適合拿來當 Phase 4 進階練習。

---

## 建議你在這個階段完成的練習

## 練習 1：解釋每個 `_text_*()` 為什麼這樣設計

如果你能講清楚：

- 為什麼 `electrical_characteristics` 要把 `min/typ/max` 寫進去
- 為什麼 `condition_raw` 必須保留
- 為什麼 `caption` 可以當圖表的檢索文字

表示你真的理解 ingestion text 對 RAG 的影響。

## 練習 2：手寫 10 個 datasheet query 測試 retrieval

例如：

- `maximum drain-source voltage`
- `RDS(ON) at high temperature`
- `junction to ambient thermal resistance`
- `gate charge curve`

然後檢查：

- 找回哪些 table
- 分數排序是否合理
- 有沒有漏掉 footnote

## 練習 3：替 `search()` 增加 threshold

這會迫使你思考：

- 分數如何解讀
- 沒命中時要怎麼 fallback
- 是要回空結果，還是回低信心結果

---

## 這份文件最重要的結論

Phase 4 不只是「把 embedding 做出來」，而是建立完整的 retrieval thinking：

- 要檢索什麼資料
- 資料要如何文字化
- 向量怎麼存
- 查詢怎麼合併
- context 怎麼提供給 LLM
- 如何驗證 retrieval 品質

你目前的 `db/inserter.py` 和 `db/query.py` 已經把這條鏈做出雛形了。接下來最需要補的不是更多框架，而是：

- retrieval evaluation
- threshold / rerank / hybrid search
- 共用設定與可維護性

只要把這些補起來，Phase 4 會從「能跑」進到「能判斷品質」。
