"""Info command for Terminotes CLI."""

from __future__ import annotations

import click

from ..config import TerminotesConfig
from ..storage import Storage, StorageError
from ._common import get_app


@click.command(name="info")
@click.pass_context
def info(ctx: click.Context) -> None:
    """Display repository information and current configuration."""

    app = get_app(ctx)
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


def _format_config(config: TerminotesConfig) -> str:
    def quote(value: str | None) -> str:
        if value is None:
            return '""'
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

    lines = [
        "[terminotes]",
        f"git_remote_url = {quote(config.git_remote_url)}",
        f"terminotes_dir = {quote(str(config.terminotes_dir))}",
        f"editor = {quote(config.editor)}",
    ]
    return "\n".join(lines)


def register(cli: click.Group) -> None:
    """Register the command with the root CLI group."""

    cli.add_command(info)
