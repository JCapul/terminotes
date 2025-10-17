# TODO – Git Sync Plugin Refactor Roadmap

## Scope & Goals
- [] Confirm target behavior: move Git synchronization into a plugin while preserving `tn sync` UX and automatic commit hooks.
- [] Enumerate current touch points (`AppContext`, services, CLI, tests) that depend on `terminotes.git_sync`.

## Architecture Design
- [] Define `SyncProvider` interface in `terminotes/plugins/base.py` (methods for bootstrap, pre/post write, sync operations, status).
- [] Specify plugin registration & loading rules via existing plugin config (default to Git plugin when `git_remote_url` present).
- [] Draft migration strategy for config: auto-enable git plugin, introduce `sync_provider` selector, document defaults.

## Implementation Phases
### Phase 1 – Plugin scaffolding
- [] Add plugin loader capable of instantiating sync providers during app bootstrap.
- [] Update `AppContext` to hold a generic `sync_provider` reference (no behavior change yet).
- [] Write unit tests for loader and default selection logic.

### Phase 2 – Interface adoption
- [] Introduce adapters so services/CLI use provider hooks instead of direct `GitSync` calls.
- [] Ensure note create/update/delete/prune workflows call provider `before_write` / `after_write` equivalents.
- [] Update CLI sync command to call provider `sync(dry_run)` and relay provider prompts/messages.
- [] Maintain temporary compatibility shim for tests referencing `GitSync`.

### Phase 3 – Git plugin extraction
- [] Relocate `terminotes/git_sync.py` logic into `terminotes/plugins/git_sync/`.
- [] Implement `GitSyncProvider` conforming to new interface and reusing existing divergence handling.
- [] Provide plugin-specific config validation (e.g., force push strategy).
- [] Delete old module, update imports, and adjust tests/mocks accordingly.

### Phase 4 – Polish & cleanup
- [] Add integration tests covering plugin-based sync flows (bootstrap, commit hooks, CLI sync).
- [] Document plugin architecture, configuration, and migration in `README`/`docs/CHANGELOG`.
- [] Supply example plugin scaffold for alt sync backends.
- [] Audit remaining Git-specific assumptions in core modules and remove or abstract them.

## Tooling & QA
- [] Expand test fixtures to simulate alternate sync providers for unit tests.
- [] Ensure `just lint`, `just test`, and CI cover new plugin code paths.
- [] Conduct manual smoke test: edit note + sync, divergence resolution prompts, dry-run outputs.

## Release Prep
- [] Capture breaking change notes (e.g., import paths) and communicate in release docs.
- [] Coordinate version bump and validate that existing configs require no manual edits.
- [] Remove this TODO once tracked in issues/project board.

