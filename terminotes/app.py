"""Application bootstrap and context container for Terminotes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import TerminotesConfig, load_config
from .git_sync import GitSync
from .storage import DB_FILENAME, Storage


@dataclass(slots=True)
class AppContext:
    """Aggregates core services for the CLI lifecycle."""

    config: TerminotesConfig
    storage: Storage
    git_sync: GitSync


def bootstrap(config_path: Path | None, *, missing_hint: bool = False) -> AppContext:
    """Load configuration and initialize storage and git sync services."""

    # Defer error mapping to the CLI, which knows how to present messages.
    config = load_config(config_path)

    git_sync = GitSync(config.terminotes_dir, config.git_remote_url)
    # Let GitSync handle creation/validation; surface errors to CLI for mapping.
    git_sync.ensure_local_clone()

    storage = Storage(config.terminotes_dir / DB_FILENAME)
    storage.initialize()

    return AppContext(config=config, storage=storage, git_sync=git_sync)
