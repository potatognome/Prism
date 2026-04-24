#!/usr/bin/env python3
"""
Examples: date_fixer — DateFixerModule public API and edge-case tests.

Exercises DateFixerModule.detect() and DateFixerModule.run() across normal
inputs, multiple date formats, auto-detect mode, and adversarial scenarios.

Run from the project root:
    python examples/test_date_fixer.py
"""

import csv
import json
import os
import sys
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
SCRIPT_LOG    = str(TEST_LOGS_FOLDER / "test_date_fixer.log")
BORDER        = {"TOP": "=", "BOTTOM": "=", "LEFT": " ", "RIGHT": " "}

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------

from prism.modules.date_fixer.date_fixer_module import DateFixerModule  # noqa: E402


def _make_module(**kwargs):
    defaults = {
        "enabled":        True,
        "date_fields":    ["signup_date"],
        "input_formats":  ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y.%m.%d", "%d.%m.%Y"],
        "output_format":  "%Y-%m-%d",
        "auto_detect":    False,
    }
    defaults.update(kwargs)
    return DateFixerModule(config=defaults, logger=logger)


def _load_csv(path: Path):
    """Load a CSV file as a list of dicts."""
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------

def test_detect_iso_format_passes(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"signup_date": "2024-01-15"}, {"signup_date": "2023-12-31"}]
    logger.colour_log(
        "!output", "report =", "!proc", "DateFixerModule.", "!text", "detect",
        "!args", "ISO dates → should pass",
        log_files=log_targets,
    )
    m = _make_module()
    report = m.detect(dataset)
    logger.colour_log("!test", "Assert: all ISO dates pass detection", log_files=log_targets)
    assert report.passed, f"Expected passed; got issues={report.issues}"
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_detect_wrong_format_flagged(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"signup_date": "15/01/2024"}]
    m = _make_module()
    report = m.detect(dataset)
    logger.colour_log("!test", "Assert: dd/mm/yyyy flagged for reformat", log_files=log_targets)
    assert "date_needs_reformat" in report.counts
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_detect_unparseable_flagged(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module()
    report = m.detect([{"signup_date": "not-a-date"}])
    logger.colour_log("!test", "Assert: unparseable value flagged", log_files=log_targets)
    assert "unparseable_date" in report.counts
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_detect_does_not_mutate(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"signup_date": "15/01/2024"}]
    original = dataset[0]["signup_date"]
    m = _make_module()
    m.detect(dataset)
    logger.colour_log("!test", "Assert: detect does not mutate data", log_files=log_targets)
    assert dataset[0]["signup_date"] == original
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_converts_ddmmyyyy(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"signup_date": "15/01/2024"}]
    m = _make_module()
    result = m.run(dataset)
    logger.colour_log("!test", "Assert: dd/mm/yyyy converted to ISO", log_files=log_targets)
    assert dataset[0]["signup_date"] == "2024-01-15", dataset[0]["signup_date"]
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_converts_mmddyyyy(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"signup_date": "03/20/2024"}]
    m = _make_module()
    result = m.run(dataset)
    logger.colour_log("!test", "Assert: mm/dd/yyyy converted to ISO", log_files=log_targets)
    assert dataset[0]["signup_date"] == "2024-03-20", dataset[0]["signup_date"]
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_dotted_format(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"signup_date": "2024.04.01"}]
    m = _make_module(input_formats=["%Y.%m.%d", "%d.%m.%Y"])
    result = m.run(dataset)
    logger.colour_log("!test", "Assert: yyyy.mm.dd converted to ISO", log_files=log_targets)
    assert dataset[0]["signup_date"] == "2024-04-01", dataset[0]["signup_date"]
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_unparseable_unchanged(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"signup_date": "not-a-date"}]
    m = _make_module()
    result = m.run(dataset)
    logger.colour_log(
        "!test", "Assert: unparseable value left unchanged", log_files=log_targets
    )
    assert dataset[0]["signup_date"] == "not-a-date"
    logger.colour_log("!warn", "Skipped entry logged:", "!data",
                      str(result.changelog), log_files=log_targets)
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_empty_field_unchanged(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"signup_date": ""}]
    m = _make_module()
    result = m.run(dataset)
    logger.colour_log("!test", "Assert: empty string left unchanged", log_files=log_targets)
    assert dataset[0]["signup_date"] == ""
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_none_field_unchanged(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"signup_date": None}]
    m = _make_module()
    m.run(dataset)
    logger.colour_log("!test", "Assert: None value left unchanged", log_files=log_targets)
    assert dataset[0]["signup_date"] is None
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_multiple_date_fields(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"start": "15/01/2024", "end": "20/03/2024"}]
    m = _make_module(date_fields=["start", "end"])
    m.run(dataset)
    logger.colour_log("!test", "Assert: both date fields converted", log_files=log_targets)
    assert dataset[0]["start"] == "2024-01-15"
    assert dataset[0]["end"] == "2024-03-20"
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_custom_output_format(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [{"signup_date": "2024-01-15"}]
    m = _make_module(output_format="%d/%m/%Y")
    m.run(dataset)
    logger.colour_log("!test", "Assert: custom output format applied", log_files=log_targets)
    assert dataset[0]["signup_date"] == "15/01/2024", dataset[0]["signup_date"]
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_auto_detect_date_column(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    dataset = [
        {"event": "15/01/2024", "name": "test_event"},
        {"event": "20/03/2024", "name": "other"},
    ]
    m = _make_module(date_fields=[], auto_detect=True)
    result = m.run(dataset)
    logger.colour_log(
        "!test", "Assert: auto-detect converted date column",
        log_files=log_targets,
    )
    assert dataset[0]["event"] == "2024-01-15", dataset[0]["event"]
    logger.colour_log("!pass", "PASSED", log_files=log_targets)


def test_run_from_csv_file(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    csv_path = INPUT_DATA / "sample_dates.csv"
    if not csv_path.exists():
        logger.colour_log("!warn", "CSV fixture missing; skipping.", log_files=log_targets)
        return

    dataset = _load_csv(csv_path)
    logger.colour_log(
        "!info", "Loaded CSV:", "!file", csv_path.name,
        "!int", str(len(dataset)), "!info", "rows",
        log_files=log_targets,
    )
    m = _make_module(date_fields=["signup_date", "last_login"])
    result = m.run(dataset)

    logger.colour_log(
        "!test", "Assert: run completes successfully", log_files=log_targets
    )
    assert result.success
    logger.colour_log("!pass", "PASSED", log_files=log_targets)

    logger.colour_log(
        "!info", "Changelog entries:", "!int", str(len(result.changelog)),
        log_files=log_targets,
    )
    for entry in result.changelog:
        logger.colour_log("!data", f"  {entry}", log_files=log_targets)


# ---------------------------------------------------------------------------
# Break / adversarial inputs
# ---------------------------------------------------------------------------

def test_break_inputs(function_log=None):
    log_targets = [TEST_LOG_FILE, function_log] if function_log else [TEST_LOG_FILE]
    m = _make_module()
    adversarial = [
        ("empty string",    ""),
        ("whitespace",      "   "),
        ("long string",     "A" * 500),
        ("null bytes",      "\x00\xff"),
        ("special chars",   "!@#$%^&*()"),
        ("negative number", "-1"),
        ("float string",    "1.5"),
        ("future year",     "2999-12-31"),
        ("zero date",       "0000-00-00"),
    ]
    for label, val in adversarial:
        dataset = [{"signup_date": val}]
        try:
            report = m.detect(dataset)
            result = m.run(dataset)
            logger.colour_log(
                "!warn", f"  Break ({label}) →",
                "!data", repr(dataset[0]["signup_date"])[:40],
                "!info", "issues:", "!int", str(len(report.issues)),
                log_files=log_targets,
            )
        except Exception as exc:
            logger.colour_log(
                "!error", f"  Break ({label}) raised:", "!data", str(exc),
                log_files=log_targets,
            )


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

Examples = [
    (1,  "test_detect_iso_format_passes",    test_detect_iso_format_passes,    "ISO dates pass detection"),
    (2,  "test_detect_wrong_format_flagged", test_detect_wrong_format_flagged, "dd/mm/yyyy flagged for reformat"),
    (3,  "test_detect_unparseable_flagged",  test_detect_unparseable_flagged,  "unparseable value flagged"),
    (4,  "test_detect_does_not_mutate",      test_detect_does_not_mutate,      "detect() does not mutate data"),
    (5,  "test_run_converts_ddmmyyyy",       test_run_converts_ddmmyyyy,       "dd/mm/yyyy → ISO"),
    (6,  "test_run_converts_mmddyyyy",       test_run_converts_mmddyyyy,       "mm/dd/yyyy → ISO"),
    (7,  "test_run_dotted_format",           test_run_dotted_format,           "yyyy.mm.dd → ISO"),
    (8,  "test_run_unparseable_unchanged",   test_run_unparseable_unchanged,   "unparseable left unchanged"),
    (9,  "test_run_empty_field_unchanged",   test_run_empty_field_unchanged,   "empty string left unchanged"),
    (10, "test_run_none_field_unchanged",    test_run_none_field_unchanged,    "None value left unchanged"),
    (11, "test_run_multiple_date_fields",    test_run_multiple_date_fields,    "multiple date columns converted"),
    (12, "test_run_custom_output_format",    test_run_custom_output_format,    "custom output_format applied"),
    (13, "test_auto_detect_date_column",     test_auto_detect_date_column,     "auto_detect finds date column"),
    (14, "test_run_from_csv_file",           test_run_from_csv_file,           "run on sample_dates.csv fixture"),
    (15, "test_break_inputs",               test_break_inputs,                "adversarial / break inputs"),
]

results, successful, unsuccessful = [], [], []

os.system("cls" if os.name == "nt" else "clear")
now = datetime.now()
logger.print_rainbow_row(log_files=[TEST_LOG_FILE])
logger.colour_log(
    "!date", now.strftime("%Y-%m-%d %H:%M:%S"),
    "!proc", "Starting examples:", "!text", "test_date_fixer",
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
    text="Test Summary — test_date_fixer",
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
