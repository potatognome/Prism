#!/usr/bin/env python3
"""
prism/core/registry.py - Prism Module Registry

Dynamically discovers and loads PrismModule subclasses from the
``prism.modules`` package.  Each sub-package inside ``modules/`` that
contains a Python module whose name matches the directory name is
treated as a Prism module.

Discovery rules
---------------
* Scan the ``prism/modules/`` directory for sub-packages.
* Each sub-package must expose a class that is a concrete subclass of
  ``PrismModule`` with a matching ``name`` attribute.
* The class is loaded via ``importlib``; no hard-coded module list.
"""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Type

from prism.module_base import PrismModule


class ModuleRegistry:
    """
    Discovers and caches PrismModule subclasses from the modules package.

    Usage::

        registry = ModuleRegistry()
        registry.discover()
        cls = registry.get("example")
    """

    def __init__(self, modules_package: str = "prism.modules") -> None:
        self._package = modules_package
        self._classes: Dict[str, Type[PrismModule]] = {}

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> List[str]:
        """
        Walk ``prism.modules`` and register all concrete PrismModule
        subclasses found there.

        Returns the list of discovered module names.
        """
        self._classes.clear()
        try:
            package = importlib.import_module(self._package)
        except ImportError:
            return []

        package_path = getattr(package, "__path__", [])
        for _, submodule_name, is_pkg in pkgutil.iter_modules(package_path):
            if not is_pkg:
                continue
            full_name = f"{self._package}.{submodule_name}"
            try:
                mod = importlib.import_module(full_name)
            except Exception:
                continue
            for _attr_name, obj in inspect.getmembers(mod, inspect.isclass):
                if (
                    issubclass(obj, PrismModule)
                    and obj is not PrismModule
                    and not inspect.isabstract(obj)
                ):
                    self._classes[obj.name] = obj

        return list(self._classes.keys())

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[Type[PrismModule]]:
        """Return the class registered under *name*, or None."""
        return self._classes.get(name)

    def all_names(self) -> List[str]:
        """Return the list of discovered module names."""
        return list(self._classes.keys())

    def __repr__(self) -> str:  # pragma: no cover
        return f"ModuleRegistry(modules={self.all_names()})"
