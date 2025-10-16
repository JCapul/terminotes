"""Sync command for Terminotes CLI."""

from __future__ import annotations

import sys

import click

from ..git_sync import GitSync, GitSyncError
from ._common import TerminotesCliError, get_app


@click.command(name="sync")
@click.option("-d", "--dry-run", is_flag=True, help="Show actions without executing.")
@click.pass_context
def sync(ctx: click.Context, dry_run: bool) -> None:
    """Synchronize local notes repo with the remote."""

    app = get_app(ctx)
    git_sync: GitSync | None = app.git_sync

    if git_sync is None or not git_sync.is_valid_repo():
        click.echo("Git repo not initialized or invalid; nothing to sync.")
        return

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

        if state == "up_to_date":
            click.echo("Already up to date; nothing to sync.")
            return

        if dry_run:
            click.echo(f"Dry-run: would run 'git push origin {branch}'")
        else:
            git_sync.push_current_branch()
            click.echo(f"Pushed updates to origin/{branch}")
    except GitSyncError as exc:
        raise TerminotesCliError(str(exc)) from exc


def _prompt_divergence_resolution(ctx: click.Context, state: str) -> str:
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


def register(cli: click.Group) -> None:
    """Register the command with the root CLI group."""

    cli.add_command(sync)
