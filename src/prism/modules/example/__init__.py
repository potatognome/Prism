#!/usr/bin/env python3
"""
prism/modules/example/__init__.py

Re-exports ExampleModule so the registry finds it at the package level.
"""

from prism.modules.example.example_module import ExampleModule

__all__ = ["ExampleModule"]
