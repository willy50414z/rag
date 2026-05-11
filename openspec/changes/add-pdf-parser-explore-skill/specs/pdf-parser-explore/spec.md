## ADDED Requirements

### Requirement: Workflow classifies the input PDF before field discovery
The skill SHALL accept a single PDF input and classify it as digital-text, scanned, hybrid, or uncertain before it proposes field-level extraction behavior.

#### Scenario: Digital PDF classification
- **WHEN** the input PDF contains extractable text with sufficient page-level coverage
- **THEN** the workflow classifies the document as digital-text

#### Scenario: Scanned PDF classification
- **WHEN** the input PDF lacks usable text extraction and page content must be read from images
- **THEN** the workflow classifies the document as scanned

#### Scenario: Uncertain classification
- **WHEN** the workflow cannot confidently distinguish between digital-text, scanned, or hybrid
- **THEN** the workflow marks the classification as uncertain and records the reason

### Requirement: Workflow produces reviewable structured intermediate artifacts
The skill SHALL generate structured intermediate artifacts that preserve document evidence before any final parser-spec draft is produced.

#### Scenario: Raw extraction artifact
- **WHEN** the workflow performs initial PDF extraction
- **THEN** it records page-level or block-level structured output with source references and extraction metadata

#### Scenario: Normalized review artifact
- **WHEN** raw extraction is complete
- **THEN** the workflow produces a normalized review-oriented representation that is easier for a human to inspect than raw extraction alone

### Requirement: Workflow presents human-readable review output alongside machine-readable state
The skill SHALL provide a human-readable review artifact and maintain machine-readable state for parser-spec generation.

#### Scenario: Review artifact for users
- **WHEN** the workflow surfaces field candidates and document observations
- **THEN** it presents them in a Markdown-oriented review format suitable for user correction

#### Scenario: Structured state for the system
- **WHEN** the workflow captures field candidates, decisions, and uncertainty
- **THEN** it also stores a machine-readable representation that can drive later parser-spec generation

### Requirement: Workflow asks targeted clarification questions
The skill SHALL ask bounded clarification questions that help resolve field meaning, candidate selection, and extraction policy.

#### Scenario: Candidate disambiguation
- **WHEN** a field has multiple plausible candidates
- **THEN** the workflow asks the user to confirm which candidate is correct or should be ignored

#### Scenario: Missing policy clarification
- **WHEN** a field is identified but its missing-value behavior is not known
- **THEN** the workflow asks whether the field should be treated as required, optional, review-needed, or error-on-missing

### Requirement: Workflow captures per-field extraction policy
The skill SHALL record per-field extraction policy, including requiredness, missing-value handling, guess policy, and validation description.

#### Scenario: Agent proposes defaults
- **WHEN** the workflow identifies a candidate field and no user policy is defined yet
- **THEN** it proposes provisional defaults for requiredness, guess policy, and validation description

#### Scenario: User confirms or edits policy
- **WHEN** the user reviews a proposed field policy
- **THEN** the workflow records whether the policy was accepted, modified, or left unresolved

### Requirement: Workflow preserves uncertainty instead of forcing unsupported conclusions
The skill SHALL preserve unresolved ambiguity rather than silently inventing a field meaning, candidate, or validation rule.

#### Scenario: Unresolved field ambiguity
- **WHEN** the workflow cannot determine a stable field interpretation from extraction evidence and user input
- **THEN** it marks the field as unresolved and includes the ambiguity in the review output

#### Scenario: Unsupported validation inference
- **WHEN** the agent cannot justify a validation description or guess policy from the available evidence
- **THEN** it labels the proposed rule as provisional and requests confirmation instead of treating it as final

### Requirement: Workflow outputs a parser-spec draft as its primary success artifact
The skill SHALL treat a reviewable parser-spec draft as the primary first-version output.

#### Scenario: Successful workflow completion
- **WHEN** classification, extraction review, and field clarification are complete for the sample PDF
- **THEN** the workflow outputs a parser-spec draft with the current field definitions, evidence references, and unresolved items

#### Scenario: Parser code remains optional
- **WHEN** the workflow completes its guaranteed first-version path
- **THEN** parser code generation is not required for the workflow to be considered successful
