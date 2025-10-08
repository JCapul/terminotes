# TODO - Plugin Refactor Roadmap

## Foundations
- [x] Finalize plugin discovery strategy using Pluggy entry points focused on export extensions.
- [x] Decide packaging model for plugins (core-provided vs external distributions, extras, naming).
- [x] Specify minimal plugin contracts (function signatures, context objects, error handling rules) and record them in developer docs.

## Core infrastructure
- [x] Create `terminotes/plugins/` package with registry helpers and protocol definitions for exporter hooks.
- [x] Implement resilient entry point loader that surfaces exporter failures without crashing the core CLI.
- [x] Design a bootstrap hook contract so plugins can execute setup logic during `terminotes.app.bootstrap`.
- [x] Define configuration access patterns for plugins (namespacing within the main TOML config and validation helpers).

## Exporter integration
- [x] Integrate the plugin manager into `services/export.py` to discover exporter contributions.
- [x] Move the HTML and Markdown exporters into built-in plugins that conform to the new interface.
- [x] Update the CLI export command to enumerate plugin-provided formats for validation and `--help` output.
- [x] Add tests ensuring plugin-provided exporters are discovered, invoked, and error-handled correctly.

## Optional utilities
- [ ] Add shared plugin context utilities (e.g. access to `AppContext`, logging, configuration lookup) if exporters need them.
- [x] Provide helpers to read plugin-specific configuration sections safely with defaults.

## Tooling and docs
- [ ] Update documentation (`README`, `docs/`) to explain exporter plugins and provide authoring guidance.
- [ ] Ship an example exporter plugin scaffold (either in `examples/` or documentation).
- [ ] Update `pyproject.toml` and `uv.lock` to expose entry points for built-in exporters and optional extras.
- [ ] Extend fixtures/utilities in `tests/` to simulate exporter plugin distributions without polluting global state.
- [ ] Ensure Justfile and CI workflows cover exporter plugin-aware unit tests and linting targets.
- [ ] Prepare CHANGELOG entries describing exporter plugin architecture adoption.

## Post-refactor cleanup
- [ ] Remove obsolete code paths (legacy exporter conditionals, direct module imports) once plugins wire in.
- [ ] Audit public APIs and type hints affected by pluginization and update docs accordingly.
- [ ] Remove this TODO once tasks migrate to the issue tracker or project board.
