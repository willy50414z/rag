# Text Layout Handling

Use this reference during ppg-explore Step 1-2 when a text PDF has extractable text but the layout is structurally messy. The goal is to understand layout risks before committing to a parser design — not to produce a normalized intermediate file.

## What this reference covers

- reading order repair signals
- line merge / paragraph reconstruction heuristics
- multi-column contamination detection
- header/footer detection
- section boundary hints

## Core rule

Prefer conservative observation over aggressive repair. When two interpretations are plausible, report the ambiguity in the explore conversation rather than silently picking one.

---

## 1. Reading order issues

Typical symptoms in text PDF extraction:

- extracted text jumps between columns
- a sentence is split by unrelated text
- labels and values appear far apart in output order
- footer text appears inside paragraph flow

When these appear during explore, note them — they affect whether a table anchor can reliably locate its target, and whether forward-fill logic will work across rows.

Useful heuristics for diagnosis:

- top-to-bottom ordering is usually safer than raw object order
- within the same line band, left-to-right is usually safer
- large horizontal gaps often indicate separate columns or label/value separation
- repeated y-position patterns across pages often indicate headers or footers

## 2. Line merge and paragraph reconstruction

These heuristics help decide whether adjacent text lines belong together (relevant when table cells contain wrapped text that could confuse row boundary detection):

Good merge signals:
- similar left alignment
- small vertical gap
- same column region
- previous line does not look complete
- next line starts like a continuation, not a new label or heading

Do not merge when:
- the next line is in another column
- the next line is clearly a table row
- the next line starts a new heading or label
- font/style shift strongly suggests a new section

## 3. Multi-column detection

Multi-column text is a major risk for parser correctness — it can make a table appear where none exists, or split a real table across unrelated regions.

Detection hints:
- persistent two-band or three-band x-coordinate clusters
- paragraphs with abrupt topic shifts mid-sentence
- similar vertical positions repeated with far-separated x positions

When detected, flag it in the explore analysis. The parser may need page-region filtering before running table extraction.

## 4. Header and footer detection

Repeated headers/footers are not harmless noise — if left in body text, they can be misidentified as table rows or section headers.

Strong header/footer signals:
- repeated text across many pages
- repeated page number patterns
- consistently near top or bottom margin
- visually separated from body text

During explore, note their content and position. During apply, the parser should filter them before table extraction.

## 5. Section boundary hints

These signals help the parser decide where one table section ends and another begins:

- bold or larger-font text spanning full page width
- rows with significantly fewer columns than the table
- blank rows followed by a standalone label row
- text matching known section header patterns (e.g. "Static Electrical Characteristics")

Record suspected section boundaries during explore so they can inform `section_split.patterns` in the spec.

## 6. Red flags

Stop and report during explore when:
- column boundaries remain unstable
- body text and tables are interleaved unpredictably
- header/footer detection would require document-specific overfitting
- the same region alternates between paragraph-like and table-like output

When blocked, keep ambiguity visible and call it out in the explore conversation — do not force a parser design on an unstable foundation.
