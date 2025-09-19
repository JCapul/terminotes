"""Click-based command-line interface for Terminotes."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Sequence

import click

from .config import (
    ConfigError,
    InvalidConfigError,
    TerminotesConfig,
    ensure_tags_known,
    load_config,
)
from .editor import DEFAULT_TEMPLATE, EditorError, open_editor
from .git_sync import GitSync, GitSyncError
from .storage import DB_FILENAME, Storage, StorageError


class TerminotesCliError(click.ClickException):
    """Shared Click exception wrapper for CLI failures."""


@click.group(invoke_without_command=True)
@click.option(
    "--tags",
    callback=lambda _, __, value: _parse_tags(value),
    help="Comma-separated tags to attach to the note.",
)
@click.option(
    "--config",
    type=click.Path(path_type=Path),
    help="Path to configuration file (default: ~/.config/terminotes/config.toml).",
)
@click.argument("message", nargs=-1)
@click.pass_context
def cli(ctx: click.Context, tags: tuple[str, ...], config: Path | None, message: Sequence[str]) -> None:
    """Terminotes entrypoint that also supports direct note capture."""

    config_obj = _load_configuration(config)
    git_sync = GitSync(config_obj.normalized_repo_path, config_obj.notes_repo_url)
    _ensure_clone(git_sync)

    storage = Storage(config_obj.normalized_repo_path / DB_FILENAME)
    _initialize_storage(storage)

    if tags:
        ensure_tags_known_or_die(config_obj, tags)

    ctx.obj = {
        "config": config_obj,
        "storage": storage,
        "cli_tags": tags,
    }

    if ctx.invoked_subcommand is None:
        content = _normalize_message(message)
        _handle_note_creation(config_obj, storage, content, tags)


@cli.command()
@click.pass_context
def ls(ctx: click.Context) -> None:  # pragma: no cover - placeholder for Stage 5
    """List the most recent notes."""

    click.echo("Subcommand 'ls' is not implemented yet.")


@cli.command()
@click.argument("note_id")
@click.pass_context
def update(ctx: click.Context, note_id: str) -> None:  # pragma: no cover
    """Update an existing note by its ID."""

    click.echo(f"Subcommand 'update' is not implemented yet (ID: {note_id}).")


@cli.command()
@click.argument("pattern")
@click.pass_context
def search(ctx: click.Context, pattern: str) -> None:  # pragma: no cover
    """Search notes for a pattern."""

    click.echo(f"Subcommand 'search' is not implemented yet (pattern: {pattern}).")


def _load_configuration(path: Path | None) -> TerminotesConfig:
    try:
        return load_config(path)
    except ConfigError as exc:  # pragma: no cover - exercised via CLI tests
        raise TerminotesCliError(str(exc)) from exc


def _ensure_clone(git_sync: GitSync) -> None:
    try:
        git_sync.ensure_local_clone()
    except GitSyncError as exc:
        raise TerminotesCliError(str(exc)) from exc


def _initialize_storage(storage: Storage) -> None:
    try:
        storage.initialize()
    except StorageError as exc:
        raise TerminotesCliError(str(exc)) from exc


def ensure_tags_known_or_die(config: TerminotesConfig, tags: Iterable[str]) -> None:
    try:
        ensure_tags_known(config, tags)
    except InvalidConfigError as exc:
        raise TerminotesCliError(str(exc)) from exc


def _parse_tags(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    tags = [part.strip() for part in raw.split(",") if part.strip()]
    return tuple(tags)


def _normalize_message(parts: Sequence[str]) -> str | None:
    if not parts:
        return None
    text = " ".join(parts).strip()
    return text or None


def _handle_note_creation(
    config: TerminotesConfig,
    storage: Storage,
    message: str | None,
    cli_tags: Sequence[str],
) -> None:
    if message is not None:
        content = message.strip()
        if not content:
            raise TerminotesCliError("Cannot create an empty note.")
        final_tags = tuple(cli_tags)
    else:
        template = _build_template(cli_tags)
        try:
            raw_note = open_editor(template, editor=config.editor)
        except EditorError as exc:
            raise TerminotesCliError(str(exc)) from exc

        content, template_tags = _parse_editor_note(raw_note)
        if not content:
            raise TerminotesCliError("Cannot create an empty note.")

        if cli_tags:
            final_tags = tuple(cli_tags)
        else:
            if template_tags:
                ensure_tags_known_or_die(config, template_tags)
                final_tags = template_tags
            else:
                final_tags = ()

    try:
        note = storage.create_note(content, final_tags)
    except StorageError as exc:
        raise TerminotesCliError(str(exc)) from exc

    click.echo(f"Created note {note.note_id}")


def _build_template(tags: Sequence[str]) -> str:
    if not tags:
        return DEFAULT_TEMPLATE
    tag_block = ", ".join(tags)
    return DEFAULT_TEMPLATE.replace("tags: []", f"tags: [{tag_block}]")


def _parse_editor_note(raw: str) -> tuple[str, tuple[str, ...]]:
    lines = raw.splitlines()
    if not lines:
        return "", ()

    if lines[0].strip() != "---":
        return raw.strip(), ()

    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        return raw.strip(), ()

    metadata = lines[1:closing_index]
    body_lines = lines[closing_index + 1 :]

    title: str | None = None
    tags: tuple[str, ...] = ()

    for line in metadata:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "title":
            title = value
        elif key == "tags" and value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if inner:
                tags = tuple(part.strip() for part in inner.split(",") if part.strip())

    body = "\n".join(body_lines).strip()
    if title:
        if body:
            content = f"{title}\n\n{body}"
        else:
            content = title
    else:
        content = body

    return content.strip(), tags


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv) if argv is not None else None
    try:
        return cli.main(args=args, prog_name="tn", standalone_mode=False)
    except click.ClickException as exc:
        click.echo(str(exc), err=True)
        return 1
    except SystemExit as exc:
        return int(exc.code)
