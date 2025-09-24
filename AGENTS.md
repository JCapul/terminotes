# Repository Guidelines

Terminotes is a Python CLI for jotting quick notes from the terminal. Notes live in SQLite, and optional git synchronization keeps the database portable when configured. This guide keeps contributors aligned as the first release ships.

## Project Structure & Module Organization
- Place runtime code under `terminotes/`, grouping modules by concern (`cli.py` for argument parsing, `editor.py` for editor launch, `storage.py` for SQLite, `git_sync.py` for git sync duties).
- Keep shared helpers in `terminotes/utils/` when logic spans modules.
- Store tests in `tests/`, mirroring the module layout (`tests/test_cli.py`, `tests/test_storage.py`).
- Keep documentation in `docs/` and configuration samples (tags, templates, repo settings) in `config/`.

## Build, Test, and Development Commands
- Use Astral's `uv` for environment and dependency management: `uv init terminotes`, `uv sync`, and `uv run python -m terminotes ...`.
- Prefer the uv-managed virtual env (`.venv/`); run tooling with `uv run ...`.
- Define a `Justfile` exposing canonical tasks, e.g. `just bootstrap` (uv sync + pre-commit setup), `just lint` (`uv run ruff check`), `just fmt` (`uv run ruff format`), `just test` (`uv run pytest`), `just cli` (`uv run python -m terminotes`).

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; keep lines ≤88 chars.
- Use `snake_case` for functions/modules, `CapWords` for classes, and uppercase constants.
- Type-hint public functions with simple built-in/typing annotations; avoid ornate generics.
- Let `ruff` handle linting (`ruff check`) and formatting (`ruff format`); run via `uv run` or `just`.

## Testing Guidelines
- Pair each feature with unit tests; use descriptive names like `test_update_rejects_unknown_tag`.
- Cover SQLite persistence, git clone/commit/push flows (mock git when feasible), and CLI argument parsing.
- Keep lightweight fixtures in `tests/fixtures/` for sample notes and tag lists.
- Target ≥80% coverage once instrumentation is configured (`uv run pytest --cov=terminotes`).

## Commit & Pull Request Guidelines
- Adopt Conventional Commits (`feat:`, `fix:`, `test:`) to signal intent (`feat(cli): add search subcommand`).
- Keep commits single-purpose; document manual steps (e.g., `git config`) in the body.
- PRs should include a summary, `just test` output (or failing rationale), linked issues, and terminal captures when UX changes.
- Require one approving review and passing CI before merging; update this guide as workflows evolve.

### Pre-commit Checks
- Always run formatting, linting, and tests locally before committing or pushing:
  - `uv run ruff format .`
  - `uv run ruff check .`
  - `uv run pytest`
- Equivalent `just` tasks are available: `just fmt && just lint && just test`.
 - Install git hooks once with `just bootstrap` (runs `pre-commit install`). Hooks enforce Ruff and Pytest on commit.

## Security & Configuration Tips
- Keep secrets in `.env.local`; provide safe defaults in `.env.example` and ignore the former in git.
- `git_remote_url` is required. The CLI ensures the git clone exists and future stages handle commits/pushes.
- Ensure git sync errors surface actionable messaging and avoid prompting inside the CLI; rely on external credentials.
- Validate tag configuration before use and parameterize SQL queries.

## Pre-release Compatibility
- This project is pre-1.0 with no user base. Backward compatibility is not required at this stage.
- We may rename config keys and APIs without migration code. For example, use `terminotes_dir` (not `repo_path`) and do not provide shims.
