#!/usr/bin/env python3
"""Prepare a new Terminotes release."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import click

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for older Python
    import tomli as tomllib  # type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


class ReleaseError(RuntimeError):
    """Raised when the release preparation fails."""


def main() -> None:
    args = parse_args()
    os.chdir(REPO_ROOT)

    ensure_clean_worktree()
    run_command(
        ["uv", "run", "pre-commit", "run", "--all-files"], "Running pre-commit hooks"
    )
    ensure_clean_worktree()

    previous_tag = get_latest_tag()
    if previous_tag is None:
        raise ReleaseError("No git tag found. Tag the current version before bumping.")

    run_command(
        ["uv", "version", "--bump", args.bump], f"Bumping version ({args.bump})"
    )
    new_version = read_project_version()
    if tag_exists(new_version):
        raise ReleaseError(f"Tag '{new_version}' already exists.")

    commits = collect_commits(previous_tag)
    if not commits:
        raise ReleaseError(f"No commits found between {previous_tag} and HEAD.")

    print(f"Commits since {previous_tag}:")
    for message in commits:
        print(f"  - {message}")

    update_changelog(new_version, commits)

    click.echo("Opening CHANGELOG.md for review...")
    click.edit(filename=str(CHANGELOG_PATH))

    run_command(["git", "add", "--all"], "Staging release files")
    run_command(
        ["git", "commit", "-m", f"Version {new_version}"], "Creating release commit"
    )
    run_command(
        ["git", "tag", "-a", new_version, "-m", f"Version {new_version}"],
        "Creating release tag",
    )

    clean_dist()
    run_command(["uv", "build"], "Building distribution artifacts")

    print(
        f"\nRelease {new_version} prepared successfully. \
            Don't forget to 'git push --tags' when you're done."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a new Terminotes release.")
    parser.add_argument(
        "bump",
        choices=("major", "minor", "patch"),
        help="Semantic version component to bump.",
    )
    return parser.parse_args()


def run_command(
    command: list[str], description: str | None = None
) -> subprocess.CompletedProcess[str]:
    if description:
        print(description)
    print("  $", " ".join(command))
    result = subprocess.run(command, text=True)
    if result.returncode != 0:
        raise ReleaseError(f"Command failed: {' '.join(command)}")
    return result


def ensure_clean_worktree() -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ReleaseError("Failed to check git status.")
    status = result.stdout.strip()
    if status:
        raise ReleaseError("Working tree is not clean. Commit or stash changes first.")


def get_latest_tag() -> str | None:
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "tag", "--list", tag], capture_output=True, text=True
    )
    return tag in result.stdout.splitlines()


def read_project_version() -> str:
    with PYPROJECT_PATH.open("rb") as fh:
        data = tomllib.load(fh)
    try:
        return str(data["project"]["version"])
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise ReleaseError("Version missing from pyproject.toml") from exc


def collect_commits(previous_tag: str) -> list[str]:
    result = subprocess.run(
        [
            "git",
            "log",
            f"{previous_tag}..HEAD",
            "--pretty=format:%s",
            "--no-merges",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseError("Failed to collect commit messages.")
    commits = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return commits


def update_changelog(version: str, commits: list[str]) -> None:
    today = date.today().isoformat()
    entry_lines = [f"## {version} - {today}", ""]
    entry_lines.extend(f"- {message}" for message in commits)
    entry_lines.append("")
    entry = "\n".join(entry_lines)

    if CHANGELOG_PATH.exists():
        existing = CHANGELOG_PATH.read_text(encoding="utf-8")
        header, separator, rest = existing.partition("\n")
        if not header.strip().startswith("# Changelog"):
            rest = existing
            header = "# Changelog"
            separator = "\n"
        else:
            rest = rest.lstrip("\n")
        new_content = f"{header}{separator}\n{entry}{rest}".rstrip() + "\n"
    else:
        new_content = f"# Changelog\n\n{entry}"

    CHANGELOG_PATH.write_text(new_content, encoding="utf-8")
    print("Updated CHANGELOG.md")


def clean_dist() -> None:
    dist_path = REPO_ROOT / "dist"
    if dist_path.exists():
        shutil.rmtree(dist_path)
    dist_path.mkdir(parents=True, exist_ok=True)
    print("Cleaned dist/ directory")


if __name__ == "__main__":
    try:
        main()
    except ReleaseError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
