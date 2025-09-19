"""Command-line interface scaffolding for Terminotes."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .config import ConfigError, InvalidConfigError, ensure_tags_known, load_config
from .git_sync import GitSync, GitSyncError


def build_parser() -> argparse.ArgumentParser:
    """Configure the CLI argument parser structure."""
    parser = argparse.ArgumentParser(
        prog="tn",
        description="Terminotes – quick notes from your terminal.",
    )
    parser.add_argument(
        "message",
        nargs="?",
        help="One-line note content (opens editor when omitted).",
    )
    parser.add_argument(
        "--tags",
        metavar="TAG[,TAG]",
        help="Comma-separated tags to attach to the note.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (default: ~/.config/terminotes/config.toml).",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "ls",
        help="List the most recent notes.",
    )

    update_parser = subparsers.add_parser(
        "update",
        help="Update an existing note by its ID.",
    )
    update_parser.add_argument("note_id", help="Identifier of the note to update.")

    search_parser = subparsers.add_parser(
        "search",
        help="Search notes for a pattern.",
    )
    search_parser.add_argument("pattern", help="Pattern to search in notes.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point invoked by ``python -m terminotes`` or the ``qn`` script."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        parser.error(str(exc))

    git_sync = GitSync(config.normalized_repo_path, config.notes_repo_url)
    try:
        git_sync.ensure_local_clone()
    except GitSyncError as exc:
        parser.error(str(exc))

    parsed_tags = _parse_tags(args.tags)
    try:
        ensure_tags_known(config, parsed_tags)
    except InvalidConfigError as exc:
        parser.error(str(exc))

    if args.command is None:
        print("Terminotes CLI scaffolding is in place. Features arriving soon.")
        parser.print_help()
        return 0

    print(f"Subcommand '{args.command}' is not implemented yet.")
    return 0


def _parse_tags(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    tags = [part.strip() for part in raw.split(",") if part.strip()]
    return tuple(tags)
