"""Tests covering export plugin integration flow."""

from __future__ import annotations

import types
from pathlib import Path

import pytest
from terminotes.exporters import ExportError
from terminotes.plugins import ExportContribution, hookimpl
from terminotes.services import export as export_service
from terminotes.storage import Storage


@pytest.fixture(autouse=True)
def reset_export_registry() -> None:
    """Ensure plugin discovery cache is cleared between tests."""

    export_service.clear_export_registry_cache()
    yield
    export_service.clear_export_registry_cache()


def _with_plugin(module: types.ModuleType):
    original = export_service._iter_plugin_modules

    def combined() -> tuple[object, ...]:
        return original() + (module,)

    return combined


def test_export_notes_invokes_custom_plugin(tmp_path: Path, monkeypatch) -> None:
    state: dict[str, object] = {}
    module = types.ModuleType("terminotes_test_plugin")

    @hookimpl
    def export_formats() -> tuple[ExportContribution, ...]:
        def formatter(
            *,
            storage: Storage,
            destination: Path,
            options: dict[str, object] | None = None,
        ) -> int:
            destination.mkdir(parents=True, exist_ok=True)
            notes = storage.snapshot_notes()
            state["called"] = True
            state["notes"] = len(notes)
            state["options"] = dict(options or {})
            return 99

        return (
            ExportContribution(
                format_id="dummy",
                formatter=formatter,
                description="Dummy exporter",
            ),
        )

    module.export_formats = export_formats

    monkeypatch.setattr(export_service, "_iter_plugin_modules", _with_plugin(module))

    storage = Storage(tmp_path / "notes.db")
    storage.initialize()
    storage.create_note("Example", "Body")

    destination = tmp_path / "out"
    count = export_service.export_notes(
        storage,
        export_format="dummy",
        destination=destination,
        site_title="Custom",
        templates_root=tmp_path,
    )

    assert count == 99
    assert destination.exists()
    assert state["called"] is True
    assert state["notes"] == 1
    assert state["options"]["site_title"] == "Custom"


def test_export_notes_wraps_plugin_error(tmp_path: Path, monkeypatch) -> None:
    module = types.ModuleType("terminotes_failing_plugin")

    @hookimpl
    def export_formats() -> tuple[ExportContribution, ...]:
        def formatter(
            *,
            storage: Storage,
            destination: Path,
            options: dict[str, object] | None = None,
        ) -> int:
            raise RuntimeError("boom")

        return (
            ExportContribution(
                format_id="broken",
                formatter=formatter,
                description="Broken exporter",
            ),
        )

    module.export_formats = export_formats

    monkeypatch.setattr(export_service, "_iter_plugin_modules", _with_plugin(module))

    storage = Storage(tmp_path / "notes.db")
    storage.initialize()

    with pytest.raises(ExportError) as exc_info:
        export_service.export_notes(
            storage,
            export_format="broken",
            destination=tmp_path / "out",
        )

    message = str(exc_info.value)
    assert "broken" in message
    assert "unexpected error" in message.lower()
