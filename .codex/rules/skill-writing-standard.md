# Skill Writing Rule

Apply this rule when creating, moving, splitting, or updating skills in this repository.

## Classification Rules

- Put repository-specific skills under `project-skills/`.
- Put domain knowledge skills under `domain-skills/`.
- Put framework or tool specific skills under `framework-skills/`.
- Put reusable non-project workflow skills under `general-skills/`.
- Put cross-agent standards and policy-like rules under `rules/`.

## Project Skill Rule

- `project-skills/<project>.md` should be a routing document, not the home of domain or framework knowledge.
- Keep only project-specific overview, routing, and repo-only workflows inside `project-skills/<project>/`.
- If a skill can be reused outside this repository with minor wording changes, do not keep it under `project-skills/`.

## Skill Placement Heuristics

- If the skill mentions repo-only folder layout, local entry points, migration rules, or repository runtime assumptions, keep it as a project skill.
- If the skill is about trading logic, validation logic, hypothesis design, or ML research patterns, prefer `domain-skills/`.
- If the skill is about Freqtrade, exchange SDK usage, or another technical framework, prefer `framework-skills/`.
- If the skill is about documentation quality, markdown editing, or similar reusable workflows, prefer `general-skills/`.
- If the content is policy, standards, or always-on behavior guidance rather than an executable workflow, prefer `rules/`.

## Skill Format

- A real skill should live in its own folder and use `SKILL.md`.
- Do not keep long-lived skill content as a loose markdown file when it should be a reusable skill.
- Use markdown files under `rules/` only for standards, rules, and reference-style guidance.
- Keep one skill per folder.

## Frontmatter and Description

- Add YAML frontmatter to every `SKILL.md`.
- Include only `name` and `description` in frontmatter unless there is a proven repo convention requiring more.
- Write `description` as:
  what the skill does + when the agent should use it.
- Keep descriptions specific enough that an agent can distinguish similar skills.
- Normalize all existing skills to the same frontmatter and description style when updating the skill tree; do not leave mixed styles across the repository.

## Content Rules

- Avoid hardcoded legacy paths unless the task truly depends on them.
- Prefer current repository paths and migration-safe wording.
- Keep project entry documents short and routing-oriented.
- Put detailed operational guidance inside the target skill, not the project index.
- When a skill or rule is moved, update every live reference in the same task.

## Maintenance Rules

- If a new skill is added, decide its category before creating it.
- If a skill changes from project-specific to reusable, move it to the appropriate non-project category.
- If content is actually a rule rather than a skill, move it under `rules/`.
- If a skill becomes obsolete, delete it instead of leaving duplicate or shadow copies.
- Re-run references after any move or rename to avoid stale paths.
