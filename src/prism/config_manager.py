#!/usr/bin/env python3
"""
prism/config_manager.py - Prism Configuration Manager

Loads and deep-merges the Prism configuration stack:
  1. config/config.yaml              (root config)
  2. config/config.d/*.yaml          (sorted, override fragments)
  3. modules/<module>.d/*.yaml       (per-module override fragments)

Provides a `PrismConfig` object with a `for_module()` slice accessor.
Config paths are never hard-coded; they are resolved relative to a
configurable base directory.
"""

import copy
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise ImportError("PyYAML is required: pip install pyyaml") from exc


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Recursively deep-merge *override* into a copy of *base*.

    Mapping values are merged recursively; all other values in *override*
    replace those in *base*.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _load_yaml_file(path: Path) -> Dict:
    """Load a single YAML file and return its contents as a dict."""
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def _load_yaml_dir(directory: Path) -> Dict:
    """
    Load all *.yaml files from *directory* in lexical order and
    deep-merge them into a single dict.
    """
    merged: Dict = {}
    if not directory.is_dir():
        return merged
    for yaml_file in sorted(directory.glob("*.yaml")):
        fragment = _load_yaml_file(yaml_file)
        merged = _deep_merge(merged, fragment)
    return merged


class PrismConfig:
    """
    Layered configuration object for the Prism orchestrator.

    Layers (applied in order, later layers win):
      1. config/config.yaml
      2. config/config.d/*.yaml  (lexical order)
      3. modules/<module>.d/*.yaml per module (applied on demand)
    """

    def __init__(self, config_dir: Path, modules_dir: Optional[Path] = None) -> None:
        self._config_dir = Path(config_dir)
        self._modules_dir = Path(modules_dir) if modules_dir else None
        self._base: Dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Build the merged config from all layers."""
        root_file = self._config_dir / "config.yaml"
        if root_file.is_file():
            self._base = _load_yaml_file(root_file)
        else:
            self._base = {}

        override_dir = self._config_dir / "config.d"
        overrides = _load_yaml_dir(override_dir)
        self._base = _deep_merge(self._base, overrides)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return a top-level config value."""
        return self._base.get(key, default)

    def for_module(self, module_name: str) -> Dict:
        """
        Return a config slice for the named module.

        The slice is:
          base["modules"][module_name]  (root + config.d merged)
        deep-merged with any overrides found in
          modules/<module_name>.d/*.yaml
        """
        base_slice: Dict = copy.deepcopy(
            self._base.get("modules", {}).get(module_name, {})
        )

        if self._modules_dir:
            override_dir = self._modules_dir / module_name / f"{module_name}.d"
            overrides = _load_yaml_dir(override_dir)
            base_slice = _deep_merge(base_slice, overrides)

        return base_slice

    @property
    def logging(self) -> Dict:
        """Return the logging config section."""
        return self._base.get("logging", {})

    @property
    def colours(self) -> Dict:
        """Return the colours config section."""
        return self._base.get("colours", {})

    @property
    def orchestrator(self) -> Dict:
        """Return the orchestrator config section."""
        return self._base.get("orchestrator", {})

    @property
    def raw(self) -> Dict:
        """Return the full merged config dict (read-only copy)."""
        return copy.deepcopy(self._base)

    def __repr__(self) -> str:  # pragma: no cover
        return f"PrismConfig(config_dir={self._config_dir})"
