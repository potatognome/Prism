#!/usr/bin/env python3
"""
prism/module_base.py - Prism Module Interface Contract

All Prism modules must subclass PrismModule and implement:
  detect(dataset)  -> IssueReport
  run(dataset)     -> ModuleResult

Modules must be:
  - Stateless except for config
  - Deterministic
  - Logging through tUilKit
  - Config-driven
  - Drop-in replaceable
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class IssueReport:
    """
    Result returned by Module.detect().

    Attributes:
        issues:  List of detected issue descriptions.
        counts:  Mapping of issue-type → count.
        passed:  True when no issues were found.
    """
    issues: List[str] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Return True when detect() found no issues."""
        return len(self.issues) == 0

    def add(self, issue: str, issue_type: str = "general") -> None:
        """Register one issue and increment its type counter."""
        self.issues.append(issue)
        self.counts[issue_type] = self.counts.get(issue_type, 0) + 1

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"IssueReport(passed={self.passed}, "
            f"issues={len(self.issues)}, counts={self.counts})"
        )


@dataclass
class ModuleResult:
    """
    Result returned by Module.run().

    Attributes:
        dataset:    The (possibly transformed) dataset.
        changelog:  Human-readable list of changes applied.
        success:    True when the run completed without errors.
        error:      Optional error message on failure.
    """
    dataset: Any = None
    changelog: List[str] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None

    def record(self, change: str) -> None:
        """Append a changelog entry."""
        self.changelog.append(change)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ModuleResult(success={self.success}, "
            f"changes={len(self.changelog)})"
        )


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class PrismModule(ABC):
    """
    Abstract base class for all Prism modules.

    Subclasses receive:
        config  — module-specific config slice (dict)
        logger  — tUilKit logger instance

    They must implement:
        detect(dataset) -> IssueReport
        run(dataset)    -> ModuleResult
    """

    #: Unique identifier for this module (override in subclass).
    name: str = "unnamed"

    def __init__(self, config: Dict, logger: Any) -> None:
        self.config = config
        self.logger = logger
        self.enabled: bool = bool(config.get("enabled", True))

    @abstractmethod
    def detect(self, dataset: Any) -> IssueReport:
        """
        Inspect *dataset* for issues without mutating it.

        Returns an IssueReport describing what was found.
        """

    @abstractmethod
    def run(self, dataset: Any) -> ModuleResult:
        """
        Apply this module's transformations to *dataset*.

        Returns a ModuleResult containing the (possibly mutated)
        dataset and a changelog of applied changes.
        """

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}(name={self.name!r}, enabled={self.enabled})"
