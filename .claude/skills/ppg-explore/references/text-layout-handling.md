# Text Layout Handling

Use this reference when a `digital-text` PDF has text that is technically extractable but structurally messy.

The goal is not to perfectly reconstruct author intent. The goal is to produce a stable `normalized.json` that is easier to review, chunk, and trace back to source blocks.

## What this reference covers

- reading order repair
- line merge / paragraph reconstruction
- multi-column contamination checks
- header/footer detection
- section boundary hints

## Core rule

Prefer conservative repair over aggressive rewriting.

If two interpretations are plausible:

- preserve the one with better traceability
- keep ambiguity visible
- avoid inventing semantic labels too early

## 1. Reading order repair

Typical symptoms:

- extracted text jumps between columns
- a sentence is split by unrelated text
- labels and values appear far apart in output order
- footer text appears inside paragraph flow

Preferred repair order:

1. Use page-local coordinates before trusting raw extraction order
2. Group nearby lines into blocks before merging into paragraphs
3. Reconstruct reading order within a column before combining columns
4. Keep uncertain blocks flagged instead of silently forcing them into one order

Useful heuristics:

- top-to-bottom is usually safer than raw object order
- within the same line band, left-to-right is usually safer for text PDF
- large horizontal gaps often indicate separate columns or label/value separation
- repeated y-position patterns across pages often indicate headers or footers

## 2. Line merge and paragraph reconstruction

Goal:

- merge obvious visual line breaks
- avoid merging unrelated lines just because they are vertically close

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

Safe normalization behaviors:

- collapse intra-paragraph line breaks into spaces
- keep paragraph boundaries explicit
- preserve source block references after merge

## 3. Multi-column handling

Multi-column text is one of the biggest ways text PDF extraction becomes misleading.

Typical failure mode:

- left column line 1
- right column line 1
- left column line 2
- right column line 2

This output may look readable at a glance but is structurally wrong.

Detection hints:

- persistent two-band or three-band x-coordinate clusters
- paragraphs with abrupt topic shifts mid-sentence
- similar vertical positions repeated with far-separated x positions

Preferred handling:

1. cluster text blocks by x-region
2. reconstruct each column independently
3. only merge columns at the section level if order is clear

If the order between columns is still uncertain:

- keep them as separate sections
- mark `uncertain: true`
- mention the risk in review output

## 4. Header and footer detection

Headers and footers are not harmless noise. If left in body text, they degrade chunking and evidence quality.

Strong header/footer signals:

- repeated text across many pages
- repeated page number patterns
- consistently near top or bottom margin
- visually separated from body text

Recommended behavior:

- mark them explicitly as `header` or `footer`
- exclude them from paragraph reconstruction
- preserve them in normalized output if they may matter for traceability

Do not silently delete them from all artifacts.

Preferred pattern:

- keep in raw
- mark in normalized
- exclude from candidate field ranking unless the user confirms relevance

## 5. Label-value candidates

For text PDF, some fields are expressed through spatial pairing rather than sentence structure.

Examples:

- `Invoice Number` on the left, value on the right
- `Date` above, value below

When detecting label-value candidates:

- preserve both text and spatial relation
- do not immediately commit to a final field meaning
- keep source blocks and page number

Useful hints:

- short textual label near a structured-looking value
- repeated label style across pages or similar documents
- same visual row or tight vertical adjacency

## 6. Section typing

Suggested `section_type` values:

- `header`
- `footer`
- `paragraph`
- `section`
- `table`
- `label_value_candidate`
- `uncertain`

Choose the narrowest type you can justify.

If unsure between two types, use `uncertain` and describe the ambiguity.

## 7. Normalization output expectations

After layout handling, `normalized.json` should make these questions easier to answer:

- What is body text vs repeated noise?
- Where do paragraphs start and end?
- Are there multiple columns?
- Which blocks support a candidate field?
- Which sections are unsafe to chunk blindly?

Good normalization is not the same as pretty text. It is a traceable, reviewable intermediate representation.

## 8. Red flags

Stop and report instead of over-normalizing when:

- column boundaries remain unstable
- merged paragraphs depend on guesswork
- body text and tables are interleaved unpredictably
- header/footer detection would require document-specific overfitting

When blocked, keep ambiguity visible and call it out in review.
