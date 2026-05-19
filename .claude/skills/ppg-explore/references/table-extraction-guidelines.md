# Table Extraction Guidelines

Use this reference during ppg-explore Step 3A (結構面分析) when a page contains visually table-like content that needs to be extracted reliably. The goal is to understand extraction risks so the parser design accounts for them — not to produce an intermediate table artifact.

## Core rule

During explore, identify which failure modes apply to each table. Every failure mode you spot here becomes a handling rule in the spec and a test case in the parser.

---

## 1. When to classify content as a table

Strong table signals:
- repeated row alignment
- consistent column bands across multiple rows
- header-like first row
- numeric values arranged in vertical bands
- parameter/value/unit/min/max style layout

Weak signals (treat as prose, not table):
- one isolated label-value pair
- a bullet list that happens to align visually
- prose with accidental spacing

---

## 2. Common table failure modes

### Merged cells

Symptoms:
- one label visually spans several columns (e.g. section header row)
- subheaders exist beneath a broader header
- cell text is empty but clearly belongs to the cell above

Impact on parser: forward-fill logic is needed. Spec must mark which columns inherit from above.

### Cross-page tables

Symptoms:
- header on page N, continuation rows on page N+1
- repeated header row with continued values
- "continued" or "(cont.)" text near table

Impact on parser: anchor must search across multiple pages. Row count expectations must account for split. Evidence trace must reflect correct source page per row.

### Wrapped cell text

Symptoms:
- long cell values appear on multiple lines
- row height varies significantly
- pdfplumber splits a logical row into two extracted rows

Impact on parser: row merging logic needed before field extraction. Anchor-based row detection may need line-span tolerance.

### Borderless tables

Symptoms:
- no visible grid lines
- alignment alone implies columns
- pdfplumber may fail to detect table at all, or split it incorrectly

Impact on parser: may need to fall back to explicit column x-range extraction rather than relying on pdfplumber's built-in table detection.

### Repeated header rows

Symptoms:
- the same header row appears on multiple pages
- sometimes mid-table on the same page (less common)

Impact on parser: must distinguish real header from repeated header. Repeated headers should be filtered, not treated as data rows.

---

## 3. Questions to answer during explore Step 3A

For each table, answer:

- Does this table have merged cells? Which columns?
- Does it span multiple pages? If so, how many?
- Do any cells contain wrapped text that could break row detection?
- Are there visible grid lines, or is alignment the only structure?
- Does the header row repeat on continuation pages?
- Are there rows that look like data but are actually section headers?

---

## 4. Chunking implications

Tables degrade retrieval when split carelessly. Flag these risks during explore:

- a table should stay intact as one chunkable unit
- summary rows should not be detached from their table
- cross-page tables may need special handling
- footnotes attached to specific rows should travel with those rows
