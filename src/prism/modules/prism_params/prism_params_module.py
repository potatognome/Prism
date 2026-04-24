#!/usr/bin/env python3
"""
prism/modules/prism_params/prism_params_module.py - Prism Parameters Module

Manages a secondary YAML configuration file containing runtime parameters
for the Prism pipeline.  Allows operator-level tunables to live in a
separate file from the orchestrator config.

Configuration keys (modules.prism_params in config.yaml):
  enabled         bool       Whether this module is active (default: true).
  params_file     str        Path to the secondary YAML params file.
                             Relative to project root or absolute.
                             (default: "config/prism_params.yaml")
  required_keys   list[str]  Top-level keys that must be present in the
                             params file (default: []).
"""

from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise ImportError("PyYAML is required: pip install pyyaml") from exc

from prism.module_base import IssueReport, ModuleResult, PrismModule


class PrismParamsModule(PrismModule):
    """
    Prism module: validates and loads a secondary YAML parameters file.

    detect() verifies the params file exists and contains all required keys.
    run()    loads the params and returns them as the dataset.
    """

    name: str = "prism_params"

    def __init__(self, config: Dict, logger: Any) -> None:
        super().__init__(config, logger)
        self._params_file: str = str(
            config.get("params_file", "config/prism_params.yaml")
        )
        self._required_keys: List[str] = list(config.get("required_keys", []))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_path(self) -> Path:
        """Return the resolved params file path."""
        p = Path(self._params_file)
        if p.is_absolute():
            return p
        # Resolve relative paths from cwd so the orchestrator can set cwd
        # to the project root before invoking modules.
        return Path.cwd() / p

    def _load_yaml(self, path: Path) -> Dict:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}

    # ------------------------------------------------------------------
    # detect
    # ------------------------------------------------------------------

    def detect(self, dataset: Any) -> IssueReport:
        """
        Verify the params file exists and contains all required keys.

        The *dataset* argument is unused; issues are file-level only.
        """
        report = IssueReport()
        path = self._resolve_path()

        if not path.is_file():
            report.add(
                f"Params file not found: {path}",
                issue_type="missing_params_file",
            )
            self.logger.colour_log(
                "!warn PrismParamsModule.detect: params file missing:",
                "!path", str(path),
            )
            return report

        try:
            params = self._load_yaml(path)
        except Exception as exc:
            report.add(
                f"Params file is not valid YAML: {exc}",
                issue_type="invalid_yaml",
            )
            self.logger.colour_log(
                "!error PrismParamsModule.detect: YAML parse error:",
                "!data", str(exc),
            )
            return report

        for key in self._required_keys:
            if key not in params:
                report.add(
                    f"Required key missing from params file: {key!r}",
                    issue_type="missing_required_key",
                )

        if report.passed:
            self.logger.colour_log(
                "!done PrismParamsModule.detect: params file OK.",
                "!path", str(path),
            )
        else:
            self.logger.colour_log(
                "!warn PrismParamsModule.detect: issues=",
                len(report.issues),
            )

        return report

    # ------------------------------------------------------------------
    # run
    # ------------------------------------------------------------------

    def run(self, dataset: Any) -> ModuleResult:
        """
        Load the secondary params YAML and return it as the result dataset.

        The loaded params dict is stored in ``result.dataset`` so downstream
        modules or the orchestrator can consume it.
        """
        result = ModuleResult(dataset=dataset)
        path = self._resolve_path()

        if not path.is_file():
            result.success = False
            result.error = f"Params file not found: {path}"
            self.logger.colour_log(
                "!error PrismParamsModule.run: params file missing:",
                "!path", str(path),
            )
            return result

        try:
            params = self._load_yaml(path)
        except Exception as exc:
            result.success = False
            result.error = f"Failed to load params YAML: {exc}"
            self.logger.colour_log(
                "!error PrismParamsModule.run: YAML parse error:",
                "!data", str(exc),
            )
            return result

        result.dataset = params
        result.record(f"Loaded params from {path}")
        self.logger.colour_log(
            "!done PrismParamsModule.run: loaded",
            len(params),
            "top-level keys from",
            "!file", path.name,
        )
        return result
