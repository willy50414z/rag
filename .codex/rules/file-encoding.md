# File Encoding Rule

Apply this rule to all text-file work unless the user explicitly requires a different encoding.

## Rules

- Read text files as UTF-8.
- Write text files as UTF-8 without BOM.
- Preserve existing line endings unless the task requires changing them.
- Treat source code, config, markdown, JSON, YAML, CSV, SQL, logs, and plain-text outputs as text files covered by this rule.
- If a file appears garbled, first suspect the viewer or terminal rendering before changing file encoding.
- Do not convert a file to another encoding unless the user asks for it or the file is confirmed to use a different encoding.

## Implementation Guidance

- When using Python file I/O, pass `encoding="utf-8"`.
- When using shell or editor tooling, prefer commands and settings that emit UTF-8 without BOM.
- Avoid locale-dependent text output when writing files.
- Re-read the file after writing when encoding correctness matters to the task.
