#!/usr/bin/env python3
"""
prism/interfaces/cli/cli.py - Prism CLI Interface

A thin wrapper around the PrismOrchestrator.  Contains NO business logic.

Supported sub-commands
----------------------
  run       Run the full pipeline (detect + run).
  detect    Run detect() only (implies --dry).
  config    Print the merged config as YAML.
  modules   List discovered modules.
  summary   Print a summary of the last run (reads the run summary dict).

Global flags
------------
  --dry             Dry-run mode (detect only, no mutations).
  --enable  NAME    Force-enable a module.
  --disable NAME    Force-disable a module.
  --set KEY=VALUE   Override a config key (dot-notation, repeatable).
  --config-dir DIR  Override the config directory path.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

try:
    import yaml
    _yaml_available = True
except ImportError:
    _yaml_available = False

# Resolve the default config dir relative to the project root.
_HERE = Path(__file__).resolve()
_DEFAULT_CONFIG_DIR = _HERE.parents[5] / "config"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prism",
        description="Prism — modular, deterministic, colour-aware data-quality orchestrator.",
    )
    parser.add_argument(
        "--config-dir",
        default=str(_DEFAULT_CONFIG_DIR),
        metavar="DIR",
        help="Path to the config/ directory (default: auto-detected).",
    )
    parser.add_argument(
        "--dry",
        action="store_true",
        default=False,
        help="Dry-run mode: run detect() only, no mutations.",
    )
    parser.add_argument(
        "--enable",
        action="append",
        default=[],
        metavar="MODULE",
        help="Force-enable a module (repeatable).",
    )
    parser.add_argument(
        "--disable",
        action="append",
        default=[],
        metavar="MODULE",
        help="Force-disable a module (repeatable).",
    )
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        dest="set_overrides",
        help="Override a config key in dot-notation (repeatable).",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    sub.add_parser("run",     help="Run the full pipeline.")
    sub.add_parser("detect",  help="Run detect() only (implies --dry).")
    sub.add_parser("config",  help="Print the merged configuration.")
    sub.add_parser("modules", help="List discovered modules.")
    sub.add_parser("summary", help="Print the last run summary (JSON).")

    return parser


def _parse_set_overrides(raw: List[str]) -> dict:
    """Parse ['key.path=value', ...] into {'key.path': 'value', ...}."""
    result = {}
    for item in raw:
        if "=" not in item:
            print(f"[prism] Warning: --set argument ignored (no '='): {item!r}", file=sys.stderr)
            continue
        k, _, v = item.partition("=")
        result[k.strip()] = v.strip()
    return result


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point.  Returns an exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    config_dir = Path(args.config_dir)
    set_overrides = _parse_set_overrides(args.set_overrides)
    dry_run = args.dry or args.command == "detect"

    # Lazy imports so the CLI can print help without tUilKit installed.
    from prism.config_manager import PrismConfig
    from prism.core.registry import ModuleRegistry
    from prism.orchestrator import PrismOrchestrator

    # Resolve modules dir relative to config_dir (assume standard layout).
    modules_dir = config_dir.parent / "src" / "prism" / "modules"
    if not modules_dir.is_dir():
        modules_dir = None  # type: ignore[assignment]

    # ---------------------------------------------------------------
    # Sub-command: config
    # ---------------------------------------------------------------
    if args.command == "config":
        cfg = PrismConfig(config_dir=config_dir, modules_dir=modules_dir)
        raw = cfg.raw
        if _yaml_available:
            print(yaml.dump(raw, default_flow_style=False, sort_keys=True))
        else:
            print(json.dumps(raw, indent=2))
        return 0

    # ---------------------------------------------------------------
    # Sub-command: modules
    # ---------------------------------------------------------------
    if args.command == "modules":
        registry = ModuleRegistry()
        discovered = registry.discover()
        if not discovered:
            print("No modules discovered.")
        else:
            print("Discovered modules:")
            for name in sorted(discovered):
                print(f"  • {name}")
        return 0

    # ---------------------------------------------------------------
    # Sub-commands: run / detect / summary
    # ---------------------------------------------------------------
    orchestrator = PrismOrchestrator(
        config_dir=config_dir,
        modules_dir=modules_dir,
        dry_run=dry_run,
        enable_overrides=args.enable,
        disable_overrides=args.disable,
        set_overrides=set_overrides,
    )

    result = orchestrator.run(dataset=None)

    if args.command == "summary":
        print(json.dumps(result, indent=2))

    failed = result.get("modules", {}).get("failed", 0)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
