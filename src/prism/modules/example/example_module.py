#!/usr/bin/env python3
"""
prism/modules/example/example_module.py - Prism Example Module

A reference implementation of the PrismModule interface that demonstrates
how Prism modules should be structured.  Drop-in replaceable.

This module:
  - Detects rows with null values in a dataset.
  - Fills null values with a configurable placeholder.

Configuration keys (modules.example in config.yaml):
  enabled         bool   Whether this module is active (default: true).
  null_placeholder str   Value used to fill nulls   (default: "N/A").
"""

from typing import Any, List

from prism.module_base import IssueReport, ModuleResult, PrismModule


class ExampleModule(PrismModule):
    """
    Example Prism module: detects and fills null values.

    Stateless except for config.  Deterministic.  Config-driven.
    """

    name: str = "example"

    def __init__(self, config: dict, logger: Any) -> None:
        super().__init__(config, logger)
        self._placeholder: str = str(config.get("null_placeholder", "N/A"))

    # ------------------------------------------------------------------
    # detect
    # ------------------------------------------------------------------

    def detect(self, dataset: Any) -> IssueReport:
        """
        Scan *dataset* for null / None values without mutating it.

        Accepts a list-of-dicts, a list-of-lists, or None.
        """
        report = IssueReport()

        if dataset is None:
            report.add("Dataset is None", issue_type="missing_dataset")
            self.logger.colour_log(
                "!warn ExampleModule.detect: dataset is None",
            )
            return report

        rows = dataset if isinstance(dataset, list) else []
        for idx, row in enumerate(rows):
            values = row.values() if isinstance(row, dict) else row
            for val in values:
                if val is None:
                    report.add(
                        f"Null value found in row {idx}",
                        issue_type="null_value",
                    )

        if report.passed:
            self.logger.colour_log(
                "!done ExampleModule.detect: no issues found.",
            )
        else:
            self.logger.colour_log(
                "!warn ExampleModule.detect: issues=", len(report.issues),
            )

        return report

    # ------------------------------------------------------------------
    # run
    # ------------------------------------------------------------------

    def run(self, dataset: Any) -> ModuleResult:
        """
        Replace None values in *dataset* with the configured placeholder.

        Returns a ModuleResult containing the transformed dataset and a
        changelog of applied changes.
        """
        result = ModuleResult(dataset=dataset)

        if dataset is None:
            result.success = False
            result.error = "Dataset is None; nothing to process."
            self.logger.colour_log(
                "!error ExampleModule.run: dataset is None",
            )
            return result

        if not isinstance(dataset, list):
            result.record("Dataset type not supported; returned unchanged.")
            return result

        filled = 0
        for idx, row in enumerate(dataset):
            if isinstance(row, dict):
                for key, val in row.items():
                    if val is None:
                        row[key] = self._placeholder
                        filled += 1
                        result.record(
                            f"Row {idx}: field {key!r} filled with {self._placeholder!r}"
                        )
            elif isinstance(row, list):
                for col, val in enumerate(row):
                    if val is None:
                        row[col] = self._placeholder
                        filled += 1
                        result.record(
                            f"Row {idx}: column {col} filled with {self._placeholder!r}"
                        )

        self.logger.colour_log(
            "!done ExampleModule.run: filled", filled, "null values.",
        )
        return result
