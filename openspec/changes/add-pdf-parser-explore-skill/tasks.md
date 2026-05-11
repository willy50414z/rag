## 1. Workflow Definition

- [x] 1.1 Define the skill entry contract for a single sample PDF and optional brief user description
- [x] 1.2 Define the backend policy routing rules for digital-text, scanned, hybrid, and uncertain PDFs
- [x] 1.3 Define the intermediate artifact schema for raw extraction, normalized review output, and machine-readable field state

## 2. Review and Clarification Flow

- [x] 2.1 Design the Markdown review format that presents candidate fields, evidence, ambiguities, and targeted questions
- [x] 2.2 Define the user-editable field template for requiredness, missing-value handling, guess policy, and validation description
- [x] 2.3 Define the targeted clarification question set for candidate selection, field meaning, and missing-value policy

## 3. Spec Draft Generation

- [x] 3.1 Define how agent-proposed default field policies are marked as provisional, confirmed, or modified
- [x] 3.2 Define the machine-readable parser-spec draft format that captures field definitions, evidence references, and unresolved items
- [x] 3.3 Define how unresolved ambiguity is preserved instead of silently converted into final extraction rules

## 4. Implementation and Validation

- [x] 4.1 Implement the first-version skill workflow using the defined contracts and review artifacts
- [ ] 4.2 Validate the workflow on `GR075N06B.pdf` and one additional narrow-scope sample document
- [x] 4.3 Document first-version limits, unsupported document classes, and recommended next-step validation before parser production use
