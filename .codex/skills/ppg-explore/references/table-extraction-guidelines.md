# Table Extraction Guidelines

Use this reference when a text PDF contains visually table-like content and the workflow must preserve it as a table artifact rather than flattening it into normal text.

The goal is not to force every table into a perfect grid. The goal is to preserve as much trustworthy row/column structure as the backend supports while keeping uncertainty visible.

## Core rule

Treat table extraction as a distinct parsing task.

Do not:

- flatten a table into ordinary paragraph text
- convert rows into final key-value fields during raw extraction
- guess merged or missing cells without evidence

## 1. When to classify content as a table

Strong table signals:

- repeated row alignment
- consistent column bands across multiple rows
- header-like first row
- numeric values arranged in vertical bands
- parameter/value/unit/min/max style layout

Weak signals:

- one isolated label-value pair
- a bullet list that happens to align visually
- prose with accidental spacing

If a block is table-like but uncertain:

- preserve it as a table candidate
- mark the limitation in `note`
- avoid premature conversion into paragraph text

## 2. Output formats

Prefer one of these two formats:

- `grid`
- `raw-text`

### Use `grid` when

- row boundaries are reliable
- column alignment is stable
- cell segmentation is defensible

### Use `raw-text` when

- OCR-like corruption exists even in a text PDF extract
- merged cells make grid reconstruction speculative
- line wrapping destroys row boundaries
- the backend can see table content but not trustworthy cell boundaries

## 3. Grid expectations

For `grid` output:

- preserve row order
- preserve column order
- keep repeated headers or repeated values if present
- represent empty visible cells as `""`
- do not deduplicate

If the first row is plausibly a header, keep it as the first row.

Do not create artificial header names.

## 4. Raw-text expectations

For `raw-text` output:

- preserve the most faithful linear representation available
- include line breaks when they help preserve row boundaries
- add a `note` explaining why grid extraction is unsafe

Example reasons:

- merged cell structure ambiguous
- cross-page continuation unresolved
- alignment too weak for stable grid

## 5. Common table failure modes

### Merged cells

Symptoms:

- one label visually spans several columns
- subheaders exist beneath a broader header

Recommended handling:

- if backend cannot represent hierarchy safely, use `raw-text`
- do not invent duplicate header names to fill gaps

### Cross-page tables

Symptoms:

- header on page N, continuation rows on page N+1
- repeated header with continued values

Recommended handling:

- preserve page-local table artifacts first
- only merge across pages if continuation is clear
- if merged, keep source page traceability in notes or metadata

### Wrapped cell text

Symptoms:

- long cell values appear on multiple lines
- row height varies significantly

Recommended handling:

- merge wrapped lines only when row membership is clear
- if not clear, degrade to `raw-text`

### Borderless tables

Symptoms:

- no visible grid lines
- alignment alone implies columns

Recommended handling:

- rely on repeated x-band patterns
- prefer conservative extraction
- if alignment confidence is weak, use `raw-text`

## 6. Relationship to normalized.json

In `normalized.json`, tables should remain distinct from paragraphs.

Recommended behaviors:

- keep `tables` as a dedicated collection
- allow sections to reference nearby tables
- allow candidate fields to cite table evidence
- do not silently absorb table rows into paragraph sections

## 7. Relationship to field extraction

Later stages may derive fields from tables, but raw/normalized extraction should not collapse the distinction.

Good downstream pattern:

- raw extraction preserves table structure
- normalized artifact marks table context
- field review chooses whether a field comes from table evidence
- parser uses table-aware logic when required

Bad downstream pattern:

- flatten table text
- lose row/column boundaries
- guess final values from a broken linear string

## 8. Review checklist

When inspecting table extraction, ask:

- Is this really a table or just aligned prose?
- Are row boundaries trustworthy?
- Are column boundaries trustworthy?
- Would forcing grid lose information?
- Is `raw-text` the more honest representation?
- Will later field extraction need row/column structure here?

## 9. Chunking implications

Tables often degrade retrieval when split carelessly.

Call out these risks in review:

- a table should stay intact as one chunkable unit
- summary rows should not be detached from their table
- cross-page tables may need special handling
- table notes and footnotes may belong with the table

## 10. Red flags

Stop and report instead of overfitting when:

- table boundaries are unclear
- grid extraction requires guessing many cells
- continuation across pages is doubtful
- the backend alternates between paragraph-like and table-like output for the same region

When blocked, prefer a truthful `raw-text` table artifact over a fragile fake grid.
