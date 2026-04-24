#!/usr/bin/env python3
"""
examples/test_config.py — Prism examples path bootstrap.

Resolves all paths used by the examples suite from the project config
(config/Prism_CONFIG.json) and writes them to test_paths.json.

Run directly to (re)generate test_paths.json:
    python examples/test_config.py
"""

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate roots
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _find_workspace_root() -> Path:
    """Walk up from PROJECT_ROOT looking for dev_local.code-workspace.
    Falls back to PROJECT_ROOT.parent for standalone-repo setups.
    """
    for parent in PROJECT_ROOT.parents:
        if (parent / "dev_local.code-workspace").exists():
            return parent
    return PROJECT_ROOT.parent


WORKSPACE_ROOT = _find_workspace_root()

# ---------------------------------------------------------------------------
# Load primary Prism config (has ROOT_MODES, PATHS, LOG_FILES, etc.)
# ---------------------------------------------------------------------------

from tUilKit import get_config_loader  # noqa: E402  (after path setup)

config_loader = get_config_loader()
prism_config_path = str(PROJECT_ROOT / "config" / "Prism_CONFIG.json")
config = config_loader.load_config(prism_config_path)


# ---------------------------------------------------------------------------
# Path resolver
# ---------------------------------------------------------------------------

def _resolve(mode_key: str, path_key: str) -> Path:
    """Return an absolute path from ROOT_MODES + PATHS config."""
    mode = config.get("ROOT_MODES", {}).get(mode_key, "project")
    base = WORKSPACE_ROOT if mode == "workspace" else PROJECT_ROOT
    return base / config.get("PATHS", {}).get(path_key, "")


# ---------------------------------------------------------------------------
# Build paths dict
# ---------------------------------------------------------------------------

CONFIG_FOLDER        = _resolve("CONFIG",      "CONFIG")
LOGS_FOLDER          = _resolve("LOGS",        "LOGS")
TEST_LOGS_FOLDER     = _resolve("TEST_LOGS",   "TEST_LOGS")
TEST_CONFIG_FOLDER   = _resolve("TEST_CONFIG", "TEST_CONFIG")
TEST_INPUTS_FOLDER   = _resolve("TEST_INPUTS", "TEST_INPUTS")
TEST_OUTPUTS_FOLDER  = _resolve("TEST_OUTPUTS", "TEST_OUTPUTS")

paths = {
    "examples_folder":      str(HERE.parent),
    "project_root":         str(PROJECT_ROOT),
    "workspace_root":       str(WORKSPACE_ROOT),
    "config_folder":        str(CONFIG_FOLDER),
    "logs_folder":          str(LOGS_FOLDER),
    "test_logs_folder":     str(TEST_LOGS_FOLDER),
    "test_config_folder":   str(TEST_CONFIG_FOLDER),
    "test_inputs_folder":   str(TEST_INPUTS_FOLDER),
    "test_outputs_folder":  str(TEST_OUTPUTS_FOLDER),
}

# ---------------------------------------------------------------------------
# Write test_paths.json
# ---------------------------------------------------------------------------

_out = HERE.parent / "test_paths.json"
with open(_out, "w", encoding="utf-8") as _f:
    json.dump(paths, _f, indent=4)

if __name__ == "__main__":
    print(f"test_paths.json written to {HERE.parent}")
    for k, v in paths.items():
        print(f"  {k}: {v}")
