"""Tests covering export plugin integration flow."""

from __future__ import annotations

import types
from pathlib import Path

import pytest
from terminotes.plugins import ExportContribution, hookimpl
from terminotes.plugins import manager as plugin_manager
from terminotes.services import export as export_service
from terminotes.services.export import ExportError
from terminotes.storage import Storage


@pytest.fixture(autouse=True)
def reset_export_registry() -> None:
    """Ensure plugin discovery cache is cleared between tests."""

    export_service.clear_export_registry_cache()
    plugin_manager.reset_plugin_manager_cache()
    yield
    export_service.clear_export_registry_cache()
    plugin_manager.reset_plugin_manager_cache()


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
            state["options"] = options
            return 99

        return (
            ExportContribution(
                format_id="dummy",
                formatter=formatter,
                description="Dummy exporter",
            ),
        )

    module.export_formats = export_formats

    original_iter = plugin_manager._builtin_plugin_modules

    def _combined() -> tuple[object, ...]:
        return original_iter() + (module,)

    monkeypatch.setattr(plugin_manager, "_builtin_plugin_modules", _combined)
    plugin_manager.reset_plugin_manager_cache()
    export_service.clear_export_registry_cache()

    storage = Storage(tmp_path / "notes.db")
    storage.initialize()
    storage.create_note("Example", "Body")

    destination = tmp_path / "out"
    count = export_service.export_notes(
        storage,
        export_format="dummy",
        destination=destination,
    )

    assert count == 99
    assert destination.exists()
    assert state["called"] is True
    assert state["notes"] == 1
    assert state["options"] is None


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

    original_iter = plugin_manager._builtin_plugin_modules

    def _combined() -> tuple[object, ...]:
        return original_iter() + (module,)

    monkeypatch.setattr(plugin_manager, "_builtin_plugin_modules", _combined)
    plugin_manager.reset_plugin_manager_cache()
    export_service.clear_export_registry_cache()

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
