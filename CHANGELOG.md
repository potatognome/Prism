## [0.3.0] - 2026-04-19
- Workspace migration to Core/SuiteTools/Applications layout.
- Path normalization for portable multi-device use (no machine-specific absolute roots).
- Consolidated Copilot instructions at project scope.

## [0.2.0] - 2026-04-19
- Workspace migration to Core/SuiteTools/Applications layout.
- Path normalization for portable multi-device use (no machine-specific absolute roots).
- Consolidated Copilot instructions at project scope.

# Changelog — Prism

All notable changes to the Prism Orchestrator Shell are documented here.

---

## [0.1.0] — 2026-04-01

### Added — Initial Prism Orchestrator Shell
- **Core orchestrator** (`orchestrator.py`): module discovery, lifecycle (detect → run),
  dry-run mode, enable/disable overrides, `--set` config overrides.
- **Config manager** (`config_manager.py`): loads `config.yaml`, deep-merges
  `config.d/*.yaml` in lexical order, supports per-module `<module>.d/*.yaml`
  overrides; exposes `PrismConfig.for_module()` slice accessor.
- **Module interface** (`module_base.py`): `PrismModule` ABC with `detect()` / `run()`
  contract; `IssueReport` and `ModuleResult` data containers.
- **Module registry** (`core/registry.py`): dynamic discovery of `PrismModule`
  subclasses via `importlib` and `pkgutil`.
- **Run summary** (`run_summary.py`): structured per-module records emitted via
  tUilKit colour logging; returns plain dict for serialisation.
- **CLI interface** (`interfaces/cli/cli.py`): thin wrapper with sub-commands
  `run`, `detect`, `config`, `modules`, `summary` and flags
  `--dry`, `--enable`, `--disable`, `--set`, `--config-dir`.
- **Interface stubs**: `interfaces/tui/`, `interfaces/api/`, `interfaces/gui/`.
- **ExampleModule** (`modules/example/`): reference implementation that detects
  and fills null values; ships with its own `example.d/` override directory.
- **tUilKit integration**: all logging via `get_logger()` / `colour_log()`;
  no `print()` in production code.
- `pyproject.toml`, `README.md`, `CHANGELOG.md`, `config/config.yaml`,
  `config/config.d/`, `config/GLOBAL_CONFIG.json`.


