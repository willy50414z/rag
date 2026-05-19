# Field Policy Template

Use this template during ppg-explore Step 5 when asking the user to confirm field-level extraction policies. Each field in the DB schema should have a policy covering required/optional, missing-value behavior, and validation.

## Template

```md
## Field: <field_name>

- Description:
- Required: yes | no | unknown
- If missing: null | error | needs_review | unknown
- Strict extraction: yes | no | unknown
- Validation description:
- Candidate priority note:
- Notes:
```

## Interpretation guidance

- `Required` means the workflow expects the field to exist for the target use case.
- `If missing` defines downstream behavior, not whether the field is conceptually important.
- `Strict extraction` means do not invent or infer unsupported values when evidence is weak.
- `Validation description` should remain natural language unless the user explicitly asks for stronger normalization.

## Default suggestion guidance

- Suggest `Strict extraction: yes` for identifiers, dates, amounts, and workflow-critical values.
- Suggest `Strict extraction: no` only for softer descriptive fields or optional annotations.
- Suggest `If missing: error` for required workflow-critical fields.
- Suggest `If missing: null` for optional fields unless review is safer.
