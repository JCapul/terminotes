"""Prune command for Terminotes CLI."""

from __future__ import annotations

import click

from ..git_sync import GitSyncError
from ..services.prune import prune_unused as prune_unused_workflow
from ..storage import PruneResult, StorageError
from ._common import TerminotesCliError, get_app


@click.command(name="prune")
@click.pass_context
def prune(ctx: click.Context) -> None:
    """Remove unused tags and stale tag associations from the database."""

    app = get_app(ctx)
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


def register(cli: click.Group) -> None:
    """Register the command with the root CLI group."""

    cli.add_command(prune)
