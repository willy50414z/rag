---
name: ppgm-propose
description: Use this skill whenever the user wants to generate `pdf_field_spec.md` from parser-first PDF exploration artifacts produced by MinerU or Docling. This skill is especially important for table-heavy PDFs because it turns parser-native artifacts into a table-first, evidence-linked extraction contract rather than flattening tables into lossy key-value fields.
---

# PDF Parser Generator MinerU Mode: Propose

This skill converts parser-first exploration artifacts into a precise `pdf_field_spec.md`.

Its core rule is:

- preserve tables as source structures
- derive normalized field records from tables
- promote only stable business-important values to top-level fields

Do not collapse important tables directly into plain KV descriptions unless the document truly only contains simple single-value fields.

## Inputs

Read artifacts from:

```text
pdf-parser-generator/{pdf_stem}/ppgm/
```

Required inputs:

- `source.md`
- `source.json`
- `review.md`

Optional supporting inputs:

- `parser_choice.md`
- `source.lossless.json`
- `layout.json`

If any required input is missing, stop and say which file is missing.

## Output

Write:

```text
pdf-parser-generator/{pdf_stem}/pdf_field_spec.md
```

The output is a semantic extraction contract for later deterministic parsing.

## Primary design rule

For table-heavy documents, the spec must use three explicit layers.

### Layer 1: Source structures

Model important tables as canonical source structures.

Each important table should define:

- table identity
- section context
- page or page range
- evidence location
- column schema
- row semantics
- notes about merged cells, shared conditions, or footnotes

### Layer 2: Derived normalized records

Model row-level or stat-level records derived from the source table.

Examples:

- one row becomes one normalized record
- one row with min/typ/max becomes multiple derived stat records
- one shared condition is expanded onto several derived records

Every derived record should be traceable back to source table evidence.

### Layer 3: Promoted top-level fields

Only promote values to top-level fields when they are:

- stable
- frequently queried
- semantically singular
- unlikely to lose meaning when detached from row context

Examples of good top-level promotions:

- product part number
- package type
- headline key specs shown in a dedicated summary area

Examples that usually should stay derived from tables:

- electrical characteristics tables
- ratings tables
- switching parameter tables
- any repeated symbol with multiple conditions

## Required `pdf_field_spec.md` structure

Use this structure.

```markdown
# Parser Spec: {pdf_filename}

## Document Metadata

- Source PDF: `...`
- Document Type: `digital-text | hybrid | scanned | uncertain`
- Backend: `MinerU | Docling`
- Generated At: `YYYY-MM-DD`
- Source Markdown: `pdf-parser-generator/{pdf_stem}/ppgm/source.md`
- Source JSON: `pdf-parser-generator/{pdf_stem}/ppgm/source.json`
- Review Artifact: `pdf-parser-generator/{pdf_stem}/ppgm/review.md`

## Extraction Quality Summary

- Markdown quality: ...
- JSON quality: ...
- Reading order: ...
- Multi-column handling: ...
- Header/footer handling: ...
- Table fidelity: ...
- Evidence risk: ...

## Extraction Model

- Modeling strategy: `field-first | table-first-with-derived-fields | mixed`
- Source of truth rule: `important tables remain canonical`
- Promotion rule: `only stable singular values become top-level fields`

## Top-level Fields

### {field_name}

- Description: ...
- Type: `string | number | object | string[] | number[]`
- Required: `yes | no`
- On missing: `error | null | needs_review`
- Strict extraction: `yes | no`
- Labels: ...
- Candidate priority: ...
- Rejection rules: ...
- Normalization rules: ...
- Example value: `...`
- Evidence requirements: `page | bbox | source_blocks | table_ref`
- Evidence notes: ...

## Canonical Tables

### {table_name}

- Description: ...
- Type: `canonical-table`
- Required: `yes | no`
- Section anchor: ...
- Page scope: ...
- Boundary hints: ...
- Column schema: `...`
- Row identity rule: ...
- Cell evidence expectation: ...
- Shared condition handling: ...
- Footnote handling: ...
- Example rows: ...
- Evidence requirements: `page | bbox | source_blocks | row_refs | cell_refs`
- Notes: ...

## Derived Records

### {record_family_name}

- Description: ...
- Source table: `{table_name}`
- Output grain: `row | stat-record | condition-expanded-record`
- Record schema: `...`
- Derivation rules: ...
- Missing-value policy: ...
- Condition propagation: ...
- Footnote propagation: ...
- Example records: ...
- Evidence requirements: `table_ref | row_ref | cell_ref`
- Notes: ...

## Chunking Considerations

- ...

## Known Ambiguities

- ...
```

## How to model tables

When the document includes meaningful parameter tables, create a `Canonical Tables` section for each important table.

Do not skip this section just because the values can be restated elsewhere.

For each canonical table, write enough detail that a later parser can:

- locate the table
- identify columns
- reconstruct rows
- attach conditions and units correctly
- propagate footnotes correctly

## How to model derived records

When a table contains stats such as `Min`, `Typ`, `Max`, or repeated symbols under different conditions, define a derived record family.

Typical derived record fields include:

- normalized symbol
- parameter
- condition
- stat
- value
- unit
- footnote refs

If a condition is shared across several rows, say how it propagates.

If a value cell is blank because the original table leaves that stat empty, preserve that distinction in the spec. Do not blur "missing in source" and "not attempted".

## How to model top-level fields

Top-level fields should be reserved for:

- document identity
- product identity
- dedicated summary boxes
- obvious single-value metadata

For datasheets, summary blocks such as headline `VDS`, `ID`, or package metadata can be top-level fields if they are visually isolated and semantically singular.

Do not promote a whole electrical table into dozens of disconnected top-level fields unless there is a strong downstream requirement and you also keep the canonical table and derived record definitions.

## Evidence rules

Every important extraction rule must remain evidence-linked.

Prefer explicit evidence requirements such as:

- page
- bbox
- source block ids
- table references
- row references
- cell references

If parser artifacts do not expose row or cell ids directly, state the fallback strategy clearly, for example:

- row reconstructed by y-band grouping
- condition inherited from nearest preceding header row
- symbol composed from adjacent text blocks

## Spec writing heuristics

Use `review.md` as the operational truth about parser quality.

If `review.md` says table fidelity is weak:

- still model the canonical table if the table matters
- explicitly describe reconstruction heuristics
- record the ambiguity instead of pretending the structure is clean

If `review.md` says a summary block is reliable:

- it is acceptable to promote those values to top-level fields

## Failure handling

Do not write a clean-looking but lossy spec.

If the parser artifacts are insufficient in some area:

- mark the ambiguity explicitly
- record fallback derivation logic
- avoid overclaiming determinism

## Success bar

A good `pdf_field_spec.md` from this skill should let a later `/ppg:apply` implementation answer all of these questions without guesswork:

- what are the canonical tables
- what records are derived from them
- which fields are truly top-level
- how does each extracted value trace back to parser evidence
- where are the known ambiguities
