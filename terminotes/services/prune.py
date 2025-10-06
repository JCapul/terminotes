"""Database pruning workflows for the CLI."""

from __future__ import annotations

from ..app import AppContext
from ..storage import PruneResult


def prune_unused(ctx: AppContext) -> PruneResult:
    """Prune orphaned tag links and tags, committing when changes occur."""

    result = ctx.storage.prune_unused_tags()

    if result.removed_links or result.removed_tags:
        ctx.git_sync.commit_db_update(ctx.storage.path, "chore(db): prune unused tags")

    return result
