# Terminotes

Terminotes is a terminal-first note taking CLI focused on fast capture with tags, SQLite persistence, and optional git synchronization. Point Terminotes at a remote repository and it keeps the SQLite database in sync; if you skip the git URL it runs entirely locally.

## Getting Started

```bash
uv sync
uv run python -m terminotes --help
```

Run `uv run python -m terminotes config` once to bootstrap `~/.config/terminotes/config.toml`, then customise the file. Set `git_remote_url` to enable git sync. You can also change where the local repository lives via `terminotes_dir` (absolute or relative to the config directory).

Use the `Justfile` shortcuts to run common workflows once the environment is bootstrapped.

## Git Sync

When `git_remote_url` is configured, Terminotes uses plain Git for synchronization.

- `tn new` and `tn edit` commit the SQLite DB locally only (no network).
- Run `tn sync` to interact with the remote:
  - Fetches and checks for divergence.
  - If remote-ahead or diverged, you’ll be prompted:
    - `local-wins`: force-push local DB to the remote (`--force-with-lease`).
    - `remote-wins`: discard local changes and hard reset to the remote.
    - `abort`: stop and leave the repo unchanged.
  - If there’s no upstream, `tn sync` sets it and pushes.
  - In non-interactive sessions, prompts are not possible and `tn sync` aborts with guidance.
  - Requires a clean working tree; commit or stash changes before syncing.
