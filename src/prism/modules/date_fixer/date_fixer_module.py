#!/usr/bin/env python3
"""
prism/modules/date_fixer/date_fixer_module.py - Prism Date-Field Fixer Module

Auto-scans a dataset (list-of-dicts) for date fields and converts them to a
configured output format.  Both the expected input format(s) and the target
output format are config-driven.

Configuration keys (modules.date_fixer in config.yaml):
  enabled         bool       Whether this module is active (default: true).
  date_fields     list[str]  Column names to treat as date fields.
                             If empty and auto_detect is false, nothing runs.
  input_formats   list[str]  strptime format strings to try when parsing
                             incoming date values.
                             (default: ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
                                        "%d-%m-%Y", "%Y/%m/%d"])
  output_format   str        strftime format for the normalised output.
                             (default: "%Y-%m-%d")
  auto_detect     bool       When true, scan all columns for date-like
                             values instead of relying on date_fields only.
                             (default: false)
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from prism.module_base import IssueReport, ModuleResult, PrismModule


# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------

# Loose pattern to flag a value as "could be a date" during auto-detection.
_DATE_HEURISTIC = re.compile(
    r"^\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}"          # numeric separators
    r"|^\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"            # e.g. "12 January 2024"
    r"|\d{4}-\d{2}-\d{2}",                           # ISO fragment inside value
    re.IGNORECASE,
)

_DEFAULT_INPUT_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%Y.%m.%d",
    "%d %b %Y",
    "%d %B %Y",
]


def _try_parse(value: str, formats: List[str]) -> Optional[datetime]:
    """Try each format in *formats*; return the first successful parse."""
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _looks_like_date(value: Any) -> bool:
    """Return True when *value* appears to be a date string."""
    if not isinstance(value, str):
        return False
    return bool(_DATE_HEURISTIC.search(value.strip()))


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class DateFixerModule(PrismModule):
    """
    Prism module: detects malformed date fields and normalises them.

    detect()  — Identifies rows where a configured date column cannot be
                parsed using any of the expected input formats, or whose
                value doesn't already match the output format.
    run()     — Converts every date-field value that can be parsed to the
                target output_format; unparseable values are flagged in the
                changelog but left unchanged.
    """

    name: str = "date_fixer"

    def __init__(self, config: Dict, logger: Any) -> None:
        super().__init__(config, logger)
        self._date_fields: List[str] = list(config.get("date_fields", []))
        self._input_formats: List[str] = list(
            config.get("input_formats", _DEFAULT_INPUT_FORMATS)
        )
        self._output_format: str = str(config.get("output_format", "%Y-%m-%d"))
        self._auto_detect: bool = bool(config.get("auto_detect", False))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _effective_date_fields(self, dataset: List[Dict]) -> List[str]:
        """Return the list of field names to inspect."""
        if self._date_fields:
            return self._date_fields
        if self._auto_detect and dataset:
            # Collect columns whose first non-None value looks like a date.
            candidate_fields: List[str] = []
            first_row = next((r for r in dataset if isinstance(r, dict)), {})
            for col in first_row.keys():
                for row in dataset:
                    val = row.get(col) if isinstance(row, dict) else None
                    if val is not None:
                        if _looks_like_date(val):
                            candidate_fields.append(col)
                        break
            return candidate_fields
        return []

    def _parse_value(self, value: Any) -> Tuple[Optional[datetime], Optional[str]]:
        """
        Attempt to parse *value* using configured input formats.

        Returns (datetime, matched_format) or (None, None) on failure.
        """
        if not isinstance(value, str) or not value.strip():
            return None, None
        for fmt in self._input_formats:
            try:
                dt = datetime.strptime(value.strip(), fmt)
                return dt, fmt
            except (ValueError, AttributeError):
                continue
        return None, None

    # ------------------------------------------------------------------
    # detect
    # ------------------------------------------------------------------

    def detect(self, dataset: Any) -> IssueReport:
        """
        Scan *dataset* for date-field values that cannot be parsed or are
        not already in the target output format.  Does not mutate the data.
        """
        report = IssueReport()

        if not isinstance(dataset, list) or not dataset:
            return report

        fields = self._effective_date_fields(dataset)
        if not fields:
            self.logger.colour_log(
                "!info DateFixerModule.detect: no date fields configured.",
            )
            return report

        for idx, row in enumerate(dataset):
            if not isinstance(row, dict):
                continue
            for field in fields:
                if field not in row:
                    continue
                val = row[field]
                if val is None:
                    continue
                if not isinstance(val, str):
                    report.add(
                        f"Row {idx}: field {field!r} is not a string ({type(val).__name__})",
                        issue_type="non_string_date",
                    )
                    continue
                # Check if value is already in the output format.
                try:
                    datetime.strptime(val.strip(), self._output_format)
                    continue  # already correct
                except ValueError:
                    pass
                # Attempt parsing with input formats.
                dt, _ = self._parse_value(val)
                if dt is None:
                    report.add(
                        f"Row {idx}: field {field!r} = {val!r} could not be parsed",
                        issue_type="unparseable_date",
                    )
                else:
                    report.add(
                        f"Row {idx}: field {field!r} = {val!r} needs reformatting",
                        issue_type="date_needs_reformat",
                    )

        if report.passed:
            self.logger.colour_log(
                "!done DateFixerModule.detect: all date fields OK.",
            )
        else:
            self.logger.colour_log(
                "!warn DateFixerModule.detect: issues=", len(report.issues),
            )

        return report

    # ------------------------------------------------------------------
    # run
    # ------------------------------------------------------------------

    def run(self, dataset: Any) -> ModuleResult:
        """
        Normalise all date-field values in *dataset* to *output_format*.

        Values that cannot be parsed are left unchanged; each such case is
        recorded in the changelog.
        """
        result = ModuleResult(dataset=dataset)

        if not isinstance(dataset, list) or not dataset:
            result.record("Dataset is empty or not a list; nothing to process.")
            return result

        fields = self._effective_date_fields(dataset)
        if not fields:
            result.record("No date fields configured; dataset returned unchanged.")
            return result

        converted = 0
        skipped = 0

        for idx, row in enumerate(dataset):
            if not isinstance(row, dict):
                continue
            for field in fields:
                if field not in row:
                    continue
                val = row[field]
                if val is None or not isinstance(val, str):
                    continue
                # Skip values already in the target format.
                try:
                    datetime.strptime(val.strip(), self._output_format)
                    continue
                except ValueError:
                    pass
                dt, matched_fmt = self._parse_value(val)
                if dt is not None:
                    new_val = dt.strftime(self._output_format)
                    row[field] = new_val
                    converted += 1
                    result.record(
                        f"Row {idx}: {field!r} converted {val!r} → {new_val!r}"
                        f" (parsed as {matched_fmt!r})"
                    )
                else:
                    skipped += 1
                    result.record(
                        f"Row {idx}: {field!r} = {val!r} could not be parsed — skipped"
                    )

        self.logger.colour_log(
            "!done DateFixerModule.run: converted", converted,
            "values,", skipped, "unparseable skipped.",
        )
        return result
