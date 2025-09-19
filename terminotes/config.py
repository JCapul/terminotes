"""Configuration management for Terminotes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class TerminotesConfig:
    """In-memory representation of the Terminotes configuration file."""

    allowed_tags: tuple[str, ...]
    editor: str | None = None


def load_config(path: Path) -> TerminotesConfig:
    """Load configuration from ``path``.

    The implementation will be filled in during later stages. A ``NotImplementedError``
    is raised for now to signal missing functionality.
    """
    raise NotImplementedError("Configuration loading pending implementation.")


def ensure_tags_known(config: TerminotesConfig, tags: Iterable[str]) -> None:
    """Validate that each tag is present in ``config.allowed_tags``."""
    raise NotImplementedError("Tag validation pending implementation.")
