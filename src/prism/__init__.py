#!/usr/bin/env python3
"""
prism/__init__.py - Prism Orchestrator Shell
Modular, deterministic, colour-aware data-quality orchestrator.
"""

__version__ = "0.1.0"
__author__ = "Daniel Austin"
__email__ = "the.potato.gnome@gmail.com"

try:
    from tUilKit import get_logger, get_config_loader, get_file_system
    __all__ = ["get_logger", "get_config_loader", "get_file_system", "__version__"]
except ImportError:  # pragma: no cover
    __all__ = ["__version__"]
