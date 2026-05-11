---
name: ppgm-apply
description: Use this skill whenever the user wants to implement a deterministic parser from parser-first PDF artifacts produced by MinerU or Docling. It reads `pdf_field_spec.md` plus `ppgm/source.md` and `ppgm/source.json`, compiles the spec into `parser_spec.json`, and generates parser/test code that preserves table structures, derived records, and evidence traceability instead of collapsing everything into flat scalar fields.
---

# PDF Parser Generator MinerU Mode: Apply

This skill turns parser-first exploration artifacts and a reviewed `pdf_field_spec.md` into executable parsing logic.

It is the third stage of the `ppgm` route:

```text
/ppgm:explore  -> parser-native Markdown / JSON artifacts
/ppgm:propose  -> reviewed pdf_field_spec.md
/ppgm:apply    -> compile spec, implement parser, validate outputs
```

The core idea is:

- do not re-parse the original PDF
- do not pretend parser-native artifacts are equivalent to `normalized.json`
- implement directly against `ppgm/source.json` and related parser-native artifacts

## Inputs

Read from:

```text
pdf-parser-generator/{pdf_stem}/
```

Required:

- `pdf_field_spec.md`
- `ppgm/source.json`
- `ppgm/source.md`

Optional but useful:

- `ppgm/review.md`
- `ppgm/source.lossless.json`
- `ppgm/layout.json`
- `ppgm/parser_choice.md`

If any required file is missing, stop and say exactly which file is missing.

## Artifact roles

- `pdf_field_spec.md`: reviewed semantic contract
- `ppgm/source.md`: human-readable parser-native artifact
- `ppgm/source.json`: machine-readable parser-native artifact
- `parser_spec.json`: compiled execution contract
- `parser.py`: executable parser over parser-native artifacts
- `test_parser.py`: validation tests

Do not modify `ppgm/source.md` or `ppgm/source.json`.

## Step 1: Compile `pdf_field_spec.md`

Compile:

```text
pdf-parser-generator/{pdf_stem}/parser_spec.json
```

The compile step must preserve the three-layer model from `ppgm-propose` when present:

- top-level fields
- canonical tables
- derived records

At minimum, the compiled spec should include:

- document metadata
- extraction quality summary
- extraction model
- top-level field definitions
- canonical table definitions
- derived record definitions
- evidence requirements
- chunking considerations
- known ambiguities

If the markdown spec is incomplete or ambiguous:

- preserve `unresolved`
- do not silently simplify the structure into flat fields

## Step 2: Read parser-native artifacts

Base parser logic on `ppgm/source.json` first.

Use `ppgm/source.md` as a debugging and review aid, not as the primary machine source unless the JSON is clearly weaker.

If `source.lossless.json` exists and exposes stronger structural detail:

- prefer it for evidence-heavy logic
- document that choice in comments or notes

Do not reconstruct a custom `normalized.json` just to imitate the `ppg` route.

## Step 3: Implement `parser.py`

Write:

```text
pdf-parser-generator/{pdf_stem}/parser.py
```

### Parser output model

The parser should return a structured result that can preserve multiple output layers.

Preferred high-level shape:

```python
{
    "top_level_fields": {
        "part_number": {
            "value": "...",
            "evidence": "...",
            "page_number": 1,
            "source_refs": [...],
            "confidence": 0.0,
        }
    },
    "canonical_tables": {
        "electrical_characteristics": {
            "rows": [...],
            "evidence": {...},
            "warnings": [...],
        }
    },
    "derived_records": {
        "electrical_stats": [
            {
                "symbol": "...",
                "parameter": "...",
                "condition": "...",
                "stat": "min|typ|max",
                "value": "...",
                "unit": "...",
                "evidence": {...},
            }
        ]
    },
    "warnings": [...]
}
```

Do not flatten canonical tables and derived records unless the spec explicitly says the document is field-first.

### Implementation rules

- implement against compiled `parser_spec.json`
- preserve evidence traceability for every important output
- use parser-native table structure when available
- if row or cell ids do not exist, implement the fallback strategy described in the spec
- distinguish:
  - missing in parser artifact
  - present but ambiguous
  - intentionally blank in source table
- do not guess strict values

For top-level fields, include at least:

- `value`
- `evidence`
- `page_number`
- `source_refs`

For canonical tables, include at least:

- extracted rows or cells
- page scope
- evidence refs
- warnings if reconstruction was heuristic

For derived records, include at least:

- normalized record values
- linkage to source table
- row or cell evidence refs when possible

## Step 4: Implement `test_parser.py`

Write:

```text
pdf-parser-generator/{pdf_stem}/test_parser.py
```

### Test goals

Do not limit tests to scalar equality.

Validate all relevant layers:

- top-level field values
- top-level field evidence
- canonical table presence and shape
- derived record count or representative records
- warnings or ambiguity behavior when required by the spec

### Example test categories

- a promoted top-level field returns the expected singular value
- a canonical table is preserved with expected column or row structure
- a derived record family emits normalized rows with preserved stat semantics
- evidence refs are non-empty for important outputs
- strict extraction does not invent unsupported values

If the spec includes unresolved ambiguity, explicitly skip or xfail the affected checks rather than pretending determinism.

## Step 5: Run validation

Run:

```bash
cd pdf-parser-generator/{pdf_stem} && python -m pytest test_parser.py --tb=short -q
```

### Result reporting

Report by layer, not just by field.

Preferred format:

```text
## Parser validation result: {pdf_filename}

Top-level fields:
- pass / fail summary

Canonical tables:
- pass / fail summary

Derived records:
- pass / fail summary

Warnings:
- key warnings or none
```

If there are failures, identify whether they come from:

- spec ambiguity
- parser logic defect
- parser-native artifact limitation

## Step 5.5: Auto-repair loop

If validation fails, attempt at most 2 focused repair rounds.

Each round:

1. isolate the failing layer:
   - top-level field
   - canonical table
   - derived record family
2. load only the relevant spec section plus the related parser-native evidence
3. patch only the affected parser logic
4. rerun tests

If the failure source is parser-native artifact weakness:

- stop the repair loop
- explicitly recommend going back to `ppgm-explore` or switching to `ppg-explore`

If the failure source is spec weakness:

- point the user to the exact section in `pdf_field_spec.md`
- do not silently invent a stronger rule than the spec provides

## Output directory

```text
pdf-parser-generator/
  {pdf_stem}/
    pdf_field_spec.md
    parser_spec.json
    parser.py
    test_parser.py
    ppgm/
      source.md
      source.json
      review.md
      parser_choice.md
      source.lossless.json
      layout.json
```

## Failure handling

- missing `pdf_field_spec.md`: tell the user to run `/ppgm:propose`
- missing `ppgm/source.json` or `ppgm/source.md`: tell the user to run `/ppgm:explore`
- compiled spec loses table-first structure: treat this as a spec/compile failure
- parser-native artifact lacks enough evidence for deterministic validation: state the limitation clearly
- user asks for strong determinism from a black-box parser artifact with weak provenance: push back explicitly

## Success bar

A successful `ppgm-apply` implementation should make it easy to answer:

- which outputs are true top-level fields
- which outputs must stay canonical tables
- which outputs are derived records
- how each important value traces back to parser-native evidence
- where parser-native artifact limitations still constrain reliability
