# RAG 學習計畫

## 目標

這份學習計畫的目標，不是只懂 RAG 名詞，而是能一步一步做出一個可用的文件理解與檢索系統，最後延伸到結構化抽取、驗證流程、Agent workflow 與 production 化。

完成這份計畫後，理想狀態是你可以獨立完成以下事情：

- 讀懂並修改常見的 Python / AI 專案程式碼
- 呼叫 LLM API 並控制輸出格式、成本與穩定性
- 處理 PDF、OCR、chunking 與 metadata
- 建立可查詢的 RAG pipeline
- 做結構化資料抽取與驗證
- 用 FastAPI + Database 包成後端服務
- 規劃 Agent workflow 與自動重試機制

## 建議學習原則

- 不要只看教學，每一階段都要做一個小成果
- 先做能跑的版本，再追求更漂亮的架構
- 每學一個新概念，都要落到你的 RAG 專案裡
- 優先建立可觀測性：log、錯誤訊息、輸入輸出樣本都要留
- 每週至少安排一次「整理與重構」，不要一路堆功能

## 建議總時程

- 核心路線：20 到 30 週
- 如果是兼職學習：大約 6 到 9 個月
- 如果是全職密集投入：大約 3 到 5 個月

---

## 學習順序總覽

```text
Phase 1  Python 與基礎工程能力
  ->
Phase 2  LLM 與 Prompt Engineering
  ->
Phase 3  PDF 與文件解析
  ->
Phase 4  Embedding 與 RAG
  ->
Phase 5  Structured Extraction
  ->
Phase 6  Validation System
  ->
Phase 7  Database 與 Backend
  ->
Phase 8  AI Agent 與 Workflow
  ->
Phase 9  MLOps / Production
```

## 最推薦的主線順序

如果你的目標是先做出一個能用的文件問答 / 抽取系統，建議照這個順序走：

1. Python -> API -> JSON
2. LLM -> Prompt -> Structured Output
3. PDF Parsing -> OCR -> Chunking
4. Embedding -> Vector DB -> RAG
5. Extraction -> Validation
6. FastAPI -> DB
7. Agent -> LangGraph
8. Production / Optimization

---

## Phase 1：Python 與基礎工程能力（2 到 4 週）

### 目標

能獨立閱讀、修改、執行 AI 專案，知道基本的除錯方式。

### 學習重點

#### Python 基礎

- 變數與資料型別
- function
- class
- module
- package
- typing
- async / await

#### 資料處理

- dict / list
- JSON
- CSV
- datetime
- regex

#### 檔案操作

- file I/O
- `pathlib`
- `os`
- `shutil`

#### API 與網路

- REST API
- `requests` / `httpx`
- headers
- auth
- rate limit
- retry

#### Git 與開發環境

- commit
- branch
- merge
- pull request
- virtual environment
- `requirements.txt` 或 `pyproject.toml`

#### Linux / Terminal 基礎

- terminal 指令
- ssh
- process
- environment variable
- stdout / stderr

### 這階段要補充的重點

原版計畫有列 Python 主題，但少了兩個實際上很重要的能力：

- 除錯能力：`print`、log、stack trace、exception handling
- 套件管理：虛擬環境、依賴版本、安裝問題排查

### 建議成果

做一個小工具：

- 讀取一份 JSON 設定檔
- 呼叫外部 API
- 把結果整理後存成 JSON 或 CSV
- 加上基本錯誤處理與 log

### 驗收標準

- 看得懂一個 300 到 500 行的 Python 小專案
- 能自己修掉常見 import / path / env 問題
- 能把 API 結果存成結構化檔案

---

## Phase 2：LLM 與 Prompt Engineering（2 到 3 週）

### 目標

理解 LLM 的輸入輸出邏輯，並能穩定產生可程式化處理的結果。

### 學習重點

#### LLM 基礎概念

- token
- context window
- hallucination
- temperature
- top_p
- latency
- cost

#### Prompt Engineering

- system prompt
- role prompting
- few-shot
- constraint prompting
- structured output

#### JSON Extraction

- schema output
- JSON validation
- function / tool calling
- strict parsing

#### OpenAI / LLM API

- chat completion
- streaming
- retry
- batching
- cost control
- timeout handling

### 這階段要補充的重點

原版方向正確，但建議加入以下兩個觀念：

- prompt 不是越長越好，重點是約束清楚、例子準確
- 結構化輸出不只靠 prompt，還要搭配 schema 驗證與 fallback

### 建議成果

做一個固定格式輸出的 LLM 小工具：

- 輸入一段文字
- 模型輸出固定 JSON
- 程式自動驗證欄位是否完整
- 失敗時自動 retry 或回報錯誤

### 驗收標準

- 能穩定產出符合 schema 的 JSON
- 知道什麼情況要用 prompt，什麼情況要加 rule-based 驗證
- 能估算一次呼叫的大概 token 成本

---

## Phase 3：PDF 與文件解析（2 到 4 週）

### 目標

讓 PDF 與掃描文件能被系統穩定解析，而不是只把它當純文字。

### 學習重點

#### PDF 結構理解

- text layer
- scanned PDF
- OCR PDF
- layout
- table structure
- headers / footers

#### PDF Parsing

- text extraction
- coordinate extraction
- table extraction
- image extraction

#### OCR

- OCR pipeline
- preprocessing
- multilingual OCR
- quality tradeoff

#### Chunking

- semantic chunk
- overlap
- section-aware chunking
- metadata
- page-level traceability

#### 文件格式轉換

- PDF -> Markdown
- PDF -> JSON
- structured document

### 這階段要補充的重點

這一段是很多 RAG 專案最容易低估的地方，建議補上：

- 保留來源定位資訊，例如頁碼、區塊、表格位置
- 不同文件類型要分流處理，合約、發票、報表不要共用同一套 parser 假設

### 建議成果

做一個 PDF 轉換器：

- 輸入 PDF
- 輸出 Markdown
- 同時輸出包含頁碼、段落、表格資訊的 JSON

### 驗收標準

- 能區分 text PDF 與 scanned PDF
- 能說明 chunk 是怎麼切出來的
- 能保留每段內容的文件來源與頁碼

---

## Phase 4：Embedding 與 RAG（3 到 4 週）

### 目標

建立真正可搜尋、可追溯、可回答問題的知識檢索系統。

### 學習重點

#### Embedding

- vector embedding
- semantic similarity
- cosine similarity
- embedding drift 基本概念

#### Vector Database

- indexing
- similarity search
- metadata filtering
- persistence

#### RAG 核心

- retrieval
- reranking
- hybrid search
- context injection
- answer grounding

#### Chunk Retrieval Strategy

- top-k
- score threshold
- parent-child retrieval
- multi-query retrieval

#### RAG Evaluation

- retrieval accuracy
- context quality
- grounding
- answer faithfulness
- failure analysis

### 這階段要補充的重點

原版有提到 retrieval 與 reranking，但建議明確補上：

- 先評估 retrieval，再評估最終答案，不要兩者混在一起
- RAG 失敗很多時候不是模型差，而是 chunking、metadata 或 query rewrite 出問題

### 建議成果

做一個 PDF 問答系統：

- 文件先切 chunk 並建索引
- 使用者可針對文件發問
- 回答時附上引用片段與頁碼

### 驗收標準

- 能解釋 top-k、threshold、rerank 的差異
- 回答可以附來源
- 能對查不到答案的 case 給出合理 fallback

---

## Phase 5：Structured Extraction（2 到 3 週）

### 目標

把文件內容轉成穩定、可驗證、可入庫的結構化資料。

### 學習重點

#### Information Extraction

- entity extraction
- field mapping
- table understanding
- key-value extraction

#### Deterministic Extraction

- regex
- rule engine
- parser
- post-processing

#### Hybrid Extraction

- regex + LLM
- layout + LLM
- retrieval + extraction

#### Output Schema

- Pydantic
- JSON Schema
- strict validation
- default / nullable / enum 設計

### 這階段要補充的重點

這裡最重要的不是把資料抽出來，而是讓抽取結果可維護：

- 每個欄位要有明確定義與型別
- 要知道哪些欄位可缺漏，哪些絕對不能缺
- 要區分「抽不到」與「文件中本來就沒有」

### 建議成果

做一個 invoice 或表單抽取器：

- 從文件中抽出固定欄位
- 用 schema 驗證格式
- 對不確定欄位標記 confidence

### 驗收標準

- 有明確 schema
- 失敗 case 可追蹤
- 規則與 LLM 分工合理，不是所有事情都丟給模型

---

## Phase 6：Validation System（2 到 4 週）

### 目標

讓系統從「能跑」進化到「可信」。

### 為什麼這階段特別重要

很多 AI 專案卡住，不是因為模型不夠強，而是因為沒有驗證層。沒有驗證，就沒有辦法知道結果能不能進資料庫、能不能進流程、能不能交給使用者。

### 學習重點

#### Data Validation

- type validation
- range validation
- required fields

#### Cross-field Validation

- subtotal consistency
- date logic
- business rules
- referential consistency

#### Confidence Scoring

- extraction confidence
- retrieval confidence
- voting system
- rule-based confidence

#### AI Self-check

- reflection
- critique
- retry strategy
- compare-and-revise

#### Human-in-the-loop

- review queue
- approval workflow
- escalation condition

### 這階段要補充的重點

建議把驗證切成三層：

1. 格式正確
2. 業務邏輯正確
3. 信心不足時要進人工審核

### 建議成果

替前一階段的 extraction system 加上 validation pipeline：

- 欄位驗證
- 跨欄位檢查
- confidence score
- review queue

### 驗收標準

- 能擋掉明顯錯資料
- 能把低信心結果分流
- 能留下驗證失敗原因

---

## Phase 7：Database 與 Backend（3 到 4 週）

### 目標

把前面的能力包成可持續使用的後端服務。

### 學習重點

#### SQL

- schema design
- index
- transaction
- normalization 與 denormalization 基本取捨

#### ORM

- SQLAlchemy
- migration
- query pattern

#### Backend API

- FastAPI
- authentication
- async API
- request / response schema

#### Queue System

- background jobs
- task queue
- retry queue
- dead-letter queue 基本概念

### 這階段要補充的重點

這階段應該開始建立「任務導向」思維，而不是只有腳本：

- 上傳文件
- 建立解析任務
- 查詢任務狀態
- 取得抽取結果

### 建議成果

做一個 Extraction API：

- 上傳 PDF
- 背景執行抽取
- 結果寫入 DB
- API 可查詢任務與結果

### 驗收標準

- 資料有 schema，不是隨便塞 JSON
- API 有明確輸入輸出
- 長任務不會阻塞主請求

---

## Phase 8：AI Agent 與 Workflow（4 到 6 週）

### 目標

建立可分工、可重試、可追蹤狀態的 AI workflow。

### 學習重點

#### Agent 基礎

- tool calling
- planning
- memory
- error handling

#### Workflow Engine

- state machine
- DAG workflow
- branching
- resume / checkpoint

#### LangGraph

- nodes
- edges
- state
- checkpoint

#### Multi-Agent

- extractor agent
- validator agent
- reviewer agent
- router agent

#### Autonomous Retry

- reflection loop
- failure recovery
- self-healing workflow
- bounded retry

### 這階段要補充的重點

不要一開始就追求 multi-agent。很多情況單一 workflow 加上幾個明確節點就夠了。建議順序是：

1. 單一 pipeline
2. 有狀態的 workflow
3. 再考慮拆 agent

### 建議成果

做一個 self-correcting workflow：

- 第一次抽取
- 驗證失敗時進入 critique / retry
- 仍失敗時送人工審核

### 驗收標準

- workflow 狀態清楚
- retry 有上限
- 每次失敗都有原因紀錄

---

## Phase 9：MLOps / Production（選修，建議在核心系統完成後再做）

### 目標

把原型系統變成可部署、可觀測、可控成本的服務。

### 學習重點

#### Docker

- container
- image
- compose

#### Monitoring

- logging
- tracing
- observability
- metrics

#### Cost Optimization

- caching
- batching
- model routing
- token budget

#### Security

- secret management
- RBAC
- data privacy
- audit log

### 建議成果

- 用 Docker 跑完整服務
- 加上基本 log 與 metrics
- 能看到每份文件花了多少時間與多少 token 成本

### 驗收標準

- 可重複部署
- 可觀測
- 成本可追蹤

---

## Phase 10：進階選修方向

依你的應用方向往下延伸，不必一開始就碰。

### A. Computer Vision 文件理解

- LayoutLM
- Donut
- OCR-free model
- document layout reasoning

適合情境：

- 掃描文件很多
- 表格與版面高度重要
- 純文字抽取效果不夠

### B. Fine-tuning

- LoRA
- QLoRA
- instruction tuning

適合情境：

- 領域格式固定
- prompt 已經逼近上限
- 有足夠高品質資料可微調

### C. Quant / Trading AI

- time series
- transformer
- reinforcement learning

### D. Voice AI

- STT
- diarization
- TTS

---

## 每階段建議成果

不要只學理論，每個階段都要留下作品。

| 階段 | 建議成果 |
| --- | --- |
| Phase 1 | 讀 JSON -> 呼叫 API -> 存檔的小工具 |
| Phase 2 | 可穩定輸出固定 JSON 的 LLM 工具 |
| Phase 3 | PDF -> Markdown / JSON 轉換器 |
| Phase 4 | PDF 問答系統 |
| Phase 5 | Invoice extraction system |
| Phase 6 | 含 validation 與 review queue 的抽取系統 |
| Phase 7 | Extraction API + DB |
| Phase 8 | Self-correcting AI workflow / agent |
| Phase 9 | Docker 化與可觀測的 production prototype |

---

## 建議技術棧

如果你想避免工具太分散，前期可以先用這套：

- 語言：Python
- API：FastAPI
- LLM 呼叫：OpenAI API 或相容 API
- 文件解析：`pymupdf`、`pdfplumber`、OCR 工具
- 結構化驗證：Pydantic
- 向量資料庫：先從本地或簡單方案開始
- 資料庫：PostgreSQL
- 非同步任務：背景工作或 task queue
- Workflow：LangGraph

---

## 每週建議節奏

如果你是兼職學習，可以用這個節奏：

- 2 天學觀念與看範例
- 2 天實作
- 1 天除錯與重構
- 1 天寫筆記與整理失敗案例

每週至少保留一份內容：

- 一個可執行的小程式
- 一份踩坑筆記
- 一份輸入 / 輸出樣本

---

## 學習時常見誤區

- 太早追求 multi-agent，結果基礎 pipeline 都還不穩
- 太早追求 fancy framework，忽略 parser、schema、validation 才是核心
- 只看 demo，不做 failure case 分析
- 沒有保存中間產物，導致問題無法定位
- 把所有抽取與判斷都丟給 LLM，缺少 deterministic rule

---

## 最後建議

如果你的主目標是「文件理解 + 結構化抽取 + RAG」，最值得優先投資的能力其實是這四個：

1. Python 與除錯能力
2. PDF / OCR / chunking 品質
3. structured output + validation
4. retrieval quality 與可追溯性

Agent、fine-tuning、production 都重要，但都應該建立在前面這四項已經穩定的前提上。

如果你照這份順序實作，做完 Phase 1 到 Phase 6，通常就已經能做出一個很實用的 RAG / extraction 系統原型。

---

## 專案實作總結

> 此章節記錄本次學習計畫的實際完成情況、技術決策與評估結果。
> 完成時間：2026-05

### 實際完成的 Phase

| Phase | 狀態 | 備註 |
| --- | --- | --- |
| Phase 1 — Python 基礎 | ✅ 完成 | |
| Phase 2 — LLM 與 Prompt Engineering | ✅ 完成 | |
| Phase 3 — PDF 與文件解析 | ✅ 完成 | 建立 vdsemi_parser，使用 pdfplumber + semantic anchor 定位表格 |
| Phase 4 — Embedding 與 RAG | ✅ 部分完成 | 完成 embedding 基礎建設，最終評估後決定不以 embedding 做主要查詢路徑 |
| Phase 5 — Structured Extraction | ✅ 完成 | parser 可穩定抽出 max_ratings、electrical、thermal、charts、footnotes |
| Phase 6 — Validation System | ✅ 完成 | 三層驗證系統：格式 → 業務邏輯 → confidence scoring |
| Phase 7+ | ⏸ 暫緩 | |

### 實際建立的系統

```
PDF
  └─► vdsemi_parser.py          解析結構化表格與圖表
        └─► normalizer.py        symbol / package / channel 正規化
              └─► validator.py   三層驗證（格式 / 業務邏輯 / confidence）
                    └─► embeddings.py + text_representations.py
                          └─► minio_client.py   圖表上傳
                                └─► upserts.py  PostgreSQL upsert（含冪等去重）

db/query.py   semantic search across 5 tables + format_context() for LLM
```

**技術選型：**

- Parser：`pdfplumber`，使用 semantic anchor（固定標題字串）定位表格位置
- Embedding model：`all-MiniLM-L6-v2`（384 維），存於 pgvector
- 資料庫：PostgreSQL + pgvector extension
- 圖片儲存：MinIO（S3-compatible object storage）
- 驗證：純 Python，無外部框架依賴

### 關鍵技術決策

#### 放棄以 Embedding 為主要 RAG 路徑

**決策：** 不使用 embedding 做主要查詢，改為評估直接 SQL lookup + LLM 的方案。

**原因：**
- Datasheet 的欄位高度結構化（symbol、parameter、condition、value 是已知欄位）
- 使用者查詢通常是精確需求，例如「VGS=4.5V 時的 RDS(ON) max 值」
- `all-MiniLM-L6-v2` 為英文模型，中文查詢語意對齊效果差（實測確認）
- Semantic search 在已知欄位的精確查詢上，準確度不如 WHERE 條件過濾

**結論：** Embedding 在跨文件探索（「哪個零件的熱阻最低」）仍有價值，但對單一 datasheet 的精確查詢，structured SQL 更可靠。

#### Skill 驅動的 Parser 開發流程

在 PDF 解析階段，建立了一系列輔助 skill（`ppg-explore` → `ppg-propose` → `ppg-apply`）來系統化地分析 PDF 結構、產出欄位規格、再落成 parser 實作。這個流程有效縮短了從 PDF 結構探索到可執行 parser 的週期。

### 代碼評估結果（外部評審）

**總體評分：7.5 / 10**

| 面向 | 評分 |
| --- | --- |
| 架構設計 | 9/10 |
| 代碼品質 | 8/10 |
| 驗證系統 | 9/10 |
| 運維可靠性 | 5/10（修正前）→ 7/10（修正後） |
| 搜尋品質 | 6/10 |

**已修正的問題（2026-05）：**

1. `validate_parsed()` 的回傳值原本被丟棄，現在有錯誤時會中止 import，低信心時印出警告
2. Validation 原本在 MinIO 上傳之後才執行，造成圖片孤立風險；現在改為在任何 I/O 之前執行
3. 原本開 3 條獨立 DB 連線；duplicate check 與 upsert_parts 合併為單一連線，減少連線開銷

**尚未修正的已知問題（留待後續）：**

- `query.py`：每次查詢建立新連線，未來包成 API 時需改用連線池
- `query.py`：每張表各取 top_k 再合併，可能遺漏更好的結果（建議改用 UNION ALL）
- `query.py`：缺少 `min_score` 參數，低語意相似度的結果也會被回傳
- `db/inserter.py:59`：`__main__` 區塊有硬編碼的機器路徑 `E:\tmp\datasheet`

### 學到的核心教訓

1. **Parser 品質決定一切**：Embedding、RAG、LLM 的效果全部建立在 parsing 品質上。anchor 對齊一個字元的差異就可能導致整張表格解析失敗。

2. **先評估再實作**：在花時間建 embedding pipeline 之後才發現 structured lookup 更適合這個需求。下次應先用 5 行 SQL 驗證查詢模式，再決定是否需要 semantic search。

3. **驗證層要有決策力**：驗證如果不影響下游行為，等於沒有驗證。`validate_parsed()` 回傳 `ValidationResult` 的設計本身是對的，但必須在呼叫端使用這個結果。

4. **連線管理在腳本階段容易被忽略**：一次性腳本開多條連線不會造成明顯問題，但 API 化之後立刻變成效能瓶頸。養成從腳本開始就注意連線生命週期的習慣。
