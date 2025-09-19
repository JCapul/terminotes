# Implementation Plan

- **Stage 1**: Bootstrap uv-based packaging (pyproject, `uv init`, module skeleton, CLI entry point) and lay down `terminotes/` scaffolding plus starter Justfile.
- **Stage 2**: Implement configuration handling for allowed tags and the remote git repository URL, including first-run cloning and validation.
- **Stage 3**: Build note creation flow (one-line command, editor template, SQLite persistence, ID generation) using the cloned repository as storage location.
- **Stage 4**: Add git integration that commits and pushes the SQLite database after note mutations, with graceful failure handling and test toggles.
- **Stage 5**: Implement `ls`, `update`, and `search` subcommands using SQLite queries.
- **Stage 6**: Establish testing/tooling setup (pytest fixtures, coverage hooks, uv-driven `ruff` lint/format tasks, docs updates).
- **Stage 7**: Final packaging polish—CLI help text, logging, release checklist, and CI readiness review.
