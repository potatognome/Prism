#!/usr/bin/env python3
"""
Examples: prism_params — PrismParamsModule public API and edge-case tests.

Exercises PrismParamsModule.detect() and PrismParamsModule.run() across
valid YAML files, missing files, invalid YAML, missing required keys,
and adversarial file paths.

Run from the project root:
    python examples/test_prism_params.py
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve()
with open(HERE.parent / "test_paths.json", encoding="utf-8") as _f:
    _p = json.load(_f)

PROJECT_ROOT     = Path(_p["project_root"])
WORKSPACE_ROOT   = Path(_p["workspace_root"])
TEST_LOGS_FOLDER = Path(_p["test_logs_folder"])
INPUT_DATA       = HERE.parent / "testInputData"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
TEST_LOGS_FOLDER.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# tUilKit factories
# ---------------------------------------------------------------------------

from tUilKit import get_colour_manager, get_logger  # noqa: E402

colour_manager = get_colour_manager()
logger         = get_logger()

TEST_LOG_FILE = str(TEST_LOGS_FOLDER / "SESSION.log")
SCRIPT_LOG    = str(TEST_LOGS_FOLDER / "test_prism_params.log")
BORDER        = {"TOP": "=", "BOTTOM": "=", "LEFT": " ", "RIGHT": " "}

VALID_PARAMS    = str(INPUT_DATA / "sample_params.yaml")
BAD_YAML_PARAMS = str(INPUT_DATA / "bad_params.yaml")

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------

from prism.modules.prism_params.prism_params_module import PrismParamsModule  # noqa: E402


def _make_module(params_file=None, required_keys=None):
    return PrismParamsModule(
        config={
            "enabled":       True,
            "params_file":   params_file or VALID_PARAMS,
            "required_keys": required_keys or ["parameters"],
        },
        logger=logger,
    )


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------

def test_detect_valid_file_passes(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    logger.colour_log(
        "!output", "report =", "!proc", "PrismParamsModule.", "!text", "detect",
        "!args", "valid YAML params file",
        log_files=log_targets,
    )
    m = _make_module()
    report = m.detect(None)
    logger.colour_log(
        "!done", "ran successfully.", "!output", "report:", "!data", repr(report),
        log_files=log_targets,
    )
    logger.colour_log("!test", "Assert: report.passed is True", log_files=log_targets)
    assert report.passed, f"Unexpected issues: {report.issues}"
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_detect_missing_file_fails(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module(params_file="/nonexistent/path/params.yaml")
    report = m.detect(None)
    logger.colour_log("!test", "Assert: missing file → issue reported", log_files=log_targets)
    assert not report.passed
    assert "missing_params_file" in report.counts
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_detect_missing_required_key(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module(required_keys=["__nonexistent_key__"])
    report = m.detect(None)
    logger.colour_log("!test", "Assert: missing required key flagged", log_files=log_targets)
    assert "missing_required_key" in report.counts
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_detect_all_required_keys_present(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module(required_keys=["parameters", "pipeline"])
    report = m.detect(None)
    logger.colour_log("!test", "Assert: all required keys present", log_files=log_targets)
    assert report.passed
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_detect_no_required_keys(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module(required_keys=[])
    report = m.detect(None)
    logger.colour_log("!test", "Assert: no required keys → passes", log_files=log_targets)
    assert report.passed
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_detect_invalid_yaml(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as fh:
        fh.write(": invalid:\n  yaml: [\nbroken\n")
        tmp = fh.name
    try:
        m = _make_module(params_file=tmp, required_keys=[])
        report = m.detect(None)
        logger.colour_log("!test", "Assert: invalid YAML → issue reported", log_files=log_targets)
        assert not report.passed
        assert "invalid_yaml" in report.counts
        logger.colour_log("!pass", "PASSED", log_files=log_targets)
    finally:
        os.unlink(tmp)


def test_run_loads_params(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    logger.colour_log(
        "!output", "result =", "!proc", "PrismParamsModule.", "!text", "run",
        "!args", "valid YAML params file",
        log_files=log_targets,
    )
    m = _make_module()
    result = m.run(None)
    logger.colour_log(
        "!done", "ran.", "!output", "dataset keys:", "!data",
        str(list(result.dataset.keys()) if isinstance(result.dataset, dict) else "—"),
        log_files=log_targets,
    )
    logger.colour_log("!test", "Assert: success", log_files=log_targets)
    assert result.success
    logger.colour_log("!pass", "PASSED", log_files=log_targets)

    logger.colour_log("!test", "Assert: dataset is dict with 'parameters'", log_files=log_targets)
    assert isinstance(result.dataset, dict)
    assert "parameters" in result.dataset
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_returns_correct_values(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module()
    result = m.run(None)
    params = result.dataset.get("parameters", {})
    logger.colour_log(
        "!info", "  null_threshold:", "!data", str(params.get("null_threshold")),
        log_files=log_targets,
    )
    logger.colour_log(
        "!info", "  encoding:", "!data", str(params.get("encoding")),
        log_files=log_targets,
    )
    logger.colour_log("!test", "Assert: null_threshold == 0.10", log_files=log_targets)
    assert params.get("null_threshold") == 0.10
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_missing_file_failure(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module(params_file="/nonexistent/params.yaml")
    result = m.run(None)
    logger.colour_log("!test", "Assert: missing file → success=False", log_files=log_targets)
    assert not result.success
    assert result.error is not None
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_loads_project_prism_params(function_log=None):
    """Load the actual prism_params.yaml from the project config folder."""
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    project_params = str(PROJECT_ROOT / "config" / "prism_params.yaml")
    m = _make_module(params_file=project_params)
    result = m.run(None)
    logger.colour_log(
        "!info", "Project prism_params.yaml —",
        "!info", "top-level keys:", "!data",
        str(list(result.dataset.keys()) if isinstance(result.dataset, dict) else "—"),
        log_files=log_targets,
    )
    logger.colour_log("!test", "Assert: project params loaded OK", log_files=log_targets)
    assert result.success
    assert "parameters" in result.dataset
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_changelog_entry(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module()
    result = m.run(None)
    logger.colour_log("!test", "Assert: changelog has at least one entry", log_files=log_targets)
    assert len(result.changelog) > 0
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


# ---------------------------------------------------------------------------
# Adversarial / break inputs
# ---------------------------------------------------------------------------

def test_break_params_file_paths(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    adversarial = [
        ("empty string path",    ""),
        ("whitespace path",      "   "),
        ("very long path",       "/tmp/" + "a" * 250 + ".yaml"),
        ("special chars path",   "/tmp/!@#$%^.yaml"),
        ("null bytes path",      "/tmp/\x00null.yaml"),
    ]
    for label, path in adversarial:
        try:
            m = _make_module(params_file=path, required_keys=[])
            report = m.detect(None)
            result = m.run(None)
            logger.colour_log(
                "!warn", f"  Break ({label}) →",
                "!info", "passed:", "!data", str(report.passed),
                "!info", "success:", "!data", str(result.success),
                log_files=log_targets,
            )
        except Exception as exc:
            logger.colour_log(
                "!warn", f"  Break ({label}) raised:", "!data", str(exc)[:80],
                log_files=log_targets,
            )


def test_break_required_keys(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    adversarial_keys = [
        [],
        [""],
        ["__no_such_key__"],
        ["a" * 500],
        ["special!@#", "key"],
        [None],
    ]
    for keys in adversarial_keys:
        try:
            filtered = [k for k in keys if k is not None]
            m = _make_module(required_keys=filtered)
            report = m.detect(None)
            logger.colour_log(
                "!warn", f"  required_keys={keys!r} →",
                "!info", "passed:", "!data", str(report.passed),
                log_files=log_targets,
            )
        except Exception as exc:
            logger.colour_log(
                "!warn", f"  keys={keys!r} raised:", "!data", str(exc)[:80],
                log_files=log_targets,
            )


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

Examples = [
    (1,  "test_detect_valid_file_passes",         test_detect_valid_file_passes,         "valid YAML → passes"),
    (2,  "test_detect_missing_file_fails",         test_detect_missing_file_fails,         "missing file → issue"),
    (3,  "test_detect_missing_required_key",       test_detect_missing_required_key,       "missing required key"),
    (4,  "test_detect_all_required_keys_present",  test_detect_all_required_keys_present,  "all required keys present"),
    (5,  "test_detect_no_required_keys",           test_detect_no_required_keys,           "no required keys → passes"),
    (6,  "test_detect_invalid_yaml",               test_detect_invalid_yaml,               "invalid YAML → issue"),
    (7,  "test_run_loads_params",                  test_run_loads_params,                  "run loads params dict"),
    (8,  "test_run_returns_correct_values",        test_run_returns_correct_values,        "run returns correct values"),
    (9,  "test_run_missing_file_failure",          test_run_missing_file_failure,          "missing file → success=False"),
    (10, "test_run_loads_project_prism_params",    test_run_loads_project_prism_params,    "loads project prism_params.yaml"),
    (11, "test_run_changelog_entry",               test_run_changelog_entry,               "changelog has an entry"),
    (12, "test_break_params_file_paths",           test_break_params_file_paths,           "adversarial file paths"),
    (13, "test_break_required_keys",               test_break_required_keys,               "adversarial required_keys values"),
]

results, successful, unsuccessful = [], [], []

os.system("cls" if os.name == "nt" else "clear")
now = datetime.now()
logger.print_rainbow_row(log_files=[TEST_LOG_FILE])
logger.colour_log(
    "!date", now.strftime("%Y-%m-%d %H:%M:%S"),
    "!proc", "Starting examples:", "!text", "test_prism_params",
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
        time.sleep(0.05)
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
    text="Test Summary — test_prism_params",
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
