# Agent General Rules

Use this file as the entry point for agent-wide, cross-project rules stored in `knowledge-base`.

## Included Rules

- [File Encoding Rule](./file-encoding.md)
  Apply this before reading, writing, patching, generating, or exporting any text file.
- [Markdown Output Language Rule](./markdown-output-language.md)
  Apply this when creating or rewriting Markdown documents unless a higher-priority constraint requires another language.
- [TAO Working Method Rule](./tao-working-method.md)
  Apply this for non-trivial tasks that require more than one action or any meaningful reasoning.
- [Skill Writing Rule](./skill-writing-standard.md)
  Apply this when creating, moving, splitting, or updating skills in this repository.

## Usage

- If a task involves text files, load the file encoding rule first.
- If a task produces or rewrites Markdown, apply the markdown output language rule.
- Apply TAO for all non-trivial tasks.
- Keep this file short; store detailed rules in linked rule documents.
