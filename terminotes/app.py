"""Application bootstrap and context container for Terminotes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import ConfigError, TerminotesConfig, load_config
from .git_sync import GitSync
from .plugins import BootstrapContext, build_settings_getter
from .plugins.runtime import run_bootstrap
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

    bootstrap_context = BootstrapContext(
        config=config, get_settings=build_settings_getter(config)
    )
    bootstrap_errors = run_bootstrap(bootstrap_context)
    if bootstrap_errors:
        first_error = bootstrap_errors[0]
        raise ConfigError(f"Plugin bootstrap failed: {first_error}") from first_error

    return AppContext(config=config, storage=storage, git_sync=git_sync)
