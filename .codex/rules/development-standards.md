# Development Standards

Repository-level standards for folder placement, code organization, and workflow integrity.

## Directory Standards

Place code and artifacts by responsibility:

- `lib/` — Shared Python library code, adapters, orchestration, analytics, and entry points.
- `freqtrade/` — Freqtrade-specific strategy code, configs, and engine-generated reports.
- `data/` — Raw market data, derived features, and reproducible dataset snapshots.
- `strategies/<strategy_family>/` — Strategy-local markdown artifacts, reviews, reports, experiments, and decision history.
- `knowledge-base/` — Reusable skills, standards, and supporting knowledge documents.

Do not introduce new code under legacy `com/willy/...` paths.

## Naming and Organization

- Use a stable lowercase strategy slug for folders: `btc-breakout`, `eth-mean-reversion`.
- Keep engine-specific implementation names aligned with the target engine's conventions.
- Keep generated outputs separate from hand-authored specs and reviews.

## Coding Conventions

- Use absolute imports rooted at `lib` or the relevant top-level package.
- Keep DTOs, adapters, and utilities independent from engine-specific orchestration.
- Do not hardcode machine-specific paths.
- Resolve repo-relative paths from REPO_ROOT or from the current module's `__file__`.
- All `lib/` subdirectories must have an `__init__.py` to support package imports.

## Workflow Integrity

- Treat strategy markdown artifacts as first-class project assets.
- Require a clear link between hypothesis, spec, implementation, and report artifacts.
- When a strategy implementation changes materially, update the related markdown artifacts in the same task when feasible.
- If the user starts with a single strategy brief file, preserve it and build from it instead of discarding it.
