#!/usr/bin/env python3
"""
Examples: example_module — ExampleModule public API and edge-case tests.

Exercises ExampleModule.detect() and ExampleModule.run() across normal
inputs, edge cases, and adversarial scenarios.  Produces colour-logged
output alongside per-function and session log files.

Run from the project root:
    python examples/test_example_module.py
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve()
with open(HERE.parent / "test_paths.json", encoding="utf-8") as _f:
    _p = json.load(_f)

PROJECT_ROOT     = Path(_p["project_root"])
WORKSPACE_ROOT   = Path(_p["workspace_root"])
TEST_LOGS_FOLDER = Path(_p["test_logs_folder"])

sys.path.insert(0, str(PROJECT_ROOT / "src"))
TEST_LOGS_FOLDER.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# tUilKit factories
# ---------------------------------------------------------------------------

from tUilKit import get_colour_manager, get_logger  # noqa: E402

colour_manager = get_colour_manager()
logger         = get_logger()

TEST_LOG_FILE  = str(TEST_LOGS_FOLDER / "SESSION.log")
SCRIPT_LOG     = str(TEST_LOGS_FOLDER / "test_example_module.log")
BORDER         = {"TOP": "=", "BOTTOM": "=", "LEFT": " ", "RIGHT": " "}

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------

from prism.modules.example.example_module import ExampleModule  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_module(null_placeholder="N/A"):
    return ExampleModule(
        config={"enabled": True, "null_placeholder": null_placeholder},
        logger=logger,
    )


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------

def test_detect_none_dataset(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    logger.colour_log(
        "!output", "report =", "!proc", "ExampleModule.", "!text", "detect",
        "!args", "with arguments:", "!data", "dataset=None",
        log_files=log_targets,
    )
    m = _make_module()
    report = m.detect(None)
    logger.colour_log(
        "!done", "ran successfully.", "!output", "report:", "!data", repr(report),
        log_files=log_targets,
    )
    logger.colour_log("!test", "Assert: report.passed is False", log_files=log_targets)
    assert not report.passed, "detect(None) should report an issue"
    logger.colour_log("!pass", "PASSED", log_files=log_targets)

    logger.colour_log("!test", "Assert: missing_dataset in counts", log_files=log_targets)
    assert "missing_dataset" in report.counts
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_detect_clean_data(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"a": 1, "b": "hello"}, {"a": 2, "b": "world"}]
    logger.colour_log(
        "!output", "report =", "!proc", "ExampleModule.", "!text", "detect",
        "!args", "with arguments:", "!data", repr(dataset),
        log_files=log_targets,
    )
    m = _make_module()
    report = m.detect(dataset)
    logger.colour_log(
        "!done", "ran successfully.", "!output", "report:", "!data", repr(report),
        log_files=log_targets,
    )
    logger.colour_log("!test", "Assert: report.passed is True", log_files=log_targets)
    assert report.passed
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_detect_null_value(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"a": None, "b": 2}]
    logger.colour_log(
        "!output", "report =", "!proc", "ExampleModule.", "!text", "detect",
        "!args", "dataset with None value",
        log_files=log_targets,
    )
    m = _make_module()
    report = m.detect(dataset)
    logger.colour_log("!test", "Assert: null_value detected", log_files=log_targets)
    assert "null_value" in report.counts
    logger.colour_log("!pass", "PASSED", log_files=log_targets)

    # Verify detect does not mutate
    logger.colour_log("!test", "Assert: dataset not mutated", log_files=log_targets)
    assert dataset[0]["a"] is None
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_fills_nulls_dicts(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"x": None, "y": 10}, {"x": 5, "y": None}]
    logger.colour_log(
        "!output", "result =", "!proc", "ExampleModule.", "!text", "run",
        "!args", "dataset with nulls in dicts",
        log_files=log_targets,
    )
    m = _make_module()
    result = m.run(dataset)
    logger.colour_log(
        "!done", "ran successfully.", "!output", "changelog entries:", "!int",
        str(len(result.changelog)),
        log_files=log_targets,
    )
    logger.colour_log("!test", "Assert: success", log_files=log_targets)
    assert result.success
    logger.colour_log("!pass", "PASSED", log_files=log_targets)

    logger.colour_log("!test", "Assert: nulls replaced with N/A", log_files=log_targets)
    assert dataset[0]["x"] == "N/A"
    assert dataset[1]["y"] == "N/A"
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_fills_nulls_lists(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [[1, None, 3], [None, 5]]
    m = _make_module()
    result = m.run(dataset)
    logger.colour_log("!test", "Assert: list nulls replaced", log_files=log_targets)
    assert dataset[0][1] == "N/A"
    assert dataset[1][0] == "N/A"
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_custom_placeholder(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"val": None}]
    m = _make_module(null_placeholder="MISSING")
    m.run(dataset)
    logger.colour_log("!test", "Assert: custom placeholder used", log_files=log_targets)
    assert dataset[0]["val"] == "MISSING"
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_none_dataset(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module()
    result = m.run(None)
    logger.colour_log("!test", "Assert: run(None) → success=False", log_files=log_targets)
    assert not result.success
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_unsupported_type(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module()
    result = m.run("not a list")
    logger.colour_log(
        "!test", "Assert: unsupported type returns success=True unchanged",
        log_files=log_targets,
    )
    assert result.success
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_detect_edge_empty_list(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module()
    report = m.detect([])
    logger.colour_log("!test", "Assert: empty list passes", log_files=log_targets)
    assert report.passed
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_detect_mixed_row_types(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module()
    dataset = [{"a": None}, [None, 2], {"b": 3}]
    report = m.detect(dataset)
    logger.colour_log(
        "!warn", "Mixed row types — nulls found:", "!int",
        str(len(report.issues)),
        log_files=log_targets,
    )


def test_run_large_dataset(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"col": None if i % 3 == 0 else i} for i in range(300)]
    m = _make_module()
    result = m.run(dataset)
    null_count = sum(1 for r in dataset if r["col"] == "N/A")
    logger.colour_log(
        "!test", "Assert: large dataset processed, replaced nulls:", "!int",
        str(null_count),
        log_files=log_targets,
    )
    assert null_count > 0
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

Examples = [
    (1,  "test_detect_none_dataset",    test_detect_none_dataset,    "detect(None) → missing_dataset issue"),
    (2,  "test_detect_clean_data",      test_detect_clean_data,      "detect with no nulls → passes"),
    (3,  "test_detect_null_value",      test_detect_null_value,      "detect with None value → null_value issue, no mutation"),
    (4,  "test_run_fills_nulls_dicts",  test_run_fills_nulls_dicts,  "run fills nulls in list-of-dicts"),
    (5,  "test_run_fills_nulls_lists",  test_run_fills_nulls_lists,  "run fills nulls in list-of-lists"),
    (6,  "test_run_custom_placeholder", test_run_custom_placeholder, "run with custom null_placeholder"),
    (7,  "test_run_none_dataset",       test_run_none_dataset,       "run(None) → success=False"),
    (8,  "test_run_unsupported_type",   test_run_unsupported_type,   "run(non-list) → unchanged, success=True"),
    (9,  "test_detect_edge_empty_list", test_detect_edge_empty_list, "detect([]) → passes"),
    (10, "test_detect_mixed_row_types", test_detect_mixed_row_types, "detect mixed dict/list rows"),
    (11, "test_run_large_dataset",      test_run_large_dataset,      "run on 300-row dataset"),
]

results, successful, unsuccessful = [], [], []

os.system("cls" if os.name == "nt" else "clear")
now = datetime.now()
logger.print_rainbow_row(log_files=[TEST_LOG_FILE])
logger.colour_log(
    "!date", now.strftime("%Y-%m-%d %H:%M:%S"),
    "!proc", "Starting examples:", "!text", "test_example_module",
    log_files=[TEST_LOG_FILE],
)

for num, name, func, description in Examples:
    function_log = str(TEST_LOGS_FOLDER / f"test_log_{name}.log")
    try:
        logger.print_rainbow_row(log_files=[TEST_LOG_FILE, function_log])
        logger.apply_border(
            text=f"Test {num}: {name}",
            pattern=BORDER,
            total_length=70,
            border_colour="!proc",
            text_colour="!text",
            log_files=[TEST_LOG_FILE, function_log],
        )
        logger.colour_log(
            "!test", "Running:", "!int", str(num), "!proc", name,
            "!info", "—", "!data", description,
            log_files=[TEST_LOG_FILE, function_log],
        )
        time.sleep(0.1)
        func(function_log=function_log)
        logger.colour_log(
            "!pass", "✅ PASSED:", "!int", str(num), "!proc", name,
            log_files=[TEST_LOG_FILE, function_log],
        )
        results.append((num, name, True))
        successful.append(name)
    except AssertionError as exc:
        logger.colour_log(
            "!fail", "❌ FAILED:", "!int", str(num), "!error", str(exc),
            log_files=[TEST_LOG_FILE, function_log],
        )
        results.append((num, name, False))
        unsuccessful.append(name)
    except Exception as exc:
        logger.colour_log(
            "!error", f"Test {num} {name} raised unexpectedly:", "!data", str(exc),
            log_files=[TEST_LOG_FILE, function_log],
        )
        results.append((num, name, False))
        unsuccessful.append(name)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

logger.print_rainbow_row(log_files=[TEST_LOG_FILE])
logger.apply_border(
    text="Test Summary — test_example_module",
    pattern=BORDER,
    total_length=70,
    log_files=[TEST_LOG_FILE],
)
logger.colour_log(
    "!info",  "Total:",  "!int", str(len(results)),
    "!done",  "Passed:", "!int", str(len(successful)),
    "!error", "Failed:", "!int", str(len(unsuccessful)),
    log_files=[TEST_LOG_FILE],
)
for num, name, passed in results:
    key = "!pass" if passed else "!fail"
    logger.colour_log(
        "!int", str(num), key, "PASS" if passed else "FAIL", "!proc", name,
        log_files=[TEST_LOG_FILE],
    )

if unsuccessful:
    sys.exit(1)
