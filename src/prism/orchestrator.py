#!/usr/bin/env python3
"""
prism/orchestrator.py - Prism Core Orchestrator

The orchestrator is the only component that knows about the full
module lifecycle.  It must not contain module logic.

Responsibilities
----------------
* Build a PrismConfig from the config layer stack.
* Discover modules via the ModuleRegistry.
* Honour module enable/disable flags (from config + CLI overrides).
* Instantiate each enabled module with its config slice + logger.
* Run the detect() → run() lifecycle for every enabled module.
* Collect results into a RunSummary.
* Support dry-run mode (detect only, no mutations).
* Emit structured logs via tUilKit.
* Apply CLI overrides (--set key.path=value).
"""

import datetime
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from prism.config_manager import PrismConfig
from prism.core.registry import ModuleRegistry
from prism.module_base import IssueReport, ModuleResult, PrismModule
from prism.run_summary import ModuleRecord, RunSummary

try:
    from tUilKit import get_logger
    _tuilkit_available = True
except ImportError:  # pragma: no cover
    _tuilkit_available = False


# ---------------------------------------------------------------------------
# Logger shim (used when tUilKit is not installed)
# ---------------------------------------------------------------------------

class _FallbackLogger:
    """Minimal logger shim used when tUilKit is unavailable."""

    def colour_log(self, *args, **kwargs) -> None:  # pragma: no cover
        pass

    def log_exception(self, msg: str, exc: Exception, **kwargs) -> None:  # pragma: no cover
        pass


def _make_logger(config: PrismConfig) -> Any:
    """Return a tUilKit logger if available, otherwise the shim."""
    if _tuilkit_available:
        return get_logger()
    return _FallbackLogger()  # pragma: no cover


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class PrismOrchestrator:
    """
    Core orchestrator for Prism.

    Parameters
    ----------
    config_dir:
        Path to the project ``config/`` directory.  Must contain
        ``config.yaml`` and optionally ``config.d/``.
    modules_dir:
        Path to the project ``src/prism/modules/`` directory.  Used to
        resolve per-module ``.d/`` override directories.
    dry_run:
        When True the orchestrator runs detect() for all modules but
        skips run().  No dataset mutations occur.
    enable_overrides:
        Module names that should be force-enabled regardless of config.
    disable_overrides:
        Module names that should be force-disabled regardless of config.
    set_overrides:
        Dict of dot-path config keys → values supplied by the CLI
        ``--set`` flag.  Applied on top of the loaded config.
    """

    def __init__(
        self,
        config_dir: Path,
        modules_dir: Optional[Path] = None,
        dry_run: bool = False,
        enable_overrides: Optional[List[str]] = None,
        disable_overrides: Optional[List[str]] = None,
        set_overrides: Optional[Dict[str, str]] = None,
    ) -> None:
        self._config_dir = Path(config_dir)
        self._modules_dir = Path(modules_dir) if modules_dir else None
        self._dry_run = dry_run
        self._enable_overrides: Set[str] = set(enable_overrides or [])
        self._disable_overrides: Set[str] = set(disable_overrides or [])
        self._set_overrides: Dict[str, str] = dict(set_overrides or {})

        self._config: Optional[PrismConfig] = None
        self._logger: Any = None
        self._registry: ModuleRegistry = ModuleRegistry()
        self._log_files: List[str] = []

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        self._config = PrismConfig(
            config_dir=self._config_dir,
            modules_dir=self._modules_dir,
        )
        self._apply_set_overrides()

    def _apply_set_overrides(self) -> None:
        """Apply --set key.path=value overrides to the raw config."""
        if not self._set_overrides or self._config is None:
            return
        raw = self._config.raw
        for dotpath, value in self._set_overrides.items():
            keys = dotpath.split(".")
            node = raw
            for k in keys[:-1]:
                node = node.setdefault(k, {})
            node[keys[-1]] = value
        # Rebuild config from the mutated raw dict (simple approach).
        import copy
        self._config._base = copy.deepcopy(raw)  # type: ignore[attr-defined]

    def _setup_logger(self) -> None:
        self._logger = _make_logger(self._config)
        log_cfg = self._config.logging if self._config else {}
        self._log_files = list(log_cfg.get("log_files", {}).values())

    def _discover_modules(self) -> List[str]:
        names = self._registry.discover()
        self._logger.colour_log(
            "!info Discovered modules:", "!list", names,
            log_files=self._log_files,
        )
        return names

    # ------------------------------------------------------------------
    # Enable / disable resolution
    # ------------------------------------------------------------------

    def _is_module_enabled(self, name: str) -> bool:
        if name in self._disable_overrides:
            return False
        if name in self._enable_overrides:
            return True
        module_cfg = self._config.for_module(name) if self._config else {}
        return bool(module_cfg.get("enabled", True))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, dataset: Any = None) -> Dict:
        """
        Execute the full Prism pipeline against *dataset*.

        Returns the run summary dict.
        """
        self._load_config()
        self._setup_logger()

        orch_cfg = self._config.orchestrator if self._config else {}
        dry_run = self._dry_run or bool(orch_cfg.get("dry_run", False))
        run_id = f"{orch_cfg.get('run_id_prefix', 'prism')}-{uuid.uuid4().hex[:8]}"

        self._logger.colour_log(
            "!rainbow <O>", spacer=1, log_files=self._log_files,
        )
        self._logger.colour_log(
            "!command Prism Orchestrator",
            "!info run_id=", run_id,
            "!info dry_run=", dry_run,
            log_files=self._log_files,
        )

        module_names = self._discover_modules()
        summary = RunSummary(run_id=run_id, dry_run=dry_run)

        for name in module_names:
            record = summary.begin_module(name)
            record.dry_run = dry_run

            if not self._is_module_enabled(name):
                self._logger.colour_log(
                    "!warn Module", "!text", name,
                    "!warn is disabled — skipping.",
                    log_files=self._log_files,
                )
                record.skipped = True
                summary.end_module(record)
                continue

            cls = self._registry.get(name)
            if cls is None:
                record.error = f"Module class not found: {name}"
                summary.end_module(record)
                continue

            module_cfg = self._config.for_module(name) if self._config else {}
            module_logger = self._logger  # module-scoped loggers extend this

            try:
                instance: PrismModule = cls(config=module_cfg, logger=module_logger)
            except Exception as exc:
                self._logger.log_exception(
                    f"!error Failed to instantiate module {name!r}", exc,
                    log_files=self._log_files,
                )
                record.error = str(exc)
                summary.end_module(record)
                continue

            # detect()
            self._logger.colour_log(
                "!proc Detecting issues:", "!text", name,
                log_files=self._log_files,
            )
            try:
                record.issue_report = instance.detect(dataset)
            except Exception as exc:
                self._logger.log_exception(
                    f"!error detect() failed for module {name!r}", exc,
                    log_files=self._log_files,
                )
                record.error = str(exc)
                summary.end_module(record)
                continue

            if dry_run:
                self._logger.colour_log(
                    "!warn [DRY RUN] Skipping run() for module:", "!text", name,
                    log_files=self._log_files,
                )
                summary.end_module(record)
                continue

            # run()
            self._logger.colour_log(
                "!proc Running module:", "!text", name,
                log_files=self._log_files,
            )
            try:
                record.result = instance.run(dataset)
                if record.result.success:
                    self._logger.colour_log(
                        "!done Module complete:", "!text", name,
                        log_files=self._log_files,
                    )
                else:
                    self._logger.colour_log(
                        "!error Module reported failure:", "!text", name,
                        log_files=self._log_files,
                    )
            except Exception as exc:
                self._logger.log_exception(
                    f"!error run() failed for module {name!r}", exc,
                    log_files=self._log_files,
                )
                record.error = str(exc)

            summary.end_module(record)

        return summary.finalise(self._logger)
