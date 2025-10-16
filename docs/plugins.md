# Terminotes Plugin Foundations

Terminotes uses [Pluggy](https://pluggy.readthedocs.io/) to coordinate optional
export formats. The plugin manager lives in `terminotes.plugins` and exposes the
`terminotes` namespace with the entry-point group `terminotes.plugins`.

## Discovery model

- First-party exporters that ship inside the core package are registered directly
  via `terminotes.plugins.register_modules`.
- External packages publish entry points under `terminotes.plugins` in their
  `pyproject.toml` or `setup.cfg` so the plugin manager can load them at
  runtime. Example:

  ```toml
  [project.entry-points."terminotes.plugins"]
  aurora-export = "terminotes_aurora.plugin"
  ```

- The plugin manager only loads metadata during bootstrap; failures from plugin
  registration are surfaced without preventing core functionality (later stages
  integrate richer error reporting).

## Packaging guidance

- Ship first-party exporters alongside `terminotes` or as dedicated
  distributions (e.g. `terminotes-export-html`). Prefix published packages with
  `terminotes-` to simplify discovery.
- Separate optional integrations behind extras in `pyproject.toml` when the
  exporter pulls in non-core dependencies.
- Each exporter plugin should define a module-level object exposing Pluggy hook
  implementations decorated with `@terminotes.plugins.hookimpl`.

## Hook contracts

Terminotes currently defines one hook specification in
`terminotes.plugins.spec`:

- `export_formats(config)` returns an iterable of `ExportContribution`
  descriptors. The hook receives the loaded `TerminotesConfig`, including the
  parsed `[plugins]` mapping for plugin-specific configuration blocks. Each
  contribution exposes a `formatter` callable that receives keyword arguments
  `storage`, `destination`, and optional `options`, writing notes to disk and
  returning the note count.

See `terminotes.plugins.types` for the authoritative dataclasses and protocol
signatures.

## Plugin configuration

Plugin settings live under a `[plugins]` table in the main Terminotes TOML file.
Each plugin should claim a unique nested table—usually the package name. For
example, a plugin named `terminotes-export-aurora` would read from the section
`[plugins."terminotes-export-aurora"]`. Plugins can access their configuration
with `config.plugins.get(<plugin-id>, {})` inside their hook implementation.

## Built-in exporters

Terminotes ships HTML and Markdown exporters as built-in plugins located in
`terminotes.plugins.html` and `terminotes.plugins.markdown`. They register
automatically during export discovery so the CLI can enumerate them for
`tn export`. The HTML plugin reads its configuration from the table
`[plugins."terminotes-html-plugin"]`, honouring keys such as `site_title` and an
optional `templates_root`. When the section is absent, the plugin falls back to
the configuration directory and ensures bundled templates exist each time the
export hook runs.

## Next steps

Future iterations will expand shared plugin utilities, document advanced
exporter authoring patterns, and harden error reporting for third-party
distributions.
