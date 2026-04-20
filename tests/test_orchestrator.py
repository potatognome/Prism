#!/usr/bin/env python3
"""
tests/test_orchestrator.py - Prism Orchestrator Test Suite

Validates:
  - PrismConfig: YAML loading, config.d deep-merge, for_module() slices.
  - PrismModule ABC: IssueReport, ModuleResult data containers.
  - ModuleRegistry: dynamic discovery of PrismModule subclasses.
  - PrismOrchestrator: full lifecycle, dry-run mode, enable/disable,
    --set overrides, run summary structure.
  - ExampleModule: detect() and run() behaviour.

tUilKit is mocked so these tests can run in any environment.
"""

import copy
import importlib
import json
import sys
import types
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path setup — allow imports from src/
# ---------------------------------------------------------------------------

_TESTS_DIR  = Path(__file__).resolve().parent
_SRC_DIR    = _TESTS_DIR.parent / "src"
_CONFIG_DIR = _TESTS_DIR.parent / "config"

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# ---------------------------------------------------------------------------
# tUilKit mock — installed before any prism imports that reference tUilKit
# ---------------------------------------------------------------------------

def _make_tuilkit_mock() -> types.ModuleType:
    """Build a minimal tUilKit stub that satisfies prism imports."""
    mock_logger = MagicMock()
    mock_logger.colour_log = MagicMock()
    mock_logger.log_exception = MagicMock()

    tuilkit = types.ModuleType("tUilKit")
    tuilkit.get_logger = MagicMock(return_value=mock_logger)
    tuilkit.get_config_loader = MagicMock(return_value=MagicMock())
    tuilkit.get_file_system = MagicMock(return_value=MagicMock())
    return tuilkit


_tuilkit_mock = _make_tuilkit_mock()
sys.modules["tUilKit"] = _tuilkit_mock


# ---------------------------------------------------------------------------
# Now import prism modules (tUilKit is already mocked in sys.modules)
# ---------------------------------------------------------------------------

from prism.config_manager import PrismConfig, _deep_merge  # noqa: E402
from prism.core.registry import ModuleRegistry              # noqa: E402
from prism.module_base import IssueReport, ModuleResult, PrismModule  # noqa: E402
from prism.modules.example.example_module import ExampleModule  # noqa: E402
from prism.orchestrator import PrismOrchestrator            # noqa: E402
from prism.run_summary import ModuleRecord, RunSummary      # noqa: E402


# ===========================================================================
# 1. Utility: _deep_merge
# ===========================================================================

class TestDeepMerge(unittest.TestCase):

    def test_flat_merge(self):
        base     = {"a": 1, "b": 2}
        override = {"b": 99, "c": 3}
        result   = _deep_merge(base, override)
        self.assertEqual(result, {"a": 1, "b": 99, "c": 3})

    def test_nested_merge(self):
        base     = {"x": {"a": 1, "b": 2}}
        override = {"x": {"b": 99, "c": 3}}
        result   = _deep_merge(base, override)
        self.assertEqual(result["x"], {"a": 1, "b": 99, "c": 3})

    def test_base_not_mutated(self):
        base     = {"a": {"nested": 1}}
        override = {"a": {"nested": 99}}
        _deep_merge(base, override)
        self.assertEqual(base["a"]["nested"], 1)

    def test_override_wins_on_scalar(self):
        result = _deep_merge({"k": "old"}, {"k": "new"})
        self.assertEqual(result["k"], "new")

    def test_empty_override(self):
        base = {"a": 1}
        self.assertEqual(_deep_merge(base, {}), {"a": 1})

    def test_empty_base(self):
        override = {"a": 1}
        self.assertEqual(_deep_merge({}, override), {"a": 1})


# ===========================================================================
# 2. PrismConfig — loading from real files
# ===========================================================================

class TestPrismConfig(unittest.TestCase):

    def setUp(self):
        self.config = PrismConfig(config_dir=_CONFIG_DIR)

    def test_loads_project_name(self):
        project = self.config.get("project", {})
        self.assertEqual(project.get("name"), "Prism")

    def test_loads_orchestrator_section(self):
        orch = self.config.orchestrator
        self.assertIsInstance(orch, dict)
        self.assertIn("dry_run", orch)

    def test_loads_logging_section(self):
        log = self.config.logging
        self.assertIsInstance(log, dict)
        self.assertIn("log_files", log)

    def test_loads_colours_section(self):
        colours = self.config.colours
        self.assertIsInstance(colours, dict)

    def test_config_d_merged(self):
        """config.d/10_display.yaml must be deep-merged into base."""
        raw = self.config.raw
        self.assertIn("display", raw)

    def test_for_module_returns_dict(self):
        cfg = self.config.for_module("example")
        self.assertIsInstance(cfg, dict)

    def test_for_module_enabled_flag(self):
        cfg = self.config.for_module("example")
        self.assertTrue(cfg.get("enabled", True))

    def test_raw_is_copy(self):
        r1 = self.config.raw
        r1["__mutated"] = True
        r2 = self.config.raw
        self.assertNotIn("__mutated", r2)

    def test_missing_config_dir_returns_empty(self):
        cfg = PrismConfig(config_dir=Path("/nonexistent/path"))
        self.assertEqual(cfg.raw, {})

    def test_for_module_unknown_returns_empty(self):
        cfg = self.config.for_module("__no_such_module__")
        self.assertEqual(cfg, {})


# ===========================================================================
# 3. IssueReport
# ===========================================================================

class TestIssueReport(unittest.TestCase):

    def test_passed_when_empty(self):
        r = IssueReport()
        self.assertTrue(r.passed)

    def test_not_passed_after_add(self):
        r = IssueReport()
        r.add("Something is wrong", issue_type="test_type")
        self.assertFalse(r.passed)

    def test_counts_incremented(self):
        r = IssueReport()
        r.add("issue A", "type_x")
        r.add("issue B", "type_x")
        r.add("issue C", "type_y")
        self.assertEqual(r.counts["type_x"], 2)
        self.assertEqual(r.counts["type_y"], 1)

    def test_issues_list(self):
        r = IssueReport()
        r.add("issue 1")
        r.add("issue 2")
        self.assertEqual(len(r.issues), 2)


# ===========================================================================
# 4. ModuleResult
# ===========================================================================

class TestModuleResult(unittest.TestCase):

    def test_default_success(self):
        r = ModuleResult()
        self.assertTrue(r.success)

    def test_record_changelog(self):
        r = ModuleResult(dataset=[])
        r.record("change 1")
        r.record("change 2")
        self.assertEqual(len(r.changelog), 2)

    def test_failure_flag(self):
        r = ModuleResult(success=False, error="oops")
        self.assertFalse(r.success)
        self.assertEqual(r.error, "oops")


# ===========================================================================
# 5. PrismModule ABC
# ===========================================================================

class TestPrismModuleABC(unittest.TestCase):

    def test_cannot_instantiate_abstract(self):
        logger = MagicMock()
        with self.assertRaises(TypeError):
            PrismModule(config={}, logger=logger)  # type: ignore[abstract]

    def test_enabled_default(self):
        class Concrete(PrismModule):
            name = "concrete"
            def detect(self, dataset): return IssueReport()
            def run(self, dataset):    return ModuleResult()

        m = Concrete(config={}, logger=MagicMock())
        self.assertTrue(m.enabled)

    def test_disabled_via_config(self):
        class Concrete(PrismModule):
            name = "concrete"
            def detect(self, dataset): return IssueReport()
            def run(self, dataset):    return ModuleResult()

        m = Concrete(config={"enabled": False}, logger=MagicMock())
        self.assertFalse(m.enabled)


# ===========================================================================
# 6. ExampleModule
# ===========================================================================

class TestExampleModule(unittest.TestCase):

    def _make_module(self, config=None):
        return ExampleModule(
            config=config or {"enabled": True, "null_placeholder": "N/A"},
            logger=MagicMock(),
        )

    # detect ---

    def test_detect_none_dataset_reports_issue(self):
        m = self._make_module()
        report = m.detect(None)
        self.assertFalse(report.passed)
        self.assertIn("missing_dataset", report.counts)

    def test_detect_clean_data_passes(self):
        m = self._make_module()
        report = m.detect([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
        self.assertTrue(report.passed)

    def test_detect_null_value_found(self):
        m = self._make_module()
        report = m.detect([{"a": None, "b": 2}])
        self.assertFalse(report.passed)
        self.assertGreater(report.counts.get("null_value", 0), 0)

    def test_detect_does_not_mutate(self):
        m = self._make_module()
        dataset = [{"a": None}]
        m.detect(dataset)
        self.assertIsNone(dataset[0]["a"])  # unchanged

    # run ---

    def test_run_none_dataset_failure(self):
        m = self._make_module()
        result = m.run(None)
        self.assertFalse(result.success)

    def test_run_fills_null_in_dicts(self):
        m = self._make_module()
        dataset = [{"a": None, "b": 2}, {"a": 3, "b": None}]
        result = m.run(dataset)
        self.assertTrue(result.success)
        self.assertEqual(dataset[0]["a"], "N/A")
        self.assertEqual(dataset[1]["b"], "N/A")

    def test_run_fills_null_in_lists(self):
        m = self._make_module()
        dataset = [[1, None, 3], [None, 5, 6]]
        result = m.run(dataset)
        self.assertEqual(dataset[0][1], "N/A")
        self.assertEqual(dataset[1][0], "N/A")

    def test_run_changelog_entries(self):
        m = self._make_module()
        dataset = [{"a": None}]
        result = m.run(dataset)
        self.assertGreater(len(result.changelog), 0)

    def test_run_custom_placeholder(self):
        m = self._make_module(config={"enabled": True, "null_placeholder": "MISSING"})
        dataset = [{"x": None}]
        m.run(dataset)
        self.assertEqual(dataset[0]["x"], "MISSING")

    def test_run_unsupported_type_returns_unchanged(self):
        m = self._make_module()
        result = m.run("not a list")
        self.assertTrue(result.success)


# ===========================================================================
# 7. ModuleRegistry
# ===========================================================================

class TestModuleRegistry(unittest.TestCase):

    def test_discover_finds_example(self):
        registry = ModuleRegistry()
        names = registry.discover()
        self.assertIn("example", names)

    def test_get_returns_class(self):
        registry = ModuleRegistry()
        registry.discover()
        cls = registry.get("example")
        self.assertIsNotNone(cls)
        self.assertTrue(issubclass(cls, PrismModule))

    def test_get_unknown_returns_none(self):
        registry = ModuleRegistry()
        registry.discover()
        self.assertIsNone(registry.get("__no_such_module__"))

    def test_all_names_after_discover(self):
        registry = ModuleRegistry()
        registry.discover()
        self.assertIsInstance(registry.all_names(), list)
        self.assertIn("example", registry.all_names())


# ===========================================================================
# 8. RunSummary / ModuleRecord
# ===========================================================================

class TestRunSummary(unittest.TestCase):

    def _make_logger(self):
        logger = MagicMock()
        logger.colour_log = MagicMock()
        return logger

    def test_summary_structure(self):
        summary = RunSummary(run_id="test-001", dry_run=False)
        rec = summary.begin_module("example")
        rec.issue_report = IssueReport()
        rec.result = ModuleResult(success=True)
        summary.end_module(rec)
        data = summary.finalise(self._make_logger())

        self.assertEqual(data["run_id"], "test-001")
        self.assertFalse(data["dry_run"])
        self.assertIn("modules", data)
        self.assertEqual(data["modules"]["total"], 1)
        self.assertEqual(data["modules"]["passed"], 1)
        self.assertEqual(data["modules"]["failed"], 0)

    def test_skipped_module(self):
        summary = RunSummary(run_id="test-002", dry_run=False)
        rec = summary.begin_module("skipped_mod")
        rec.skipped = True
        summary.end_module(rec)
        data = summary.finalise(self._make_logger())
        self.assertEqual(data["modules"]["skipped"], 1)

    def test_failed_module(self):
        summary = RunSummary(run_id="test-003", dry_run=False)
        rec = summary.begin_module("failed_mod")
        rec.error = "Something went wrong"
        summary.end_module(rec)
        data = summary.finalise(self._make_logger())
        self.assertEqual(data["modules"]["failed"], 1)

    def test_elapsed_seconds_present(self):
        summary = RunSummary(run_id="test-004")
        data = summary.finalise(self._make_logger())
        self.assertIsNotNone(data.get("elapsed_seconds"))

    def test_module_results_list(self):
        summary = RunSummary(run_id="test-005")
        for name in ["mod_a", "mod_b"]:
            rec = summary.begin_module(name)
            rec.result = ModuleResult()
            summary.end_module(rec)
        data = summary.finalise(self._make_logger())
        self.assertEqual(len(data["module_results"]), 2)


# ===========================================================================
# 9. PrismOrchestrator — full pipeline
# ===========================================================================

class TestPrismOrchestrator(unittest.TestCase):

    def _make_orchestrator(self, **kwargs):
        return PrismOrchestrator(
            config_dir=_CONFIG_DIR,
            **kwargs,
        )

    def test_run_returns_summary_dict(self):
        orch = self._make_orchestrator()
        result = orch.run(dataset=None)
        self.assertIsInstance(result, dict)
        self.assertIn("run_id", result)
        self.assertIn("modules", result)

    def test_run_id_has_prefix(self):
        orch = self._make_orchestrator()
        result = orch.run(dataset=None)
        self.assertTrue(result["run_id"].startswith("prism-"))

    def test_dry_run_flag_in_summary(self):
        orch = self._make_orchestrator(dry_run=True)
        result = orch.run(dataset=None)
        self.assertTrue(result["dry_run"])

    def test_disable_module_skips_it(self):
        orch = self._make_orchestrator(disable_overrides=["example"])
        result = orch.run(dataset=None)
        skipped_names = [
            r["module"] for r in result["module_results"] if r["skipped"]
        ]
        self.assertIn("example", skipped_names)

    def test_enable_override_forces_module_on(self):
        """
        Explicitly disabling via config then re-enabling via CLI override
        should keep the module active.
        """
        orch = self._make_orchestrator(
            enable_overrides=["example"],
            disable_overrides=[],
        )
        result = orch.run(dataset=[{"a": None}])
        passed_names = [
            r["module"] for r in result["module_results"] if not r["skipped"]
        ]
        self.assertIn("example", passed_names)

    def test_set_override_applied(self):
        """--set modules.example.null_placeholder=CUSTOM should reach module."""
        orch = self._make_orchestrator(
            set_overrides={"modules.example.null_placeholder": "CUSTOM"}
        )
        dataset = [{"col": None}]
        orch.run(dataset=dataset)
        # After run() the null should have been replaced.
        self.assertEqual(dataset[0]["col"], "CUSTOM")

    def test_no_modules_does_not_raise(self):
        """Orchestrator must be resilient when no modules are discovered."""
        with patch.object(ModuleRegistry, "discover", return_value=[]):
            orch = self._make_orchestrator()
            result = orch.run(dataset=None)
        self.assertEqual(result["modules"]["total"], 0)

    def test_example_module_runs_against_dataset(self):
        dataset = [{"a": 1, "b": None}, {"a": None, "b": 2}]
        orch = self._make_orchestrator()
        result = orch.run(dataset=dataset)
        # Both None values should have been filled by ExampleModule.
        self.assertEqual(dataset[0]["b"], "N/A")
        self.assertEqual(dataset[1]["a"], "N/A")
        # Verify via result structure.
        module_res = next(
            (r for r in result["module_results"] if r["module"] == "example"),
            None,
        )
        self.assertIsNotNone(module_res)
        self.assertTrue(module_res["success"])


# ===========================================================================
# 10. CLI arg parsing
# ===========================================================================

class TestCLI(unittest.TestCase):

    def _cli(self, *args):
        from prism.interfaces.cli.cli import _build_parser, _parse_set_overrides
        return _build_parser, _parse_set_overrides

    def test_parse_set_overrides_valid(self):
        from prism.interfaces.cli.cli import _parse_set_overrides
        result = _parse_set_overrides(["a.b=1", "x.y.z=hello"])
        self.assertEqual(result["a.b"], "1")
        self.assertEqual(result["x.y.z"], "hello")

    def test_parse_set_overrides_no_eq_ignored(self):
        from prism.interfaces.cli.cli import _parse_set_overrides
        result = _parse_set_overrides(["invalid_no_eq"])
        self.assertEqual(result, {})

    def test_parser_dry_flag(self):
        from prism.interfaces.cli.cli import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["--dry", "run"])
        self.assertTrue(args.dry)

    def test_parser_enable_disable(self):
        from prism.interfaces.cli.cli import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["--enable", "mod_a", "--disable", "mod_b", "run"])
        self.assertIn("mod_a", args.enable)
        self.assertIn("mod_b", args.disable)

    def test_parser_detect_subcommand(self):
        from prism.interfaces.cli.cli import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["detect"])
        self.assertEqual(args.command, "detect")


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
