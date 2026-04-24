#!/usr/bin/env python3
"""
prism/modules/prism_params/__init__.py

Re-exports PrismParamsModule so the registry finds it at the package level.
"""

from prism.modules.prism_params.prism_params_module import PrismParamsModule

__all__ = ["PrismParamsModule"]
