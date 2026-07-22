# AGENTS.md — Agent configuration for django-controlled-vocabularies

<!-- Thin index only — bloat here = ignored instructions. Details live in the pointed-to
     files: CONTEXT.md, docs/brainstorm.md, docs/agents/. -->

django-controlled-vocabularies is a Django app for **managing, publishing, and consuming SKOS
controlled vocabularies** in research infrastructure. Relational models are the source of truth;
RDF is a projection produced only at the import/export boundary. See the [`README`](README.md) for
scope, [`CONTEXT.md`](CONTEXT.md) for the ubiquitous language, and
[`docs/brainstorm.md`](docs/brainstorm.md) for early design notes.

## Stack & commands

- **Stack:** Python 3.11+, Django 5.2+, Poetry-managed. Installable Django app (also runnable standalone).
- **Install:** `poetry install`
- **Test:** `poetry run pytest`
- **Lint:** `poetry run ruff check .`
- **Format:** `poetry run ruff format .`
- **Type-check:** `poetry run mypy`
- **Deps audit:** `poetry run deptry .`
- **Build:** `poetry build`

## Agent skills

### Issue tracker

Issues and PRs tracked in GitHub Issues via the `gh` CLI. See [`docs/agents/issue-tracker.md`](docs/agents/issue-tracker.md).

### Triage labels

Canonical five-label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, `wontfix`). See [`docs/agents/triage-labels.md`](docs/agents/triage-labels.md).

### Domain docs

Single-context layout — `CONTEXT.md` at the root, `docs/brainstorm.md` for early design notes. See
[`docs/agents/domain.md`](docs/agents/domain.md).

### CI checks

Required status checks (exact names), all reusable-workflow contexts from `django-mvp/shared`:

- `call-build / Code Quality`
- `call-build / Security Scan`
- `call-build / Build Package`
- `call-tests / Test Python 3.12, Django 5.2`
- `call-tests / Test Python 3.12, Django 6.0`
- `call-tests / Test Python 3.13, Django 5.2`
- `call-tests / Test Python 3.13, Django 6.0`

CI is repo-native, on the django-mvp family standard (callers pinned to a family tag).

## Development workflow

Feature work follows a spec-driven process: spec → plan → tasks → implement → review → PR, with
`specs/NNN-slug/` directories generated per feature (there is no Spec Kit install in the repo).
Project standards and the quality bar live in `memory/constitution.md`.
