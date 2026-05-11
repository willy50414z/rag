## Context

The project already has PDF learning materials and an emerging `PDF -> JSON -> parser` practice, but the current workflow depends on manual prompting and repeated explanation of field meaning. Existing PDF-focused skills and libraries can extract text, tables, or OCR output, yet they do not provide a consistent discovery workflow that helps a user move from a sample document to a reviewable parser specification.

This change introduces a new skill-level workflow for parser discovery. It is intentionally narrower than a universal parser generator. The workflow begins with one sample PDF, classifies the document type, produces structured intermediate artifacts, asks targeted clarification questions, and captures user decisions into a machine-readable spec draft.

Key constraints:

- The workflow must remain backend-policy driven and must not hard-couple to a single PDF extraction dependency.
- The first version should optimize for clarity and reviewability, not full automation.
- Human-readable review output and machine-readable spec output both matter.
- The first version should support simple document classes better than arbitrary enterprise PDFs.

## Goals / Non-Goals

**Goals:**

- Provide a repeatable workflow from sample PDF to parser spec draft.
- Standardize intermediate artifacts such as document classification, raw extraction, normalized review output, and field definitions.
- Let users review and edit a Markdown-oriented artifact rather than raw JSON alone.
- Capture field semantics such as requiredness, missing-value handling, guess policy, and validation description.
- Use targeted clarification questions instead of fully open-ended conversation.

**Non-Goals:**

- Generating a production-ready universal parser for arbitrary PDFs in the first version.
- Solving handwriting-heavy, low-quality scan, or highly irregular multi-template documents.
- Replacing dedicated annotation or review UIs.
- Defining a rigid DSL that users must write by hand on day one.

## Decisions

### 1. Position the skill as a parser discovery assistant, not a universal parser generator

The workflow will stop at a reviewable parser spec draft in its guaranteed scope. Optional parser code generation may be added later, but the skill will not promise that output as its first-version success criterion.

Alternative considered:

- Promise direct parser generation from the first sample PDF.

Why not:

- It creates the wrong product expectation and hides the real uncertainty in field meaning and document variation.

### 2. Use backend policy routing instead of a hard dependency on one PDF skill or library

The workflow will define a backend selection policy rather than require one fixed ingestion tool. For example, it can prefer lightweight text extraction for digital PDFs and stronger OCR or layout-aware tools for scanned or hybrid documents.

Alternative considered:

- Bundle or hard-wire a single PDF skill into the workflow.

Why not:

- It increases maintenance cost, makes capability drift more likely, and blocks the workflow when one backend is unavailable or inappropriate.

### 3. Produce dual artifacts: Markdown for review, structured spec for system use

The workflow will generate both:

- A human-readable review artifact in Markdown
- A machine-readable artifact for field definitions and parser-spec state

Alternative considered:

- Use JSON only
- Use Markdown only

Why not:

- JSON alone is poor for review and correction.
- Markdown alone is too ambiguous to be the durable system contract.

### 4. Let the agent propose default field constraints, then require user confirmation or correction

For each field candidate, the agent may propose defaults for:

- requiredness
- missing-value handling
- strict/no-guess behavior
- validation description

These defaults must be clearly marked as provisional until confirmed or modified by the user.

Alternative considered:

- Require users to author all field constraints from scratch

Why not:

- It creates too much friction and makes the workflow harder to adopt.

### 5. Favor targeted clarification prompts over free-form exploratory dialogue

The workflow should ask bounded questions such as:

- Which candidate is the real document number?
- Should footer values be ignored?
- Is this field required or optional?
- If no supported value is found, should the workflow return null, error, or review-needed?

Alternative considered:

- Fully free-form conversational exploration

Why not:

- It increases ambiguity, slows convergence, and makes results harder to capture as a spec.

## Risks / Trade-offs

- [Users expect parser code immediately] -> Make the first-version contract explicit: the guaranteed output is a reviewable parser spec draft, not a production parser.
- [Raw extraction appears complete but semantics are wrong] -> Preserve source references, candidate evidence, and uncertainty markers at every stage.
- [Markdown review becomes too loose to parse back] -> Use a semi-structured review format with stable field sections and constrained keys.
- [Backend differences create inconsistent outputs] -> Normalize ingestion results into a workflow-owned intermediate schema.
- [One sample PDF creates a false sense of generalization] -> Treat the output as a spec draft and recommend multi-sample validation before any production parser is trusted.

## Migration Plan

This is a net-new capability and does not require runtime migration. The practical rollout path is:

1. Add the new capability specification.
2. Implement a first-version skill workflow for one sample PDF at a time.
3. Validate the workflow against a narrow document class before expanding scope.

Rollback is straightforward because the feature is additive: remove or archive the skill artifacts without affecting existing learning materials.

## Open Questions

- Should the first version stop at `parser spec draft`, or also emit a parser skeleton as a non-guaranteed convenience output?
- Which backend policy should be preferred by default when multiple PDF extraction options are available?
- Should field validation remain natural-language-first throughout version one, or should some common constraint patterns be normalized automatically?
- How much ambiguity should the workflow tolerate before it must force a manual review outcome?
