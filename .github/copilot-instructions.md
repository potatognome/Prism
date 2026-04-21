# Copilot Instructions - Prism

## Purpose
Prism is a deterministic, colour-aware data-quality orchestrator. Keep orchestration, interfaces, registry/config wiring, and module implementations separated.
This file is minimal by design. All general rules, agent edit policies, and centralized log/config options are defined in the modular copilot-instructions files.

Refer to:
- [Modular copilot-instructions](./copilot-instructions.d/*.md) for extensions to the general rules in this file.

## Shared Policies Propagated from dev_local/.github
- Treat this repository as its own root. Do not depend on parent dev_local paths existing on another machine.
- Keep all config, logs, tests, and output locations config-driven. Respect ROOT_MODES, PATHS, LOG_FILES, and any `.d` override directories.
- Never hardcode machine-specific absolute paths.
- Use tUilKit config and logging patterns for production code; prefer factory-based access to shared services where available.
- Use semantic colour/log keys such as `!info`, `!proc`, `!done`, `!warn`, `!error`, `!path`, `!file`, `!data`, `!test`, `!pass`, `!fail`, and `!date`.
- Keep tests deterministic and update test bootstrap files such as `tests/test_paths.json` when path behavior changes.
- Update `README.md`, `CHANGELOG.md`, `pyproject.toml`, and config version fields together when behavior or releases change.
- Keep changelog dates in `YYYY-MM-DD` format and place substantive docs under `docs/`.

## Project-Specific Rules
- Keep Prism modules registry-driven and deterministic.
- Prefer semantic colour roles and existing shared utilities over local reinvention.
- Keep config layering explicit under `config/` and related fragment directories.
- Tests should cover orchestration flow, module registration, config loading, and deterministic outputs.
