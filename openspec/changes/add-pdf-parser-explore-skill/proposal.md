## Why

Users can already extract text or tables from PDFs with existing tools, but the hard part is turning a semi-structured document into a stable extraction spec. Today that work is fragmented across ad hoc prompts, manual inspection, and one-off parser experiments. We need a guided workflow that helps users move from a sample PDF to a reviewable parser spec with clear human checkpoints.

This change is needed now because the project is already exploring `PDF -> JSON -> parser` practice using `GR075N06B.pdf`, and the current friction is not low-level extraction alone. The missing capability is a reusable discovery workflow that classifies the document, surfaces structured candidates, asks targeted questions about field meaning, and captures those decisions into artifacts that can later drive parser implementation.

## What Changes

- Add a new skill-oriented workflow for PDF parser discovery rather than direct universal parser generation.
- Define a guided flow that starts from a single PDF and produces document classification, raw structured extraction, normalized review output, targeted clarification questions, and a parser spec draft.
- Standardize the interaction model so users primarily review a human-readable Markdown document while the system maintains machine-readable spec artifacts.
- Support backend routing policy for PDF ingestion so the workflow can prefer available PDF extraction tools without hard-coupling the skill to a single backend implementation.
- Capture field definitions such as requiredness, missing-value behavior, guess policy, and validation description as part of the review and spec process.

## Capabilities

### New Capabilities
- `pdf-parser-explore`: Guide a user from a sample PDF through classification, structured extraction review, field clarification, and parser spec drafting.

### Modified Capabilities
- None.

## Impact

- New OpenSpec capability and requirements for a PDF parser discovery workflow.
- New workflow artifacts describing review Markdown, machine-readable spec output, and targeted clarification loops.
- Future skill implementation will likely depend on existing PDF extraction backends such as Anthropic's `pdf` skill, `docling`, or equivalent local tools, but the workflow should remain backend-policy driven rather than hard-wired to one dependency.
