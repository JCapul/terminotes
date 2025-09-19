"""Command-line interface scaffolding for Terminotes."""

from __future__ import annotations

import argparse
from typing import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Configure the CLI argument parser structure."""
    parser = argparse.ArgumentParser(
        prog="qn",
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

    if args.command is None:
        print("Terminotes CLI scaffolding is in place. Feature implementation coming soon.")
        parser.print_help()
        return 0

    print(f"Subcommand '{args.command}' is not implemented yet.")
    return 0
