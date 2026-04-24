#!/usr/bin/env python3
"""
examples/exemplar.py — Prism Exemplar Application Entry Point

Demonstrates Prism's public config API with a colour-logged interactive menu.

  • Loads tUilKit factories in verbose mode.
  • Reads config/Prism_CONFIG.json (primary global config).
  • Reads and displays all ROOT_MODES.
  • Verifies and displays resolved paths for LOG_FILES, config files,
    and input data files.

Run from the project root:
    python examples/exemplar.py
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap from test_paths.json
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve()
_paths_file = HERE.parent / "test_paths.json"
if not _paths_file.exists():
    # Auto-generate on first run.
    import subprocess
    subprocess.run(
        [sys.executable, str(HERE.parent / "test_config.py")], check=True
    )

with open(_paths_file, encoding="utf-8") as _f:
    _p = json.load(_f)

PROJECT_ROOT     = Path(_p["project_root"])
WORKSPACE_ROOT   = Path(_p["workspace_root"])
TEST_LOGS_FOLDER = Path(_p["test_logs_folder"])
CONFIG_FOLDER    = Path(_p["config_folder"])

sys.path.insert(0, str(PROJECT_ROOT / "src"))
TEST_LOGS_FOLDER.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# tUilKit factory imports (verbose / production mode)
# ---------------------------------------------------------------------------

from tUilKit import get_colour_manager, get_config_loader, get_logger  # noqa: E402

config_loader  = get_config_loader()
colour_manager = get_colour_manager()
logger         = get_logger()

# ---------------------------------------------------------------------------
# Log targets
# ---------------------------------------------------------------------------

TEST_LOG_FILE = str(TEST_LOGS_FOLDER / "SESSION.log")
SCRIPT_LOG    = str(TEST_LOGS_FOLDER / "exemplar.log")
LOG_TARGETS   = [TEST_LOG_FILE, SCRIPT_LOG]

BORDER = {"TOP": "=", "BOTTOM": "=", "LEFT": " ", "RIGHT": " "}

# ---------------------------------------------------------------------------
# Prism config loading
# ---------------------------------------------------------------------------

_prism_cfg_path = str(PROJECT_ROOT / "config" / "Prism_CONFIG.json")
PRISM_CONFIG    = config_loader.load_config(_prism_cfg_path)

# Also load the YAML orchestrator config via PrismConfig.
from prism.config_manager import PrismConfig  # noqa: E402

prism_yaml_config = PrismConfig(config_dir=PROJECT_ROOT / "config")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_path(mode_key: str, path_key: str) -> Path:
    """Resolve an absolute path from ROOT_MODES + PATHS in Prism_CONFIG."""
    mode = PRISM_CONFIG.get("ROOT_MODES", {}).get(mode_key, "project")
    base = WORKSPACE_ROOT if mode == "workspace" else PROJECT_ROOT
    return base / PRISM_CONFIG.get("PATHS", {}).get(path_key, "")


def _section_header(title: str) -> None:
    logger.print_rainbow_row(log_files=LOG_TARGETS)
    logger.apply_border(
        text=title,
        pattern=BORDER,
        total_length=70,
        border_rainbow=True,
        log_files=LOG_TARGETS,
    )


# ---------------------------------------------------------------------------
# Menu actions
# ---------------------------------------------------------------------------

def show_project_info() -> None:
    """Display basic project information from Prism_CONFIG.json."""
    _section_header("📋  Prism — Project Information")
    info = PRISM_CONFIG.get("INFO", {})
    logger.colour_log(
        "!info", "  Name:",        "!data", info.get("PROJECT_NAME",  "—"),
        log_files=LOG_TARGETS,
    )
    logger.colour_log(
        "!info", "  Version:",     "!data", info.get("VERSION",       "—"),
        log_files=LOG_TARGETS,
    )
    logger.colour_log(
        "!info", "  Description:", "!data", info.get("PROJECT_DESCRIPTION", "—"),
        log_files=LOG_TARGETS,
    )
    logger.colour_log(
        "!info", "  Entry point:", "!path", info.get("MAIN_ENTRY_POINT", "—"),
        log_files=LOG_TARGETS,
    )


def show_root_modes() -> None:
    """Read and display all ROOT_MODES from the primary config."""
    _section_header("🗂️   ROOT_MODES — Config Resolution Strategy")
    root_modes = PRISM_CONFIG.get("ROOT_MODES", {})
    roots      = PRISM_CONFIG.get("ROOTS",      {})

    logger.colour_log("!info", "  Defined roots:", log_files=LOG_TARGETS)
    for key, val in roots.items():
        logger.colour_log(
            "!info", f"    {key}:", "!path", str(val),
            log_files=LOG_TARGETS,
        )

    logger.colour_log("!info", "  Mode assignments:", log_files=LOG_TARGETS)
    for key, val in root_modes.items():
        if key.startswith("ROOT_MODES:"):
            continue  # description entries
        colour = "!done" if val == "project" else "!proc"
        logger.colour_log(
            "!info", f"    {key}:", colour, val,
            log_files=LOG_TARGETS,
        )


def validate_paths() -> None:
    """Verify and display resolved paths for all configured path keys."""
    _section_header("🔍  Path Validation — Resolved Paths")
    path_keys = list(PRISM_CONFIG.get("PATHS", {}).keys())
    all_ok = True

    for path_key in path_keys:
        mode_key = path_key  # ROOT_MODES key matches PATHS key by convention
        resolved = _resolve_path(mode_key, path_key)
        exists   = resolved.exists()
        status   = "!done" if exists else "!warn"
        flag     = "✅" if exists else "⚠️ (not yet created)"
        logger.colour_log(
            "!info", f"  {path_key}:",
            status, flag,
            "!path", str(resolved),
            log_files=LOG_TARGETS,
        )
        if not exists:
            all_ok = False

    if all_ok:
        logger.colour_log(
            "!done", "All configured paths exist.", log_files=LOG_TARGETS
        )
    else:
        logger.colour_log(
            "!warn",
            "Some paths do not exist yet — they will be created at runtime.",
            log_files=LOG_TARGETS,
        )


def show_log_files() -> None:
    """Display configured LOG_FILES paths and check existence."""
    _section_header("📝  LOG_FILES — Configured Log Destinations")
    log_files = PRISM_CONFIG.get("LOG_FILES", {})
    logs_mode = PRISM_CONFIG.get("ROOT_MODES", {}).get("LOGS", "workspace")
    logs_base = WORKSPACE_ROOT if logs_mode == "workspace" else PROJECT_ROOT
    logs_rel  = PRISM_CONFIG.get("PATHS", {}).get("LOGS", ".logs/Prism/")

    for log_key, log_name in log_files.items():
        full_path = logs_base / logs_rel / log_name
        exists    = full_path.exists()
        status    = "!done" if exists else "!info"
        flag      = "✅" if exists else "—"
        logger.colour_log(
            "!info", f"  {log_key}:", status, flag,
            "!path", str(full_path.parent) + "/",
            "!file", log_name,
            log_files=LOG_TARGETS,
        )


def show_yaml_config() -> None:
    """Load and display the merged YAML orchestrator config."""
    _section_header("⚙️   Orchestrator Config (config.yaml + config.d/)")
    raw = prism_yaml_config.raw
    logger.colour_log(
        "!info", "  project.name:",
        "!data", raw.get("project", {}).get("name", "—"),
        log_files=LOG_TARGETS,
    )
    logger.colour_log(
        "!info", "  project.version:",
        "!data", raw.get("project", {}).get("version", "—"),
        log_files=LOG_TARGETS,
    )
    orch = raw.get("orchestrator", {})
    logger.colour_log(
        "!info", "  orchestrator.dry_run:", "!data", str(orch.get("dry_run")),
        log_files=LOG_TARGETS,
    )
    logger.colour_log(
        "!info", "  orchestrator.run_id_prefix:", "!data", orch.get("run_id_prefix"),
        log_files=LOG_TARGETS,
    )
    modules = raw.get("modules", {})
    logger.colour_log(
        "!info", "  Registered modules:", "!int", str(len(modules)),
        log_files=LOG_TARGETS,
    )
    for mod_name, mod_cfg in modules.items():
        enabled = mod_cfg.get("enabled", True)
        status  = "!done" if enabled else "!warn"
        flag    = "enabled" if enabled else "disabled"
        logger.colour_log(
            "!info", f"    {mod_name}:", status, flag,
            log_files=LOG_TARGETS,
        )


def show_root_mode_validation() -> None:
    """Load each ROOT_MODE value and validate its path category."""
    _section_header("✔️   ROOT_MODE Validation — All Modes")
    root_modes = PRISM_CONFIG.get("ROOT_MODES", {})
    valid_modes = {"project", "workspace"}

    for key, val in root_modes.items():
        if key.startswith("ROOT_MODES:"):
            continue
        if val in valid_modes:
            logger.colour_log(
                "!done", f"  {key} = {val!r}", log_files=LOG_TARGETS
            )
        else:
            logger.colour_log(
                "!warn", f"  {key} = {val!r} (unexpected value)",
                log_files=LOG_TARGETS,
            )


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main() -> None:
    os.system("cls" if os.name == "nt" else "clear")
    now = datetime.now()

    logger.print_rainbow_row(log_files=LOG_TARGETS)
    logger.colour_log(
        "!date", now.strftime("%Y-%m-%d %H:%M:%S"),
        "!proc", "Prism Exemplar — starting",
        log_files=LOG_TARGETS,
    )
    logger.colour_log(
        "!info", "  Config loader:", "!data", repr(config_loader),
        log_files=LOG_TARGETS,
    )
    logger.colour_log(
        "!info", "  Primary config:", "!path", _prism_cfg_path,
        log_files=LOG_TARGETS,
    )

    while True:
        print()
        logger.apply_border(
            text="🔷  Prism — Data-Quality Orchestrator  🔷",
            pattern=BORDER,
            total_length=70,
            border_rainbow=True,
            log_files=LOG_TARGETS,
        )
        print()
        logger.colour_log("!info", "  📋 Main Menu:", log_files=LOG_TARGETS)
        logger.colour_log("!list", "  1", "!info", ". 📋 Project information",
                          log_files=LOG_TARGETS)
        logger.colour_log("!list", "  2", "!info", ". 🗂️  ROOT_MODES overview",
                          log_files=LOG_TARGETS)
        logger.colour_log("!list", "  3", "!info", ". ✔️  ROOT_MODE validation",
                          log_files=LOG_TARGETS)
        logger.colour_log("!list", "  4", "!info", ". 🔍 Validate config paths",
                          log_files=LOG_TARGETS)
        logger.colour_log("!list", "  5", "!info", ". 📝 LOG_FILES overview",
                          log_files=LOG_TARGETS)
        logger.colour_log("!list", "  6", "!info", ". ⚙️  Orchestrator YAML config",
                          log_files=LOG_TARGETS)
        logger.colour_log("!list", "  7", "!info", ". 🚪 Exit",
                          log_files=LOG_TARGETS)
        print()

        choice = input("Select option (1-7): ").strip()

        if choice == "1":
            show_project_info()
        elif choice == "2":
            show_root_modes()
        elif choice == "3":
            show_root_mode_validation()
        elif choice == "4":
            validate_paths()
        elif choice == "5":
            show_log_files()
        elif choice == "6":
            show_yaml_config()
        elif choice in ("7", "q", "quit", "exit"):
            logger.colour_log(
                "!done", "👋 Goodbye!", log_files=LOG_TARGETS
            )
            logger.print_rainbow_row(log_files=LOG_TARGETS)
            break
        else:
            logger.colour_log(
                "!error", "❌ Invalid choice — please enter 1–7.",
                log_files=LOG_TARGETS,
            )


if __name__ == "__main__":
    main()
