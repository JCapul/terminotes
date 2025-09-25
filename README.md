# Terminotes

Terminotes is a terminal-first note taking CLI, 99% vibecoded with Codex CLI and GPT-5 under my tight supervision 😉

It focuses on fast capture from the shell, durable storage in SQLite, and simple Git synchronization so you can keep your notes database in a repo and carry it between machines.


## Features

- Fast capture via editor (`tn edit`) and direct log entries (`tn log -- ...`).
- SQLite storage with simple schema and safe parameterized queries.
- Git-backed portability: store the DB in a repo and sync on demand.
- Practical commands: list, search, delete, info, and sync.

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) for environment and workflow.
- Git installed and a reachable remote for your notes repo.

## Installation

Clone the repository and set up the environment with uv:

```bash
uv sync
```

Install pre-commit hooks (optional but recommended):

```bash
uv run pre-commit install
```

You can run Terminotes either via the console script or the module:

```bash
uv run tn --help
# or
uv run python -m terminotes --help
```

## Quick Start

1) Create or edit your configuration file:

```bash
uv run tn config
```

This bootstraps a TOML file (default `~/.config/terminotes/config.toml`). Update it to point to your notes repo and editor. Minimal example:

```toml
git_remote_url = "git@github.com:you/terminotes-notes.git"
terminotes_dir = "notes-repo"  # absolute or relative to the config dir
editor = "vim"
```

Important: `git_remote_url` is required. Terminotes ensures a local clone exists under `terminotes_dir` and stores the SQLite DB there.

2) Capture a first note:

```bash
uv run tn edit
```

3) List your notes:

```bash
uv run tn ls --limit 10
```

4) Sync with the remote when ready:

```bash
uv run tn sync
```

## Usage

Below are the primary subcommands. Use `uv run tn --help` and `uv run tn <cmd> --help` for details.

- `config` — Create/open the config file in your editor.
  - Example: `uv run tn config`

- `edit` — Create a new note or edit an existing one.
  - New note: `uv run tn edit`
  - Edit by id: `uv run tn edit --id 42`
  - Edit last updated: `uv run tn edit --last`

- `log` — Quick log entry without opening an editor.
  - Example: `uv run tn log -- This is a log #til #python`
  - Title is derived from the first sentence or line, truncated when long.

- `ls` — List most recent notes (by last edit time).
  - Example: `uv run tn ls --limit 10`
  - Options: `--limit/-n`, `--reverse` (oldest first for current sort)

- `search` — Simple case-insensitive substring search across title/body/description.
  - Example: `uv run tn search "python" --limit 20`
  - Options: `--limit/-n`, `--reverse`

- `delete` — Delete a note by id.
  - Example: `uv run tn delete --yes 42`
  - Uses a confirmation prompt unless `--yes` is provided.

- `sync` — Fetch, detect divergence, and push with the selected strategy.
  - Requires a clean working tree; commit or stash changes first.
  - Divergence prompt choices: `local-wins`, `remote-wins`, or `abort`.

- `info` — Show current repo path, totals, and last edited note.

## Configuration

The config file is TOML and lives by default at `~/.config/terminotes/config.toml`. Keys:

- `git_remote_url` (string, required): your notes repo remote URL.
- `terminotes_dir` (string, optional): where the local repo lives; absolute or relative path. Default: `notes-repo` under the config directory.
- `editor` (string, optional): command to launch when editing notes via `tn edit`.

You can start from `config/config.sample.toml`.

## Data Model

Notes are stored in an SQLite file named `terminotes.sqlite3` under `terminotes_dir`. Schema (simplified):

- `id` (INTEGER PRIMARY KEY)
- `title` (TEXT)
- `body` (TEXT)
- `description` (TEXT)
- `created_at` (TEXT, ISO 8601)
- `updated_at` (TEXT, ISO 8601)
- `can_publish` (INTEGER as boolean)

Timestamps are stored in UTC.

## Git Sync

Terminotes uses your local clone of the notes repository and commits SQLite changes locally during `edit`/`log`/`delete`. Network interaction only happens during `tn sync`:

- `fetch --prune` then divergence detection.
- If remote-ahead or diverged, you can pick:
  - `remote-wins`: hard reset to `origin/<branch>` (replaces local DB with remote).
  - `local-wins`: force-push with lease.
  - `abort`: do nothing.
- If no upstream exists, `tn sync` pushes and sets upstream.

In non-interactive sessions, prompts are disabled and an error message is shown with guidance. A clean working tree is required.

## Development

Use `uv` and the provided `Justfile` tasks:

```bash
just bootstrap   # uv sync + pre-commit install
just cli         # run CLI (defaults to --help)
just fmt         # ruff format
just lint        # ruff check
just test        # pytest
```

Coding conventions:

- PEP 8 with 4-space indentation, max line length 88.
- Type hints for public functions; keep generics simple.
- Keep runtime code under `terminotes/`; tests under `tests/`.

## Testing

Run tests with uv:

```bash
uv run pytest
```

Tests cover: SQLite persistence, CLI argument parsing, and Git workflows (git interactions are mocked in unit tests).

## Contributing

Pull requests are welcome. Before submitting:

- Follow Conventional Commits (e.g., `feat(cli): add search subcommand`).
- Run `just fmt && just lint && just test`.
- Include a summary, test output, and linked issues in your PR.

See `AGENTS.md` for repository conventions and tips.

## Roadmap

- JSON output for `ls` and `search`.
- Sort options for `ls` (e.g., by created time).
- Full-text search via SQLite FTS5.
- Additional metadata and export tools.

## Troubleshooting

- “Configuration not found”: run `uv run tn config` to create a config file.
- “Working tree has uncommitted changes”: commit or stash before `tn sync`.
- Non-interactive environments cannot prompt for divergence resolution; run `tn sync` in a terminal.

## Security

- Keep secrets and credentials outside the repo (e.g., system git credentials).
- Terminotes validates inputs and parameterizes SQL; avoid pasting secrets into notes you intend to publish.

## License

License information will be added before a stable release.
