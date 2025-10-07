Terminotes
  [![Version](http://img.shields.io/pypi/v/terminotes.svg?style=flat)](https://pypi.python.org/pypi/terminotes/)
  [![Downloads](https://pepy.tech/badge/terminotes)](https://pepy.tech/project/terminotes)
===

Terminotes is a terminal-first note taking CLI, 99% vibecoded with Codex CLI and GPT-5 under my tight supervision 😉.

It focuses on fast capture from a shell, durable storage in SQLite, and simple Git synchronization so you can keep your notes database in a repo and carry it between machines.


## Features

- Fast capture via editor (`tn edit`) and direct log entries (`tn log -- ...`).
- SQLite storage with simple schema and safe parameterized queries.
- Git-backed portability: store the DB in a repo and sync on demand.
- Practical commands: list, search, delete, info, sync, and export.
- Link capture with `tn link`, including optional comments, auto-applied `link` tags, and Wayback fallbacks.

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) for environment and workflow.
- Git installed and a reachable remote for your notes repo.

## Installation

Install Terminotes globally via uv:

```bash
uv tool install terminotes
```

This places the `tn` console script on your `PATH`, so you can invoke Terminotes from any shell without activating a virtual environment. Use `tn --help` to explore the CLI. If you prefer a local development checkout, follow the contributing instructions later in this document.

## Quick Start

1) Create or edit your configuration file:

```bash
tn config
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
tn edit
```

3) List your notes:

```bash
tn ls --limit 10
```

4) Sync with the remote when ready:

```bash
tn sync
```

## Usage

Below are the primary subcommands. Use `tn --help` and `tn <cmd> --help` for details.

- `config` — Create/open the config file in your editor.
  - Example: `tn config`

- `edit` — Create a new note or edit an existing one.
  - New note: `tn edit`
  - Edit by id: `tn edit --id 42`
  - Edit last updated: `tn edit --last`

- `log` — Quick log entry without opening an editor.
  - Example: `tn log --tag work --tag focus -- This is a log entry`
  - Title is derived from the first sentence or line, truncated when long.
  - Repeat `--tag` to associate tags; tag names are normalized to lowercase.
- `link` — Save a URL with optional comment and Wayback fallback metadata.
  - Example: `tn link https://example.com "Great article" --tag reading`
  - Multi-word comments become the first paragraph of the note body, followed by the Markdown link (and Wayback fallback when present).
  - Automatically adds the `link` tag alongside any additional `--tag` arguments and stores the latest archived snapshot (when available) under the note's extra data.
  - Fetches the page title and appends the hostname when possible; otherwise the raw URL becomes the note title. A warning is shown if no Wayback snapshot is available.

- `ls` — List most recent notes (by last edit time).
  - Example: `tn ls --limit 10 --tag work`
  - Options: `--limit/-n`, `--reverse`, `--tag/--tag` (filter by tag; repeatable)

- `search` — Simple case-insensitive substring search across title/body/description.
  - Example: `tn search python --tag personal`
  - Options: `--limit/-n`, `--reverse`, `--tag/--tag`

- `delete` — Delete a note by id.
  - Example: `tn delete --yes 42`
  - Uses a confirmation prompt unless `--yes` is provided.

- `prune` — Remove unused tags and stale tag associations.
  - Example: `tn prune`

- `sync` — Fetch, detect divergence, and push with the selected strategy.
  - Requires a clean working tree; commit or stash changes first.
  - Divergence prompt choices: `local-wins`, `remote-wins`, or `abort`.

- `export` — Render notes to a static site or Markdown files.
  - HTML: `tn export --format html --dest ./site --site-title "My Notes"`
  - Markdown: `tn export --format markdown --dest ./markdown`
  - Outputs go into the destination directory, which is created if missing.

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
- `extra_data` (TEXT as JSON) for structured metadata, e.g. link source and Wayback fallback URLs captured by `tn link`.
- Tags are stored in a normalized (lowercase) many-to-many table; each note can belong to multiple tags and vice versa.

Timestamps are stored in UTC.

## Git Sync

Terminotes uses your local clone of the notes repository and commits SQLite changes locally during `edit`/`log`/`delete`/`prune`. Network interaction only happens during `tn sync`:

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
just bootstrap    # uv sync + pre-commit install
just fmt          # ruff format
just lint         # ruff check
just test         # pytest
just precommit    # run all pre-commit tasks
```

## Contributing

Pull requests are welcome. Before submitting:

- Follow Conventional Commits (e.g., `feat(cli): add search subcommand`).
- Run `just precommit`.
- Include a summary, test output, and linked issues in your PR.

See `AGENTS.md` for repository conventions and tips.
