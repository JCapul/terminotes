# Terminotes

Terminotes is a terminal-first note taking CLI focused on fast capture with tags, SQLite persistence, and optional git synchronization. Point Terminotes at a remote repository and it keeps the SQLite database in sync; if you skip the git URL it runs entirely locally.

## Getting Started

```bash
uv sync
uv run python -m terminotes --help
```

Run `uv run python -m terminotes config` once to bootstrap `~/.config/terminotes/config.toml`, then customise the file. Set `notes_repo_url` to enable git sync or leave it blank to keep notes purely local.

Use the `Justfile` shortcuts to run common workflows once the environment is bootstrapped.
