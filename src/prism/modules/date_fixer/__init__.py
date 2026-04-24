#!/usr/bin/env python3
"""
prism/modules/date_fixer/__init__.py

Re-exports DateFixerModule so the registry finds it at the package level.
"""

from prism.modules.date_fixer.date_fixer_module import DateFixerModule

__all__ = ["DateFixerModule"]
