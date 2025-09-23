# Terminotes

Terminotes is a terminal-first note taking CLI focused on fast capture with tags, SQLite persistence, and optional git synchronization. Point Terminotes at a remote repository and it keeps the SQLite database in sync; if you skip the git URL it runs entirely locally.

## Getting Started

```bash
uv sync
uv run python -m terminotes --help
```

Run `uv run python -m terminotes config` once to bootstrap `~/.config/terminotes/config.toml`, then customise the file. Set `notes_repo_url` to enable git sync or leave it blank to keep notes purely local. You can also change where the local repository lives via `notes_repo_path` (absolute or relative to the config directory).

Use the `Justfile` shortcuts to run common workflows once the environment is bootstrapped.

## Git Sync

When `notes_repo_url` is configured, Terminotes syncs the SQLite database using plain Git:

- After each successful `new` or `edit`, Terminotes stages the DB file, commits, and pushes to the current branch.
- If the push fails due to remote/local divergence, you’ll be prompted with options:
  - `local-wins`: force-push your local database to the remote (uses `--force-with-lease`).
  - `remote-wins`: discard local changes to the DB and hard reset to the remote.
  - `abort`: stop and leave the repo unchanged.
- Non-interactive sessions cannot prompt; Terminotes aborts with guidance.
