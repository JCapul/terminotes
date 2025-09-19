# Terminotes

Terminotes is a terminal-first note taking CLI focused on fast capture with tags, SQLite persistence, and automatic git sync. Notes are stored in a SQLite database inside a git repository so they can follow you everywhere.

## Getting Started

```bash
uv sync
uv run python -m terminotes --help
```

Copy `config/config.sample.toml` to your configuration directory (default `~/.config/terminotes/config.toml`), set `notes_repo_url`, and populate `allowed_tags` before running the CLI. Terminotes clones the notes repository into its config directory automatically.

Use the `Justfile` shortcuts to run common workflows once the environment is bootstrapped.
