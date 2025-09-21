# Terminotes

Terminotes is a terminal-first note taking CLI focused on fast capture with tags, SQLite persistence, and an optional backup mechanism. The default provider mirrors the SQLite database into a git repository, but the architecture allows other backup strategies to slot in later.

## Getting Started

```bash
uv sync
uv run python -m terminotes --help
```

Run `uv run python -m terminotes config` once to bootstrap `~/.config/terminotes/config.toml`, then customise the file. Enable the default Git backup by providing a `backup.repo_url`, or disable the backup block entirely if you prefer to manage persistence locally.

Use the `Justfile` shortcuts to run common workflows once the environment is bootstrapped.
