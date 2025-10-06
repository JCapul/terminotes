"""Click-based command-line interface for Terminotes."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import click

from .app import AppContext, bootstrap
from .config import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_CONFIG_PATH,
    ConfigError,
    MissingConfigError,
    TerminotesConfig,
    bootstrap_config_file,
)
from .editor import EditorError, open_editor
from .exporters import ExportError
from .git_sync import GitSync, GitSyncError
from .services.delete import delete_note as delete_note_workflow
from .services.export import export_notes as run_export
from .services.notes import (
    create_link_entry,
    create_log_entry,
    create_via_editor,
    update_via_editor,
)
from .services.prune import prune_unused as prune_unused_workflow
from .storage import PruneResult, Storage, StorageError
from .utils.datetime_fmt import parse_user_datetime, to_user_friendly_local

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


class TerminotesCliError(click.ClickException):
    """Shared Click exception wrapper for CLI failures."""


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-c",
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

    try:
        app = bootstrap(config_path_opt, missing_hint=True)
    except MissingConfigError as exc:
        raise TerminotesCliError(
            "Configuration not found. Run 'tn config' once to set up Terminotes."
        ) from exc
    except (ConfigError, GitSyncError, StorageError) as exc:  # pragma: no cover
        # Preserve original behaviour: map to Click exception wrapper.
        raise TerminotesCliError(str(exc)) from exc

    ctx.obj["app"] = app


@cli.command(name="edit")
@click.option(
    "-i",
    "--id",
    "note_id",
    type=int,
    default=None,
    help=("Edit the note with this id. When omitted, a new note is created."),
)
@click.option(
    "-l",
    "--last",
    "edit_last",
    is_flag=True,
    help="Edit the last updated note (mutually exclusive with --id)",
)
@click.pass_context
def edit(ctx: click.Context, note_id: int | None, edit_last: bool) -> None:
    """Create a new note or edit an existing one.

    By default, creates a new note. Use --id to edit an existing note.
    """

    app: AppContext = ctx.obj["app"]

    if note_id is not None and edit_last:
        raise TerminotesCliError("Use only one of --id or --last.")

    if note_id or edit_last:
        note_id = -1 if edit_last else note_id

        try:
            updated = update_via_editor(
                app,
                note_id,
                edit_fn=open_editor,
                warn=lambda msg: click.echo(msg),
            )
        except (EditorError, StorageError, GitSyncError) as exc:
            raise TerminotesCliError(str(exc)) from exc

        click.echo(f"Updated note {updated.id}")
        return

    # Create new note
    try:
        note_obj = create_via_editor(
            app,
            edit_fn=open_editor,
            warn=lambda msg: click.echo(msg),
        )
    except (EditorError, StorageError, GitSyncError) as exc:
        raise TerminotesCliError(str(exc)) from exc

    click.echo(f"Created note {note_obj.id}")


@cli.command(name="log")
@click.option(
    "-t",
    "--tag",
    "tags",
    multiple=True,
    help="Tag to associate with the new note (repeatable)",
)
@click.option(
    "-c",
    "--created",
    "created_opt",
    type=str,
    default=None,
    help="Set creation time (ISO 8601 or 'YYYY-MM-DD HH:MM').",
)
@click.argument("content", nargs=-1)
@click.pass_context
def log(
    ctx: click.Context,
    content: tuple[str, ...],
    tags: tuple[str, ...],
    created_opt: str | None,
) -> None:
    """Create a new log entry from CLI content.

    Usage: tn log -- This is a log entry
    """

    app: AppContext = ctx.obj["app"]

    body = " ".join(content).strip()
    if not body:
        raise TerminotesCliError("Content is required for 'tn log'.")

    tags = ("log",) + tags

    created_at = None
    if created_opt:
        try:
            created_at = parse_user_datetime(created_opt)
        except ValueError as exc:
            raise TerminotesCliError(str(exc)) from exc

    try:
        note = create_log_entry(app, body, tags=tags, created_at=created_at)
    except (StorageError, GitSyncError) as exc:  # pragma: no cover - pass-through
        raise TerminotesCliError(str(exc)) from exc

    click.echo(f"Created note {note.id} (tagged as log)")


@cli.command(name="link")
@click.argument("url")
@click.argument("comment", nargs=-1)
@click.option(
    "-t",
    "--tag",
    "tags",
    multiple=True,
    help="Tag to associate with the link note (repeatable)",
)
@click.option(
    "-c",
    "--created",
    "created_opt",
    type=str,
    default=None,
    help="Set creation time (ISO 8601 or 'YYYY-MM-DD HH:MM').",
)
@click.pass_context
def link(
    ctx: click.Context,
    url: str,
    comment: tuple[str, ...],
    tags: tuple[str, ...],
    created_opt: str | None,
) -> None:
    """Capture a URL with optional comment and Wayback fallback."""

    app: AppContext = ctx.obj["app"]
    comment_text = " ".join(comment).strip()

    created_at = None
    if created_opt:
        try:
            created_at = parse_user_datetime(created_opt)
        except ValueError as exc:
            raise TerminotesCliError(str(exc)) from exc

    try:
        note, snapshot = create_link_entry(
            app,
            url,
            comment_text,
            tags=tags,
            created_at=created_at,
            warn=lambda msg: click.echo(msg),
        )
    except ValueError as exc:
        raise TerminotesCliError(str(exc)) from exc
    except (StorageError, GitSyncError) as exc:
        raise TerminotesCliError(str(exc)) from exc

    if snapshot is not None:
        click.echo(f"Saved link note {note.id} (Wayback fallback: {snapshot['url']})")
    else:
        click.echo(f"Saved link note {note.id}")


@cli.command(name="delete")
@click.option(
    "-y",
    "--yes",
    "assume_yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.argument("note_id", type=int)
@click.pass_context
def delete(ctx: click.Context, note_id: int, assume_yes: bool) -> None:
    """Delete a note identified by NOTE_ID from the database."""

    app: AppContext = ctx.obj["app"]
    if not assume_yes:
        confirm = click.confirm(
            f"Delete note {note_id}?", default=False, show_default=True
        )
        if not confirm:
            raise TerminotesCliError("Deletion aborted.")

    try:
        delete_note_workflow(app, note_id)
    except StorageError as exc:
        raise TerminotesCliError(str(exc)) from exc
    except GitSyncError as exc:  # pragma: no cover - pass-through
        raise TerminotesCliError(str(exc)) from exc

    click.echo(f"Deleted note {note_id}")


@cli.command()
@click.pass_context
def prune(ctx: click.Context) -> None:
    """Remove unused tags and stale tag associations from the database."""

    app: AppContext = ctx.obj["app"]
    try:
        prune_result: PruneResult = prune_unused_workflow(app)
    except (StorageError, GitSyncError) as exc:
        raise TerminotesCliError(str(exc)) from exc

    if prune_result.removed_tags == 0 and prune_result.removed_links == 0:
        click.echo("Nothing to prune; tag tables already clean.")
        return

    tag_label = "tag" if prune_result.removed_tags == 1 else "tags"
    link_label = "link" if prune_result.removed_links == 1 else "links"
    click.echo(
        "Pruned "
        f"{prune_result.removed_tags} {tag_label} and "
        f"{prune_result.removed_links} orphaned {link_label}."
    )


@cli.command()
@click.option("-d", "--dry-run", is_flag=True, help="Show actions without executing.")
@click.pass_context
def sync(ctx: click.Context, dry_run: bool) -> None:
    """Synchronize local notes repo with the remote.

    Performs a fetch, detects divergence, prompts for resolution when needed,
    and pushes with the appropriate strategy. Requires a clean working tree.
    """

    app: AppContext = ctx.obj["app"]
    git_sync: GitSync = app.git_sync

    if git_sync is None or not git_sync.is_valid_repo():
        click.echo("Git repo not initialized or invalid; nothing to sync.")
        return

    # Enforce clean working tree (strict mode)
    if not git_sync.is_worktree_clean():
        raise TerminotesCliError(
            "Working tree has uncommitted changes. Commit or stash before syncing."
        )

    try:
        git_sync.fetch_prune()
        branch = git_sync.current_branch()
        state = git_sync.detect_divergence()

        if state in ("remote_ahead", "diverged"):
            choice = _prompt_divergence_resolution(ctx, state)
            if choice == "abort":
                raise TerminotesCliError("Sync aborted by user.")
            if choice == "remote-wins":
                if dry_run:
                    click.echo(f"Dry-run: would run 'git reset --hard origin/{branch}'")
                else:
                    git_sync.hard_reset_to_remote(branch)
                    click.echo(f"Replaced local DB with origin/{branch} version")
                return
            # local-wins: force push
            if dry_run:
                click.echo(
                    f"Dry-run: would run 'git push --force-with-lease origin {branch}'"
                )
            else:
                git_sync.force_push_with_lease(branch)
                click.echo(f"Force-pushed local DB to origin/{branch}")
            return

        if state == "no_upstream":
            if dry_run:
                click.echo(f"Dry-run: would run 'git push -u origin {branch}'")
            else:
                git_sync.push_set_upstream(branch)
                click.echo(f"Pushed and set upstream to origin/{branch}")
            return

        # Explicitly handle up_to_date: nothing to do
        if state == "up_to_date":
            click.echo("Already up to date; nothing to sync.")
            return

        # local_ahead
        if dry_run:
            click.echo(f"Dry-run: would run 'git push origin {branch}'")
        else:
            git_sync.push_current_branch()
            click.echo(f"Pushed updates to origin/{branch}")
    except GitSyncError as exc:
        raise TerminotesCliError(str(exc)) from exc


@cli.command()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Open the Terminotes configuration file in the editor."""

    # Use the provided --config path when present
    selected_path: Path | None = ctx.obj.get("config_path")
    effective_path = selected_path or DEFAULT_CONFIG_PATH

    created = bootstrap_config_file(effective_path)
    config_path = effective_path

    try:
        result = click.edit(filename=str(config_path))
    except OSError as exc:  # pragma: no cover - editor launch failure rare
        raise TerminotesCliError(f"Failed to launch editor: {exc}") from exc

    if created:
        click.echo(f"Created configuration at {config_path}")

    if result is None:
        click.echo(f"Opened configuration at {config_path}")
    else:  # pragma: no cover - depends on click behaviour
        click.echo(f"Updated configuration at {config_path}")


@cli.command()
@click.option("-n", "--limit", type=int, default=10, help="Maximum notes to list")
@click.option(
    "-r",
    "--reverse",
    is_flag=True,
    help="Reverse order (oldest first for current sort)",
)
@click.option(
    "-t",
    "--tag",
    "tags",
    multiple=True,
    help="Filter notes by tag (repeatable)",
)
@click.pass_context
def ls(ctx: click.Context, limit: int, reverse: bool, tags: tuple[str, ...]) -> None:
    """List the most recent notes (by last edit time)."""

    app: AppContext = ctx.obj["app"]
    storage: Storage = app.storage

    try:
        notes = list(storage.list_notes(limit=limit, tags=tags))
    except StorageError as exc:  # pragma: no cover - pass-through
        raise TerminotesCliError(str(exc)) from exc

    if reverse:
        notes = list(reversed(notes))

    for n in notes:
        updated = to_user_friendly_local(n.updated_at)
        title = n.title or ""
        tag_list = sorted(tag.name for tag in n.tags)
        tag_suffix = f"  [tags: {', '.join(tag_list)}]" if tag_list else ""
        click.echo(f"{n.id:>4}  {updated}  {title}{tag_suffix}")


@cli.command()
@click.argument("pattern")
@click.option("-n", "--limit", type=int, default=20, help="Maximum matches to show")
@click.option(
    "-r",
    "--reverse",
    is_flag=True,
    help="Reverse order (oldest first for current sort)",
)
@click.option(
    "-t",
    "--tag",
    "tags",
    multiple=True,
    help="Filter matches by tag (repeatable)",
)
@click.pass_context
def search(
    ctx: click.Context,
    pattern: str,
    limit: int,
    reverse: bool,
    tags: tuple[str, ...],
) -> None:
    """Search notes for a pattern (case-insensitive substring)."""

    app: AppContext = ctx.obj["app"]
    storage: Storage = app.storage

    pat = (pattern or "").strip()
    if not pat:
        raise TerminotesCliError("Search pattern must not be empty.")

    try:
        matches = list(storage.search_notes(pat, tags=tags))
    except StorageError as exc:  # pragma: no cover - pass-through
        raise TerminotesCliError(str(exc)) from exc

    # Order is already updated_at DESC; apply reverse if requested
    if reverse:
        matches = list(reversed(matches))

    # Apply limit after ordering (simple approach for now)
    if limit > 0:
        matches = matches[:limit]
    else:
        matches = []

    for n in matches:
        updated = to_user_friendly_local(n.updated_at)
        title = n.title or ""
        tag_list = sorted(tag.name for tag in n.tags)
        tag_suffix = f"  [tags: {', '.join(tag_list)}]" if tag_list else ""
        click.echo(f"{n.id:>4}  {updated}  {title}{tag_suffix}")


@cli.command()
@click.option(
    "-f",
    "--format",
    "export_format",
    type=click.Choice(["html", "markdown"], case_sensitive=False),
    required=True,
    help="Export format",
)
@click.option(
    "-d",
    "--dest",
    "destination",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Destination directory for the export",
)
@click.option(
    "-s",
    "--site-title",
    default="Terminotes",
    show_default=True,
    help="Site title for HTML exports",
)
@click.pass_context
def export(
    ctx: click.Context, export_format: str, destination: Path, site_title: str
) -> None:
    """Export notes as HTML or Markdown."""

    app: AppContext = ctx.obj["app"]

    if destination.exists() and destination.is_file():
        raise TerminotesCliError("Destination must be a directory path.")

    templates_root = (
        app.config.source_path.parent if app.config.source_path else DEFAULT_CONFIG_DIR
    )

    try:
        count = run_export(
            app.storage,
            export_format=export_format,
            destination=destination,
            site_title=site_title,
            templates_root=templates_root,
        )
    except ExportError as exc:
        raise TerminotesCliError(str(exc)) from exc

    click.echo(f"Exported {count} notes to {destination}")


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.pass_context
def info(ctx: click.Context) -> None:
    """Display repository information and current configuration."""

    app: AppContext = ctx.obj["app"]
    config: TerminotesConfig = app.config
    storage: Storage = app.storage

    db_path = storage.path
    total_notes = storage.count_notes()
    tag_names = storage.list_tags()

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
    tags_display = ", ".join(tag_names) if tag_names else "(none)"
    click.echo(f"  Tags          : {tags_display}")
    click.echo(f"  Last edited   : {last_id} – {last_title_display}")
    click.echo("\nConfiguration:\n")
    click.echo(config_dump)


def _prompt_divergence_resolution(ctx: click.Context, state: str) -> str:
    import sys

    if not sys.stdin.isatty():
        raise TerminotesCliError(
            "Cannot prompt in non-interactive session. "
            "Re-run in a terminal or resolve manually."
        )

    if state == "remote_ahead":
        preface = (
            "Remote has new commits. The notes database cannot be merged.\n"
            "Choose how to proceed."
        )
    else:
        preface = (
            "Local and remote have diverged. The notes database cannot be merged.\n"
            "Choose how to proceed."
        )
    click.echo(preface, err=True)

    choice = click.prompt(
        "Choose resolution",
        type=click.Choice(["local-wins", "remote-wins", "abort"], case_sensitive=False),
        default="abort",
        show_choices=True,
    ).lower()
    return choice


def _format_config(config: TerminotesConfig) -> str:
    # Render configuration as TOML for consistency.
    def quote(s: str | None) -> str:
        if s is None:
            return '""'
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    lines = [
        f"git_remote_url = {quote(config.git_remote_url)}",
        f"terminotes_dir = {quote(str(config.terminotes_dir))}",
        f"editor = {quote(config.editor)}",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv) if argv is not None else None
    try:
        return cli.main(args=args, prog_name="tn", standalone_mode=False)
    except click.ClickException as exc:
        click.echo(str(exc), err=True)
        return 1
    except SystemExit as exc:
        return int(exc.code)
