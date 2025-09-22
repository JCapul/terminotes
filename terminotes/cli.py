"""Click-based command-line interface for Terminotes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import click
import yaml

from .config import (
    DEFAULT_CONFIG_PATH,
    ConfigError,
    MissingConfigError,
    TerminotesConfig,
    load_config,
)
from .editor import EditorError, open_editor
from .git_sync import GitSync, GitSyncError
from .storage import DB_FILENAME, Storage, StorageError


class TerminotesCliError(click.ClickException):
    """Shared Click exception wrapper for CLI failures."""


@dataclass(slots=True)
class ParsedEditorNote:
    """Outcome of parsing the editor payload."""

    title: str | None
    body: str
    tags: tuple[str, ...]
    metadata: dict[str, Any]

    @property
    def content(self) -> str:
        if self.title:
            if self.body:
                return f"{self.title}\n\n{self.body}".strip()
            return self.title.strip()
        return self.body.strip()


@click.group()
@click.option(
    "--config",
    "config_path_opt",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to configuration TOML file.",
)
@click.pass_context
def cli(ctx: click.Context, config_path_opt: Path | None) -> None:
    """Terminotes command group."""

    ctx.ensure_object(dict)
    invoked = ctx.invoked_subcommand

    if invoked is None:
        click.echo(ctx.command.get_help(ctx))
        ctx.exit(0)

    # Persist the selected config path for subcommands like 'config'
    ctx.obj["config_path"] = config_path_opt

    if invoked == "config":
        return

    config_obj = _load_configuration(
        config_path_opt, allow_create=False, missing_hint=True
    )
    storage = Storage(config_obj.repo_path / DB_FILENAME)
    _initialize_storage(storage)

    git_sync = _initialize_git_sync(config_obj)

    ctx.obj["config"] = config_obj
    ctx.obj["storage"] = storage
    ctx.obj["git_sync"] = git_sync


@cli.command()
@click.pass_context
def new(ctx: click.Context) -> None:
    """Create a new note using the configured editor."""

    config: TerminotesConfig = ctx.obj["config"]
    storage: Storage = ctx.obj["storage"]

    timestamp = _current_timestamp()
    metadata = {
        "title": "",
        "date": timestamp,
        "last_edited": timestamp,
        "tags": [],
    }

    template = _render_editor_document(title="", body="", metadata=metadata)
    parsed = _invoke_editor(template, config.editor)

    final_tags = _normalize_tags_or_warn(config, parsed.tags)

    try:
        note = storage.create_note(parsed.title or "", parsed.body, final_tags)
    except StorageError as exc:
        raise TerminotesCliError(str(exc)) from exc

    click.echo(f"Created note {note.id}")


@cli.command(name="edit")
@click.argument("note_id", required=False, type=int)
@click.pass_context
def edit(ctx: click.Context, note_id: int | None) -> None:
    """Edit an existing note by its ID."""

    config: TerminotesConfig = ctx.obj["config"]
    storage: Storage = ctx.obj["storage"]

    try:
        if note_id is None:
            existing = storage.fetch_last_updated_note()
            note_id = existing.id
        else:
            existing = storage.fetch_note(note_id)
    except StorageError as exc:
        raise TerminotesCliError(str(exc)) from exc

    now_iso = _current_timestamp()
    title = existing.title or ""
    body = existing.body
    metadata: dict[str, Any] = {
        "title": title or "",
        "date": existing.created_at.isoformat(),
        "last_edited": now_iso,
    }
    if existing.tags:
        metadata["tags"] = list(existing.tags)

    template = _render_editor_document(
        title=metadata["title"], body=body, metadata=metadata
    )
    parsed = _invoke_editor(template, config.editor)

    if parsed.tags:
        final_tags = _normalize_tags_or_warn(config, parsed.tags)
    else:
        final_tags = existing.tags

    try:
        updated = storage.update_note(
            note_id, parsed.title or "", parsed.body, final_tags
        )
    except StorageError as exc:
        raise TerminotesCliError(str(exc)) from exc

    click.echo(f"Updated note {updated.id}")


@cli.command()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Open the Terminotes configuration file in the editor."""

    # Use the provided --config path when present
    selected_path: Path | None = ctx.obj.get("config_path")
    effective_path = selected_path or DEFAULT_CONFIG_PATH

    created = _bootstrap_config_file(effective_path)
    config_obj = _load_configuration(effective_path, allow_create=False)
    config_path = config_obj.source_path
    if config_path is None:  # pragma: no cover - defensive
        raise TerminotesCliError("Configuration path is not available.")

    try:
        result = click.edit(filename=str(config_path), editor=config_obj.editor)
    except OSError as exc:  # pragma: no cover - editor launch failure rare
        raise TerminotesCliError(f"Failed to launch editor: {exc}") from exc

    if created:
        click.echo(f"Created configuration at {config_path}")

    if result is None:
        click.echo(f"Opened configuration at {config_path}")
    else:  # pragma: no cover - depends on click behaviour
        click.echo(f"Updated configuration at {config_path}")


@cli.command()
@click.pass_context
def ls(ctx: click.Context) -> None:  # pragma: no cover - placeholder
    """List the most recent notes."""

    click.echo("Subcommand 'ls' is not implemented yet.")


@cli.command()
@click.argument("pattern")
@click.pass_context
def search(ctx: click.Context, pattern: str) -> None:  # pragma: no cover
    """Search notes for a pattern."""

    click.echo(f"Subcommand 'search' is not implemented yet (pattern: {pattern}).")


@cli.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Display repository information and current configuration."""

    config: TerminotesConfig = ctx.obj["config"]
    storage: Storage = ctx.obj["storage"]

    db_path = storage.path
    total_notes = storage.count_notes()

    try:
        last_note = storage.fetch_last_updated_note()
        last_title_display = last_note.title or "(title inferred from body)"
        last_id = last_note.id
    except StorageError:
        last_title_display = "(none)"
        last_id = "-"

    config_dump = _format_config(config)

    click.echo("Terminotes repository info:\n")
    click.echo(f"  Database file : {db_path}")
    click.echo(f"  Total notes   : {total_notes}")
    click.echo(f"  Last edited   : {last_id} – {last_title_display}")
    click.echo("\nConfiguration:\n")
    click.echo(config_dump)


def _load_configuration(
    path: Path | None = None,
    *,
    allow_create: bool,
    missing_hint: bool = False,
) -> TerminotesConfig:
    try:
        return load_config(path)
    except MissingConfigError as exc:
        if allow_create:
            _bootstrap_config_file(exc.path)
            return load_config(exc.path)
        if missing_hint:
            raise TerminotesCliError(
                "Configuration not found. Run 'tn config' once to set up Terminotes."
            ) from exc
        raise TerminotesCliError(str(exc)) from exc
    except ConfigError as exc:  # pragma: no cover - exercised via CLI tests
        raise TerminotesCliError(str(exc)) from exc


def _initialize_storage(storage: Storage) -> None:
    try:
        storage.initialize()
    except StorageError as exc:
        raise TerminotesCliError(str(exc)) from exc


def _initialize_git_sync(config: TerminotesConfig) -> GitSync | None:
    if not config.notes_repo_url:
        return None

    git_sync = GitSync(config.repo_path, config.notes_repo_url)
    try:
        git_sync.ensure_local_clone()
    except GitSyncError as exc:
        raise TerminotesCliError(str(exc)) from exc
    return git_sync


def _normalize_tags_or_warn(
    config: TerminotesConfig, tags: Iterable[str]
) -> tuple[str, ...]:
    # Keep only allowed tags; warn about unknown ones.
    allowed = set(config.allowed_tags)
    original = list(tags)
    valid = [t for t in original if t in allowed]
    unknown = [t for t in original if t not in allowed]
    if unknown:
        unknown_list = ", ".join(unknown)
        click.echo(
            f"Warning: Unknown tag(s): {unknown_list}. Saving without them.",
        )
    # Preserve order, remove duplicates
    deduped: list[str] = []
    for t in valid:
        if t not in deduped:
            deduped.append(t)
    return tuple(deduped)


def _render_editor_document(title: str, body: str, metadata: dict[str, Any]) -> str:
    payload = yaml.safe_dump(metadata, sort_keys=False).strip()
    body_block = body.rstrip()
    if body_block:
        return f"---\n{payload}\n---\n\n{body_block}\n"
    return f"---\n{payload}\n---\n\n"


def _invoke_editor(template: str, editor: str | None) -> ParsedEditorNote:
    try:
        raw_note = open_editor(template, editor=editor)
    except EditorError as exc:
        raise TerminotesCliError(str(exc)) from exc

    parsed = _parse_editor_note(raw_note)
    return parsed


def _parse_editor_note(raw: str) -> ParsedEditorNote:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        stripped = raw.strip()
        return ParsedEditorNote(title=None, body=stripped, tags=(), metadata={})

    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        stripped = raw.strip()
        return ParsedEditorNote(title=None, body=stripped, tags=(), metadata={})

    metadata_block = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :]).strip()

    metadata: dict[str, Any] = {}
    try:
        loaded = yaml.safe_load(metadata_block) or {}
        if isinstance(loaded, dict):
            metadata = loaded
    except yaml.YAMLError:
        metadata = {}

    title: str | None = None
    title_value = metadata.get("title")
    if isinstance(title_value, str):
        title = title_value.strip() or None

    tags_value = metadata.get("tags")
    tags: tuple[str, ...]
    if isinstance(tags_value, str):
        tags_iter = [part.strip() for part in tags_value.split(",") if part.strip()]
        tags = tuple(tags_iter)
    elif isinstance(tags_value, Iterable) and not isinstance(tags_value, (str, bytes)):
        tags = tuple(str(tag).strip() for tag in tags_value if str(tag).strip())
    else:
        tags = ()

    return ParsedEditorNote(title=title, body=body, tags=tags, metadata=metadata)


def _split_content(content: str) -> tuple[str | None, str]:
    if not content:
        return None, ""
    parts = content.split("\n\n", 1)
    if len(parts) == 2:
        title = parts[0].strip() or None
        body = parts[1].strip()
        return title, body
    return None, content.strip()


def _current_timestamp() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _format_config(config: TerminotesConfig) -> str:
    data: dict[str, Any] = {
        "notes_repo_url": config.notes_repo_url,
        "repo_path": str(config.repo_path),
        "allowed_tags": list(config.allowed_tags),
        "editor": config.editor,
    }

    return yaml.safe_dump(data, sort_keys=False).strip()


def _bootstrap_config_file(path: Path) -> bool:
    if path.exists():
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    default_content = 'notes_repo_url = ""\nallowed_tags = []\neditor = "vim"\n'
    path.write_text(default_content, encoding="utf-8")
    return True


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv) if argv is not None else None
    try:
        return cli.main(args=args, prog_name="tn", standalone_mode=False)
    except click.ClickException as exc:
        click.echo(str(exc), err=True)
        return 1
    except SystemExit as exc:
        return int(exc.code)
