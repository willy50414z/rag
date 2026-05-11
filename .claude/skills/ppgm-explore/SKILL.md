---
name: ppgm-explore
description: Use this skill whenever the user wants a parser-first PDF exploration workflow based on MinerU, Docling, or pdfplumber, especially for digital-text PDFs, layout-heavy PDFs, or table-heavy PDFs where downstream extraction quality matters. This skill generates parser-native artifacts plus a review document that preserves table structure, evidence traceability, and downstream parser design constraints.
---

# PDF Parser Generator MinerU Mode: Explore

This skill explores a PDF with a parser-first workflow and prepares trustworthy artifacts for downstream spec generation.

Use this skill when the user wants to:

- inspect a PDF with MinerU or Docling first
- compare parser-native output against the original layout
- prepare `source.md`, `source.json`, and `review.md` for later spec writing
- preserve table structure instead of flattening everything into simple key-value fields

Do not use this skill as the final extraction step. Its job is to produce reviewable evidence and structural observations, not the final parser contract.

## Scope

Best fit:

- digital-text PDFs
- text PDFs with non-trivial layout
- documents where tables, footnotes, headers, or multi-column reading order affect extraction quality

Use caution:

- hybrid PDFs
- scanned PDFs
- PDFs with weak text layers or severe OCR issues

If the PDF is not a good fit for MinerU or Docling, say so explicitly in `review.md`.

## Workflow

Input:

- a sample PDF path
- optional preferred backend: `pdfplumber`, `mineru`, `docling`, or `auto`

Output directory:

```text
pdf-parser-generator/{pdf_stem}/ppgm/
```

Required outputs:

- `parser_choice.md`
- `source.md`
- `source.json`
- `review.md`

Optional outputs when available:

- `source.lossless.json`
- `layout.json`
- `tables/`
- `images/`

## Step 1: Choose backend

判斷主要提取目標後再選擇 backend，順序如下：

**條件 A：digital-text PDF，且主要目標為結構化表格，且表格內無圖片嵌入**

1. `pdfplumber` — 直接從 PDF 座標提取欄位邊界與列結構，cell-level evidence 最完整；僅限 digital-text，對 scanned 或圖片嵌入表格無效
2. `MinerU` — pdfplumber 失敗、或文件同時有大量非表格內容需要全文理解時使用
3. `Docling` — 最終 fallback

**條件 B：其他情況（hybrid、scanned、圖片嵌入表格、複雜版面、需要全文理解）**

1. `MinerU`
2. `Docling`

決策規則：

- PDF 分類為 `digital-text` **且** 主要提取目標為表格 **且** 表格中未見圖片嵌入 → 優先使用 `pdfplumber`
- 其他情況 → 優先使用 `MinerU`
- 使用者明確指定 backend 時，忽略以上規則，直接採用指定值

Record the choice in `parser_choice.md` with:

- chosen backend
- reason for choosing it
- environment or tooling constraints
- fallback notes if the preferred backend failed

## Step 2: Classify document type

Classify the PDF as one of:

- `digital-text`
- `hybrid`
- `scanned`
- `uncertain`

State the classification in `review.md` and explain the evidence briefly.

## Step 3: Generate parser-native artifacts

Run the chosen backend and keep its artifacts as close to native output as practical.

Rules:

- do not prematurely normalize away parser evidence
- preserve page references, layout hints, and table-related structures
- keep any tool-native row or cell metadata if available

`source.md` should remain the parser-produced Markdown artifact.

`source.json` should remain the parser-produced machine-readable artifact or the closest faithful representation available from the backend.

## Step 4: Review with a table-first mindset

Create `review.md` as a human review artifact. It must not only judge text quality. It must explain whether the parser output is structurally useful for downstream deterministic extraction.

Always review these areas:

- markdown quality
- json quality
- reading order
- multi-column behavior
- header and footer behavior
- table fidelity
- evidence traceability

For table-heavy PDFs, table fidelity is a first-class review axis, not a side note.

## Table-first review rules

When the document contains tables, review them as source structures rather than as field containers.

For each important table, capture:

- table title or section context
- page number
- approximate table boundary or evidence reference
- visible column schema
- whether row boundaries are recoverable
- whether cell-level evidence is recoverable
- whether shared conditions, units, or footnotes are represented clearly

Do not summarize a table only as "the values are present". That is not enough for downstream parsing.

Specifically look for these failure modes:

- row/column collapse into prose
- symbol and parameter columns drifting apart
- merged condition cells losing row scope
- unit cells detached from numeric values
- repeated symbols across multiple rows becoming ambiguous
- footnote markers surviving without clear attachment targets

## Step 5: Write `review.md`

`review.md` should include these sections in order.

### 1. Document summary

Include:

- PDF path
- document type classification
- chosen backend
- overall suitability for parser-first exploration

### 2. Extraction quality summary

Brief bullets for:

- Markdown quality
- JSON quality
- Reading order
- Multi-column handling
- Header/footer handling
- Table fidelity
- Evidence traceability

### 3. Important table review

For each important table, include:

- section name or inferred table name
- source page
- whether the parser preserved the table as a table
- likely column schema
- major ambiguities
- whether it is usable for deterministic downstream parsing

### 4. Downstream modeling recommendation

This section is required when tables matter.

State clearly whether downstream spec generation should use:

- `field-first`
- `table-first with derived fields`
- `mixed`

Default recommendation for datasheets and parameter tables:

- `table-first with derived fields`

Explain why.

### 5. Open issues and parser risks

List unresolved ambiguities that the spec writer must explicitly account for.

Examples:

- shared test condition appears only once above several rows
- subscript and main symbol split across separate blocks
- footer text is interleaved into reading order
- parser preserves table text but not explicit cell boundaries

## Required interpretation guidance

When writing `review.md`, explicitly judge whether the downstream spec should preserve three layers:

1. canonical table representation
2. derived row-level records
3. promoted top-level fields

If a table is important and the parser artifacts support it even partially, recommend keeping the table as the source of truth.

## Output quality bar

Good output from this skill should make the next step straightforward:

- the spec writer should know which tables deserve first-class modeling
- the spec writer should know which values can safely become top-level fields
- the spec writer should know where evidence is weak

Bad output from this skill looks clean but leaves downstream ambiguity unresolved.

## Failure handling

If pdfplumber, MinerU, or Docling fails:

- record the failure in `parser_choice.md`
- keep any partial artifacts that are useful
- explain in `review.md` what is missing
- do not fabricate structure that the parser did not actually preserve

## Relationship to later steps

This skill prepares inputs for `ppgm-propose`.

It should leave enough evidence so the later spec can distinguish:

- source tables
- derived normalized records
- stable promoted fields

That distinction is mandatory for table-heavy documents.
