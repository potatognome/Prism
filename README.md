# Prism

> **Modular, deterministic, colour-aware data-quality orchestrator.**

Prism is a pipeline engine and module orchestrator built on the tUilKit ecosystem.
It provides a config-layered, colour-aware foundation for data cleanup, normalisation,
and analytics preparation.

---

## Quick Start

```bash
# Install (with tUilKit available):
pip install -e .

# Run the full pipeline:
prism run

# Dry-run (detect only, no mutations):
prism --dry run
# or:
prism detect

# List discovered modules:
prism modules

# Inspect the merged configuration:
prism config

# Print the last run summary as JSON:
prism summary

# Override flags:
prism --enable my_module --disable example run
prism --set modules.example.null_placeholder=MISSING run
```

---

## Architecture

```
prism/
  config/
    config.yaml          ← root config
    config.d/            ← sorted override fragments
    GLOBAL_CONFIG.json   ← tUilKit global config
  src/
    prism/
      core/
        registry.py      ← dynamic module discovery
      modules/
        example/         ← reference module implementation
      interfaces/
        cli/cli.py       ← thin CLI wrapper (no business logic)
        tui/             ← (stub) terminal UI layer
        api/             ← (stub) REST/RPC API layer
        gui/             ← (stub) graphical UI layer
      config_manager.py  ← YAML loading + deep merge
      module_base.py     ← PrismModule ABC + IssueReport + ModuleResult
      orchestrator.py    ← pipeline engine
      run_summary.py     ← structured run summary
  tests/
    test_orchestrator.py
```

---

## Configuration

Prism uses a layered YAML configuration system.

| Layer | File | Purpose |
|-------|------|---------|
| Root | `config/config.yaml` | Base configuration |
| Overrides | `config/config.d/*.yaml` | Sorted fragment overrides |
| Module | `modules/<name>/<name>.d/*.yaml` | Per-module overrides |

All layers are deep-merged; later layers win on conflicts.
A module's config slice is accessed via `config.for_module("name")`.

---

## Module Interface

```python
from prism.module_base import PrismModule, IssueReport, ModuleResult

class MyModule(PrismModule):
    name = "my_module"

    def detect(self, dataset) -> IssueReport:
        report = IssueReport()
        # … inspect dataset, call report.add() for each issue …
        return report

    def run(self, dataset) -> ModuleResult:
        result = ModuleResult(dataset=dataset)
        # … mutate dataset, call result.record() for each change …
        return result
```

Drop the module sub-package into `src/prism/modules/` and Prism
will discover it automatically at runtime.

---

## Version History

### 0.1.0 (Current)
- Initial Prism Orchestrator Shell
- Config loading with deep-merge (config.yaml + config.d + module.d)
- Abstract PrismModule interface (detect/run contract)
- ModuleRegistry for dynamic discovery via importlib
- PrismOrchestrator with dry-run, enable/disable, --set overrides
- RunSummary with structured tUilKit logging
- CLI: run, detect, config, modules, summary sub-commands
- ExampleModule reference implementation

---

## Author

Daniel Austin (the.potato.gnome@gmail.com)

---

**Part of the tUilKit ecosystem** — Interface-driven utilities for CLI applications.
