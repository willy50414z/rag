---
name: planka-debug
description: 透過 Planka REST API 查詢卡片詳情、留言、操作紀錄與附件，用於 debug agentic-research 框架執行錯誤。當需要查看 Planka 卡片的執行歷程、錯誤訊息或 spec 附件時使用此 skill。
---

# Planka Debug Skill

用於直接透過 Planka HTTP API 查詢卡片狀態，協助 debug agentic-research 框架的執行錯誤。

## 前置條件

從 `.env` 取得以下變數：
- `PLANKA_API_URL`（通常是 `http://localhost:7204`）
- `PLANKA_TOKEN`（Bearer token）
- `DATABASE_URL`（PostgreSQL 連線字串，用於查 project spec）

## 從 URL 取得 card_id

Planka 卡片 URL 格式：`http://localhost:7204/cards/{card_id}`

card_id 直接從 URL 路徑取得。

## 常用 API 操作

### 1. 取得卡片基本資訊

```bash
curl -s -H "Authorization: Bearer {PLANKA_TOKEN}" \
  "{PLANKA_API_URL}/api/cards/{card_id}" | python -m json.tool
```

回傳：卡片名稱、描述（含 thread_id）、所在 list、建立時間、commentsTotal。

### 2. 查看所有留言（執行紀錄與錯誤）

```bash
curl -s -H "Authorization: Bearer {PLANKA_TOKEN}" \
  "{PLANKA_API_URL}/api/cards/{card_id}/comments" | python -m json.tool
```

留言按時間排序，框架會將每個 node 的執行狀態與錯誤訊息發到這裡。

**關鍵留言格式：**
- `[SPEC-REVIEW] START / ROUND N / PASS` — spec 審查流程
- `[PLAN] Loop N` — 研究圖 plan node
- `[NODE ENTER/EXIT]` — 各節點進出記錄
- `**[ERROR] ... Failed**` — 錯誤訊息，含 exception 內容

### 3. 查看卡片操作歷程（移動紀錄）

```bash
curl -s -H "Authorization: Bearer {PLANKA_TOKEN}" \
  "{PLANKA_API_URL}/api/cards/{card_id}/actions" | python -m json.tool
```

回傳卡片在各 list（Planning / Spec Pending Review / Verify / Done / Failed）間的移動紀錄，可重建執行時間軸。

### 4. 列出附件清單

```bash
curl -s -H "Authorization: Bearer {PLANKA_TOKEN}" \
  "{PLANKA_API_URL}/api/cards/{card_id}" \
  | python -c "import sys,json; d=json.load(sys.stdin); [print(a.get('name'), a.get('id')) for a in d.get('included',{}).get('attachments',[])]"
```

### 5. 查看 DB 中的 project spec 結構

```python
import psycopg, json

conn = psycopg.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT id, plugin_name, config FROM projects WHERE id = %s", (project_id,))
row = cur.fetchone()
spec = (row[2] or {}).get("spec", {})
print("spec keys:", list(spec.keys()))
print("trading_scope:", spec.get("trading_scope"))
print("data:", spec.get("data"))
conn.close()
```

`project_id` 從卡片描述的 `thread_id: <project_id>` 取得。

## Debug 流程

1. **從 URL 取得 card_id**
2. **查留言** → 找最新的 `**[ERROR]**` 留言，取得 exception 類型與訊息
3. **查操作歷程** → 重建卡片經過哪些 list，確認是在哪個階段失敗
4. **根據錯誤定位程式碼**：
   - `KeyError: 'trading_scope'` → `config_generator.py` 或 spec 欄位問題
   - `KeyError: 'data'` → `backtest.py` 或 spec 欄位問題
   - `spec_fields.json not found` → synthesizer/refine prompt 未產出 JSON
5. **查 DB spec** → 確認 `trading_scope`、`data`、`execution` 欄位是否存在且有值

## 常見錯誤模式

| 錯誤訊息 | 根本原因 | 修復方向 |
|---------|---------|---------|
| `KeyError: 'trading_scope'` | spec 缺少結構化欄位，或 spec 審查未產出 `spec_fields.json` | 重新跑 spec review（卡片移回 Spec Pending Review） |
| `spec_fields.json not found` | synthesize/refine 輪 LLM 未寫出此檔案 | 檢查 prompt 是否包含 spec_fields.json 輸出要求 |
| `LLM call failed` | claude-cli / gemini-cli 未登入或 timeout | 確認 container 內 CLI 登入狀態 |
| `Spec review timed out` | spec_review_graph 超時（通常 > 10 分鐘） | 將卡片移回 Planning 再重新觸發 |
