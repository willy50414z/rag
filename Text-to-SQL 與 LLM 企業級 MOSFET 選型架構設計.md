# Text-to-SQL + LLM 企業級 MOSFET 選型架構設計

## 背景

有一個關聯式資料庫，存放多家公司的 MOSFET 產品及相關參數（如 Vds、Id、Rds(on)、封裝等）。之前嘗試過 RAG 方案，但因為資料本質是結構化參數，embedding 檢索不適合精確的數值範圍查詢與多條件邏輯組合。

核心想法：**使用者提問 → LLM 提取查詢參數並生成 SQL → 查詢資料庫 → LLM 對結果做判斷排序（類似 re-rank）→ 回覆使用者**。

## 核心結論

這個流程**完全符合企業級應用範式**，比純 RAG 更適合結構化參數查詢。主流企業（資料庫廠商、數據分析平台）的 AI 助手都採用類似架構：

```
使用者提問 → LLM 解析意圖 + 提取參數 → 生成 SQL → 執行查詢 → LLM 對結果做語義排序/解釋 → 回覆
```

### 與 RAG 的差異

| 面向 | RAG（embedding） | Text-to-SQL |
|------|------------------|-------------|
| 適合場景 | 模糊語意匹配（"耐高壓的 MOSFET"） | 精確數值條件（Vds > 600V, Id < 20A） |
| 資料準確性 | 依賴 chunk 品質與檢索覆蓋率 | 所有原始資料來自 DB，LLM 只做排序/解釋 |
| 可控性 | 黑箱檢索 | SQL 可審計、可優化、可加權限控制 |
| 成本 | 需要 embedding 與向量儲存 | 不需要額外基礎設施 |

---

## 一、防幻覺策略（5 層）

如何讓 agent 完全依照 SQL 撈出來的資料做判斷，不瞎編？

### 第 1 層：Prompt 強制約束

在 system prompt 中明確禁止使用自身知識：

```python
system_prompt = """
你是一個嚴格的 MOSFET 選型助手。你必須遵守：
1. 只能使用下面【資料庫查詢結果】中提供的產品資料
2. 如果查詢結果為空，回答「沒有找到符合條件的產品」
3. 禁止編造任何參數值（如 Vds, Id, Rds(on) 等）
4. 禁止推薦結果中不存在的型號
5. 你的回答中每個參數值都必須能在【資料庫查詢結果】中找到對應
"""
```

### 第 2 層：結構化資料注入

用 JSON 或 Markdown 表格注入查詢結果，不要轉成自然語言。每筆記錄帶 row_id 方便追溯：

```python
context = json.dumps([
    {"row_id": i, "part_number": r[0], "vds": r[1], "id": r[2], ...}
    for i, r in enumerate(query_result)
], ensure_ascii=False)
```

Prompt 中要求引用時必須帶上 row_id。

### 第 3 層：Tool Calling 只讀模式

- 定義 `get_mosfet_products` 工具，返回值是確定的 DB 查詢結果
- LLM 無法直接輸出產品參數，必須透過工具調用取得資料後再組織答案
- 可設置 `tool_choice: "required"` 強制先調用工具

### 第 4 層：驗證層（安全網）

LLM 生成回覆後，用程式做一次校驗：

```python
def validate_reply(llm_output, db_results):
    mentioned_parts = extract_part_numbers(llm_output)
    for part in mentioned_parts:
        if part not in [row['part_number'] for row in db_results]:
            return False, f"編造了型號 {part}"
    return True, "OK"
```

發現編造時，讓 LLM 重新生成或降級為簡單表格輸出。

### 第 5 層：先排序後解釋（兩段式輸出）

不讓 LLM 自由排序，而是讓它生成排序表達式，程式執行排序後再送回去解釋：

```
第一輪：LLM 生成排序邏輯（如 "ORDER BY Rds(on) ASC, Vds DESC"）
       → 程式執行排序得到 final_results
第二輪：LLM 只負責用自然語言解釋 final_results 的前幾名
```

這徹底杜絕 LLM 在排序階段瞎編順序的可能。

---

## 二、Schema Linking：讓 LLM 準確理解欄位

LLM 看到 CREATE TABLE 後仍容易混淆同義欄位、枚舉值、單位換算。解決方案是提供結構化的 schema 描述：

```json
{
  "table_name": "mosfets",
  "columns": [
    {
      "name": "part_no",
      "type": "text",
      "description": "產品型號，如 IRF540N",
      "examples": ["IRF540N", "STP55NF06"]
    },
    {
      "name": "vds_max",
      "type": "real",
      "description": "漏源擊穿電壓（單位：V），用戶說「耐壓」、「電壓等級」均指此欄位",
      "allowed_ops": [">", "<", "=", "BETWEEN"]
    },
    {
      "name": "rds_on",
      "type": "real",
      "description": "導通電阻（單位：mΩ），用戶說「內阻」、「導通損耗」",
      "unit_note": "存儲值為毫歐，如 10 表示 10mΩ"
    },
    {
      "name": "package",
      "type": "text",
      "description": "封裝形式",
      "enum_values": ["TO-220", "TO-247", "DPAK", "SOT-23"]
    }
  ],
  "domain_knowledge": "用戶提及「小封裝」通常指 package IN ('SOT-23','DPAK')；「低內阻」指 rds_on < 20"
}
```

### 關鍵要點

- **欄位業務含義**：明確常見口語表達的對應關係
- **枚舉值標準化**：用戶可能說 TO220，但標準是 TO-220，需在 prompt 中說明映射
- **單位說明**：避免 LLM 自己換算（尤其電阻 mΩ vs Ω）
- **數值模糊詞處理**：「約」、「左右」、「大概」→ ±10% 範圍；「大於」、「超過」→ `>`；「以下」、「小於」→ `<`

---

## 三、Few-shot 優化設計

### 示例模板

每個示例包含三部分：使用者問題 + 生成 SQL + 簡短解釋（幫助 LLM 理解映射邏輯）：

```python
few_shot_examples = [
    {
        "user": "找幾款耐壓600V以上，電流20A以下的TO-220封裝MOSFET",
        "sql": "SELECT part_no, vds_max, id_max, rds_on, package FROM mosfets WHERE vds_max > 600 AND id_max < 20 AND package = 'TO-220' LIMIT 10;",
        "explanation": "條件：電壓>600，電流<20，封裝精確匹配"
    },
    {
        "user": "我需要內阻很低的管子，用於開關電源，耐壓最好能到650V，電流能力30A左右",
        "sql": "SELECT part_no, vds_max, id_max, rds_on FROM mosfets WHERE vds_max >= 650 AND id_max BETWEEN 25 AND 35 ORDER BY rds_on ASC LIMIT 5;",
        "explanation": "低內阻用ORDER BY rds_on；「30A左右」用BETWEEN；優先滿足耐壓"
    },
    {
        "user": "有沒有小封裝的N溝道MOS？要能過5A電流",
        "sql": "SELECT part_no, package, id_max FROM mosfets WHERE package IN ('SOT-23', 'DPAK', 'SOT-223') AND id_max >= 5 LIMIT 10;",
        "explanation": "小封裝映射到具體枚舉值列表"
    }
]
```

### 必須覆蓋的情境

- **空結果預期**：告訴 LLM 若查不到，輸出 `-- NO_RESULTS_EXPECTED` 作為佔位符，不要自己編數據
- **模糊枚舉值**：如「貼片封裝」→ `package IN ('DPAK','SOT-23','SOT-223')`
- **多條件優先級**：當無法完全滿足時，先放鬆哪個條件（如「耐壓優先於電流」）

### 動態 Few-shot 檢索（進階）

- 對使用者問題做簡單 embedding，檢索最相似的 2-3 個 few-shot 示例
- 或基於關鍵詞匹配：問題包含「封裝」就召回封裝相關示例
- 這是 RAG + Text-to-SQL 的結合，但 few-shot 庫很小，成本可控

---

## 四、完整 Prompt 結構

```python
system_prompt = """
你是一個專業的 SQL 生成助手，服務於 MOSFET 選型資料庫。

【資料庫 Schema】
{detailed_schema_json}

【查詢規則】
1. 只生成 SELECT 語句，不允許修改數據。
2. 始終添加 LIMIT 20（除非用戶明確要求更多）。
3. 封裝型號必須使用標準枚舉值（見 schema）。
4. 用戶說「小封裝」、「貼片」等，映射到 package IN ('DPAK','SOT-23','SOT-223')。
5. 用戶說「低內阻」，按 rds_on 升序排序。
6. 如果用戶條件可能無結果，優先使用寬鬆範圍（如 BETWEEN），並在註釋中說明。
7. 輸出只包含 SQL，不要額外解釋。

【Few-shot 示例】
{retrieved_few_shot_examples}

現在用戶提問：{user_question}
請輸出 SQL：
"""
```

---

## 五、SQL 校驗與修正層（推薦）

即使 prompt 優化到位，LLM 仍可能寫錯欄位名。增加輕量級的 SQL 校驗層：

```python
field_aliases = {
    "drain_current": "id_max",
    "voltage_rating": "vds_max",
    "rdson": "rds_on",
    "case": "package"
}
```

- 解析 LLM 生成的 SQL 中的 WHERE 條件欄位
- 檢查欄位是否存在於 schema 中
- 若欄位名錯誤，用預定義的別名映射表自動修正
- 修正後執行，或返回錯誤讓 LLM 重試

這是「prompt 優化 + 規則修正」的混合方法，在企業級中非常穩定。

---

## 六、完整流程示例

```python
def chat_with_mosfet_db(user_question):
    # 1. LLM 生成 SQL（使用 few-shot 約束格式）
    sql = llm.generate_sql(
        f"用戶問題：{user_question}\n"
        "表結構：mosfets(id, part_no, vds_max, id_max, rds_on, package, brand)\n"
        "輸出：只輸出 SQL，不要解釋"
    )

    # 2. 執行 SQL（建議設置超時和行數限制）
    raw_results = db.execute(sql).fetchall()
    if not raw_results:
        return "未找到匹配產品"

    # 3. 讓 LLM 做語義排序/解釋（但不允許修改數據）
    final_answer = llm.generate(
        system_prompt="你是選型助手，只能使用以下數據。禁止編造。",
        user_prompt=f"""
        用戶問題：{user_question}
        資料庫查詢結果（JSON格式）：
        {json.dumps(raw_results)}

        請按用戶意圖（如性價比、低導通損耗等）對結果排序，並推薦前三款。
        輸出格式：先解釋排序依據，再以表格列出推薦產品及關鍵參數。
        """
    )

    # 4. 可選：驗證 final_answer 中出現的所有產品型號都在 raw_results 中
    return final_answer
```

---

## 七、企業級落地檢查清單

| 項目 | 說明 |
|------|------|
| SQL 安全 | 使用參數化查詢 + 唯讀資料庫帳戶，限制 LLM 生成 DROP/UPDATE/INSERT |
| 防 SQL 注入 | 對 LLM 生成的 SQL 做輕量級解析（禁止分號、多語句） |
| 處理空結果 | 讓 LLM 學會給出改條件建議（如「Vds>700V 無結果，是否接受 650V？」），需要 few-shot 示例 |
| 複雜參數提取 | 如「小封裝、低內阻」需映射到具體欄位與條件，建議用語義層定義模糊詞的條件範圍 |
| 超時與行數限制 | SQL 執行加 timeout 與 LIMIT，防止惡意或低效查詢 |

---

## 八、各層級投入產出總結

| 層級 | 方法 | 投入產出比 |
|------|------|-----------|
| 基礎 | 提供清晰 schema 描述（帶業務含義 + 枚舉值） | 高，必做 |
| 進階 | 3-5 個精心設計的 few-shot 示例（覆蓋常見口語映射） | 極高，快速見效 |
| 高階 | 動態 few-shot 檢索 + 欄位別名修正層 | 進一步提升穩定性，需少量開發 |
| 安全 | 5 層防幻覺策略 + SQL 校驗層 | 企業級可靠度的底線 |

做完這些，LLM 生成的 SQL 準確率可從 60-70% 提升到 90% 以上（取決於問題複雜度和資料庫品質）。

---

## 關鍵設計原則

1. **所有原始資料來自 DB**，LLM 只做排序/解釋，不生成參數值
2. **SQL 可審計、可優化、可加權限控制**
3. **不需要 embedding 和向量檢索**，成本低
4. **防幻覺靠多層防禦**，不是單一 prompt 就能解決
5. **「先排序後解釋」兩段式設計**徹底杜絕排序階段的幻覺
