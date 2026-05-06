"""Protocol defining the interface every language analyzer must satisfy."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from spartastruct.analyzer.base import AnalysisResult


class BaseAnalyzer(Protocol):
    """Every language analyzer must implement this interface."""

    def analyze(
        self,
        files: list[Path],
        warnings: list[str] | None = None,
    ) -> AnalysisResult:
        """Analyze a list of source files and return a complete AnalysisResult."""
        ...
