# Evaluation Rubric

Use this rubric to compare `ppg-explore` and `ppgm-explore` on the same PDF samples.

The goal is not to crown a universal winner from one file. The goal is to understand which workflow is better for your document mix, your tolerance for black-box behavior, and your downstream extraction needs.

## Recommended test set

Compare the two workflows on at least 3 sample types:

- a clean text PDF
- a multi-column or layout-heavy text PDF
- a text PDF with important tables

If your real workload includes them, also test:

- a hybrid PDF
- a poor-quality text layer PDF

## 1. Parsing completeness

Ask:

- Did either workflow miss entire sections?
- Were headers, footers, footnotes, or small text dropped?
- Were tables partially lost?
- Did one workflow silently omit content the other preserved?

Good sign:

- important content is present, even if not perfectly normalized

Bad sign:

- clean-looking output that quietly drops information

## 2. Reading order quality

Ask:

- Are paragraphs in the correct order?
- Are multi-column pages linearized correctly?
- Are label/value relationships preserved?
- Does the output read like the original document?

This matters because bad reading order corrupts both human review and downstream chunking.

## 3. Table fidelity

Ask:

- Are tables preserved as tables, not flattened prose?
- Are row/column boundaries usable?
- Are summary rows preserved?
- Are cross-page or borderless tables still understandable?

This is often a decisive category. Many workflows look good until tables matter.

## 4. Traceability

Ask:

- Can you trace a final field back to source evidence?
- Is page-level provenance preserved?
- Are block, span, or table references available?
- If something is wrong, can you debug it without rereading the whole PDF manually?

`ppg-explore` usually wins here when custom artifact design is strong.
`ppgm-explore` may lose if the parser output is too black-box.

## 5. Human review cost

Ask:

- How long does it take to inspect output and trust it?
- Is the Markdown readable?
- Does the JSON expose too much noise or too little detail?
- Do you spend more time fixing parser output than you would building your own structure?

This is where parser-first workflows can win big if the native artifacts are already good enough.

## 6. Deterministic downstream suitability

Ask:

- Can this workflow support a stable `pdf_field_spec.md`?
- Can it support deterministic parser rules later?
- Does it preserve enough structure for `ppg:apply` to validate evidence?
- Will you end up re-parsing the PDF anyway because the artifact is not reliable enough?

If the answer is "we still have to rebuild everything," then parser-first did not actually simplify the pipeline.

## 7. Operational cost

Ask:

- Installation difficulty
- Runtime speed
- CPU/GPU requirements
- Memory usage
- Windows compatibility
- Batch execution convenience

Parser-first workflows often have better output quality but higher operational weight.

## 8. Transparency and controllability

Ask:

- When the output is wrong, can you explain why?
- Can you tune the behavior?
- Can you make small local fixes?
- Or are you mostly at the mercy of the parser?

This is a major strategic difference:

- `ppg-explore` favors control
- `ppgm-explore` favors leverage

## 9. Robustness across document families

Ask:

- Does the workflow generalize across invoices, datasheets, forms, reports, and table-heavy docs?
- Does it only shine on one document family?
- Does performance collapse when layout changes slightly?

Do not judge from one successful sample.

## 10. Net workflow value

The most important question:

- After including review time, debugging time, and downstream implementation time, which workflow actually gets you to a trustworthy extraction system faster?

This is the decision metric that matters most.

## Suggested scorecard

Use a 1-5 score for each workflow on each sample:

- parsing completeness
- reading order quality
- table fidelity
- traceability
- human review cost
- deterministic downstream suitability
- operational cost
- transparency / controllability

Then add short notes:

- where `ppg-explore` clearly wins
- where `ppgm-explore` clearly wins
- where the difference is negligible

## Likely outcome patterns

Common outcomes:

- `ppgm-explore` wins on speed and initial artifact convenience
- `ppg-explore` wins on traceability and deterministic downstream use
- parser-first workflows do well on normal text PDFs but may still fail on key tables or niche layouts

If this pattern shows up consistently, the best answer is often hybrid:

- use parser-first artifacts for acceleration
- keep `ppg` review/spec/apply for control
