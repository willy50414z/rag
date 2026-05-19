# Phase 8：AI Agent 與 Workflow 教學

> 本文件以本專案的 datasheet import pipeline 為主軸，說明如何從線性腳本演進為可狀態、可重試、可追蹤的 AI workflow。

---

## 一、你目前在哪裡

`import_pipeline.py` 現在是一個**線性腳本**：

```
parse → validate → upsert_parts → upload_charts → embed → upsert_all
```

這樣的設計有幾個隱患：

| 問題 | 情境 |
| --- | --- |
| 無法從中斷點恢復 | embedding 失敗時，parts 已入庫，子表沒有，下次重跑整個流程都重跑 |
| 驗證失敗只能中止 | 低信心的文件只能警告後繼續，沒有分流機制 |
| 無法追蹤每份文件的狀態 | 批次處理 100 份 PDF 時，哪些成功、哪些在哪個步驟失敗，完全不可見 |
| 重試是手動的 | 失敗後要重跑整個腳本，無法只重跑失敗的步驟 |

Phase 8 要解決的就是這些問題。

---

## 二、三個核心概念

### 2.1 Agent 是什麼

**Agent = 有工具的 LLM，加上讓它決定下一步的 loop。**

最小的 agent 結構：

```python
while not done:
    action = llm.decide(state, tools)   # LLM 選擇工具與參數
    result = tools[action.name](**action.args)  # 執行工具
    state  = update_state(state, result)         # 更新狀態
```

這裡的 `state` 就是記憶體（memory）。`tools` 就是 agent 可以呼叫的能力。

對應到本專案：
- **工具**：`parse()`、`validate()`、`embed()`、`upsert_all()` 都可以成為工具
- **狀態**：`part_number`、`validation_result`、`numeric_part_id`、目前執行到哪一步
- **LLM**：在自動化工作流中，LLM 負責的是「判斷」（驗證結果夠好嗎？要重試還是送審？），而非執行

### 2.2 Workflow vs Agent

兩者的差別在於**誰決定下一步**：

| | Workflow | Agent |
| --- | --- | --- |
| 控制流 | 程式碼預先定義（DAG） | LLM 動態決定 |
| 適合情境 | 步驟固定、順序可預期 | 步驟不確定、需要推理 |
| 可預測性 | 高 | 低 |
| 本專案建議 | 主流程用 Workflow | 驗證失敗時的「判斷」可用 Agent |

**結論：不要把所有事情都交給 LLM 決定。** 本專案的 import 流程步驟固定，應該用 Workflow；只有「這份文件信心不足，要補充哪些欄位」這類需要推理的判斷才值得引入 LLM agent。

### 2.3 狀態機（State Machine）

Workflow 的底層是狀態機：

```
[PENDING] → [PARSING] → [VALIDATING] → [UPLOADING] → [EMBEDDING] → [UPSERTING] → [DONE]
                                ↓                                          ↓
                           [REVIEW_QUEUE]                            [FAILED]
```

每個狀態對應一個節點（node），節點之間的連線是邊（edge），邊可以帶條件（conditional edge）。

---

## 三、LangGraph 入門

LangGraph 是 LangChain 團隊出的 workflow 框架，核心概念：

- **State**：一個 dict 或 dataclass，在所有節點之間共享
- **Node**：一個 Python 函式，接收 state，回傳更新後的部分 state
- **Edge**：節點之間的連線，可以是固定的，也可以依條件分流
- **Graph**：把 nodes 和 edges 組裝起來，形成可執行的 workflow
- **Checkpoint**：可選的持久化層，讓 workflow 從任一節點繼續執行

### 安裝

```bash
pip install langgraph langchain-anthropic
```

### 最小範例

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END

class State(TypedDict):
    x: int
    result: str

def double(state: State) -> dict:
    return {"x": state["x"] * 2}

def to_string(state: State) -> dict:
    return {"result": f"答案是 {state['x']}"}

graph = StateGraph(State)
graph.add_node("double", double)
graph.add_node("to_string", to_string)
graph.set_entry_point("double")
graph.add_edge("double", "to_string")
graph.add_edge("to_string", END)

app = graph.compile()
print(app.invoke({"x": 5, "result": ""}))
# {'x': 10, 'result': '答案是 10'}
```

---

## 四、把 Import Pipeline 改成 LangGraph Workflow

### 4.1 定義 State

State 要包含整個 workflow 執行過程中需要傳遞的資訊：

```python
from typing import TypedDict, Any
from pathlib import Path

class ImportState(TypedDict):
    # 輸入
    pdf_path: str
    parser_module: Any          # 傳入 parser module

    # 各階段產出
    parsed: dict                # normalize_parsed() 的結果
    validation_result: dict     # ValidationResult 的序列化
    numeric_part_id: int | None
    embeddings: Any             # EmbeddingsBundle

    # 控制流
    status: str                 # pending / validating / uploading / embedding / done / failed / review
    error_message: str | None
    retry_count: int
```

### 4.2 定義節點

每個節點是一個純函式，只更新它負責的 state 欄位：

```python
from pathlib import Path
from datasheet_parser.normalizer import normalize_parsed
from db.validator import validate_parsed
from db.embeddings import EmbeddingsBundle, embed
from db.text_representations import to_embed_text
from db.upserts import upsert_parts, upsert_all
from db.minio_client import build_minio_client, upload_charts
import psycopg2, os

def node_parse(state: ImportState) -> dict:
    """解析 PDF + normalize"""
    pdf_path = Path(state["pdf_path"])
    parser   = state["parser_module"]
    parsed   = normalize_parsed(parser.parse(str(pdf_path)))
    return {"parsed": parsed, "status": "parsed"}


def node_validate(state: ImportState) -> dict:
    """驗證解析結果，產出 ValidationResult"""
    result = validate_parsed(state["parsed"])
    return {
        "validation_result": {
            "valid":            result.valid,
            "confidence":       result.confidence,
            "review_required":  result.review_required,
            "error_count":      len(result.errors),
            "warning_count":    len(result.warnings),
            "summary":          result.summary(),
        },
        "status": "validated",
    }


def node_upsert_parts(state: ImportState) -> dict:
    """upsert_parts，取得 numeric_part_id"""
    parts = state["parsed"]["tables"]["parts"]
    conn  = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn:
            with conn.cursor() as cur:
                numeric_part_id = upsert_parts(cur, parts)
    finally:
        conn.close()
    return {"numeric_part_id": numeric_part_id, "status": "parts_upserted"}


def node_upload_charts(state: ImportState) -> dict:
    """上傳圖表到 MinIO"""
    parser      = state["parser_module"]
    pdf_path    = state["pdf_path"]
    part_number = state["parsed"]["tables"]["parts"][0]["part_number"]
    part_id     = state["numeric_part_id"]

    charts_full = parser.parse_typical_charts(pdf_path, part_number)
    for row in charts_full:
        row["part_id"] = part_id

    client = build_minio_client(
        os.environ.get("MINIO_ENDPOINT", "localhost:9000"),
        os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
    )
    upload_charts(client, os.environ.get("MINIO_BUCKET", "ds-typical-characteristics"), charts_full)
    return {"status": "charts_uploaded"}


def node_embed(state: ImportState) -> dict:
    """產生所有 embedding"""
    tables = state["parsed"]["tables"]
    part_id = state["numeric_part_id"]

    # inject part_id（必須在 embed 前完成）
    for tname in ("max_ratings", "thermal_characteristics",
                  "electrical_characteristics", "typical_charts"):
        for row in tables[tname]:
            row["part_id"] = part_id

    footnotes = state["parsed"]["footnotes"]
    embeddings = EmbeddingsBundle(
        max_ratings=embed([to_embed_text(r, "max_ratings")                for r in tables["max_ratings"]]),
        thermal    =embed([to_embed_text(r, "thermal_characteristics")    for r in tables["thermal_characteristics"]]),
        electrical =embed([to_embed_text(r, "electrical_characteristics") for r in tables["electrical_characteristics"]]),
        charts     =embed([to_embed_text(r, "typical_charts")             for r in tables["typical_charts"]]),
        footnotes  =embed([to_embed_text({"marker": m, "text": t}, "footnotes") for m, t in footnotes.items()]),
    )
    return {"embeddings": embeddings, "status": "embedded"}


def node_upsert_all(state: ImportState) -> dict:
    """將子表全部寫入 PostgreSQL"""
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        upsert_all(conn, state["parsed"], state["embeddings"], state["numeric_part_id"])
    finally:
        conn.close()
    return {"status": "done"}


def node_review_queue(state: ImportState) -> dict:
    """低信心文件：寫入 review queue（此處示意為 print，實際可寫入 DB 或 Slack）"""
    vr = state["validation_result"]
    print(f"[REVIEW QUEUE] {state['pdf_path']}")
    print(f"  confidence={vr['confidence']:.2f}  warnings={vr['warning_count']}")
    print(f"  {vr['summary']}")
    return {"status": "review_queued"}


def node_failed(state: ImportState) -> dict:
    """錯誤終止節點：印出錯誤摘要"""
    vr = state.get("validation_result", {})
    print(f"[FAILED] {state['pdf_path']}")
    if vr:
        print(vr.get("summary", ""))
    return {"status": "failed"}
```

### 4.3 定義條件邊（Conditional Edges）

```python
def route_after_validate(state: ImportState) -> str:
    """validate 之後的路由：
      - 有 errors → 'failed'
      - review_required（低信心但無錯誤）→ 'review_queue'
      - 正常 → 'upsert_parts'
    """
    vr = state["validation_result"]
    if vr["error_count"] > 0:
        return "failed"
    if vr["review_required"]:
        return "review_queue"
    return "upsert_parts"
```

### 4.4 組裝 Graph

```python
from langgraph.graph import StateGraph, END

def build_import_graph():
    graph = StateGraph(ImportState)

    graph.add_node("parse",         node_parse)
    graph.add_node("validate",      node_validate)
    graph.add_node("upsert_parts",  node_upsert_parts)
    graph.add_node("upload_charts", node_upload_charts)
    graph.add_node("embed",         node_embed)
    graph.add_node("upsert_all",    node_upsert_all)
    graph.add_node("review_queue",  node_review_queue)
    graph.add_node("failed",        node_failed)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "validate")

    # 驗證後分流
    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "upsert_parts":  "upsert_parts",
            "review_queue":  "review_queue",
            "failed":        "failed",
        }
    )

    graph.add_edge("upsert_parts",  "upload_charts")
    graph.add_edge("upload_charts", "embed")
    graph.add_edge("embed",         "upsert_all")
    graph.add_edge("upsert_all",    END)
    graph.add_edge("review_queue",  END)
    graph.add_edge("failed",        END)

    return graph.compile()
```

### 4.5 執行

```python
import importlib, os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv("db/.env")

app = build_import_graph()
result = app.invoke({
    "pdf_path":      r"E:\pdfs\VSP007N06MS-G.pdf",
    "parser_module": importlib.import_module("datasheet_parser.vdsemi_parser"),
    "parsed":        {},
    "validation_result": {},
    "numeric_part_id":   None,
    "embeddings":        None,
    "status":            "pending",
    "error_message":     None,
    "retry_count":       0,
})
print(f"\nFinal status: {result['status']}")
```

---

## 五、加入自動重試（Autonomous Retry）

「自我修正」的核心是：**失敗後，不是直接放棄，而是先嘗試修正，超過次數才送人工審核。**

```python
MAX_RETRY = 2

def route_after_validate(state: ImportState) -> str:
    vr = state["validation_result"]

    if vr["error_count"] > 0:
        # 有 errors：嘗試重試
        if state["retry_count"] < MAX_RETRY:
            return "retry_parse"   # 回到 parse 重試
        return "failed"            # 超過次數，放棄

    if vr["review_required"]:
        return "review_queue"

    return "upsert_parts"


def node_retry_parse(state: ImportState) -> dict:
    """重試前記錄原因，retry_count +1"""
    vr = state["validation_result"]
    print(f"[RETRY {state['retry_count'] + 1}/{MAX_RETRY}] "
          f"confidence={vr['confidence']:.2f} errors={vr['error_count']}")
    # 實際可在這裡調整 parser 參數，例如換不同的 anchor 策略
    return {"retry_count": state["retry_count"] + 1, "status": "retrying"}


# 在 graph 中加入：
graph.add_node("retry_parse", node_retry_parse)
graph.add_edge("retry_parse", "parse")   # 回到 parse 重跑
```

整體重試流程：

```
parse → validate
              ↓ error, retry_count < MAX_RETRY
         retry_parse → parse（重新開始）
              ↓ error, retry_count >= MAX_RETRY
           failed
              ↓ review_required
         review_queue
              ↓ valid
         upsert_parts → ... → done
```

**關鍵限制：** retry 必須有上限。`MAX_RETRY = 2` 是合理起點，超過就送人工，不能無限循環。

---

## 六、加入 Checkpoint（從中斷點繼續）

LangGraph 的 Checkpoint 讓 workflow 可以持久化每個節點的狀態。如果 `upload_charts` 在第 37 份文件失敗，下次重跑可以從那份文件的 `upload_charts` 繼續，不必從頭 parse。

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# 使用 SQLite 儲存 checkpoint（也可換成 PostgreSQL）
checkpointer = SqliteSaver.from_conn_string("import_checkpoints.db")
app = build_import_graph().compile(checkpointer=checkpointer)

# 每次執行需要一個唯一的 thread_id（用 PDF 檔名即可）
config = {"configurable": {"thread_id": "VSP007N06MS-G"}}

result = app.invoke(initial_state, config=config)
```

如果中途失敗，下次執行同一個 `thread_id`，LangGraph 會從最後成功的節點繼續，而不是從頭開始。

---

## 七、Multi-Agent：加入 Reviewer Agent

當文件進入 `review_queue`，可以讓一個 LLM agent 先做初步審核，自動填補信心不足的欄位，再決定是否需要人工介入。

```python
from anthropic import Anthropic

client = Anthropic()

def reviewer_agent(state: ImportState) -> dict:
    """
    LLM agent 審核低信心文件。
    工具：get_field_value、suggest_correction、escalate_to_human
    """
    vr      = state["validation_result"]
    parsed  = state["parsed"]

    # 把驗證摘要和部分原始資料送給 LLM
    prompt = f"""
你是一個半導體 datasheet 審核專家。

以下是一份驗證結果（confidence={vr['confidence']:.2f}）：
{vr['summary']}

請判斷：
1. 這些 warning 是可接受的（parser 已盡力），還是代表抽取有誤？
2. 如果可接受，回覆 APPROVE。
3. 如果有疑問，列出你認為需要人工確認的欄位，回覆 ESCALATE: <原因>。
"""
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    decision = response.content[0].text.strip()

    if decision.startswith("APPROVE"):
        print(f"[REVIEWER] 自動通過：{decision}")
        return {"status": "approved_by_agent"}
    else:
        print(f"[REVIEWER] 送人工審核：{decision}")
        return {"status": "escalated_to_human"}


# 在 graph 中 review_queue 之後插入 reviewer_agent
graph.add_node("reviewer_agent", reviewer_agent)
graph.add_edge("review_queue",   "reviewer_agent")

def route_after_review(state: ImportState) -> str:
    if state["status"] == "approved_by_agent":
        return "upsert_parts"   # 審核通過，繼續入庫
    return END                   # 人工審核，流程暫停

graph.add_conditional_edges("reviewer_agent", route_after_review,
                             {"upsert_parts": "upsert_parts", END: END})
```

---

## 八、完整狀態圖總覽

```
[parse]
   │
[validate]
   ├─ errors + retry_count < MAX_RETRY ──► [retry_parse] ──► [parse]
   ├─ errors + retry_count >= MAX_RETRY ──► [failed] ──► END
   ├─ review_required ──► [review_queue] ──► [reviewer_agent]
   │                                              ├─ approved ──► [upsert_parts]
   │                                              └─ escalated ──► END（等人工）
   └─ valid ──────────────────────────────► [upsert_parts]
                                                │
                                           [upload_charts]
                                                │
                                           [embed]
                                                │
                                           [upsert_all]
                                                │
                                              END
```

---

## 九、與 Phase 7 的連接點

Phase 8 的 workflow 是 Phase 7 API 的理想後端：

```
POST /import  →  建立 ImportTask（DB）
                  └─► 放入 task queue（Celery / ARQ）
                          └─► worker 執行 LangGraph workflow
                                  └─► 狀態更新回 DB（PENDING/RUNNING/DONE/FAILED）

GET /tasks/{id}  →  回傳目前狀態（從 DB 或 checkpoint 查）
```

這樣每份文件的處理狀態都可以 API 查詢，長任務不阻塞主請求，workflow 失敗可以重試，完全符合 Phase 7 的驗收標準。

---

## 十、學習建議與實作順序

**不要一開始就追求 multi-agent。** 建議照這個順序：

1. **先把現有 pipeline 改成 LangGraph graph**（不加 retry、不加 agent）
   - 目標：理解 State + Node + Edge 的運作方式
   - 驗收：`app.invoke()` 可以跑通，狀態在節點間正確傳遞

2. **加入 conditional edge 做驗證分流**
   - 目標：低信心文件進 review_queue，有 errors 的文件進 failed
   - 驗收：三條路各自可以觸發

3. **加入 retry loop**
   - 目標：有錯誤時重試，超過次數才放棄
   - 驗收：retry_count 正確遞增，MAX_RETRY 後確實停止

4. **加入 checkpoint**
   - 目標：中斷後可以從上次成功的節點繼續
   - 驗收：手動中斷後重跑，確認節點不重複執行

5. **加入 reviewer agent**
   - 目標：LLM 對低信心文件做初步判斷
   - 驗收：APPROVE 的文件正常入庫，ESCALATE 的文件停在人工審核狀態

---

## 常見誤區（對應本專案）

| 誤區 | 在本專案的對應風險 |
| --- | --- |
| 把 LLM 決定所有步驟 | Parser 和 validator 是 deterministic 的，不需要 LLM 決定是否要執行 |
| 沒有 retry 上限 | 若 PDF 本身有問題，無限 retry 只會浪費時間和費用 |
| State 太大 | 把整個 PDF bytes 放進 State 會讓 checkpoint 很慢；應存路徑而非內容 |
| 每個節點都是 LLM call | 只有「判斷」需要 LLM，parse / embed / upsert 是確定性操作，不需要 |
| 忽略失敗原因紀錄 | workflow 結束時，`status + error_message` 必須寫回 DB，否則失敗原因無法追蹤 |
