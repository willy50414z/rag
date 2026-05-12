## Context

`db/inserter.py:run()` 目前是一個約 90 行的 god function，混合 5 種職責：parser discovery、PDF 解析呼叫、SentenceTransformer embedding、MinIO upload、PostgreSQL upsert。同時，parser 的存放位置已從 `pdf-parser-generator/<stem>/parser.py`（按 PDF 檔名）遷移到 `datasheet_parser/<vendor>_parser.py`（按 vendor），原本以 stem 動態載入的 convention 與實際檔案配置脫節。

使用者已在 explore 階段確認三個重要決策：
- parser 以 **module 物件** 形式傳入（非 string key、非 Protocol）。
- embedding 屬於 **獨立 layer**，不歸 DB 也不歸 pipeline orchestrator。
- 新的 `import_pdf` 入口住在 **獨立的 pipeline module**（不放在 `db/` 之下），讓 `db/` 真的只剩 DB 相關職責。

## Goals / Non-Goals

**Goals:**
- 拆解 `run()`，使每個 module 只承擔單一職責。
- 提供可程式呼叫的 `import_pdf(pdf_path, parser)` entry point，使 caller 可以自行決定要用哪個 parser。
- `db/` 之下只放與 PostgreSQL / MinIO / embedding 相關的 I/O layer；orchestration 不再住在 `db/`。
- 保留現有 CLI（`python db/inserter.py <pdf_path>`）的呼叫方式，但內部只是薄 wrapper。
- 維持資料寫入語意不變：同一個 PG transaction 內完成 6 張表的 upsert；MinIO 上傳在 DB 寫入之前發生。

**Non-Goals:**
- 不更動 `datasheet_parser/vdsemi_parser.py` 內部解析邏輯。
- 不更動 PostgreSQL schema 或 MinIO bucket / key 命名。
- 不引入 dependency injection container、Protocol class、ABC，或其他重型抽象。
- 不處理 partial re-insert（單獨重灌某張表）的需求 — 留待未來真有需求再做。
- 不解決「MinIO 成功 → DB 失敗 → MinIO orphan」的 cleanup 問題（保留現有語意）。

## Decisions

### Decision 1: parser 以 module 物件形式傳入
**選擇**：`import_pdf(pdf_path: Path, parser)`，`parser` 為 module 物件，需具備 `parse(pdf_path: str) -> dict` 與 `parse_typical_charts(pdf_path: str, part_id: str) -> list[dict]` 兩個 callable。

**理由**：現有 parser 是 ad-hoc convention（一個 module 提供 `parse()` 與 `parse_typical_charts()` 兩個 free function），尚未複雜到需要正式抽 Protocol。Module 物件對 caller 最直白、IDE 友善、不需要 registry。

**替代方案**：
- string key + registry → 增加 indirection，CLI 才需要這層 mapping，pipeline layer 不該背。
- Protocol class → 過度工程，目前只有一個 vendor parser。

**對應結構**：CLI 層 (`db/inserter.py`) 自行做 vendor name → module 的 lookup（一個小的 dict 或 import-by-name），pipeline 層只看 module。

### Decision 2: embedding 為獨立 layer
**選擇**：新增 `db/embeddings.py`，提供 `EmbeddingGenerator` 物件（封裝 SentenceTransformer），暴露 `encode_records(parsed: dict) -> EmbeddingsBundle` API。pipeline 呼叫此 layer 後，將結果作為參數傳入 DB sink。

**理由**：
- SentenceTransformer 載入成本高 (~1s+)，未來可能需要重用 instance 處理多個 PDF。
- embedding model 可能換成 OpenAI API 或其他 provider；與 SQL 寫入綁死會綁死換 provider 的彈性。
- DB layer 不應依賴 ML stack（測試 DB 寫入不該需要載入模型）。

**替代方案**：
- 把 embedding 塞進 `db/upserts.py` 內 → DB layer 變重，測試難。
- 由 caller 自行算 embedding → caller 要懂太多細節（哪些 column 要 embed、用什麼 text representation）。

**API 草案**：
```python
class EmbeddingGenerator:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"): ...
    def encode_bundle(self, parsed: dict, footnotes: dict) -> EmbeddingsBundle: ...

@dataclass
class EmbeddingsBundle:
    max_ratings:  list[list[float]]
    thermal:      list[list[float]]
    electrical:   list[list[float]]
    charts:       list[list[float]]
    footnotes:    list[list[float]]
```
text representation function（`_text_max_rating`、`_text_thermal` 等）跟著搬到 `db/embeddings.py`，因為它們專屬於決定「要 embed 什麼字串」。

### Decision 3: `import_pdf` 住在 repo-root 的 `import_pipeline.py`
**選擇**：新增 `import_pipeline.py`（位於 repo root，與 `db/`、`datasheet_parser/` 同層），exports `import_pdf(pdf_path, parser)`。

**理由**：
- `db/` 應該只剩 DB / 外部儲存相關 I/O；orchestration 跨越 parser、embedding、MinIO、DB 多層，不屬於任何單一 layer。
- 放在 repo root 與 `db/`、`datasheet_parser/` 同層，反映它「協調多個 layer」的角色。
- 命名為 `import_pipeline.py` 而非 `pipeline.py`，避免日後其他 pipeline（例如 query / re-embed）混淆。

**替代方案**：
- 留在 `db/inserter.py` → 違背「DB 操作分開」的初衷。
- 建立 `pipelines/` 資料夾 → 目前只有一個 pipeline，過度組織。

### Decision 4: DB sink 為粗顆粒度的單一 transaction
**選擇**：`db/upserts.py` 暴露 `upsert_all(conn, parsed, embeddings) -> None`（內部開 cursor、執行 6 個 `upsert_*`、由 caller 控制 connection lifecycle 與 commit/rollback 透過 `with conn:` context）。

**理由**：目前唯一的 caller 是 `import_pdf`，需要的就是「6 張表一個 transaction」。細顆粒度（`session.upsert_parts()`、`session.upsert_max_ratings()`）對目前需求是 over-engineering。

**替代方案**：保留個別 `upsert_*` function 為 module-level public（給未來 partial re-insert 用） → 不主動暴露，但保留為 public function，需要時直接 import。

### Decision 5: MinIO 與 DB 的執行順序維持原狀
**選擇**：`import_pdf` 內部依序為：parse → embed → MinIO upload → DB upsert。MinIO 失敗則中止，不寫 DB；DB 失敗則 MinIO 留下 orphan chart。

**理由**：保留現有語意以縮小變更範圍。orphan cleanup 是獨立議題，不在本次重構 scope。

### Decision 6: CLI 層的 vendor → parser mapping
**選擇**：在 `db/inserter.py` 內維護一個小的 dict：
```python
_VENDOR_PARSERS = {
    "vdsemi": "datasheet_parser.vdsemi_parser",
}
```
CLI 接收 `<pdf_path>` 與 optional `<vendor>` 參數；若未指定 vendor，根據 part_id prefix 推測（例如 `VSP*` → vdsemi）。找不到 mapping 就 raise。

**理由**：實際 vendor 數量會在未來成長；用 dict 比 if/else 鏈乾淨。inference rule 與 dict 都集中在 CLI 層，pipeline 不知道「vendor」這個概念。

## Risks / Trade-offs

- **[Risk] CLI 行為變化可能影響既有腳本** → Mitigation：保留 `python db/inserter.py <pdf_path>` 的呼叫方式不變；vendor 推測規則必須涵蓋現有所有 PDF（VSP007N06MS-G、VS11240GTH、VS1602GTH 全部 vdsemi）。
- **[Risk] embedding generation 與 DB upsert 之間的 list 順序錯位** → Mitigation：在 `EmbeddingsBundle` 與 `parsed` dict 之間用同一個 dataclass / typed dict 為 schema，避免 caller 自行管理 index。增加一個輕量 assertion（list 長度相等）。
- **[Risk] 重構過程意外改變 upsert 行為** → Mitigation：先把現有 `upsert_*` function 的 SQL 與資料轉換邏輯一字不變地搬到新 module；之後再做純 refactor。視需要對 VSP007N06MS-G 做一次 end-to-end 對照測試（重跑前後 DB 內容比對）。
- **[Risk] orphan MinIO chart 的問題未解決** → Mitigation：本次明列為 Non-Goal，未來獨立 change 處理；可先在 README 或 module docstring 註記此限制。
- **[Trade-off] `import_pipeline.py` 放 repo root 增加 root 目錄檔案數** → 接受，比起塞進 `db/` 違背職責劃分，這是較小代價。
