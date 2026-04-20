#!/usr/bin/env python3
"""
prism/run_summary.py - Prism Run Summary Builder

Collects per-module results and emits a structured run summary
via tUilKit logging.  The summary is also returned as a plain
dict so callers can serialise or display it however they need.
"""

import datetime
from datetime import timezone
from typing import Any, Dict, List, Optional

from prism.module_base import IssueReport, ModuleResult


# ---------------------------------------------------------------------------
# Per-module record
# ---------------------------------------------------------------------------

class ModuleRecord:
    """Tracks the detect + run outcome for a single module execution."""

    def __init__(self, module_name: str) -> None:
        self.module_name: str = module_name
        self.skipped: bool = False
        self.dry_run: bool = False
        self.issue_report: Optional[IssueReport] = None
        self.result: Optional[ModuleResult] = None
        self.error: Optional[str] = None

    @property
    def success(self) -> bool:
        """True when the module ran without error."""
        if self.skipped:
            return True
        if self.error:
            return False
        if self.result is not None:
            return self.result.success
        return True

    def to_dict(self) -> Dict:
        """Serialise this record to a plain dict."""
        issues = []
        issue_counts: Dict = {}
        changelog: List[str] = []
        if self.issue_report:
            issues = list(self.issue_report.issues)
            issue_counts = dict(self.issue_report.counts)
        if self.result:
            changelog = list(self.result.changelog)
        return {
            "module": self.module_name,
            "skipped": self.skipped,
            "dry_run": self.dry_run,
            "success": self.success,
            "error": self.error,
            "issues_found": len(issues),
            "issue_counts": issue_counts,
            "changes_applied": len(changelog),
            "changelog": changelog,
        }


# ---------------------------------------------------------------------------
# Run summary
# ---------------------------------------------------------------------------

class RunSummary:
    """
    Accumulates per-module records and produces a final unified summary.

    Usage::

        summary = RunSummary(run_id="prism-001", dry_run=False)
        record = summary.begin_module("example")
        record.issue_report = IssueReport(...)
        record.result = ModuleResult(...)
        summary.end_module(record)
        data = summary.finalise(logger)
    """

    def __init__(self, run_id: str, dry_run: bool = False) -> None:
        self.run_id: str = run_id
        self.dry_run: bool = dry_run
        self.started_at: datetime.datetime = datetime.datetime.now(timezone.utc)
        self.finished_at: Optional[datetime.datetime] = None
        self._records: List[ModuleRecord] = []

    # ------------------------------------------------------------------
    # Record lifecycle
    # ------------------------------------------------------------------

    def begin_module(self, module_name: str) -> ModuleRecord:
        """Create and return a new ModuleRecord for the named module."""
        return ModuleRecord(module_name)

    def end_module(self, record: ModuleRecord) -> None:
        """Commit a completed ModuleRecord to the summary."""
        self._records.append(record)

    # ------------------------------------------------------------------
    # Finalisation
    # ------------------------------------------------------------------

    def finalise(self, logger: Any) -> Dict:
        """
        Mark the run as complete, emit the summary via *logger*, and
        return a plain dict representation.
        """
        self.finished_at = datetime.datetime.now(timezone.utc)
        data = self._build_dict()
        self._emit(logger, data)
        return data

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_dict(self) -> Dict:
        elapsed: Optional[float] = None
        if self.finished_at:
            elapsed = (self.finished_at - self.started_at).total_seconds()
        module_summaries = [r.to_dict() for r in self._records]
        total = len(self._records)
        skipped = sum(1 for r in self._records if r.skipped)
        failed = sum(1 for r in self._records if not r.success)
        passed = total - skipped - failed
        return {
            "run_id": self.run_id,
            "dry_run": self.dry_run,
            "started_at": self.started_at.isoformat() + "Z",
            "finished_at": (
                self.finished_at.isoformat() + "Z" if self.finished_at else None
            ),
            "elapsed_seconds": elapsed,
            "modules": {
                "total": total,
                "passed": passed,
                "skipped": skipped,
                "failed": failed,
            },
            "module_results": module_summaries,
        }

    def _emit(self, logger: Any, data: Dict) -> None:
        """Emit the summary to the tUilKit logger (no print())."""
        log_files: List[str] = []
        try:
            log_files = list(
                logger._log_files.values()  # type: ignore[attr-defined]
            )
        except AttributeError:
            pass

        summary = data["modules"]
        logger.colour_log(
            "!rainbow <O>", spacer=5,
            log_files=log_files,
        )
        logger.colour_log(
            "!info Prism Run Summary !data",
            f"run_id={data['run_id']!r}",
            log_files=log_files,
        )
        logger.colour_log(
            "!date started=", data["started_at"],
            "!date finished=", data.get("finished_at", "N/A"),
            log_files=log_files,
        )
        logger.colour_log(
            "!info Modules:",
            "!done passed=", summary["passed"],
            "!warn skipped=", summary["skipped"],
            "!error failed=", summary["failed"],
            log_files=log_files,
        )
        for rec in data["module_results"]:
            status = "!done" if rec["success"] else "!error"
            tag = " [DRY RUN]" if rec["dry_run"] else ""
            tag += " [SKIPPED]" if rec["skipped"] else ""
            logger.colour_log(
                status,
                f"  {rec['module']}{tag}",
                "!info issues=", rec["issues_found"],
                "!info changes=", rec["changes_applied"],
                log_files=log_files,
            )
        logger.colour_log("!rainbow <O>", spacer=5, log_files=log_files)
