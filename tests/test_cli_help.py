"""CLI help flag behaviour tests."""

from __future__ import annotations

from click.testing import CliRunner
from terminotes import cli


def test_cli_root_help_short_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["-h"])

    assert result.exit_code == 0
    assert "Usage" in result.output
